import uuid
from typing import Optional, Tuple, Sequence
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate

async def create_company(db: AsyncSession, data: CompanyCreate) -> Company:
    db_obj = Company(**data.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_company(db: AsyncSession, id: uuid.UUID) -> Optional[Company]:
    result = await db.execute(select(Company).where(Company.id == id))
    return result.scalar_one_or_none()

async def get_company_by_domain(db: AsyncSession, domain: str, org_id: uuid.UUID) -> Optional[Company]:
    result = await db.execute(select(Company).where(Company.domain == domain, Company.organization_id == org_id))
    return result.scalar_one_or_none()

async def list_companies(db: AsyncSession, org_id: uuid.UUID, skip: int = 0, limit: int = 20) -> Tuple[Sequence[Company], int]:
    query = select(Company).where(Company.organization_id == org_id)
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()
    
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all(), total

async def update_company(db: AsyncSession, id: uuid.UUID, data: CompanyUpdate) -> Optional[Company]:
    db_obj = await get_company(db, id)
    if not db_obj:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, key, value)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_company(db: AsyncSession, id: uuid.UUID) -> bool:
    db_obj = await get_company(db, id)
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.commit()
    return True
