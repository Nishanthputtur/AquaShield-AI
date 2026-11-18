"""
Authentication Pydantic schemas for AquaShield AI.
"""

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    """Payload for user authentication."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """JWT bearer token response."""

    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    """Authenticated user profile representation."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    email: str
    role: str

