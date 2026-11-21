# 06 — Simulation Requirements

## 1. Overview

The AquaShield AI simulation engine is a background service (`SimulationService`) that drives the virtual water network. It maintains a discrete-tick loop, advances sensor state on each tick, and persists readings to the database. Engineers control the engine exclusively through five HTTP endpoints.

---

## 2. Engine States

The engine operates as a finite-state machine with four possible states:

```
           ┌────────────────────────────────────┐
           │                                    │
  ─────► STOPPED ──start──► RUNNING ──pause──► PAUSED
           ▲                   │                  │
           │                   │                  │
           └───────stop─────────┘◄──resume─────────┘
           │
           └── reset (from any state)
```

| State | Description |
|---|---|
| `STOPPED` | Engine is idle. No ticks are generated. The tick counter is at its last value. |
| `RUNNING` | Engine tick loop is active. Readings are generated and persisted on each tick. |
| `PAUSED` | Tick loop is suspended. No readings are generated. State is preserved. |

> **Note:** `RESET` is an action, not a persistent state. After reset, the engine returns to `STOPPED` with tick = 0 and clears the in-memory reading buffer.

---

## 3. Control Endpoints

All five endpoints are restricted to the **Engineer** role. Any other authenticated role receives `403 Forbidden`.

| Endpoint | Description | Allowed From | Returns |
|---|---|---|---|
| `POST /api/v1/simulation/start` | Start the tick loop | `STOPPED` | `{ state: "RUNNING", tick: 0 }` |
| `POST /api/v1/simulation/pause` | Suspend the tick loop | `RUNNING` | `{ state: "PAUSED", tick: N }` |
| `POST /api/v1/simulation/resume` | Resume the tick loop | `PAUSED` | `{ state: "RUNNING", tick: N }` |
| `POST /api/v1/simulation/stop` | Stop the tick loop | `RUNNING` or `PAUSED` | `{ state: "STOPPED", tick: N }` |
| `POST /api/v1/simulation/reset` | Reset tick to 0 and stop | Any | `{ state: "STOPPED", tick: 0 }` |

Calling an action that is invalid for the current state returns `409 Conflict`.

---

## 4. State Query

```
GET /api/v1/simulation/state
```

Returns the current engine state and tick counter without side effects. Used by the Engineer frontend to seed the initial UI state and during the 3-second auto-poll while `RUNNING`.

**Response schema:**
```json
{
  "state": "RUNNING",
  "tick": 42
}
```

---

## 5. Tick Behaviour

- Each tick advances all 328 virtual sensors by one reading.
- Readings are persisted to the `sensor_readings` table within the same tick.
- The tick counter increments by 1 per cycle.
- Tick interval is configured internally by the `SimulationService`; it is not user-configurable in M3.

---

## 6. Frontend Polling Strategy

The Engineer page implements client-side polling:

1. On mount: `GET /simulation/state` to seed UI.
2. When state becomes `RUNNING`: start a 3-second interval that calls `GET /simulation/state` and `GET /monitoring/readings?limit=328`.
3. If the polled state is no longer `RUNNING`: clear the interval immediately.
4. On unmount: always clear the interval to prevent memory leaks.
