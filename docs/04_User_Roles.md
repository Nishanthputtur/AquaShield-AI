# 04 — User Roles

## Role Overview

AquaShield AI implements a **fixed-role, default-deny** authorization model. Each authority user is assigned exactly one role at account creation. Role changes are not supported in M3; they are planned for M4 administration workflows.

---

## 1. Administrator

**Primary function:** Account provisioning and personnel management.

**Permissions:**
- Create new authority user accounts (all 5 roles).
- List all existing users.
- Update a user's name or email.

**Denied:**
- Simulation control.
- Monitoring readings.
- Inspection or maintenance records.

**Frontend page:** `/admin` — Users table and new-user creation form.

---

## 2. Engineer

**Primary function:** Operate the virtual water simulation engine and monitor live telemetry.

**Permissions:**
- Start, pause, resume, stop, and reset the simulation.
- Retrieve current simulation state and tick counter.
- Retrieve sensor readings with inline asset context.

**Denied:**
- User management.
- Inspection or maintenance data.

**Frontend page:** `/engineer` — Simulation control panel and live sensor chart with parameter selector.

---

## 3. Maintenance Officer

**Primary function:** Review outstanding field inspections and log remedial maintenance actions.

**Permissions:**
- Read all submitted inspections (across all Field Inspectors).
- Create maintenance records.
- Read all maintenance records (not filtered to own records — D04-14).

**Denied:**
- User management.
- Simulation control.
- Asset lookup.

**Frontend page:** `/maintenance` — Inspection list, maintenance creation form, maintenance records table.

---

## 4. Field Inspector

**Primary function:** Conduct on-site physical inspections of water infrastructure assets and submit findings.

**Permissions:**
- Look up a single asset by its identifier.
- Submit inspection reports (findings + optional condition assessment).

**Denied:**
- Inspection history retrieval (own or others' — D04-09).
- Maintenance records.
- Simulation control.
- User management.

**Frontend page:** `/inspector` — Asset lookup with quick-select chips and inspection submission form.

---

## 5. Utility Manager

**Primary function:** Executive oversight of the municipal water network.

**Permissions (M3):**
- Authenticated session with role-aware navigation.

**Planned (M4):**
- Read-only access to aggregate KPI dashboards, anomaly summaries, and regulatory reports.

**Denied (M3):** All operational endpoints; dashboard data is read-only and scoped to M4.

**Frontend page:** `/manager` — Welcome banner with network statistics and M4 roadmap.

---

## Seeded Demo Accounts

| Email | Role | Password |
|---|---|---|
| `admin@aquashield.demo` | Administrator | `password123` |
| `engineer@aquashield.demo` | Engineer | `password123` |
| `maintenance@aquashield.demo` | Maintenance Officer | `password123` |
| `inspector@aquashield.demo` | Field Inspector | `password123` |
| `manager@aquashield.demo` | Utility Manager | `password123` |

> **Note:** Demo accounts use a weak password for evaluation convenience. Production deployments must enforce strong passwords.
