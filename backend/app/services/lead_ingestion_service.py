"""LeadIngestionService — transform Hunter output into PostgreSQL records.

This service is the only place that directly writes hunter data to the
database.  It converts DiscoveredCompany / DiscoveredPerson / VerificationResult
objects into ORM models and persists them.

Responsibilities
----------------
1. Upsert Company (by domain or name + org_id)
2. Upsert Person (by email or name + company_id)
3. Upsert Contact (by value + person_id)
4. Mark contact verification status from VerificationResult
5. Create Lead row
6. Optionally link lead to Campaign via CampaignLead
7. Create LeadSource audit record

Returns the list of new Lead UUIDs so the workflow can track them.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.lead_source import LeadSource as LeadSourceModel
from app.models.person import Person
from app.models.campaign_lead import CampaignLead
from app.schemas.hunter import (
    DiscoveredCompany,
    DiscoveredPerson,
    VerificationResult,
    VerificationStatus,
)
from app.services.deduplication_service import normalize_domain

logger = logging.getLogger(__name__)


class LeadIngestionService:
    """Persist Hunter output into Xobalt AI's PostgreSQL schema."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ingest(
        self,
        *,
        organization_id: uuid.UUID,
        campaign_id: Optional[uuid.UUID],
        company: DiscoveredCompany,
        people: list[DiscoveredPerson],
        verification_results: list[VerificationResult],
    ) -> list[uuid.UUID]:
        """Persist one company + its people as Leads and return their IDs."""
        lead_ids: list[uuid.UUID] = []

        # 1. Upsert company
        db_company = await self._upsert_company(organization_id, company)

        # Build a quick lookup: email → verification result
        verif_map = {vr.contact_value: vr for vr in verification_results}

        if not people:
            # No people found: create a company-only lead
            lead = await self._create_lead(
                organization_id=organization_id,
                campaign_id=campaign_id,
                company_id=db_company.id,
                person_id=None,
                source_name=company.source or "hunter",
            )
            lead_ids.append(lead.id)
        else:
            for person_data in people:
                db_person = await self._upsert_person(
                    organization_id, db_company.id, person_data
                )

                # Upsert email contact
                if person_data.email:
                    vr = verif_map.get(person_data.email)
                    await self._upsert_contact(db_person.id, person_data.email, vr)

                lead = await self._create_lead(
                    organization_id=organization_id,
                    campaign_id=campaign_id,
                    company_id=db_company.id,
                    person_id=db_person.id,
                    source_name=person_data.source or company.source or "hunter",
                )
                lead_ids.append(lead.id)

        await self._db.commit()
        logger.info(
            "Ingested company '%s' → %d lead(s).", company.name, len(lead_ids)
        )
        return lead_ids

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _upsert_company(
        self, organization_id: uuid.UUID, data: DiscoveredCompany
    ) -> Company:
        """Find existing company by domain or create a new one."""
        norm = normalize_domain(data.domain)

        if norm:
            result = await self._db.execute(
                select(Company).where(
                    Company.organization_id == organization_id,
                    Company.domain == norm,
                )
            )
            existing = result.scalar_one_or_none()
        else:
            result = await self._db.execute(
                select(Company).where(
                    Company.organization_id == organization_id,
                    Company.name == data.name,
                )
            )
            existing = result.scalar_one_or_none()

        if existing:
            # Opportunistically fill in blank fields
            changed = False
            for field in ("industry", "employee_count", "city", "state", "country",
                          "description", "linkedin_url", "website_url"):
                if getattr(existing, field) is None and getattr(data, field) is not None:
                    setattr(existing, field, getattr(data, field))
                    changed = True
            if changed:
                self._db.add(existing)
            return existing

        company = Company(
            organization_id=organization_id,
            name=data.name,
            domain=norm,
            website_url=data.website_url,
            industry=data.industry,
            employee_count=data.employee_count,
            city=data.city,
            state=data.state,
            country=data.country,
            description=data.description,
            linkedin_url=data.linkedin_url,
        )
        self._db.add(company)
        await self._db.flush()  # get company.id without committing
        return company

    async def _upsert_person(
        self,
        organization_id: uuid.UUID,
        company_id: uuid.UUID,
        data: DiscoveredPerson,
    ) -> Person:
        """Find existing person by email or create a new one."""
        # Try to find by email first (most reliable key)
        if data.email:
            result = await self._db.execute(
                select(Person)
                .join(Contact, Person.id == Contact.person_id)
                .where(Contact.value == data.email)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        # Fallback: name + company
        first_name = data.first_name or (data.full_name.split()[0] if data.full_name else "") or ""
        last_name = data.last_name or (" ".join(data.full_name.split()[1:]) if data.full_name else "") or ""

        if first_name or last_name:
            result = await self._db.execute(
                select(Person).where(
                    Person.company_id == company_id,
                    Person.first_name == first_name,
                    Person.last_name == last_name,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        person = Person(
            organization_id=organization_id,
            company_id=company_id,
            first_name=first_name or "Unknown",
            last_name=last_name or "Unknown",
            title=data.job_title,
            linkedin_url=data.linkedin_url,
        )
        self._db.add(person)
        await self._db.flush()
        return person

    async def _upsert_contact(
        self,
        person_id: uuid.UUID,
        email: str,
        verification: Optional[VerificationResult],
    ) -> Contact:
        """Create or update the email contact row for a person."""
        result = await self._db.execute(
            select(Contact).where(
                Contact.person_id == person_id,
                Contact.value == email,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if verification:
                existing.is_verified = verification.status == VerificationStatus.valid
                existing.verification_provider = verification.provider
            self._db.add(existing)
            return existing

        contact = Contact(
            person_id=person_id,
            type="email",
            value=email,
            is_primary=True,
            is_verified=verification.status == VerificationStatus.valid
            if verification
            else False,
            verification_provider=verification.provider if verification else None,
        )
        self._db.add(contact)
        await self._db.flush()
        return contact

    async def _create_lead(
        self,
        *,
        organization_id: uuid.UUID,
        campaign_id: Optional[uuid.UUID],
        company_id: uuid.UUID,
        person_id: Optional[uuid.UUID],
        source_name: str,
    ) -> Lead:
        """Create a new Lead row and optionally link it to a campaign."""
        lead = Lead(
            organization_id=organization_id,
            company_id=company_id,
            person_id=person_id,
            status="new",
        )
        self._db.add(lead)
        await self._db.flush()

        # LeadSource audit record
        source = LeadSourceModel(
            lead_id=lead.id,
            provider=source_name,
        )
        self._db.add(source)

        # Link to campaign if provided
        if campaign_id:
            cl = CampaignLead(
                campaign_id=campaign_id,
                lead_id=lead.id,
                status="pending",
            )
            self._db.add(cl)

        await self._db.flush()
        return lead
