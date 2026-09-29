import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class PersonBase(BaseModel):
    first_name: str
    last_name: str
    title: Optional[str] = None
    department: Optional[str] = None
    seniority: Optional[str] = None
    linkedin_url: Optional[str] = None

class PersonCreate(PersonBase):
    organization_id: uuid.UUID
    company_id: Optional[uuid.UUID] = None

class PersonUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    seniority: Optional[str] = None
    linkedin_url: Optional[str] = None
    company_id: Optional[uuid.UUID] = None

class PersonResponse(PersonBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    company_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PersonListResponse(BaseModel):
    items: list[PersonResponse]
    total: int
    page: int
    size: int
