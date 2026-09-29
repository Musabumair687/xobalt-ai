import uuid
from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class LeadStatusEnum(str, Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    unqualified = "unqualified"
    converted = "converted"
    lost = "lost"

class LeadBase(BaseModel):
    status: LeadStatusEnum = Field(default=LeadStatusEnum.new)
    score: Optional[int] = Field(default=None, ge=0, le=100)
    qualification_status: str = "unqualified"
    priority: str = "medium"
    notes: Optional[str] = None

class LeadCreate(LeadBase):
    organization_id: uuid.UUID
    person_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None

class LeadUpdate(BaseModel):
    status: Optional[LeadStatusEnum] = None
    score: Optional[int] = Field(default=None, ge=0, le=100)
    qualification_status: Optional[str] = None
    priority: Optional[str] = None
    notes: Optional[str] = None

class LeadResponse(LeadBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    person_id: Optional[uuid.UUID] = None
    company_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
    page: int
    size: int
