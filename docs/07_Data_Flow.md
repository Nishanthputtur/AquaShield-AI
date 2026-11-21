# 07 — Data Flow

## 1. Overview

This document traces how sensor data moves from its point of generation inside the simulation engine through the persistence layer, the API, and finally to the frontend dashboard.

---

## 2. End-to-End Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│  SIMULATION ENGINE  (simulator/)                                    │
│                                                                     │
│  create_virtual_city()   →  populate ASSETS in-memory dict         │
│  initialize_sensors()    →  attach 328 SensorReading generators    │
│  SimulationGenerator.generate()  →  produce [{sensor_id, asset_id,  │
│                                      parameter, value, timestamp}]  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  list[dict]  (one reading per sensor per tick)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PERSISTENCE LAYER  (backend/app/services/monitoring_service.py)    │
│                                                                     │
│  persist_readings(db, readings)                                     │
│    →  INSERT INTO sensor_readings (sensor_id, asset_id, parameter, │
│                                    value, unit, timestamp)          │
│    →  db.commit()                                                   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  rows in sensor_readings table
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  POSTGRESQL  (aquashield database)                                  │
│                                                                     │
│  Tables: sensor_readings, assets, zones, cities                    │
│  Joined at query time:                                              │
│    sensor_readings → assets → zones → cities                       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  SQLAlchemy query results
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  API LAYER  (backend/app/routes/monitoring.py)                      │
│                                                                     │
│  GET /api/v1/monitoring/readings?limit=N                            │
│    →  get_recent_readings(db, limit)                                │
│    →  join assets for display name + city/zone context             │
│    →  serialize to MonitoringReadingsResponse                       │
│    →  return JSON { readings: [...] }                               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  HTTP JSON response
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FRONTEND  (src/pages/Engineer.jsx + src/components/Chart.jsx)      │
│                                                                     │
│  api.getReadings(token, 328)                                        │
│    →  setReadings(data.readings)                                    │
│    →  Chart.jsx filters by selected parameter                       │
│    →  groups by asset_id → one line per asset                      │
│    →  renders Chart.js line chart (last 30 timestamps per asset)   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Inspection Data Flow

```
Field Inspector (browser)
  │  POST /api/v1/inspections { asset_id, findings, condition }
  ▼
routes/inspections.py
  │  resolve asset_id string → Asset.asset_id integer
  │  set inspector_id = current_user.user_id  (server-derived, D04-12)
  │  INSERT INTO inspections (...)
  ▼
PostgreSQL: inspections table

Maintenance Officer (browser)
  │  GET /api/v1/inspections
  ▼
routes/inspections.py
  │  SELECT inspections JOIN assets JOIN zones JOIN cities
  │  serialize to InspectionListResponse { inspections: [...], total }
  ▼
Maintenance.jsx: inspection list panel
```

---

## 4. Maintenance Data Flow

```
Maintenance Officer (browser)
  │  POST /api/v1/maintenance { asset_id, maintenance_details, status, notes }
  ▼
routes/maintenance.py
  │  resolve asset_id string → Asset.asset_id integer
  │  set maintenance_officer_id = current_user.user_id  (server-derived, D04-13)
  │  INSERT INTO maintenance_records (...)
  ▼
PostgreSQL: maintenance_records table

Maintenance Officer (browser)
  │  GET /api/v1/maintenance
  ▼
routes/maintenance.py
  │  SELECT maintenance_records JOIN assets JOIN zones JOIN cities
  │  serialize to MaintenanceListResponse { maintenance_records: [...], total }
  ▼
Maintenance.jsx: records table
```

---

## 5. M4 Analytics Extension (Planned)

In M4, an analytics engine will sit between the PostgreSQL store and the API:

```
sensor_readings (PostgreSQL)
  │
  ▼
Analytics Engine (Python service)
  │  - anomaly detection (z-score / isolation forest)
  │  - predictive maintenance scoring
  │  - cross-city flow comparison
  ▼
analytics_results table (PostgreSQL)
  │
  ▼
GET /api/v1/analytics/* endpoints
  │
  ▼
Manager.jsx KPI dashboard
```
