from datetime import datetime

from pydantic import BaseModel, Field

from .models import QueueStatus


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ServiceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    duration_minutes: int = Field(default=30, ge=1, le=480)
    description: str | None = None


class ServiceResponse(ServiceCreate):
    id: int
    is_active: bool

    model_config = {"from_attributes": True}


class QueueJoinRequest(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=7, max_length=20)
    service_id: int


class QueueResponse(BaseModel):
    id: int
    token_number: int
    customer_name: str
    phone: str
    service_id: int
    service_name: str
    status: QueueStatus
    joined_at: datetime


class GalleryCreate(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    image_url: str = Field(min_length=5, max_length=500)
    description: str | None = None


class GalleryResponse(GalleryCreate):
    id: int
    is_active: bool

    model_config = {"from_attributes": True}
