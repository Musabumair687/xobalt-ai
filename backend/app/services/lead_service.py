import uuid
from typing import Optional, Tuple, Sequence
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lead import Lead
from app.models.campaign_lead import CampaignLead
from app.schemas.lead import LeadCreate, LeadUpdate, LeadStatusEnum

async def create_lead(db: AsyncSession, data: LeadCreate) -> Lead:
    db_obj = Lead(**data.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_lead(db: AsyncSession, id: uuid.UUID) -> Optional[Lead]:
    result = await db.execute(select(Lead).where(Lead.id == id))
    return result.scalar_one_or_none()

async def list_leads(db: AsyncSession, org_id: uuid.UUID, status: Optional[LeadStatusEnum] = None, skip: int = 0, limit: int = 20) -> Tuple[Sequence[Lead], int]:
    query = select(Lead).where(Lead.organization_id == org_id)
    if status:
        query = query.where(Lead.status == status)
    
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()
    
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all(), total

async def update_lead(db: AsyncSession, id: uuid.UUID, data: LeadUpdate) -> Optional[Lead]:
    db_obj = await get_lead(db, id)
    if not db_obj:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, key, value)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_lead_score(db: AsyncSession, id: uuid.UUID, score: int) -> Optional[Lead]:
    db_obj = await get_lead(db, id)
    if not db_obj:
        return None
    db_obj.score = score
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_lead_status(db: AsyncSession, id: uuid.UUID, status: LeadStatusEnum) -> Optional[Lead]:
    db_obj = await get_lead(db, id)
    if not db_obj:
        return None
    db_obj.status = status
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_lead(db: AsyncSession, id: uuid.UUID) -> bool:
    db_obj = await get_lead(db, id)
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.commit()
    return True

async def get_leads_by_company(db: AsyncSession, company_id: uuid.UUID) -> Sequence[Lead]:
    result = await db.execute(select(Lead).where(Lead.company_id == company_id))
    return result.scalars().all()

async def get_leads_by_campaign(db: AsyncSession, campaign_id: uuid.UUID) -> Sequence[Lead]:
    query = select(Lead).join(CampaignLead, Lead.id == CampaignLead.lead_id).where(CampaignLead.campaign_id == campaign_id)
    result = await db.execute(query)
    return result.scalars().all()
