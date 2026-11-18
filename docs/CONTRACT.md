Owner saves this as docs/CONTRACT.md

# AquaShield AI
# Canonical M3 API Contract

Version: 1.0  
Date: 17 November 2026  
Status: M3 integration contract  
Applies to: Backend and authority frontend  
Base path: `/api/v1`

## 1. Purpose and change control

This document defines the API interface between the AquaShield AI FastAPI backend and React authority application.

All implementation and integration agents must follow this contract.

Any contract change requires a dated entry containing:

- Change date.
- Changed endpoint or schema.
- Previous and new behaviour.
- Reason for the change.
- Project Owner approval reference, where the change affects an approved decision.
- Required backend and frontend updates.
- Required test updates.

Do not silently change request fields, response fields, role permissions or error behaviour.

## 2. Common conventions

### 2.1 Content type

Request and response bodies use JSON.

`Content-Type: application/json`

### 2.2 Authentication

All protected endpoints require:

`Authorization: Bearer <access_token>`

The login endpoint is the only endpoint that does not require an existing token.

### 2.3 Authority roles

The supported role values are exactly:

- `Administrator`
- `Engineer`
- `Maintenance Officer`
- `Field Inspector`
- `Utility Manager`

Role comparisons must use the exact stored role values.

### 2.4 Common error envelope

All documented errors use the following structure.

401 Unauthorized:

```json
{
  "detail": "Invalid authentication credentials"
}
```

403 Forbidden:

```json
{
  "detail": "Insufficient permissions"
}
```

404 Not Found:

```json
{
  "detail": "Resource not found"
}
```

409 Conflict:

```json
{
  "detail": "Conflict reason"
}
```

422 Unprocessable Entity uses FastAPI request-validation format. Example:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "email"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

The exact validation error details depend on the failed field and validation rule. The `detail` envelope remains consistent.

### 2.5 Date and timestamp representation

Dates and timestamps are serialized as JSON strings.

Examples use ISO 8601 timestamps:

`2026-11-23T10:30:00+05:30`

The project's exact timezone and UTC serialization policy must remain consistent across endpoints.

### 2.6 User response protection

The `password_hash` database field must never appear in any API response.

This applies to login, user creation, user listing, user updates and authenticated-user retrieval.

### 2.7 General response rules

- Do not expose database credentials or internal exceptions.
- Do not accept client-supplied role or attribution values where the server derives them.
- Do not expose fields beyond the endpoint's approved response schema.
- Do not grant access based on frontend navigation alone. Enforce authorization in FastAPI.
- Return 403 for authenticated users whose roles lack permission.
- Return 401 for missing, invalid or expired authentication credentials.

## 3. Permission matrix

`Y` means permitted. `N` means denied.

| Endpoint | Administrator | Engineer | Maintenance Officer | Field Inspector | Utility Manager |
|---|:---:|:---:|:---:|:---:|:---:|
| POST /auth/login | Y | Y | Y | Y | Y |
| GET /auth/me | Y | Y | Y | Y | Y |
| POST /users | Y | N | N | N | N |
| GET /users | Y | N | N | N | N |
| PATCH /users/{id} | Y | N | N | N | N |
| POST /simulation/{action} | N | Y | N | N | N |
| GET /simulation/state | N | Y | N | N | N |
| GET /monitoring/readings | N | Y | N | N | N |
| GET /assets/{id} | N | N | N | Y | N |
| POST /inspections | N | N | N | Y | N |
| GET /inspections | N | N | Y | N | N |
| POST /maintenance | N | N | Y | N | N |
| GET /maintenance | N | N | Y | N | N |

This matrix follows CR-01A, CR-01B, CR-01C.5, CR-01C.6 and the approved D04 decisions.

Engineer receives asset context inline in monitoring responses. Engineer does not receive the standalone asset lookup endpoint.

The Maintenance Officer receives asset context embedded in inspection responses.

Field Inspector receives the standalone single-asset lookup endpoint. This does not grant asset listing, search or filtering.

## 4. Endpoint specifications

### 4.1 POST /api/v1/auth/login

Purpose: Authenticate an authority user and issue a JWT.

Authorized roles: All five authority roles, before authentication.

Authentication required: No.

Request body:

| Field | Type | Required | Constraint |
|---|---|---|---|
| email | string | Yes | Valid email format |
| password | string | Yes | Non-empty |

Example request:

```json
{
  "email": "engineer@aquashield.demo",
  "password": "REPLACE_WITH_LOCAL_DEMO_PASSWORD"
}
```

Success status: 200 OK.

Response schema:

```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

Example response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiJ9.example.signature",
  "token_type": "bearer"
}
```

Error cases:

- 401: Invalid email or password. Use the common 401 envelope.
- 422: Missing fields, empty password or invalid email format.

Passwords are verified against Argon2id hashes. JWT signing follows approved D03 configuration, HS256.

### 4.2 GET /api/v1/auth/me

Purpose: Return the authenticated user's own identity and role.

Authorized roles: Any authenticated authority role.

Authentication required: Yes.

Request body: None.

Success status: 200 OK.

Response schema:

```json
{
  "user_id": 1,
  "name": "Example Engineer",
  "email": "engineer@aquashield.demo",
  "role": "Engineer"
}
```

Example response:

```json
{
  "user_id": 2,
  "name": "Arun Kumar",
  "email": "engineer@aquashield.demo",
  "role": "Engineer"
}
```

Error cases:

- 401: Missing, invalid or expired token.
- 403: Not expected for the five authenticated authority roles.

The response contains only the current user's information. It never includes `password_hash`.

### 4.3 POST /api/v1/users

Purpose: Create an authority account.

Authorized role: Administrator only.

Authentication required: Yes.

Request body:

| Field | Type | Required | Constraint |
|---|---|---|---|
| name | string | Yes | Non-empty |
| email | string | Yes | Valid email format; unique |
| password | string | Yes | Plaintext input, hashed with Argon2id before storage |
| role | string | Yes | One of the five approved authority roles |

Example request:

```json
{
  "name": "Meera Rao",
  "email": "meera@aquashield.demo",
  "password": "LOCAL_DEMO_PASSWORD",
  "role": "Field Inspector"
}
```

Success status: 201 Created.

Response schema:

```json
{
  "user_id": 6,
  "name": "Meera Rao",
  "email": "meera@aquashield.demo",
  "role": "Field Inspector",
  "created_at": "2026-11-23T10:30:00+05:30"
}
```

Example response:

```json
{
  "user_id": 6,
  "name": "Meera Rao",
  "email": "meera@aquashield.demo",
  "role": "Field Inspector",
  "created_at": "2026-11-23T10:30:00+05:30"
}
```

Error cases:

- 401: Invalid authentication credentials.
- 403: Authenticated non-Administrator.
- 409: Email already exists.
- 422: Missing required field, invalid email or unsupported role.

Never return the submitted password or stored password hash.

### 4.4 GET /api/v1/users

Purpose: Retrieve authority user accounts.

Authorized role: Administrator only.

Authentication required: Yes.

Request body: None.

Query parameters: None defined by this contract.

Success status: 200 OK.

Response schema: Array of user objects.

Each object:

```json
{
  "user_id": 1,
  "name": "Example Administrator",
  "email": "admin@aquashield.demo",
  "role": "Administrator",
  "created_at": "2026-11-17T10:00:00+05:30"
}
```

Example response:

```json
[
  {
    "user_id": 1,
    "name": "Example Administrator",
    "email": "admin@aquashield.demo",
    "role": "Administrator",
    "created_at": "2026-11-17T10:00:00+05:30"
  },
  {
    "user_id": 2,
    "name": "Arun Kumar",
    "email": "engineer@aquashield.demo",
    "role": "Engineer",
    "created_at": "2026-11-17T10:05:00+05:30"
  }
]
```

Error cases:

- 401: Invalid authentication credentials.
- 403: Authenticated non-Administrator.

Every returned user excludes `password_hash`.

### 4.5 PATCH /api/v1/users/{id}

Purpose: Update another user's name and/or email.

Authorized role: Administrator only.

Authentication required: Yes.

Path parameter:

| Parameter | Type | Required |
|---|---|---|
| id | integer | Yes |

Request body:

| Field | Type | Required | Constraint |
|---|---|---|---|
| name | string | No | Non-empty when supplied |
| email | string | No | Valid email format and unique when supplied |

At least one field must be supplied.

Only `name` and `email` are accepted. Fields such as `role`, `password_hash` and `created_at` result in HTTP 422.

Example request:

```json
{
  "name": "Meera Rao",
  "email": "meera.rao@aquashield.demo"
}
```

Success status: 200 OK.

Response schema:

```json
{
  "user_id": 6,
  "name": "Meera Rao",
  "email": "meera.rao@aquashield.demo",
  "role": "Field Inspector",
  "created_at": "2026-11-23T10:30:00+05:30"
}
```

Example response:

```json
{
  "user_id": 6,
  "name": "Meera Rao",
  "email": "meera.rao@aquashield.demo",
  "role": "Field Inspector",
  "created_at": "2026-11-23T10:30:00+05:30"
}
```

Error cases:

- 401: Invalid authentication credentials.
- 403: Authenticated non-Administrator.
- 404: User ID does not exist.
- 409: Email already belongs to another user.
- 422: Unknown field, empty body, invalid email or invalid field value.

Password reset and role modification are outside this endpoint.

The response never includes `password_hash`.

### 4.6 POST /api/v1/simulation/{action}

Purpose: Control the virtual sensor simulation.

Authorized role: Engineer only.

Authentication required: Yes.

Path parameter:

| Parameter | Type | Required | Allowed values |
|---|---|---|---|
| action | string | Yes | start, pause, resume, stop, reset |

Request body: None.

No sixth action exists. In particular, `step` is invalid.

Success status: 200 OK.

Response schema:

```json
{
  "state": "RUNNING",
  "tick": 1
}
```

Example requests:

`POST /api/v1/simulation/start`

`POST /api/v1/simulation/pause`

`POST /api/v1/simulation/resume`

`POST /api/v1/simulation/stop`

`POST /api/v1/simulation/reset`

Example response for Start:

```json
{
  "state": "RUNNING",
  "tick": 1
}
```

Example response for Pause:

```json
{
  "state": "PAUSED",
  "tick": 8
}
```

Example response for Stop:

```json
{
  "state": "STOPPED",
  "tick": 8
}
```

The permitted response states are exactly:

- `RUNNING`
- `PAUSED`
- `STOPPED`

Error cases:

- 401: Invalid authentication credentials.
- 403: Authenticated non-Engineer.
- 422: Invalid action or malformed path.
- 409: Invalid state transition or conflicting simulation operation.

Simulation state and tick counter remain in memory for the M3 single-worker demonstration. Sensor readings persist in PostgreSQL.

### 4.7 GET /api/v1/simulation/state

Purpose: Retrieve current simulation state.

Authorized role: Engineer only.

Authentication required: Yes.

Request body: None.

Success status: 200 OK.

Response schema:

```json
{
  "state": "RUNNING",
  "tick": 8
}
```

Example response:

```json
{
  "state": "RUNNING",
  "tick": 8
}
```

Error cases:

- 401: Invalid authentication credentials.
- 403: Authenticated non-Engineer.

### 4.8 GET /api/v1/monitoring/readings

Purpose: Retrieve virtual sensor readings and approved related asset context.

Authorized role: Engineer only.

Authentication required: Yes.

Request body: None.

Query parameters: None defined by this contract.

Success status: 200 OK.

Response schema:

```json
{
  "readings": [
    {
      "sensor_id": "string",
      "asset_id": "string",
      "parameter": "string",
      "value": "number or string",
      "unit": "string",
      "timestamp": "string",
      "asset": {
        "asset_id": "string",
        "name": "string",
        "type": "string",
        "status": "string",
        "city_name": "string",
        "zone_name": "string"
      }
    }
  ]
}
```

Example response:

```json
{
  "readings": [
    {
      "sensor_id": "C1-P-001-PRESSURE",
      "asset_id": "C1-P-001",
      "parameter": "Pressure",
      "value": 45.0,
      "unit": "PSI",
      "timestamp": "2026-11-23T10:30:00+05:30",
      "asset": {
        "asset_id": "C1-P-001",
        "name": "Zorawarpur Pipeline 1",
        "type": "Pipeline",
        "status": "Operational",
        "city_name": "Zorawarpur",
        "zone_name": "North Heights"
      }
    }
  ]
}
```

The asset object contains exactly the six approved fields. Engineer does not receive the standalone asset lookup endpoint.

Error cases:

- 401: Invalid authentication credentials.
- 403: Authenticated non-Engineer.

### 4.9 GET /api/v1/assets/{id}

Purpose: Retrieve one known asset to support Field Inspector asset selection.

Authorized role: Field Inspector only.

Authentication required: Yes.

Path parameter:

| Parameter | Type | Required |
|---|---|---|
| id | string | Yes |

Request body: None.

Success status: 200 OK.

Response schema contains exactly six fields:

```json
{
  "asset_id": "string",
  "name": "string",
  "type": "string",
  "status": "string",
  "city_name": "string",
  "zone_name": "string"
}
```

Example response:

```json
{
  "asset_id": "C1-PS-001",
  "name": "Zorawarpur Pump Station 1",
  "type": "Pump Station",
  "status": "Operational",
  "city_name": "Zorawarpur",
  "zone_name": "North Heights"
}
```

Error cases:

- 401: Invalid authentication credentials.
- 403: Any authenticated role other than Field Inspector.
- 404: Asset ID does not exist.
- 422: Invalid path parameter.

No asset listing, filtering, search or unrestricted registry browsing is provided.

### 4.10 POST /api/v1/inspections

Purpose: Submit an inspection.

Authorized role: Field Inspector only.

Authentication required: Yes.

Request body:

| Field | Type | Required | Constraint |
|---|---|---|---|
| asset_id | string | Yes | Must reference an existing asset |
| findings | string | Yes | Non-empty inspection findings |
| condition | string | No | Condition description |

Example request:

```json
{
  "asset_id": "C1-PS-001",
  "findings": "Unusual vibration observed during inspection.",
  "condition": "Requires attention"
}
```

The request must be strict. Any unknown field is rejected with HTTP 422.

Specifically, `inspector_id` must never be accepted from the client.

The backend obtains the authenticated user identity and sets:

`inspector_id = current_user.user_id`

Success status: 201 Created.

Response schema:

```json
{
  "inspection_id": 101,
  "asset_id": "C1-PS-001",
  "inspector_id": 4,
  "inspection_date": "2026-11-23T10:35:00+05:30",
  "findings": "Unusual vibration observed during inspection.",
  "condition": "Requires attention",
  "status": "Submitted"
}
```

Example response:

```json
{
  "inspection_id": 101,
  "asset_id": "C1-PS-001",
  "inspector_id": 4,
  "inspection_date": "2026-11-23T10:35:00+05:30",
  "findings": "Unusual vibration observed during inspection.",
  "condition": "Requires attention",
  "status": "Submitted"
}
```

Error cases:

- 401: Invalid authentication credentials.
- 403: Authenticated non-Field Inspector.
- 404: Referenced asset does not exist.
- 422: Missing or invalid fields, or unknown fields such as `inspector_id`.

The response confirms submission. It does not provide inspection-history permission.

### 4.11 GET /api/v1/inspections

Purpose: Retrieve inspection records for the Maintenance Officer's review workflow.

Authorized role: Maintenance Officer only.

Authentication required: Yes.

Request body: None.

Query parameters: None defined by this contract.

Success status: 200 OK.

Response schema: Array of inspection objects. Each object contains the inspection fields and an embedded asset object.

Example response:

```json
[
  {
    "inspection_id": 101,
    "asset_id": "C1-PS-001",
    "inspector_id": 4,
    "inspection_date": "2026-11-23T10:35:00+05:30",
    "findings": "Unusual vibration observed during inspection.",
    "condition": "Requires attention",
    "status": "Submitted",
    "asset": {
      "asset_id": "C1-PS-001",
      "name": "Zorawarpur Pump Station 1",
      "type": "Pump Station",
      "status": "Operational",
      "city_name": "Zorawarpur",
      "zone_name": "North Heights"
    }
  }
]
```

Error cases:

- 401: Invalid authentication credentials.
- 403: Any authenticated role other than Maintenance Officer.

Field Inspector inspection-history retrieval is not permitted.

### 4.12 POST /api/v1/maintenance

Purpose: Record maintenance information.

Authorized role: Maintenance Officer only.

Authentication required: Yes.

Request body:

| Field | Type | Required | Constraint |
|---|---|---|---|
| asset_id | string | Yes | Must reference an existing asset |
| maintenance_details | string | Yes | Non-empty maintenance details |
| status | string | Yes | Allowed status vocabulary requires confirmation |
| notes | string | No | Additional notes |

Example request:

```json
{
  "asset_id": "C1-PS-001",
  "maintenance_details": "Pump station vibration inspection and bearing adjustment.",
  "status": "Open",
  "notes": "Follow-up inspection required."
}
```

The backend obtains the authenticated user identity and sets:

`maintenance_officer_id = current_user.user_id`

The request body must not accept `maintenance_officer_id` supplied by the client. Its presence results in HTTP 422.

Success status: 201 Created.

Response schema:

```json
{
  "maintenance_id": 201,
  "asset_id": "C1-PS-001",
  "maintenance_officer_id": 3,
  "maintenance_date": "2026-11-23T11:00:00+05:30",
  "maintenance_details": "Pump station vibration inspection and bearing adjustment.",
  "status": "Open",
  "notes": "Follow-up inspection required."
}
```

Example response:

```json
{
  "maintenance_id": 201,
  "asset_id": "C1-PS-001",
  "maintenance_officer_id": 3,
  "maintenance_date": "2026-11-23T11:00:00+05:30",
  "maintenance_details": "Pump station vibration inspection and bearing adjustment.",
  "status": "Open",
  "notes": "Follow-up inspection required."
}
```

Error cases:

- 401: Invalid authentication credentials.
- 403: Authenticated non-Maintenance Officer.
- 404: Referenced asset does not exist.
- 422: Missing required fields, invalid values or supplied `maintenance_officer_id`.

### 4.13 GET /api/v1/maintenance

Purpose: Retrieve maintenance records for the Maintenance Officer.

Authorized role: Maintenance Officer only.

Authentication required: Yes.

Request body: None.

Query parameters: None defined by this contract.

Success status: 200 OK.

The response contains all maintenance records. It is not filtered by `maintenance_officer_id`.

Success status: 200 OK.

Example response:

```json
[
  {
    "maintenance_id": 201,
    "asset_id": "C1-PS-001",
    "maintenance_officer_id": 3,
    "maintenance_date": "2026-11-23T11:00:00+05:30",
    "maintenance_details": "Pump station vibration inspection and bearing adjustment.",
    "status": "Open",
    "notes": "Follow-up inspection required.",
    "asset": {
      "asset_id": "C1-PS-001",
      "name": "Zorawarpur Pump Station 1",
      "type": "Pump Station",
      "status": "Operational",
      "city_name": "Zorawarpur",
      "zone_name": "North Heights"
    }
  }
]
```

Error cases:

- 401: Invalid authentication credentials.
- 403: Authenticated role other than Maintenance Officer.

## 5. Frozen role and data boundaries

The following rules apply throughout M3:

1. CR-01A default-deny authorization remains active.
2. CR-01B Detailed Design Chapter 5 Section 5.2 governs role permissions.
3. CR-01C.5 requires an explicit exception for Field Inspector inspection retrieval. No such exception exists.
4. CR-01C.6 excludes analytical-result and decision-information endpoints for all five roles in M3.
5. D04-06 grants Engineer related asset context inline in monitoring responses.
6. D04-12 requires server-derived inspection attribution.
7. D04-13 requires server-derived maintenance attribution.
8. D04-14 permits Maintenance Officers to read all maintenance records.
9. Role changes, inspection updates and maintenance updates are outside M3.
10. The frozen 18-table M2 schema must remain unchanged.

## 6. Contract ambiguities requiring confirmation

The following details are not fully established by the approved decisions. They must be checked against Antigravity's implementation and existing database models before the frontend treats them as frozen field-level constraints.

| Area | Unspecified detail |
|---|---|
| Login | Exact password policy and token expiry response behaviour |
| User creation | Password minimum length and other password validation rules |
| User fields | Maximum lengths and nullability for name and email |
| User listing | Pagination and ordering policy |
| PATCH user | Whether explicit `null` values are rejected |
| Simulation | Exact legal state transitions and meaning of the tick counter |
| Simulation | Whether Start from Stopped resets the tick counter |
| Monitoring | Reading ordering, retention window and result limit |
| Monitoring | Whether an empty reading collection returns `{"readings": []}` |
| Inspection | Exact condition vocabulary |
| Inspection | Default status and source of inspection_date |
| Inspection | Exact validation length and format for findings |
| Maintenance | Exact status vocabulary |
| Maintenance | Default or server-side source of maintenance_date |
| Maintenance | Whether notes are nullable or omitted when absent |
| Lists | Whether empty lists return HTTP 200 and `[]` |
| Timestamps | Exact timezone and serialization policy |
| All endpoints | Confirm success codes and response models against the running implementation |

Where an implementation decision is required, record it as a dated contract change. Do not silently add fields or statuses.

## 7. Change log

| Version | Date | Change |
|---|---|---|
| 1.0 | 17 November 2026 | Initial canonical M3 API contract for frontend integration |