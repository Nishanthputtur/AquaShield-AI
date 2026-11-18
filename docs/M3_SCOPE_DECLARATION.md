Owner saves this as docs/M3_SCOPE_DECLARATION.md

# AquaShield AI
# M3 Scope Declaration

Version: 1.0  
Date: 17 November 2026  
Milestone: M3 Backend APIs and Authority Application  
Demonstration target: 23 November 2026

## 1. Purpose

This document formally defines the M3 delivery boundary for AquaShield AI.

M3 delivers the authenticated authority backend and the React authority application required to demonstrate the five approved authority roles.

M3 follows the approved Detailed Design, database schema and Project Owner decisions.

## 2. M3 deliverables

### 2.1 Backend

M3 delivers 13 API endpoints.

| No. | Method and endpoint | Authorized role |
|---:|---|---|
| 1 | POST `/api/v1/auth/login` | All five roles |
| 2 | GET `/api/v1/auth/me` | All authenticated roles |
| 3 | POST `/api/v1/users` | Administrator |
| 4 | GET `/api/v1/users` | Administrator |
| 5 | PATCH `/api/v1/users/{id}` | Administrator |
| 6 | POST `/api/v1/simulation/{action}` | Engineer |
| 7 | GET `/api/v1/simulation/state` | Engineer |
| 8 | GET `/api/v1/monitoring/readings` | Engineer |
| 9 | GET `/api/v1/assets/{id}` | Field Inspector |
| 10 | POST `/api/v1/inspections` | Field Inspector |
| 11 | GET `/api/v1/inspections` | Maintenance Officer |
| 12 | POST `/api/v1/maintenance` | Maintenance Officer |
| 13 | GET `/api/v1/maintenance` | Maintenance Officer |

The API contract defines request and response structures, authorization and validation requirements.

### 2.2 Authority frontend

M3 includes a React and Tailwind CSS authority application with role-conditional navigation.

The demonstration workflows cover:

- Administrator user management.
- Engineer simulation and sensor monitoring.
- Field Inspector asset lookup and inspection submission.
- Maintenance Officer inspection review and maintenance management.
- Utility Manager authentication and role presentation.

### 2.3 Security

M3 includes:

- Argon2id password hashing.
- JWT HS256 authentication under approved D03.
- Database-backed user identity and role verification.
- CR-01A default-deny authorization.
- CR-01B Detailed Design permission precedence.
- Server-derived inspection attribution under D04-12.
- Server-derived maintenance attribution under D04-13.
- Password-hash exclusion from API responses.

### 2.4 Simulation and monitoring

M3 includes exactly five simulation controls:

1. Start.
2. Pause.
3. Resume.
4. Stop.
5. Reset.

Engineer receives sensor readings with approved inline asset context.

Simulation state remains in memory. Sensor readings persist in PostgreSQL. The M3 demonstration uses one application worker.

## 3. M3 exclusions

The following functionality is deliberately outside M3.

### 3.1 Analytics and decision intelligence

No analytical-result or decision-information API endpoints are introduced in M3.

This applies to all five authority roles.

### 3.2 Administrator operational access

Administrator M3 functionality is limited to user management.

The M3 release does not provide Administrator access to:

- Simulation status or controls.
- Sensor monitoring.
- Inspection records.
- Maintenance records.
- General operational monitoring.

The M3 authority application also does not implement city/zone management or asset creation, editing and deletion.

### 3.3 Field Inspector history

Field Inspector submits inspection records and receives confirmation.

Field Inspector inspection-history retrieval is excluded. CR-01C.5 requires an explicit exception, and no such exception has been approved.

### 3.4 Record modifications

M3 does not include:

- User role changes.
- Inspection update endpoints.
- Maintenance update endpoints.
- Inspection deletion.
- Maintenance deletion.

### 3.5 Public application

M3 does not implement the Public Water Information Portal.

The authority application and public portal remain separate applications under the approved architecture.

## 4. M4 scope

M4 is assigned the analytics and decision-intelligence functionality.

Planned functionality:

- Anomaly detection.
- Asset Health Score (AHS).
- Risk Score (RS).
- Leak-risk analysis.
- Predictive maintenance.
- Maintenance prioritization.
- Explainable recommendations.
- Analytical-result APIs.
- Decision-information APIs.

CR-01C.6 establishes the following boundary:

1. M3 introduces no analytical-result or decision-information API endpoints.
2. No authority role receives these API permissions in M3.
3. Engineer, Maintenance Officer and Utility Manager retain their documented analytical-result use cases, with API implementation planned for M4.
4. Administrator's M3 analytics restriction is not permanent.
5. During M4, analytical and decision-information visibility will be reviewed for all five authority roles under CR-01A and CR-01B.

Approved M4 permissions must be documented in the M4 authorization and API specifications.

## 5. M5 scope

The current roadmap assigns the following functionality to M5:

- Separate Public Water Information Portal.
- Public complaint submission.
- Complaint tracking.
- Public notifications.

The public portal follows its no-login design.

No PublicUser authority role or database table is introduced.

The M5 assignment is a project roadmap scope decision. It is not inferred from the analytics decision CR-01C.6.

## 6. Rationale for scope boundaries

### CR-01A: Default-deny authorization

Only explicitly approved role permissions are implemented. Broad or assumed permissions do not grant access.

### CR-01B: Document precedence

Detailed Design Chapter 5 Section 5.2 governs role-to-use-case permissions. Broader descriptions do not independently grant protected endpoint access.

### CR-01C.5: System Design precedence

The approved Detailed Design governs over conflicting System Design role descriptions. Field Inspector inspection retrieval requires a specific exception.

### CR-01C.6: Analytics scope

Analytics and decision-information APIs are deliberately excluded from M3 for every authority role. Their visibility is reviewed in M4.

### M3 demonstration scope

The limited M3 Administrator interface and role-specific workflows prioritize a functioning, testable release for the 23 November internal demonstration.

The exclusions are intentional release boundaries. They must not be presented as completed functionality.

## 7. Academic honesty and requirement classification

The project distinguishes three categories.

### Documented requirements

Requirements explicitly present in the approved project documents, including:

- Five authority roles.
- The virtual infrastructure model.
- The 18-table database design.
- Engineer simulation and monitoring responsibilities.
- Field Inspector inspection submission.
- Maintenance Officer inspection review and maintenance responsibilities.
- Utility Manager analytical and decision-information responsibilities.

### Approved interpretations

Interpretations adopted through explicit Project Owner decisions include:

- D04-06: Engineer receives limited related asset context inline with monitoring readings.
- D04-14: Maintenance Officer read access includes all maintenance records, based on the approved interpretation of Manage Maintenance.

These interpretations must not be misrepresented as exact wording from the original Detailed Design.

### Project scope and authorization decisions

The following are explicit project decisions:

- CR-01A default-deny authorization.
- CR-01B document precedence.
- CR-01C.5 System Design precedence.
- CR-01C.6 M3/M4 analytics boundary.
- D04-03, D04-10 and D04-15 M3 exclusions.
- The M3 Administrator scope reduction.
- The M5 public portal and operations scope assignment.

### Implementation evidence

A documented endpoint, planned screen or approved decision does not prove implementation.

Completion claims must refer to actual source code, successful tests and working application demonstrations.

M1 and M2 completion figures describe their recorded verification checkpoints. M3 completion must be established through its own implementation and integration tests.

## 8. Acceptance criteria

M3 is accepted as complete when:

1. All 13 contracted endpoints operate according to the permission matrix.
2. All five authority roles authenticate.
3. Unauthorized operations return the expected denial response.
4. Inspection and maintenance attribution is server-derived.
5. Simulation uses exactly five controls.
6. Sensor readings and related asset context reach the Engineer interface.
7. Field Inspector can submit an inspection for a known asset.
8. Maintenance Officer can review inspection information and manage maintenance records.
9. The authority frontend integrates with the actual FastAPI backend.
10. Existing tests remain passing.
11. M3 integration and role-workflow tests pass.
12. The demonstration environment starts using documented instructions.

M3 completion must be supported by implementation and test evidence, not documentation alone.

---

Project Owner: Final approval authority  
Technical Architect: ChatGPT  
Independent Technical Reviewer: DeepSeek  
Implementation Engineer: Google Antigravity