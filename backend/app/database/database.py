"""
Declarative base and FastAPI session dependency for AquaShield AI.

Two responsibilities:

    1. Provide the SQLAlchemy declarative base (Base) that every ORM
       model in backend/app/models/ inherits from.
    2. Provide the get_db() dependency that FastAPI routes use to
       obtain a short-lived session.

This module imports nothing from backend.app.models. Models import
Base from this module. That one-way dependency is what avoids a
circular import when models/__init__.py imports every model to
register the tables with Base.metadata.

Importing this module does not create the engine, open a connection,
or register any tables. Table registration happens later, when a
module imports a concrete model class.
"""

from typing import Generator

from sqlalchemy.orm import DeclarativeBase, Session

from backend.app.database.connection import SessionLocal


class Base(DeclarativeBase):
    """SQLAlchemy declarative base.

    Every ORM model in backend/app/models/ inherits from this class.
    Base.metadata collects table definitions as each model module
    is imported. The tables only exist in the metadata after the
    model modules have been imported at least once.
    """

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session.

    A fresh session is created per request and closed afterward,
    even if the request raises. The route handler is responsible
    for calling db.commit() on its own writes; the dependency
    only guarantees cleanup.

    Typical use in a route:

        from fastapi import Depends
        from sqlalchemy.orm import Session
        from backend.app.database.database import get_db

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()