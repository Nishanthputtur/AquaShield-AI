# 09 — Technology Stack

## 1. Backend

### Python 3.12+

The server-side language. Python was chosen for its rich ecosystem of data-science libraries (NumPy, scikit-learn) which will power M4 analytics, and for the FastAPI framework's native async support and automatic OpenAPI documentation generation.

### FastAPI

High-performance async web framework built on Starlette and Pydantic. Used for all 15 API endpoints. Key features used:
- Dependency injection (`Depends`) for authentication and role guards.
- Pydantic v2 request/response models with `extra="forbid"` strict validation.
- Automatic `/docs` (Swagger UI) and `/redoc` documentation endpoints.

### SQLAlchemy 2.0 (ORM)

Object-relational mapper for all database interactions. Features used:
- Declarative model definitions.
- Connection pooling (`pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`).
- Multi-table `JOIN` queries for inspection and maintenance list endpoints.

### PostgreSQL 15

Primary relational database. Chosen for:
- ACID compliance essential for financial-grade water authority records.
- `CHECK` constraints on the `role` column enforcing the five valid role values.
- Foreign key constraints enforcing referential integrity across all tables.

### Argon2-cffi

Implements the Argon2id password hashing algorithm. The 2015 Password Hashing Competition winner, resistant to GPU and side-channel attacks.

### PyJWT

Signs and verifies JSON Web Tokens using the HS256 (HMAC-SHA256) algorithm. Tokens carry `sub` (user_id) and `exp` (30-minute expiry) claims. Role is always re-verified from the database on each request.

### pytest

Backend test runner. 194 tests across 9 test modules covering authentication, user CRUD, simulation control, monitoring, asset lookup, inspections, and maintenance.

---

## 2. Frontend

### React 18

Component-based UI library. Features used:
- `useState`, `useEffect`, `useCallback` hooks throughout all pages.
- `createContext` / `useContext` for the global `AuthContext` (user, token, login, logout).
- Strict mode enabled in development via `React.StrictMode`.

### Vite 8

Frontend build tool and development server. Provides:
- Hot Module Replacement (HMR) for instant feedback during development.
- `/api` proxy to `http://127.0.0.1:8000` — eliminates browser CORS issues.
- Production bundle via Rollup: single JS chunk (~384 kB gzip ~125 kB).

### Tailwind CSS 3

Utility-first CSS framework. Used throughout all pages with:
- `content` array scanning `./src/**/*.{js,jsx}` for class purging.
- Cyan-600 as the primary brand accent colour.
- Responsive grid layouts (`grid-cols-1 lg:grid-cols-2`).

### Chart.js 4 + react-chartjs-2

Charting library. Used in the Engineer page to render a multi-line time-series chart of sensor readings grouped by asset. Registered components: `LineElement`, `PointElement`, `LinearScale`, `CategoryScale`, `Tooltip`, `Legend`, `Title`.

### react-router-dom v6

Client-side routing. Routes are protected by a `ProtectedRoute` component that checks the authenticated user's role and redirects to their role-specific home page on mismatch.

---

## 3. Infrastructure

### Docker + Docker Compose

The project includes a `Dockerfile` for the backend service and a `docker-compose.yml` for orchestrating the FastAPI server and PostgreSQL container together. Planned for M4 CI/CD pipeline integration.

### Environment Variables

All secrets and configuration are injected at runtime via a `.env` file (gitignored). A `.env.example` template is committed to the repository.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | HS256 signing secret (minimum 256 bits) |
| `JWT_ALGORITHM` | Token algorithm (`HS256`) |
| `JWT_EXPIRE_MINUTES` | Token lifetime (`30`) |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `APP_ENV` | Runtime environment (`production` / `demo`) |
| `DEMO_ADMIN_PASSWORD` | Seed password for demo accounts |

---

## 4. Version Summary

| Component | Version Pinned |
|---|---|
| Python | ≥ 3.12 |
| FastAPI | ≥ 0.111 |
| SQLAlchemy | ≥ 2.0 |
| psycopg (PostgreSQL driver) | ≥ 3.1 |
| argon2-cffi | ≥ 23.1 |
| PyJWT | ≥ 2.8 |
| React | 18.x |
| Vite | ≥ 5 |
| Tailwind CSS | 3.x |
| Chart.js | 4.x |
| PostgreSQL | ≥ 15 |
