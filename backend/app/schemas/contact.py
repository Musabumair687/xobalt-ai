import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ContactBase(BaseModel):
    type: str
    value: str
    is_primary: bool = False

class ContactCreate(ContactBase):
    person_id: uuid.UUID

class ContactUpdate(BaseModel):
    type: Optional[str] = None
    value: Optional[str] = None
    is_primary: Optional[bool] = None

class ContactVerificationUpdate(BaseModel):
    is_verified: bool
    verification_provider: Optional[str] = None
    verified_at: Optional[datetime] = None

class ContactResponse(ContactBase):
    id: uuid.UUID
    person_id: uuid.UUID
    is_verified: bool
    verification_provider: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
