"""
User Pydantic schemas for AquaShield AI.

Defines schemas for user creation, update, and serialized responses.
CRITICAL: password_hash is strictly excluded from all response schemas.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

AllowedRole = Literal[
    "Administrator",
    "Engineer",
    "Maintenance Officer",
    "Field Inspector",
    "Utility Manager",
]


class UserCreate(BaseModel):
    """Payload for creating a new authority user."""

    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: AllowedRole


class UserUpdate(BaseModel):
    """Payload for updating user name or email.

    Strict: extra fields (role, password_hash, created_at, etc.) are forbidden.
    """

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1)
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """Public representation of an authority user.

    CRITICAL: password_hash is intentionally omitted.
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    email: str
    role: str
    created_at: datetime


class UserListResponse(BaseModel):
    """Collection response for user listings."""

    users: list[UserResponse]
    total: int

