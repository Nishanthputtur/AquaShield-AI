"""
SQLAlchemy engine and session factory for AquaShield AI.

Creates the process-wide engine against the PostgreSQL database
specified in settings.DATABASE_URL.

Importing this module does NOT open a database connection. SQLAlchemy's
engine is lazy: it configures a connection pool but does not acquire any
connection until the first .connect() or .execute() call. That means the
backend can be imported, tested, and started even when PostgreSQL is not
running; only the first real query will raise a connection error.

Importing this module must not:

    - create the virtual city
    - initialize sensors
    - generate readings
    - seed database records
    - execute any SQL
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.config.settings import settings


# Process-wide engine.
#
# pool_pre_ping: verify a connection is alive before handing it out.
#   Prevents stale-connection errors after PostgreSQL closes idle
#   connections (default idle timeout on many servers is short).
#
# pool_recycle=3600: force-recycle connections after 1 hour, well
#   below any typical PostgreSQL server-side connection lifetime.
#
# echo: controlled by settings.DATABASE_ECHO. Useful in development
#   to see the SQL that SQLAlchemy emits.
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_recycle=3600,
)


# Session factory. Bound to the engine above.
#
# autoflush=False: do not auto-flush pending changes before queries.
#   Gives the caller explicit control over when SQL is emitted.
#
# autocommit=False: explicit transaction boundaries. Every write must
#   be committed. Standard for FastAPI request handlers.
#
# expire_on_commit=False: after commit, loaded attributes remain
#   readable without a second query. Avoids "DetachedInstanceError"
#   when returning ORM objects from a session that has just closed.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def test_connection() -> None:
    """Verify the database is reachable. Raises a clear error if not.

    Called explicitly from startup or from a dedicated healthcheck
    endpoint. Never called at import time.

    On success returns None. On failure raises RuntimeError with a
    redacted URL (password replaced) and a hint about the most common
    causes.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise RuntimeError(
            f"Cannot connect to PostgreSQL at "
            f"{_redact_url(settings.DATABASE_URL)}. "
            f"Confirm PostgreSQL is running, the database exists, and "
            f"DATABASE_URL in backend/.env is correct. "
            f"Original error: {exc}"
        ) from exc


def _redact_url(url: str) -> str:
    """Replace the password in a database URL with **** for safe logging.

    Example: postgresql://user:secret@host:5432/db
          -> postgresql://user:****@host:5432/db
    """
    if "://" not in url or "@" not in url:
        return url
    scheme, rest = url.split("://", 1)
    userinfo, hostpart = rest.rsplit("@", 1)
    if ":" not in userinfo:
        return url
    user, _ = userinfo.split(":", 1)
    return f"{scheme}://{user}:****@{hostpart}"