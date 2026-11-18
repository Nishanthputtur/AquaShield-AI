"""
FastAPI route dependencies for authentication and authorization.
"""

from typing import Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.models.user import User
from backend.app.services.auth_service import decode_access_token

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Validate bearer token and return the authenticated user record.

    Raises 401 UNAUTHORIZED with a generic message on any authentication failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None or not credentials.credentials:
        raise credentials_exception

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise credentials_exception

    user_id = payload.get("user_id")
    token_role = payload.get("role")
    if user_id is None or token_role is None:
        raise credentials_exception

    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise credentials_exception

    # DB-backed role verification (D03)
    if user.role != token_role:
        raise credentials_exception

    return user


def require_role(*roles: str) -> Callable[[User], User]:
    """Return a dependency requiring the authenticated user to hold one of the specified roles.

    Raises 403 FORBIDDEN if the user's role is not authorized.
    """
    allowed_roles = set()
    for r in roles:
        if isinstance(r, (list, tuple, set)):
            allowed_roles.update(r)
        else:
            allowed_roles.add(r)

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted",
            )
        return current_user

    return role_checker

