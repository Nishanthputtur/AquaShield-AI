Owner saves this as docs/VIVA_NOTES.md

# AquaShield AI
# Technical Viva Notes

Project: Water Infrastructure Decision Intelligence Platform  
Programme: MCA  
Demonstration date: 23 November 2026

## 1. Elevator pitch

AquaShield AI is a web-based platform for monitoring and managing a virtual water distribution infrastructure. It uses simulated sensor readings to demonstrate infrastructure monitoring, inspection recording and maintenance workflows. Its architecture combines React, FastAPI, Python and PostgreSQL, with analytics planned as a later project milestone.

## 2. Architecture: seven logical layers

| Layer | Responsibility | Technology |
|---|---|---|
| 1. Presentation | Authority dashboards, forms, charts and navigation | React, Tailwind CSS |
| 2. API | HTTP endpoints and request/response handling | FastAPI |
| 3. Authentication and authorization | Login, JWT verification and role restrictions | JWT HS256, Argon2id |
| 4. Application services | User, inspection, maintenance and workflow logic | Python |
| 5. Simulation and monitoring | Virtual assets, sensors, events and reading generation | Python simulator |
| 6. Data persistence | Relational models, database access and stored readings | PostgreSQL |
| 7. Analytics | Anomaly detection, health, risk and maintenance decision support | Pandas, NumPy, Scikit-learn |

These are seven logical presentation layers, not an additional set of database or deployment components.

## 3. M1: Simulator foundation

M1 establishes the virtual infrastructure and simulated sensor environment.

Infrastructure inventory:

- 4 cities.
- 16 zones.
- 108 assets.
- 328 sensors.
- 11 sensor classes.
- 6 event types.
- SimulationGenerator with a 5-state lifecycle.

Asset distribution:

| Asset | Count |
|---|---:|
| Treatment Facilities | 8 |
| Reservoirs | 8 |
| Pump Stations | 12 |
| Pipelines | 48 |
| Valves | 32 |

The simulator generates data and events for the virtual environment. It does not interact with physical infrastructure.

M1 tests: 99 passing at the recorded M1 checkpoint.

## 4. M2: Database and persistence

M2 establishes PostgreSQL persistence and the approved relational design.

The database contains exactly 18 tables:

`users`, `cities`, `zones`, `assets`, `treatment_facilities`, `reservoirs`, `pump_stations`, `pipelines`, `valves`, `sensors`, `sensor_readings`, `anomalies`, `asset_health_scores`, `risk_scores`, `inspections`, `maintenance_records`, `complaints`, `notifications`.

Verified seeded inventory:

| Component | Count |
|---|---:|
| Cities | 4 |
| Zones | 16 |
| Assets | 108 |
| Sensors | 328 |

The M2 baseline had 115 passing tests across the recorded project test suite. This is the historical pre-M3 baseline, not the final M3 test count.

## 5. M3: Backend APIs

M3 introduces the authority backend using FastAPI.

Security:

- Argon2id password hashing.
- JWT authentication using approved HS256 configuration.
- Database-backed user identity and role verification.
- Default-deny authorization under CR-01A.
- Detailed Design Chapter 5 Section 5.2 governs role permissions under CR-01B.
- Server-derived inspection and maintenance attribution.

### Thirteen API endpoints

Authentication:
1. `POST /api/v1/auth/login`
2. `GET /api/v1/auth/me`

Administrator:
3. `POST /api/v1/users`
4. `GET /api/v1/users`
5. `PATCH /api/v1/users/{id}`

Engineer:
6. `POST /api/v1/simulation/{action}`
7. `GET /api/v1/simulation/state`
8. `GET /api/v1/monitoring/readings`

Field Inspector:
9. `GET /api/v1/assets/{id}`
10. `POST /api/v1/inspections`

Maintenance Officer:
11. `GET /api/v1/inspections`
12. `POST /api/v1/maintenance`
13. `GET /api/v1/maintenance`

### Role summary

| Role | M3 responsibilities |
|---|---|
| Administrator | Manage authority users |
| Engineer | Control simulation and monitor readings |
| Field Inspector | Look up a known asset and submit inspections |
| Maintenance Officer | Review inspections and manage maintenance records |
| Utility Manager | Authenticate and access role-appropriate navigation; analytics APIs are outside M3 |

The `GET /maintenance` endpoint returns all maintenance records under the approved D04-14 interpretation.

### M3 simulation

The five controls are:

Start, Pause, Resume, Stop and Reset.

Simulation state and tick counter are held in memory. Sensor readings are persisted in PostgreSQL. M3 demonstration deployment uses one FastAPI worker.

## 6. Frontend

The authority frontend uses React and Tailwind CSS.

It provides:

- Login.
- Authentication state.
- Role-conditional navigation.
- Administrator user management.
- Engineer simulation and monitoring dashboard.
- Field Inspector asset lookup and inspection form.
- Maintenance Officer inspection and maintenance screens.
- Utility Manager login and role presentation.

The Public Water Information Portal remains a separate application.

## 7. Scope decisions

### M3

- Authority backend APIs.
- Five authority roles.
- Authentication and authorization.
- Simulation and sensor monitoring.
- Inspection and maintenance workflows.
- Minimum React authority interface for demonstration.

### M4

- Anomaly detection APIs.
- Asset Health Score (AHS).
- Risk Score (RS).
- Leak-risk analysis.
- Predictive maintenance.
- Maintenance prioritization.
- Explainable recommendations.
- Analytical-result and decision-information APIs.

CR-01C.6 explicitly excludes analytical-result and decision-information API endpoints from M3 for all five roles.

### M5

- Separate Public Water Information Portal.
- Public complaints workflow.
- Public notifications functionality.

## 8. Known limitations

1. The system uses simulated rather than physical infrastructure data.
2. M3 does not expose analytics-result or decision-information APIs.
3. Administrator M3 scope focuses on user management.
4. Field Inspector does not retrieve inspection history.
5. Inspection and maintenance update endpoints are outside M3.
6. Utility Manager does not receive analytics functionality in M3.
7. The simulation uses one application worker because its active state is held in memory.
8. The public portal is a separate application outside the M3 delivery.

## 9. Ten anticipated viva questions

Q1. What problem does AquaShield AI address?

It demonstrates a structured software platform for monitoring virtual water infrastructure and supporting inspection and maintenance workflows.

Q2. Why does the project use simulated data?

The project is an academic virtual environment. Simulation provides controlled sensor readings and infrastructure events without physical hardware.

Q3. Why FastAPI?

FastAPI provides Python-based HTTP APIs, request validation, dependency-based authentication and API documentation.

Q4. Why PostgreSQL?

PostgreSQL provides relational storage, foreign-key relationships, constraints and transactional persistence.

Q5. How are passwords protected?

The backend hashes passwords with Argon2id. It does not store plaintext passwords.

Q6. How does JWT authentication work?

A successful login returns a signed access token. Protected requests supply the token. The backend validates it and checks the associated user's role.

Q7. What is default-deny authorization?

A role receives access only when an approved use case grants that permission. All other protected operations are denied.

Q8. What is AHS and RS?

AHS measures asset health from 0 to 100, where 100 is healthiest. RS measures risk from 0 to 100, where 100 represents the highest risk. Their analytics implementation is outside M3.

Q9. How does the simulation work?

The simulator generates readings for virtual sensors. The M3 backend controls its lifecycle, persists monitoring readings and returns them to the Engineer dashboard.

Q10. What is the main difference between M3 and M4?

M3 provides authenticated authority workflows and monitoring APIs. M4 introduces analytics and decision-intelligence APIs.

## 10. Demonstration honesty

Explain the difference between completed implementation, approved design and planned future functionality.

Use the latest test results when reporting implementation quality. The 115-test figure refers to the recorded pre-M3 baseline. Never present it as the final M3 test result without a fresh test run.