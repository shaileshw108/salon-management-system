from datetime import datetime

from pydantic import BaseModel, Field

from .models import QueueStatus


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ServiceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    duration_minutes: int = Field(default=30, ge=1, le=480)
    description: str | None = Field(default=None, max_length=1000)


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
    status_token: str


class QueueStatusResponse(BaseModel):
    id: int
    token_number: int
    service_name: str
    status: QueueStatus
    joined_at: datetime


class GalleryCreate(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    image_url: str = Field(min_length=5, max_length=500)
    description: str | None = Field(default=None, max_length=1000)


class GalleryResponse(GalleryCreate):
    id: int
    is_active: bool
    model_config = {"from_attributes": True}


class QueueActionResponse(QueueResponse):
    pass
