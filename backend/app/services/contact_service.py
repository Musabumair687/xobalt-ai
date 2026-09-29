import uuid
from typing import Optional, Sequence
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactUpdate

async def create_contact(db: AsyncSession, data: ContactCreate) -> Contact:
    db_obj = Contact(**data.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_contact(db: AsyncSession, id: uuid.UUID) -> Optional[Contact]:
    result = await db.execute(select(Contact).where(Contact.id == id))
    return result.scalar_one_or_none()

async def get_contacts_for_person(db: AsyncSession, person_id: uuid.UUID) -> Sequence[Contact]:
    result = await db.execute(select(Contact).where(Contact.person_id == person_id))
    return result.scalars().all()

async def update_contact(db: AsyncSession, id: uuid.UUID, data: ContactUpdate) -> Optional[Contact]:
    db_obj = await get_contact(db, id)
    if not db_obj:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(db_obj, key, value)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def verify_contact(db: AsyncSession, id: uuid.UUID, provider: str) -> Optional[Contact]:
    db_obj = await get_contact(db, id)
    if not db_obj:
        return None
    db_obj.is_verified = True
    db_obj.verification_provider = provider
    db_obj.verified_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_contact(db: AsyncSession, id: uuid.UUID) -> bool:
    db_obj = await get_contact(db, id)
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.commit()
    return True

async def get_primary_email(db: AsyncSession, person_id: uuid.UUID) -> Optional[Contact]:
    result = await db.execute(select(Contact).where(Contact.person_id == person_id, Contact.type == "email", Contact.is_primary == True))
    return result.scalar_one_or_none()
