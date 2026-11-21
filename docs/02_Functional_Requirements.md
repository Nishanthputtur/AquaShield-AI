# 02 — Functional Requirements

## 1. Authority Roles

AquaShield AI supports exactly five named roles. Role values are case-sensitive strings stored in the `users` table.

| Role | Key Responsibilities |
|---|---|
| **Administrator** | Provision and manage authority user accounts |
| **Engineer** | Operate the simulation engine and monitor telemetry |
| **Maintenance Officer** | Review field inspections and log maintenance actions |
| **Field Inspector** | Look up assets and submit physical inspection reports |
| **Utility Manager** | Executive read-only overview of network health |

---

## 2. Feature Catalogue

### 2.1 Authentication

- `POST /api/v1/auth/login` — exchange email + password for a 30-minute JWT.
- `GET /api/v1/auth/me` — return the authenticated user's profile (`user_id`, `name`, `email`, `role`).
- Tokens signed with HS256; secret injected via environment variable.
- Passwords hashed with Argon2id; plaintext never stored or returned.

### 2.2 User Management (Administrator only)

- `GET /api/v1/users` — list all authority users (excludes `password_hash`).
- `POST /api/v1/users` — create a new user with any approved role.
- `PATCH /api/v1/users/{id}` — update `name` or `email` only; role changes are out of scope for M3.

### 2.3 Simulation Engine (Engineer only)

Five control actions exposed over HTTP:

| Endpoint | Action | Allowed From States |
|---|---|---|
| `POST /simulation/start` | Start engine | STOPPED |
| `POST /simulation/pause` | Pause engine | RUNNING |
| `POST /simulation/resume` | Resume engine | PAUSED |
| `POST /simulation/stop` | Stop engine | RUNNING, PAUSED |
| `POST /simulation/reset` | Reset to tick 0 | Any |

- `GET /simulation/state` — returns `{ state, tick }`.

### 2.4 Monitoring / Telemetry (Engineer only)

- `GET /api/v1/monitoring/readings?limit=N` — return up to N recent sensor readings (default 100, max 1 000) with inline asset context.

### 2.5 Asset Lookup (Field Inspector only)

- `GET /api/v1/assets/{id}` — return a single asset record with city and zone metadata.

### 2.6 Inspections

| Method | Endpoint | Role |
|---|---|---|
| `POST` | `/api/v1/inspections` | Field Inspector |
| `GET` | `/api/v1/inspections` | Maintenance Officer |

- `inspector_id` is always server-derived from the JWT; it is never accepted in the request body.

### 2.7 Maintenance

| Method | Endpoint | Role |
|---|---|---|
| `POST` | `/api/v1/maintenance` | Maintenance Officer |
| `GET` | `/api/v1/maintenance` | Maintenance Officer |

- `maintenance_officer_id` is always server-derived from the JWT.
- `GET` returns **all** records, not filtered to the caller.

### 2.8 Analytics (M4 — planned)

Real-time network anomaly detection, predictive maintenance scoring, cross-city flow analytics, and executive KPI dashboards are planned for the M4 sprint.

### 2.9 Public Portal (M4 — planned)

A read-only public dashboard showing aggregate water-quality statistics for citizen transparency is scoped to M4.

---

## 3. Default-Deny Authorization

All endpoints enforce the principle of least privilege. Any role not explicitly listed as authorised for an endpoint receives `403 Forbidden`. Unauthenticated requests receive `401 Unauthorized`.
