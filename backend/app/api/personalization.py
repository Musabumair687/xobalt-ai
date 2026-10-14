"""API router for Phase 6 Personalization and Human Approval."""

import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.dependencies import get_db
from app.schemas.personalization import PersonalizationResult, ApprovalRequest, ApprovalResponse
from app.services.personalization_service import PersonalizationService
from app.services.message_validation_service import MessageValidationService
from app.services.approval_service import ApprovalService
from app.workflows.personalization_workflow import build_personalization_graph
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.message import Message
from app.models.user import User
from sqlalchemy import select
from app.auth import get_current_user
from app.integrations.provider_errors import safe_provider_error
from app.services.integration_settings_service import get_organization_settings

try:
    from app.api.website_intelligence import get_llm
except ImportError:
    def get_llm():
        from app.config import get_settings
        settings = get_settings()
        if settings.LLM_PROVIDER == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(api_key=settings.GROQ_API_KEY, model_name=settings.GROQ_MODEL)
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(google_api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/personalization", tags=["Personalization & Approval"])

@router.post(
    "/generate",
    response_model=PersonalizationResult,
    status_code=status.HTTP_200_OK
)
async def generate_personalization(
    lead_id: uuid.UUID,
    campaign_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Trigger the Personalization workflow for a specific lead and campaign."""
    owned = await db.execute(
        select(Lead.id, Campaign.id)
        .join(Campaign, Campaign.id == campaign_id)
        .where(
            Lead.id == lead_id,
            Lead.organization_id == current_user.organization_id,
            Campaign.organization_id == current_user.organization_id,
        )
    )
    if owned.first() is None:
        raise HTTPException(status_code=404, detail="Lead or campaign not found")

    try:
        llm = get_llm(
            await get_organization_settings(db, current_user.organization_id)
        )
    except Exception as e:
        logger.error(f"Failed to load LLM: {e}")
        raise HTTPException(status_code=500, detail="LLM configuration error")
        
    p_service = PersonalizationService(llm)
    v_service = MessageValidationService()
    
    graph = build_personalization_graph(db, p_service, v_service)
    
    initial_state = {
        "lead_id": lead_id, 
        "campaign_id": campaign_id,
        "errors": [],
        "warnings": []
    }
    
    try:
        final_state = await graph.ainvoke(initial_state)
        
        return PersonalizationResult(
            lead_id=lead_id,
            campaign_id=campaign_id,
            message_id=final_state.get("message_id"),
            status=final_state.get("approval_status", "draft"),
            validation_result=final_state.get("validation_result"),
            errors=final_state.get("errors", [])
        )
        
    except Exception as e:
        safe_error = safe_provider_error("personalization", e)
        logger.error("Personalization failed (%s).", safe_error.error_type)
        raise HTTPException(status_code=502, detail=str(safe_error)) from e


@router.post(
    "/messages/{message_id}/approve",
    response_model=ApprovalResponse,
    status_code=status.HTTP_200_OK
)
async def approve_message(
    message_id: uuid.UUID,
    request: ApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process a human approval action for a generated message."""
    owned_message = await db.execute(
        select(Message.id).where(
            Message.id == message_id,
            Message.organization_id == current_user.organization_id,
        )
    )
    if owned_message.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Message not found")

    approval_svc = ApprovalService(db)
    
    try:
        msg = await approval_svc.process_approval(
            message_id=message_id,
            action=request.action,
            edited_subject=request.edited_subject,
            edited_body=request.edited_body,
            reason=request.rejection_reason
        )
        
        return ApprovalResponse(
            message_id=msg.id,
            new_status=msg.status
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing approval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
