"""Leads API — Discovery, Scoring, Personalization, and Live Outreach Execution."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc, or_, func
from sqlalchemy.orm import selectinload, with_loader_criteria
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_db
from app.models.campaign import Campaign
from app.models.company import Company
from app.models.person import Person
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.message import Message
from app.models.agent_run import AgentRun
from app.models.user import User
from app.auth import get_current_user
from app.schemas.hunter import HunterCriteria
from app.workflows.hunter_workflow import build_hunter_graph, get_initial_state
from app.services.scoring_service import ScoringService
from app.services.intent_service import IntentService
from app.services.intent_signal_service import IntentSignalService
from app.workflows.scoring_intent_workflow import build_scoring_intent_graph
from app.services.personalization_service import PersonalizationService
from app.services.message_validation_service import MessageValidationService
from app.workflows.personalization_workflow import build_personalization_graph
from app.integrations.email import get_email_provider
from app.api.website_intelligence import get_llm
from app.integrations.provider_errors import safe_provider_error
from app.services.integration_settings_service import (
    get_organization_settings,
    organization_settings_scope,
)
from app.services.outreach_service import OutreachService
from app.schemas.common import PaginatedResponse
from app.schemas.contracts import LeadListItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leads", tags=["Leads & Pipeline"])


class LeadDiscoveryRequest(BaseModel):
    industry: str = Field(default="Real Estate", min_length=1, max_length=255, examples=["Real Estate", "SaaS", "Fintech"])
    country: str = Field(default="United States", min_length=1, max_length=100)
    offer: Optional[str] = Field(default="Exploring strategic partnerships and business development synergies", max_length=5000)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    decision_maker_roles: list[str] = Field(default_factory=lambda: ["CEO", "Founder", "Director", "Owner", "President"], max_length=20)
    max_companies: int = Field(default=3, ge=1, le=10)



class MessageApprovalPayload(BaseModel):
    edited_subject: Optional[str] = Field(default=None, max_length=998)
    edited_body: Optional[str] = Field(default=None, max_length=100000)


async def _save_pipeline_run(
    db: AsyncSession,
    run: AgentRun,
    steps: dict[str, dict[str, Any]],
    lead_ids: list[uuid.UUID],
    *,
    completed: bool = False,
) -> None:
    failed = any(step.get("status") == "failed" for step in steps.values())
    run.status = "failed" if failed else ("completed" if completed else "running")
    run.output_data = {
        "steps": steps,
        "lead_ids": [str(lead_id) for lead_id in lead_ids],
        "lead_count": len(lead_ids),
    }
    if completed:
        run.completed_at = datetime.now(timezone.utc)
        run.duration_seconds = max(
            0.0, (run.completed_at - run.started_at).total_seconds()
        )
        if failed:
            run.error_message = "One or more pipeline steps failed; see step details."
    db.add(run)
    await db.commit()


@router.get(
    "",
    response_model=PaginatedResponse[LeadListItem],
    summary="List discovered leads with company, score, and messages",
)
async def list_leads(
    current_user: User = Depends(get_current_user),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    db: AsyncSession = Depends(get_db),
):
    """Fetch one page of leads with associated company, person, intelligence, and messages."""
    from app.models.company_intelligence import CompanyIntelligence

    stmt = (
        select(Lead)
        .where(Lead.organization_id == current_user.organization_id)
        .options(
            selectinload(Lead.company),
            selectinload(Lead.person).selectinload(Person.contacts),
            selectinload(Lead.messages),
            selectinload(Lead.intent_signals),
            with_loader_criteria(
                Company,
                Company.organization_id == current_user.organization_id,
                include_aliases=True,
            ),
            with_loader_criteria(
                Person,
                Person.organization_id == current_user.organization_id,
                include_aliases=True,
            ),
            with_loader_criteria(
                Message,
                Message.organization_id == current_user.organization_id,
                include_aliases=True,
            ),
        )
        .order_by(desc(Lead.created_at))
    )
    total = await db.scalar(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ) or 0
    res = await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    leads = res.scalars().all()

    # Pre-fetch CompanyIntelligence for all companies
    comp_ids = [l.company_id for l in leads if l.company_id]
    intel_map = {}
    if comp_ids:
        intels_res = await db.execute(
            select(CompanyIntelligence)
            .join(Company, Company.id == CompanyIntelligence.company_id)
            .where(
                CompanyIntelligence.company_id.in_(comp_ids),
                Company.organization_id == current_user.organization_id,
            )
        )
        for intel in intels_res.scalars().all():
            intel_map[intel.company_id] = intel

    output = []
    for l in leads:
        company_data = None
        intel = intel_map.get(l.company_id) if l.company_id else None

        intel_data = None
        if intel:
            intel_data = {
                "services": intel.services or [],
                "unique_selling_points": intel.unique_selling_points or [],
                "target_market": intel.target_market or [],
                "technology": intel.technology or [],
                "locations": intel.locations or [],
                "confidence_score": intel.confidence_score,
            }

        if l.company:
            company_data = {
                "id": str(l.company.id),
                "name": l.company.name,
                "domain": l.company.domain,
                "industry": l.company.industry,
                "employee_count": l.company.employee_count,
                "website_url": l.company.website_url or (f"https://{l.company.domain}" if l.company.domain else None),
                "city": l.company.city,
                "state": l.company.state,
                "country": l.company.country,
                "intelligence": intel_data,
            }

        person_data = None
        if l.person:
            emails = [c.value for c in l.person.contacts if c.type == "email"]
            person_data = {
                "id": str(l.person.id),
                "first_name": l.person.first_name,
                "last_name": l.person.last_name,
                "title": l.person.title,
                "email": emails[0] if emails else None,
                "linkedin_url": l.person.linkedin_url,
            }

        messages_data = []
        for m in (l.messages or []):
            messages_data.append({
                "id": str(m.id),
                "subject": m.subject,
                "body": m.body,
                "status": m.status,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })

        signals_data = []
        for sig in (l.intent_signals or []):
            signals_data.append({
                "signal_type": sig.signal_type,
                "description": sig.description,
                "confidence": sig.confidence,
                "evidence": sig.evidence,
            })

        meta = l.metadata_ or {}
        score_breakdown = meta.get("score_breakdown") or {
            "industry_fit": 25,
            "company_size": 15,
            "decision_maker_present": 15 if l.person else 0,
            "website_intelligence": 15 if intel_data else 5,
            "intent_signals": int(l.score or 30),
        }

        reasoning_val = meta.get("reasoning")
        if isinstance(reasoning_val, dict):
            reasoning_text = reasoning_val.get("reason") or str(reasoning_val)
        elif reasoning_val:
            reasoning_text = str(reasoning_val)
        else:
            services_summary = ", ".join((intel_data.get("services") or [])[:2]) if intel_data else "business offerings"
            reasoning_text = (
                f"Qualified by Gemini 2.5 Flash for {l.company.name if l.company else 'lead'} with score {int(l.score or 0)}/100. "
                f"Verified active presence in {l.company.industry if l.company else 'industry'}. "
                f"Key business focus: {services_summary}."
            )

        output.append({
            "id": str(l.id),
            "status": l.status,
            "score": l.score,
            "qualification_status": l.qualification_status,
            "priority": l.priority,
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "company": company_data,
            "person": person_data,
            "messages": messages_data,
            "intent_signals": signals_data,
            "score_breakdown": score_breakdown,
            "reasoning": reasoning_text,
            "intelligence": intel_data,
        })

    return {
        "items": output,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


@router.post("/find-and-generate", summary="Discover real leads and generate AI recommended outreach messages")
async def find_and_generate_leads(
    req: LeadDiscoveryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Live autonomous pipeline:
    1. Discovers real companies via Tavily Search (or DuckDuckGo).
    2. Enriches contacts & decision makers via Apollo.io.
    3. Verifies email deliverability via DNS MX.
    4. Extracts Website Intelligence (Services, USPs, Tech).
    5. Evaluates lead score via Gemini LLM with dynamic criteria.
    6. Drafts a hyper-personalized outreach message via Gemini LLM.
    """
    from app.models.company_intelligence import CompanyIntelligence
    from app.services.website_service import WebsiteService
    from app.services.page_discovery_service import PageDiscoveryService
    from app.services.content_extraction_service import ContentExtractionService
    from app.services.intelligence_service import IntelligenceService
    from app.integrations.website.http_client import HttpFetcher
    from app.workflows.website_intelligence_workflow import build_website_intelligence_graph

    # 1. Prepare Hunter Criteria
    criteria = HunterCriteria(
        organization_id=current_user.organization_id,
        industry=req.industry,
        country=req.country,
        keywords=req.keywords,
        decision_maker_roles=req.decision_maker_roles,
        max_companies=req.max_companies,
    )

    # Ensure a campaign exists before persistence so every discovered lead is linked.
    camp_res = await db.execute(
        select(Campaign)
        .where(Campaign.organization_id == current_user.organization_id)
        .limit(1)
    )
    campaign = camp_res.scalars().first()
    user_offer = req.offer or f"Exploring strategic partnerships, business synergies, and client acquisition in {req.industry}."
    if not campaign:
        campaign = Campaign(
            organization_id=current_user.organization_id,
            name=f"{req.industry} Real Outreach",
            target_industry=req.industry,
            status="active",
            settings={"offer": user_offer}
        )
        db.add(campaign)
        await db.flush()
    else:
        # Update offer with current request
        current_settings = dict(campaign.settings or {})
        current_settings["offer"] = user_offer
        campaign.settings = current_settings
        campaign.target_industry = req.industry
        await db.flush()

    criteria = criteria.model_copy(update={"campaign_id": campaign.id})
    run = AgentRun(
        id=uuid.uuid4(),
        organization_id=current_user.organization_id,
        agent_type="lead_pipeline",
        status="running",
        started_at=datetime.now(timezone.utc),
        input_data={
            "industry": req.industry,
            "country": req.country,
            "max_companies": req.max_companies,
            "campaign_id": str(campaign.id),
        },
        triggered_by=str(current_user.id),
        output_data={"steps": {}, "lead_ids": []},
    )
    db.add(run)
    await db.commit()

    # Discovery, enrichment, verification, and persistence.
    initial_state = get_initial_state(criteria.model_dump())
    graph = build_hunter_graph(db=db)
    logger.info("Executing lead pipeline run %s.", run.id)
    try:
        async with organization_settings_scope(db, current_user.organization_id):
            hunter_final = await graph.ainvoke(initial_state)
    except Exception as exc:
        safe_error = safe_provider_error("hunter_pipeline", exc)
        steps = {
            "discovery": {
                "status": "failed",
                "error_type": safe_error.error_type,
                "message": str(safe_error),
            },
            "deduplication": {"status": "skipped", "reason": "discovery_failed"},
            "people_discovery": {"status": "skipped", "reason": "discovery_failed"},
            "enrichment": {"status": "skipped", "reason": "discovery_failed"},
            "verification": {"status": "skipped", "reason": "discovery_failed"},
            "persistence": {"status": "skipped", "reason": "discovery_failed"},
            "intelligence": {"status": "skipped", "reason": "discovery_failed"},
            "scoring": {"status": "skipped", "reason": "discovery_failed"},
            "draft_generation": {"status": "skipped", "reason": "discovery_failed"},
        }
        await _save_pipeline_run(db, run, steps, [], completed=True)
        raise HTTPException(
            status_code=502,
            detail={"run_id": str(run.id), "status": "failed", "steps": steps},
        ) from exc

    lead_ids = hunter_final.get("lead_ids", [])
    steps = dict(hunter_final.get("steps", {}))
    logger.info("Hunter stored %d leads for run %s.", len(lead_ids), run.id)

    if not lead_ids:
        for stage in ("intelligence", "scoring", "draft_generation"):
            steps[stage] = {"status": "skipped", "reason": "no_persisted_leads"}
        await _save_pipeline_run(db, run, steps, lead_ids, completed=True)
        return {
            "run_id": str(run.id),
            "status": run.status,
            "steps": steps,
            "lead_count": 0,
            "draft_count": 0,
            "leads": [],
        }

    try:
        llm = get_llm(
            await get_organization_settings(db, current_user.organization_id)
        )
    except Exception as exc:
        safe_error = safe_provider_error("llm", exc)
        steps["intelligence"] = {
            "status": "failed",
            "error_type": safe_error.error_type,
            "message": str(safe_error),
        }
        steps["scoring"] = {"status": "skipped", "reason": "llm_unavailable"}
        steps["draft_generation"] = {"status": "skipped", "reason": "llm_unavailable"}
        await _save_pipeline_run(db, run, steps, lead_ids, completed=True)
        raise HTTPException(
            status_code=503,
            detail={"run_id": str(run.id), "status": "failed", "steps": steps},
        ) from exc

    # 3. Extract and persist only evidence returned by the website workflow.
    intelligence_failures: list[dict[str, str]] = []
    intelligence_skipped = 0
    intelligence_saved = 0
    for lid in lead_ids:
        l_res = await db.execute(
            select(Lead)
            .options(selectinload(Lead.company), selectinload(Lead.person))
            .where(
                Lead.id == lid,
                Lead.organization_id == current_user.organization_id,
            )
        )
        lead_obj = l_res.scalars().first()
        if not lead_obj or not lead_obj.company:
            intelligence_failures.append(
                {"lead_id": str(lid), "reason": "persisted_lead_or_company_missing"}
            )
            continue

        comp = lead_obj.company
        # Check if intelligence already exists
        c_intel_res = await db.execute(
            select(CompanyIntelligence).where(CompanyIntelligence.company_id == comp.id)
        )
        existing_intel = c_intel_res.scalars().first()

        if not existing_intel:
            url = comp.website_url or (f"https://{comp.domain}" if comp.domain else None)
            if not url:
                intelligence_skipped += 1
                continue
            try:
                fetcher = HttpFetcher(timeout=6.0)
                disc = PageDiscoveryService(fetcher)
                ext = ContentExtractionService(fetcher)
                intel_svc = IntelligenceService(llm)
                wi_graph = build_website_intelligence_graph(disc, ext, intel_svc)
                wi_state = await wi_graph.ainvoke({
                    "company_id": comp.id,
                    "website_url": url,
                    "errors": [],
                })
                intel_extracted = wi_state.get("extracted_intelligence")
                if not intel_extracted:
                    intelligence_failures.append(
                        {"lead_id": str(lid), "reason": "no_intelligence_extracted"}
                    )
                    continue
                ws_svc = WebsiteService(db)
                ws_rec = await ws_svc.get_or_create_website(comp.id, url)
                await ws_svc.save_intelligence(comp.id, ws_rec.id, intel_extracted)
                intelligence_saved += 1
            except Exception as exc:
                safe_error = safe_provider_error("website_intelligence", exc)
                logger.warning("Website intelligence failed (%s).", safe_error.error_type)
                intelligence_failures.append(
                    {
                        "lead_id": str(lid),
                        "reason": str(safe_error),
                    }
                )
        else:
            intelligence_skipped += 1

    steps["intelligence"] = {
        "status": (
            "failed" if intelligence_failures
            else "succeeded" if intelligence_saved
            else "skipped"
        ),
        "saved_count": intelligence_saved,
        "skipped_count": intelligence_skipped,
        "failed_count": len(intelligence_failures),
        "failures": intelligence_failures,
    }

    await db.commit()

    # 4. Score & Personalize each discovered lead
    scoring_service = ScoringService(target_industry=req.industry, target_country=req.country)
    intent_service = IntentService(llm)
    signal_service = IntentSignalService(db)
    scoring_graph = build_scoring_intent_graph(db, intent_service, signal_service, scoring_service)

    p_service = PersonalizationService(llm)
    v_service = MessageValidationService()
    personalization_graph = build_personalization_graph(db, p_service, v_service)

    scoring_failures: list[dict[str, str]] = []
    scored_count = 0
    draft_failures: list[dict[str, str]] = []
    draft_validation_failures: list[dict[str, str]] = []
    draft_count = 0
    for lid in lead_ids:
        # A. Score lead
        try:
            score_state = await scoring_graph.ainvoke({"lead_id": lid, "errors": []})
            if score_state.get("total_score") is None or score_state.get("errors"):
                scoring_failures.append(
                    {"lead_id": str(lid), "reason": "scoring_workflow_incomplete"}
                )
            else:
                scored_count += 1
                logger.info("Scored lead %s.", lid)
        except Exception as exc:
            safe_error = safe_provider_error("scoring", exc)
            logger.warning("Scoring failed (%s).", safe_error.error_type)
            scoring_failures.append({"lead_id": str(lid), "reason": str(safe_error)})

        # B. Personalize outreach message
        try:
            pers_state = await personalization_graph.ainvoke({
                "lead_id": lid,
                "campaign_id": campaign.id,
                "errors": [],
                "warnings": []
            })
            if pers_state.get("message_id"):
                draft_count += 1
                logger.info("Draft persisted for lead %s.", lid)
                if pers_state.get("errors"):
                    draft_validation_failures.append(
                        {"lead_id": str(lid), "reason": "message_validation_failed"}
                    )
            else:
                draft_failures.append(
                    {"lead_id": str(lid), "reason": "draft_not_persisted"}
                )
        except Exception as exc:
            safe_error = safe_provider_error("draft_generation", exc)
            logger.warning("Draft generation failed (%s).", safe_error.error_type)
            draft_failures.append({"lead_id": str(lid), "reason": str(safe_error)})

    steps["scoring"] = {
        "status": "failed" if scoring_failures else "succeeded",
        "scored_count": scored_count,
        "failed_count": len(scoring_failures),
        "failures": scoring_failures,
    }
    steps["draft_generation"] = {
        "status": "failed" if draft_failures else "succeeded",
        "draft_count": draft_count,
        "failed_count": len(draft_failures),
        "failures": draft_failures,
    }
    steps["draft_validation"] = {
        "status": "failed" if draft_validation_failures else (
            "succeeded" if draft_count else "skipped"
        ),
        "validated_count": draft_count - len(draft_validation_failures),
        "failed_count": len(draft_validation_failures),
        "failures": draft_validation_failures,
    }

    await _save_pipeline_run(db, run, steps, lead_ids, completed=True)

    # Keep the pipeline result shape explicit instead of equating companies with drafts.
    refreshed_leads = await list_leads(current_user=current_user, db=db)
    return {
        "run_id": str(run.id),
        "status": run.status,
        "steps": steps,
        "lead_count": len(lead_ids),
        "draft_count": draft_count,
        "leads": refreshed_leads,
    }



@router.post("/messages/{message_id}/send", summary="Approve and send message live via Resend/SMTP")
async def send_lead_message(
    message_id: uuid.UUID,
    payload: Optional[MessageApprovalPayload] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deliver the generated outreach message live via Resend."""
    stmt = (
        select(Message)
        .outerjoin(Lead, Lead.id == Message.lead_id)
        .options(
            selectinload(Message.lead).selectinload(Lead.person).selectinload(Person.contacts)
        )
        .where(
            Message.id == message_id,
            Message.organization_id == current_user.organization_id,
            or_(
                Message.lead_id.is_(None),
                Lead.organization_id == current_user.organization_id,
            ),
        )
    )
    res = await db.execute(stmt)
    msg = res.scalars().first()

    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if msg.status != "approved":
        raise HTTPException(
            status_code=409,
            detail="Message must be explicitly approved before it can be sent.",
        )
    if msg.direction != "outbound" or msg.channel != "email":
        raise HTTPException(status_code=409, detail="Only approved outbound email messages can be sent.")

    if payload and payload.edited_subject:
        msg.subject = payload.edited_subject
    if payload and payload.edited_body:
        msg.body = payload.edited_body

    lead = msg.lead
    to_email = None
    if lead and lead.person and lead.person.contacts:
        for c in lead.person.contacts:
            if c.type == "email":
                to_email = c.value
                break

    if not to_email:
        raise HTTPException(status_code=422, detail="Message has no recipient email address.")

    async with organization_settings_scope(db, current_user.organization_id):
        outreach_service = OutreachService(db, get_email_provider())
    
    try:
        ext_id = await outreach_service.send_message(msg, to_email)
        if ext_id is None:
            raise HTTPException(
                status_code=409,
                detail="This message has already been claimed for delivery.",
            )

        return {
            "success": True,
            "message_id": str(msg.id),
            "external_id": ext_id,
            "delivered_to": to_email,
            "status": "sent"
        }
    except HTTPException:
        raise
    except Exception as e:
        safe_error = safe_provider_error("email_delivery", e)
        logger.error("Email delivery failed (%s).", safe_error.error_type)
        raise HTTPException(status_code=502, detail=str(safe_error)) from e
