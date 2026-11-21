# 05 — Virtual Water City

## 1. Purpose

AquaShield AI simulates a realistic municipal water network to generate continuous sensor telemetry without requiring a physical testbed. The virtual city provides a deterministic, reproducible environment for demonstrating and testing all platform features.

---

## 2. Network Topology

```
4 Cities
└── 16 Zones  (4 zones per city)
    └── 108 Assets  (Treatment Facilities, Pump Stations, Pipelines, Valves)
        └── 328 Virtual Sensors  (multiple sensors per asset)
```

### 2.1 Cities

| City ID | Name | Zones |
|---|---|---|
| C1 | City 1 | C1-Z1 … C1-Z4 |
| C2 | City 2 | C2-Z1 … C2-Z4 |
| C3 | City 3 | C3-Z1 … C3-Z4 |
| C4 | City 4 | C4-Z1 … C4-Z4 |

Each city represents an independent municipal water authority district with its own treatment, distribution, and monitoring infrastructure.

### 2.2 Zones

Each city is subdivided into four operational zones. Zones represent geographic distribution districts (e.g., residential north, industrial south). Assets are assigned to exactly one zone.

### 2.3 Assets

| Asset Type | Identifier Format | Count |
|---|---|---|
| Treatment Facility | `C{n}-TF-{nnn}` | 4 |
| Pump Station | `C{n}-PS-{nnn}` | 36 |
| Pipeline | `C{n}-P-{nnn}` | 48 |
| Valve | `C{n}-V-{nnn}` | 20 |
| **Total** | | **108** |

Each asset has a database record with `asset_type`, `asset_name` (the identifier string), `status`, and a foreign-key reference to its zone.

### 2.4 Sensors

| Sensor Parameter | Unit | Typical Assets |
|---|---|---|
| Pressure | bar | Pump Stations, Pipelines |
| Flow Rate | m³/h | Pipelines, Pump Stations |
| Water Level | m | Treatment Facilities |
| Water Temperature | °C | All |
| pH | — | Treatment Facilities, Pipelines |
| Turbidity | NTU | Treatment Facilities |

A total of **328 sensors** are distributed across the 108 assets. Each sensor is associated with one asset and emits one parameter per tick.

---

## 3. Data Generation

The virtual city is initialised by `simulator/city/virtual_city.py` (`create_virtual_city()`) and sensors are assigned by `simulator/sensors.py` (`initialize_sensors()`). These are called once on backend startup and whenever the monitoring endpoint is first queried.

The simulation generator (`simulator/generators.py`) produces one reading per sensor per tick. Readings are written to the `sensor_readings` table and surfaced through `GET /api/v1/monitoring/readings`.

---

## 4. Asset Naming Convention

Human-readable display names are formed by combining the PascalCase type name (mapped to spaced title case) with the asset identifier:

| DB `asset_type` | Display Name Example |
|---|---|
| `TreatmentFacility` | `Treatment Facility C1-TF-001` |
| `PumpStation` | `Pump Station C2-PS-005` |
| `Pipeline` | `Pipeline C1-P-001` |
| `Valve` | `Valve C3-V-012` |

This mapping is centralised in `backend/app/services/asset_service._display_name()`.
