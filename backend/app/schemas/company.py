import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class CompanyBase(BaseModel):
    name: str
    domain: Optional[str] = None
    website_url: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = Field(default=None, ge=0)
    annual_revenue: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    founded_year: Optional[int] = None
    linkedin_url: Optional[str] = None

class CompanyCreate(CompanyBase):
    organization_id: uuid.UUID

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    website_url: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[int] = Field(default=None, ge=0)
    annual_revenue: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    founded_year: Optional[int] = None
    linkedin_url: Optional[str] = None

class CompanyResponse(CompanyBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CompanyListResponse(BaseModel):
    items: list[CompanyResponse]
    total: int
    page: int
    size: int
