# 08 — System Architecture

## 1. High-Level Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                    │
│                                                                           │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │  React 18 SPA  (Vite, Tailwind CSS, Chart.js, react-router-dom) │   │
│   │  http://localhost:5173                                           │   │
│   │                                                                  │   │
│   │  Pages: Login | Engineer | Inspector | Maintenance | Admin |     │   │
│   │         Manager                                                  │   │
│   │                                                                  │   │
│   │  AuthContext  →  localStorage (JWT token + user object)         │   │
│   │  api.js       →  fetch() → /api/*  (Vite proxy)                 │   │
│   └──────────────────────────────┬───────────────────────────────────┘   │
└──────────────────────────────────┼───────────────────────────────────────┘
                                   │  HTTP / JSON
                                   │  (proxied: /api → localhost:8000)
┌──────────────────────────────────┼───────────────────────────────────────┐
│                           API LAYER                                       │
│                                  ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │  FastAPI  (uvicorn ASGI server)                                  │   │
│   │  http://127.0.0.1:8000                                           │   │
│   │                                                                  │   │
│   │  Routers:                                                        │   │
│   │    /api/v1/auth          ← AuthService (login, /me)             │   │
│   │    /api/v1/users         ← CRUD (Administrator)                 │   │
│   │    /api/v1/simulation/*  ← SimulationService (Engineer)         │   │
│   │    /api/v1/monitoring/*  ← MonitoringService (Engineer)         │   │
│   │    /api/v1/assets/*      ← AssetService (Field Inspector)       │   │
│   │    /api/v1/inspections   ← InspectionRoutes (FI + MO)          │   │
│   │    /api/v1/maintenance   ← MaintenanceRoutes (MO)               │   │
│   │                                                                  │   │
│   │  Middleware:                                                     │   │
│   │    CORSMiddleware         (origins from CORS_ORIGINS env var)    │   │
│   │    get_current_user()     (JWT decode + DB role verification)    │   │
│   │    require_role("X")      (dependency injection, 403 on mismatch)│   │
│   └────────────────────┬─────────────────────────────────────────────┘   │
└───────────────────────┼────────────────────────────────────────────────┘
                        │  SQLAlchemy ORM (psycopg3 driver)
                        │  connection pool (size=5, overflow=10)
┌───────────────────────┼────────────────────────────────────────────────┐
│                      DATA LAYER                                          │
│                       ▼                                                  │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │  PostgreSQL 15                                                   │   │
│   │  Database: aquashield                                            │   │
│   │                                                                  │   │
│   │  Tables:                                                         │   │
│   │    users              (user_id, name, email, password_hash,     │   │
│   │                        role, created_at)                        │   │
│   │    cities             (city_id, city_name)                      │   │
│   │    zones              (zone_id, zone_name, city_id)             │   │
│   │    assets             (asset_id, asset_name, asset_type,        │   │
│   │                        status, zone_id)                         │   │
│   │    sensor_readings    (reading_id, sensor_id, asset_id,        │   │
│   │                        parameter, value, unit, timestamp)       │   │
│   │    inspections        (inspection_id, asset_id, inspector_id,  │   │
│   │                        inspection_date, findings, condition,    │   │
│   │                        status)                                  │   │
│   │    maintenance_records (maintenance_id, asset_id,              │   │
│   │                         maintenance_officer_id,                │   │
│   │                         maintenance_date, maintenance_details, │   │
│   │                         status, notes)                         │   │
│   └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Simulation Engine (Background Service)

```
┌────────────────────────────────────────────────────────────────────┐
│  SimulationService (singleton, lives in-process with FastAPI)      │
│                                                                    │
│  State machine: STOPPED ↔ RUNNING ↔ PAUSED                       │
│                                                                    │
│  Tick loop (asyncio background task):                              │
│    SimulationGenerator.generate()  →  list[ReadingDict]           │
│    persist_readings(db, readings)  →  INSERT sensor_readings      │
│    tick += 1                                                       │
│    sleep(interval)                                                 │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Deployment Topology

```
┌──────────────┐     HTTP     ┌──────────────┐    TCP/5432   ┌──────────────┐
│   Browser    │◄────────────►│  FastAPI +   │◄─────────────►│  PostgreSQL  │
│  (React SPA) │   :5173/:8000│   uvicorn    │               │   :5432      │
└──────────────┘              └──────────────┘               └──────────────┘

(In production, an nginx reverse proxy sits in front of both services,
 terminates TLS, and routes /api/* to uvicorn and /* to the React build.)
```

---

## 4. Request Lifecycle (Authenticated Endpoint)

```
1. Browser → fetch("/api/v1/monitoring/readings", { Authorization: Bearer <jwt> })
2. Vite proxy → forwards to http://127.0.0.1:8000/api/v1/monitoring/readings
3. FastAPI → CORSMiddleware passes, router matched
4. Depends(get_current_user) → decode JWT → db.query(User) → return User object
5. Depends(require_role("Engineer")) → check user.role == "Engineer" or raise 403
6. get_monitoring_readings() → query sensor_readings JOIN assets → format response
7. JSON response → Vite proxy → browser → React state update → Chart re-render
```
