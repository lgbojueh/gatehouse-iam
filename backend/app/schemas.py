from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: str
    active: bool
    created_at: datetime


class RoleUpdate(BaseModel):
    role: str


class AuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_user_id: int | None
    event_type: str
    target: str
    detail: str
    created_at: datetime
