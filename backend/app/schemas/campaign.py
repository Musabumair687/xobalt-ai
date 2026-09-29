import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class CampaignBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "draft"
    target_industry: Optional[str] = None
    target_company_size_min: Optional[int] = None
    target_company_size_max: Optional[int] = None
    target_locations: Optional[list[str]] = None
    daily_limit: int = 30

class CampaignCreate(CampaignBase):
    organization_id: uuid.UUID
    created_by_id: Optional[uuid.UUID] = None

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    target_industry: Optional[str] = None
    target_company_size_min: Optional[int] = None
    target_company_size_max: Optional[int] = None
    target_locations: Optional[list[str]] = None
    daily_limit: Optional[int] = None

class CampaignResponse(CampaignBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    created_by_id: Optional[uuid.UUID] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]
    total: int
    page: int
    size: int
