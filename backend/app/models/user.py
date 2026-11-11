"""User model — one authority-role user table."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Integer,
    String,
    text,
)

from backend.app.database.database import Base


ALLOWED_ROLES = (
    "Administrator",
    "Engineer",
    "Maintenance Officer",
    "Field Inspector",
    "Utility Manager",
)

_ROLE_CHECK = (
    "role IN ("
    + ", ".join(f"'{r}'" for r in ALLOWED_ROLES)
    + ")"
)


class User(Base):
    """Authority user. Five roles permitted by CHECK constraint."""

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    __table_args__ = (
        CheckConstraint(_ROLE_CHECK, name="ck_users_role"),
    )