"""
Demo user seeding script for AquaShield AI.

Seeds 5 authority users across all approved roles when APP_ENV == 'demo'.
Idempotent: skips users if their email already exists.
Supports --reset-names flag to update existing user names to human names.
"""

import os
import sys
from pathlib import Path

# Load backend/.env into os.environ if not already present
env_file = Path(__file__).resolve().parent.parent / "backend" / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

# Guard: must be demo environment
if os.getenv("APP_ENV") != "demo":
    raise SystemExit("APP_ENV must be 'demo' to seed demo users.")

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database.connection import SessionLocal
from backend.app.models.user import User
from backend.app.services.auth_service import hash_password

DEMO_USERS = [
    {
        "name": "Admin User",
        "email": "admin@aquashield.demo",
        "role": "Administrator",
        "password_env": "DEMO_ADMIN_PASSWORD",
    },
    {
        "name": "Engineer User",
        "email": "engineer@aquashield.demo",
        "role": "Engineer",
        "password_env": "DEMO_ENGINEER_PASSWORD",
    },
    {
        "name": "Maintenance Officer",
        "email": "maintenance@aquashield.demo",
        "role": "Maintenance Officer",
        "password_env": "DEMO_MAINTENANCE_PASSWORD",
    },
    {
        "name": "Field Inspector",
        "email": "inspector@aquashield.demo",
        "role": "Field Inspector",
        "password_env": "DEMO_INSPECTOR_PASSWORD",
    },
    {
        "name": "Utility Manager",
        "email": "manager@aquashield.demo",
        "role": "Utility Manager",
        "password_env": "DEMO_MANAGER_PASSWORD",
    },
]


def seed_users(reset_names: bool = False) -> None:
    db = SessionLocal()
    inserted = 0
    updated = 0
    try:
        for user_info in DEMO_USERS:
            existing = (
                db.query(User).filter(User.email == user_info["email"]).first()
            )
            if existing:
                if reset_names:
                    existing.name = user_info["name"]
                    updated += 1
                    print(f"Updated name for {user_info['email']} -> {user_info['name']}")
                else:
                    print(f"Skipping existing user: {user_info['email']}")
                continue

            password = os.getenv(user_info["password_env"], "password123")
            pw_hash = hash_password(password)
            user = User(
                name=user_info["name"],
                email=user_info["email"],
                role=user_info["role"],
                password_hash=pw_hash,
            )
            db.add(user)
            inserted += 1

        db.commit()
        if reset_names:
            print(f"Reset names for {updated} user(s).")
        else:
            print(f"Seeded {inserted} demo user(s).")
    except Exception as exc:
        db.rollback()
        print(f"Error seeding demo users: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    reset = "--reset-names" in sys.argv
    seed_users(reset_names=reset)
