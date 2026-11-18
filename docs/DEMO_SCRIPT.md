Owner saves this as docs/DEMO_SCRIPT.md

# AquaShield AI
# Final Internal Project Demonstration Script

Presentation date: 23 November 2026  
Target duration: 5 minutes  
Audience: Project Guide and Internal Evaluation Panel  
Application: AquaShield AI Authority Application

## 1. Demonstration setup

### Local services

The demonstration runs locally using:

| Service | Expected address |
|---|---|
| React authority application | `http://localhost:5173` |
| FastAPI backend | `http://127.0.0.1:8000` |
| FastAPI documentation | `http://127.0.0.1:8000/docs` |
| PostgreSQL | `localhost:5432` |

These are the planned development addresses. Confirm the actual configured ports and frontend API base URL before the presentation.

### Required running services

1. PostgreSQL service.
2. AquaShield PostgreSQL database.
3. FastAPI backend.
4. React authority frontend.

Start FastAPI with one worker for the demonstration:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Start the authority frontend from its application directory:

```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

Use the actual project startup instructions if the final README specifies a different command.

### Demo accounts

The demonstration uses one pre-seeded account for each authority role.

| Role | Demo account |
|---|---|
| Administrator | `admin@aquashield.demo` |
| Engineer | `engineer@aquashield.demo` |
| Maintenance Officer | `maintenance@aquashield.demo` |
| Field Inspector | `inspector@aquashield.demo` |
| Utility Manager | `manager@aquashield.demo` |

Passwords are configured locally through the demo environment variables or the gitignored `backend/.env`.

Required password variables:

- `DEMO_ADMIN_PASSWORD`
- `DEMO_ENGINEER_PASSWORD`
- `DEMO_MAINTENANCE_PASSWORD`
- `DEMO_INSPECTOR_PASSWORD`
- `DEMO_MANAGER_PASSWORD`

Do not print, commit or include real demo passwords in this document.

### Prepare demonstration data

Before the panel arrives:

- Confirm database connection.
- Confirm 4 cities, 16 zones and 108 assets.
- Confirm 328 sensors.
- Confirm five demo user accounts.
- Confirm Engineer monitoring readings are available after simulation starts.
- Confirm at least one inspection record exists or create one during the presentation.
- Confirm maintenance records are available for the Maintenance Officer view.
- Prepare three known asset IDs for the Field Inspector demonstration.

Suggested reference IDs:

| Asset ID | Demonstration asset |
|---|---|
| C1-PS-001 | Zorawarpur Pump Station 1 |
| C1-P-001 | Zorawarpur Pipeline 1 |
| C1-V-001 | Zorawarpur Valve 1 |

Verify these IDs against the actual seeded database before using them.

## 2. Five-minute demonstration

### Opening: 20 seconds

"Good morning. Our project is AquaShield AI, a Water Infrastructure Decision Intelligence Platform.

It represents a virtual water distribution environment. We use simulated infrastructure and sensor readings to demonstrate monitoring, inspection and maintenance workflows.

The infrastructure contains four cities, sixteen zones and 108 assets, supported by simulated sensor data."

### Role 1: Administrator, approximately 50 seconds

Demonstration:

1. Open the login page.
2. Log in using the Administrator account.
3. Show the Administrator dashboard.
4. Open the user-management screen.
5. Display the existing five authority accounts.
6. Create one demonstration user with a valid name, email, password and authority role.
7. Show the new account in the user list.

Talk track:

"The Administrator manages authority user accounts. Account creation supports all five approved roles. User updates are restricted to name and email. Password hashes are never returned through the API."

Do not demonstrate role changes, city management, zone management, asset management, simulation monitoring or operational-record access.

### Role 2: Engineer, approximately 65 seconds

Demonstration:

1. Log out and log in as Engineer.
2. Open the monitoring dashboard.
3. Select Start.
4. Show the simulation state changing to Running.
5. Show new sensor readings appearing in the chart.
6. Select Pause and show the state change.
7. Select Resume.
8. Select Stop.
9. Select Reset.

Talk track:

"The Engineer controls the virtual simulation and monitors sensor readings. Each reading includes the relevant asset context, such as asset ID, name, type, status, city and zone.

The simulation uses five controls: Start, Pause, Resume, Stop and Reset. Sensor readings are persisted in PostgreSQL."

The chart refreshes periodically while the simulation is Running. Do not use an additional Step control.

### Role 3: Field Inspector, approximately 50 seconds

Demonstration:

1. Log out and log in as Field Inspector.
2. Enter a known asset ID supplied by the demonstration reference card or guide.
3. Retrieve the individual asset details.
4. Show its name, type, status, city and zone.
5. Enter inspection findings.
6. Submit the inspection.
7. Show the submission confirmation.

Talk track:

"The Field Inspector selects an asset using a known asset identifier and records inspection findings. The backend derives inspector attribution from the authenticated identity. The client cannot choose another inspector's identity."

Do not open an inspection-history screen. Field Inspector inspection retrieval is not permitted in M3.

### Role 4: Maintenance Officer, approximately 55 seconds

Demonstration:

1. Log out and log in as Maintenance Officer.
2. Open the inspection list.
3. Open an inspection and show its associated asset details.
4. Open the maintenance form.
5. Enter maintenance details and status.
6. Submit the maintenance record.
7. Open the maintenance list and show the saved record.

Talk track:

"The Maintenance Officer reviews inspection information and associated asset details. The officer records maintenance information. The backend derives maintenance attribution from the authenticated account.

The approved M3 scope also allows the Maintenance Officer to view all maintenance records."

This access follows the Project Owner-approved interpretation of D04-14.

### Role 5: Utility Manager, approximately 30 seconds

Demonstration:

1. Log out and log in as Utility Manager.
2. Show the Utility Manager identity and role-aware navigation.
3. Explain the analytics milestone boundary.

Talk track:

"The Utility Manager's documented responsibilities include viewing analytical and decision information. These API capabilities are scheduled for M4 under the approved CR-01C.6 decision. We have not added placeholder analytics endpoints to M3."

## 3. Panel briefing: M3 boundaries

State these points clearly.

### Analytics

Anomaly detection, Asset Health Score, Risk Score, predictive maintenance, maintenance prioritization, explainable recommendations and decision-information APIs are not part of M3.

CR-01C.6 defers analytical-result and decision-information API endpoints for all five authority roles to M4.

### Administrator permissions

The M3 Administrator demonstration focuses on user management.

Administrator does not receive M3 access to:

- Simulation status or controls.
- Inspection records.
- Maintenance records.
- Raw sensor monitoring.
- General operational data.

The M3 scope does not implement the documented city, zone and asset management use cases.

### Field Inspector permissions

Field Inspector submits inspections and receives confirmation.

Inspection-history retrieval is excluded under the approved document-precedence and default-deny rules.

### Role changes

Role changes are outside M3 scope under D04-03. User roles are fixed at account creation.

### Record updates

Inspection and maintenance update endpoints are outside M3 scope under D04-10 and D04-15.

### Simulation deployment constraint

The M3 demonstration runs FastAPI using one worker because simulation state and the background ticking task are held in application memory.

## 4. Eight anticipated panel questions

### Q1. Is AquaShield connected to actual municipal water infrastructure?

No. AquaShield is an academic virtual infrastructure platform. It uses simulated assets, sensors and readings. It does not connect to physical municipal infrastructure.

### Q2. How is sensor data generated?

The simulator generates readings for the defined infrastructure and sensor classes. The backend processes and stores monitoring readings in PostgreSQL.

### Q3. How do you protect authority accounts?

Passwords use Argon2id hashing. Users authenticate through JWT-based login. FastAPI verifies authentication and role permissions on protected endpoints.

### Q4. Why does each role have different access?

The application follows default-deny authorization under CR-01A. Detailed Design Chapter 5 Section 5.2 governs documented role permissions under CR-01B.

### Q5. Why does the Administrator not see inspections or maintenance?

The approved Detailed Design does not grant the Administrator those operational read permissions. Broad administrative descriptions do not independently grant access.

### Q6. Why does the Field Inspector not see inspection history?

The Field Inspector use case permits recording inspection information. Retrieval requires a separate exception. No such exception was approved for M3.

### Q7. Why are analytics not available in this demonstration?

CR-01C.6 places analytics-result and decision-information API implementation in M4. M3 focuses on the backend authority workflows.

### Q8. Why does the simulation require one worker?

The M3 simulation state and ticking task are in application memory. Multiple application workers would hold separate simulation states and risk generating duplicate reading batches. One worker is the documented demonstration constraint.

## 5. Final presentation checklist

Before the panel arrives:

- [ ] PostgreSQL is running.
- [ ] Database connection succeeds.
- [ ] Infrastructure counts are verified.
- [ ] Five demo accounts authenticate.
- [ ] Backend starts without errors.
- [ ] Frontend loads without errors.
- [ ] Administrator user creation works.
- [ ] Engineer simulation and chart work.
- [ ] Field Inspector asset lookup and inspection submission work.
- [ ] Maintenance Officer inspection review and maintenance creation work.
- [ ] Utility Manager login works.
- [ ] No unauthorized access succeeds.
- [ ] Three demonstration asset IDs are verified.
- [ ] Backup demo data is available.
- [ ] API and UI ports are confirmed.
- [ ] The five-minute script is rehearsed.

Demonstration rule: present only functionality verified in the final running build. Do not describe planned or deferred functionality as completed.