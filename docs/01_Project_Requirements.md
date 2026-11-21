# 01 — Project Requirements

## 1. Overview

AquaShield AI is a full-stack water-infrastructure monitoring and management platform designed for municipal water authorities. It combines a live simulation engine, role-based access control, and a real-time analytics frontend to give authority personnel complete operational visibility over city water networks.

---

## 2. Technology Stack

| Layer | Technology | Version |
|---|---|---|
| API Server | FastAPI (Python) | ≥ 0.111 |
| ORM | SQLAlchemy | ≥ 2.0 |
| Database | PostgreSQL | ≥ 15 |
| Auth hashing | argon2-cffi (Argon2id) | ≥ 23.1 |
| Auth tokens | PyJWT (HS256) | ≥ 2.8 |
| Frontend framework | React 18 | 18.x |
| Frontend build tool | Vite | ≥ 5 |
| Frontend styling | Tailwind CSS | 3.x |
| Charts | Chart.js + react-chartjs-2 | 4.x |
| Routing | react-router-dom | v6 |
| Containerisation | Docker + Docker Compose | ≥ 24 |
| Test runner | pytest | ≥ 9 |

---

## 3. Virtual Water Network Scale

| Entity | Count |
|---|---|
| Cities | **4** |
| Zones (districts) | **16** (4 per city) |
| Infrastructure assets | **108** |
| Virtual sensors | **328** |

### Asset type breakdown

| Type | Count |
|---|---|
| Treatment Facilities | 4 |
| Pump Stations | 36 |
| Pipelines | 48 |
| Valves | 20 |

---

## 4. Deployment Requirements

- Backend must start with `uvicorn backend.app.main:app`.
- Frontend dev server runs on `localhost:5173` with a Vite proxy to `localhost:8000`.
- PostgreSQL must be reachable at the URL specified in `DATABASE_URL`.
- A `.env` file must supply `JWT_SECRET_KEY`, `DATABASE_URL`, and `CORS_ORIGINS`.
- All five demo authority users must be seeded via `python scripts/seed_users.py`.

---

## 5. Quality Gates

- All backend endpoints covered by pytest (194 tests, 0 failures before release).
- `npm run build` must complete with exit code 0.
- No `password_hash` value may appear in any API response or frontend payload.
