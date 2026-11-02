from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import UserRole


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    role: UserRole


class LoginResponse(BaseModel):
    user: UserResponse
