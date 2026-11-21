# 10 — Project Structure

## 1. Repository Root

```
AquaShield-AI/
├── backend/                # FastAPI application
├── frontend/               # React applications
├── simulator/              # Virtual city & sensor engine
├── scripts/                # Utility scripts (seeding, migrations)
├── tests/                  # All test files
├── docs/                   # Project documentation (this directory)
├── Dockerfile              # Backend container image
├── docker-compose.yml      # Multi-service orchestration
├── pytest.ini              # pytest configuration
├── requirements.txt        # Python dependency pins (top-level)
└── .env                    # Runtime secrets (gitignored)
```

---

## 2. Backend (`backend/`)

```
backend/
└── app/
    ├── main.py                   # FastAPI app factory, router mounts, startup hooks
    ├── config/
    │   └── settings.py           # Pydantic Settings (DATABASE_URL, JWT_SECRET_KEY, etc.)
    ├── database/
    │   ├── connection.py         # SessionLocal factory, engine creation
    │   └── database.py           # get_db() dependency
    ├── models/                   # SQLAlchemy ORM models
    │   ├── user.py               # User (user_id, name, email, password_hash, role)
    │   ├── asset.py              # Asset (asset_id, asset_name, asset_type, status)
    │   ├── city.py               # City (city_id, city_name)
    │   ├── zone.py               # Zone (zone_id, zone_name, city_id)
    │   ├── sensor.py             # SensorReading (reading_id, sensor_id, ...)
    │   └── maintenance.py        # Inspection + MaintenanceRecord models
    ├── schemas/                  # Pydantic request/response schemas
    │   ├── user.py               # UserCreate, UserResponse, UserUpdate
    │   ├── asset.py              # AssetResponse, ReadingItem, MonitoringReadingsResponse
    │   ├── inspection.py         # InspectionCreate, InspectionResponse, etc.
    │   ├── maintenance.py        # MaintenanceCreate, MaintenanceResponse, etc.
    │   └── simulation.py         # SimulationStateResponse, SimulationActionResponse
    ├── routes/                   # FastAPI routers (one file per resource)
    │   ├── auth.py               # POST /login, GET /me
    │   ├── users.py              # GET/POST /users, PATCH /users/{id}
    │   ├── simulation.py         # POST /simulation/{action}, GET /simulation/state
    │   ├── monitoring.py         # GET /monitoring/readings
    │   ├── assets.py             # GET /assets/{id}
    │   ├── inspections.py        # POST/GET /inspections
    │   └── maintenance.py        # POST/GET /maintenance
    ├── services/                 # Business logic layer
    │   ├── auth_service.py       # hash_password, verify_password, create_token
    │   ├── monitoring_service.py # persist_readings, get_recent_readings
    │   ├── simulation_service.py # SimulationService singleton, tick loop
    │   └── asset_service.py      # _display_name() helper
    └── dependencies.py           # get_current_user(), require_role()
```

---

## 3. Frontend (`frontend/`)

```
frontend/
└── authority/                    # Authority personnel SPA
    ├── index.html                # Vite entry point
    ├── vite.config.js            # Vite config + /api proxy
    ├── tailwind.config.js        # Tailwind content paths
    ├── postcss.config.js         # PostCSS (required by Tailwind v3)
    ├── package.json
    └── src/
        ├── main.jsx              # React root (BrowserRouter + AuthProvider)
        ├── App.jsx               # Route definitions + ProtectedRoute component
        ├── index.css             # Tailwind directives (@tailwind base/components/utilities)
        ├── contexts/
        │   └── AuthContext.jsx   # AuthProvider, useAuth() hook
        ├── services/
        │   ├── api.js            # Centralised fetch wrapper + api.* methods
        │   └── auth.js           # localStorage helpers (saveToken, getToken, etc.)
        ├── components/
        │   ├── Nav.jsx           # Role-aware top navigation bar
        │   └── Chart.jsx         # Chart.js multi-line sensor telemetry chart
        └── pages/
            ├── Login.jsx         # Login form + demo quick-login buttons
            ├── Engineer.jsx      # Simulation controls + live telemetry chart
            ├── Inspector.jsx     # Asset lookup + inspection submission form
            ├── Maintenance.jsx   # Inspection list + maintenance form + records table
            ├── Admin.jsx         # Users table + create-user form
            └── Manager.jsx       # Executive welcome dashboard + M4 roadmap
```

---

## 4. Simulator (`simulator/`)

```
simulator/
├── city/
│   ├── virtual_city.py    # create_virtual_city() — builds ASSETS dict
│   └── assets.py          # ASSETS global registry (asset_id → asset metadata)
├── sensors.py             # initialize_sensors() — binds sensors to assets
├── generators.py          # SimulationGenerator — produce readings per tick
└── events/                # (future) anomaly event injection
```

---

## 5. Tests (`tests/`)

```
tests/
└── backend/
    ├── test_auth.py               # Login, /me, session handling  (4 tests)
    ├── test_users.py              # User CRUD                     (8 tests)
    ├── test_simulation_service.py # SimulationService unit tests  (8 tests)
    ├── test_monitoring.py         # Simulation + monitoring routes (14 tests)
    ├── test_assets.py             # Asset lookup                  (6 tests)
    ├── test_inspections.py        # Inspection endpoints          (10 tests)
    ├── test_maintenance.py        # Maintenance endpoints         (12 tests)
    ├── test_database.py           # DB model/schema tests         (115 tests)
    └── test_api.py                # (placeholder)
```

**Total: 194 tests, 0 failures.**

---

## 6. Scripts (`scripts/`)

```
scripts/
└── seed_users.py    # Create the 5 demo authority users in the database.
                     # --reset-names flag updates names without re-creating accounts.
```

---

## 7. Documentation (`docs/`)

```
docs/
├── 01_Project_Requirements.md
├── 02_Functional_Requirements.md
├── 03_Non_Functional_Requirements.md
├── 04_User_Roles.md
├── 05_Virtual_Water_City.md
├── 06_Simulation_Requirements.md
├── 07_Data_Flow.md
├── 08_System_Architecture.md
├── 09_Technology_Stack.md
├── 10_Project_Structure.md        ← this file
├── CONTRACT.md                    # Canonical M3 API contract (field authority)
├── DEMO_SCRIPT.md                 # Step-by-step demo walkthrough
├── M3_SCOPE_DECLARATION.md        # M3 approved decisions and scope boundary
└── VIVA_NOTES.md                  # Viva preparation notes
```
