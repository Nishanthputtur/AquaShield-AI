# 03 — Non-Functional Requirements

## 1. Security

### 1.1 Password Storage — Argon2id

All user passwords are hashed with the **Argon2id** algorithm via the `argon2-cffi` library (≥ 23.1). Argon2id is the OWASP-recommended winner of the 2015 Password Hashing Competition and provides resistance against both GPU and side-channel attacks.

- Memory cost: library defaults (≥ 64 MiB)
- Parallelism: library defaults (≥ 4 threads)
- Output length: 32 bytes
- `password_hash` is **never** returned in any API response.

### 1.2 Token-Based Authentication — JWT HS256

- Tokens are signed with HMAC-SHA256 (`HS256`).
- `JWT_SECRET_KEY` is a minimum-256-bit random secret injected at runtime via environment variable; it has no default.
- Token expiry: **30 minutes**. Clients must re-authenticate after expiry.
- Role is **not** trusted from the token payload alone; every protected endpoint re-queries the database to verify the user's current role.

### 1.3 Transport Security

- All production traffic must be served over TLS (HTTPS).
- CORS is restricted to the origins listed in `CORS_ORIGINS`.
- The Vite development proxy eliminates browser CORS during local development.

### 1.4 Input Validation

- Pydantic v2 models with `extra="forbid"` reject unknown request fields with `422 Unprocessable Entity`.
- String fields enforce `min_length` and, where applicable, `max_length` constraints.

---

## 2. Performance

### 2.1 Database Connection Pooling

SQLAlchemy is configured with a connection pool to avoid per-request connection overhead:

- `pool_size`: 5 persistent connections
- `max_overflow`: 10 additional connections under load
- `pool_pre_ping`: enabled — stale connections are detected and replaced automatically.

### 2.2 Query Efficiency

- Inspection and maintenance list endpoints use a single SQL `JOIN` across `inspections / maintenance_records → assets → zones → cities` rather than N+1 queries.
- Monitoring readings are fetched in a single ordered `SELECT … LIMIT N` query.

### 2.3 Frontend Polling

The Engineer simulation page polls `GET /simulation/state` and `GET /monitoring/readings` every **3 seconds** only while the simulation is in the `RUNNING` state. Polling stops immediately on `PAUSED` or `STOPPED`.

---

## 3. Usability

### 3.1 Role-Aware Navigation

The React frontend presents only the navigation links relevant to the authenticated user's role. Attempting to access a route reserved for another role redirects the user to their own home page rather than showing an error screen.

### 3.2 Session Persistence

On page load, the frontend attempts `GET /auth/me` with the stored token. If the token is valid, the session is restored transparently. If the token has expired, the token is cleared and the user is redirected to the login page.

### 3.3 Demo Quick-Login

The login page provides one-click buttons for each of the five seeded demo accounts, allowing evaluators to switch roles quickly during demonstrations without manual credential entry.

### 3.4 Responsive Design

All pages use Tailwind CSS utility classes and are readable on screens from 375 px (mobile) to 1 440 px (desktop) without horizontal scrolling.

---

## 4. Maintainability

- All backend business logic lives in service modules (`auth_service`, `monitoring_service`, `asset_service`) separate from route handlers.
- A single `asset_service._display_name()` function centralises the mapping from database asset types to human-readable display names across all four route modules.
- Frontend API calls are centralised in `src/services/api.js`; no fetch calls exist outside that module.
