from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

class MessageResponse(BaseModel):
    message: str
    success: bool = True

class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
