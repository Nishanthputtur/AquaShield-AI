"""
Authentication and token management service for AquaShield AI.

Provides password hashing and verification using Argon2id, and
JWT creation and validation using PyJWT.
"""

from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
import jwt

from backend.app.config.settings import settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(password: str, hash: str) -> bool:
    """Verify a plaintext password against an Argon2id hash.

    Returns True if valid, False on mismatch or corrupted hash.
    """
    try:
        return _hasher.verify(hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: int, role: str) -> str:
    """Encode a PyJWT access token with user_id and role claims."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate a PyJWT access token.

    Returns:
        dict: {"user_id": int, "role": str}

    Raises:
        jwt.InvalidTokenError: on any validation or decoding failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        sub = payload.get("sub")
        role = payload.get("role")
        if sub is None or role is None:
            raise jwt.InvalidTokenError("Token missing 'sub' or 'role' claim")
        return {"user_id": int(sub), "role": str(role)}
    except jwt.PyJWTError as exc:
        raise jwt.InvalidTokenError(str(exc)) from exc
    except (ValueError, TypeError) as exc:
        raise jwt.InvalidTokenError(f"Invalid claim types: {exc}") from exc

