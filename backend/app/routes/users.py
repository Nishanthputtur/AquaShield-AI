"""
User management endpoints for AquaShield AI.

All endpoints are strictly restricted to users with the Administrator role.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.dependencies import require_role
from backend.app.models.user import User
from backend.app.schemas.user import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from backend.app.services.auth_service import hash_password

router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
    dependencies=[Depends(require_role("Administrator"))],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
)
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    include_in_schema=False,
)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Create a new authority user.

    Validates payload, enforces email uniqueness, hashes password,
    and returns the created user without password_hash.
    """
    existing = db.query(User).filter(User.email == str(payload.email)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{payload.email}' already exists",
        )

    pw_hash = hash_password(payload.password)
    user = User(
        name=payload.name,
        email=str(payload.email),
        password_hash=pw_hash,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=UserListResponse)
@router.get("/", response_model=UserListResponse, include_in_schema=False)
def list_users(db: Session = Depends(get_db)):
    """List all authority users ordered by user_id."""
    users = db.query(User).order_by(User.user_id.asc()).all()
    return UserListResponse(users=users, total=len(users))


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Fetch user by user_id."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
):
    """Update user name or email.

    Disallows updating role, password_hash, or created_at.
    Returns 404 if user not found, 409 if new email already exists.
    """
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )

    if payload.email is not None:
        new_email = str(payload.email)
        if new_email != user.email:
            existing = db.query(User).filter(User.email == new_email).first()
            if existing and existing.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Email '{new_email}' already in use",
                )
            user.email = new_email

    if payload.name is not None:
        user.name = payload.name

    db.commit()
    db.refresh(user)
    return user

