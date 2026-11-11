"""
Application configuration for AquaShield AI.

Loads settings from environment variables, with backend/.env as the
default source. Environment variables take precedence over .env.

Importing this module only parses settings. It does not:

    - create the virtual city
    - initialize sensors
    - generate readings
    - seed database records
    - open a database connection

All of those happen explicitly later: connection.py builds the engine,
seed.py populates inventory, monitoring_service.py handles persistence.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# backend/.env — resolved relative to this file so it is found
# regardless of the working directory used to start the app.
#
#   __file__              = backend/app/config/settings.py
#   .parent               = backend/app/config
#   .parent.parent        = backend/app
#   .parent.parent.parent = backend
ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings.

    Reads from environment variables and from backend/.env.
    Environment variables take precedence over .env values.
    """

    # ---- Application -------------------------------------------------
    APP_NAME: str = "AquaShield AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ---- Database ----------------------------------------------------
    # Local development default. Override via backend/.env in any
    # environment that uses different credentials or host.
    DATABASE_URL: str = (
        "postgresql://postgres:postgres@localhost:5432/aquashield"
    )
    # Echo SQL statements to stdout. Useful during development only.
    DATABASE_ECHO: bool = False

    # ---- CORS --------------------------------------------------------
    # Comma-separated origins for the two React frontends.
    # Defaults cover Vite (5173) and CRA (3000) local dev.
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ---- Pydantic configuration --------------------------------------
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---- Convenience -------------------------------------------------
    @property
    def cors_origin_list(self) -> list[str]:
        """CORS_ORIGINS split into a list for middleware use."""
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]


# Module-level singleton. .env is read once, on import. That is the
# only side effect of importing this module.
settings = Settings()