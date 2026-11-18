"""
Simulation lifecycle and background execution service for AquaShield AI.

Coordinates the virtual simulation generator, manages lifecycle state
(STOPPED | RUNNING | PAUSED), controls periodic tick generation and reading
persistence, and enriches sensor readings with asset context.
"""

import asyncio
import os
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from simulator.city.assets import ASSETS
from simulator.city.virtual_city import create_virtual_city
from simulator.generators import SimulationGenerator, SimulationState


class SimulationService:
    """Manages virtual simulation lifecycle, background ticking, and persistence."""

    def __init__(self) -> None:
        if not ASSETS:
            create_virtual_city()
        self._generator: SimulationGenerator = SimulationGenerator()
        self._state: str = "STOPPED"
        self._tick: int = 0
        self._ticking_task: Optional[asyncio.Task] = None
        self._lock: asyncio.Lock = asyncio.Lock()
        self._tick_interval: int = int(
            os.getenv("SIMULATION_TICK_SECONDS", "5")
        )

    # ------------------------------------------------------------------
    # Lifecycle controls
    # ------------------------------------------------------------------

    async def start(self) -> dict:
        """Start the simulation from STOPPED state."""
        async with self._lock:
            if self._state != "STOPPED":
                raise HTTPException(
                    status_code=409,
                    detail=f"Simulation is {self._state}, cannot start",
                )

            if not ASSETS:
                create_virtual_city()

            if self._generator.state == SimulationState.STOPPED:
                self._generator.reset()
                self._generator.start()
            elif self._generator.state == SimulationState.IDLE:
                self._generator.start()
            elif self._generator.state == SimulationState.PAUSED:
                self._generator.resume()

            self._state = "RUNNING"
            self._tick = 0
            self._ticking_task = asyncio.create_task(self._tick_loop())
            return {"state": self._state, "tick": self._tick}

    async def pause(self) -> dict:
        """Pause a currently running simulation."""
        async with self._lock:
            if self._state != "RUNNING":
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot pause from {self._state}",
                )

            if self._generator.state == SimulationState.RUNNING:
                self._generator.pause()

            self._state = "PAUSED"
            return {"state": self._state, "tick": self._tick}

    async def resume(self) -> dict:
        """Resume a currently paused simulation."""
        async with self._lock:
            if self._state != "PAUSED":
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot resume from {self._state}",
                )

            if self._generator.state == SimulationState.PAUSED:
                self._generator.resume()

            self._state = "RUNNING"
            return {"state": self._state, "tick": self._tick}

    async def stop(self) -> dict:
        """Stop a running or paused simulation."""
        async with self._lock:
            if self._state not in ("RUNNING", "PAUSED"):
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot stop from {self._state}",
                )

            await self._cancel_task()

            if self._generator.state in (
                SimulationState.RUNNING,
                SimulationState.PAUSED,
            ):
                self._generator.stop()

            self._state = "STOPPED"
            self._tick = 0
            return {"state": self._state, "tick": self._tick}

    async def reset(self) -> dict:
        """Reset simulation and clear all registered events."""
        async with self._lock:
            await self._cancel_task()
            self._generator.reset()
            self._state = "STOPPED"
            self._tick = 0
            return {"state": self._state, "tick": self._tick}

    # ------------------------------------------------------------------
    # Background ticking and cancellation
    # ------------------------------------------------------------------

    async def _tick_loop(self) -> None:
        """Infinite loop generating and persisting sensor readings on interval."""
        while True:
            interval = float(
                os.getenv("SIMULATION_TICK_SECONDS", str(self._tick_interval))
            )
            await asyncio.sleep(interval)

            async with self._lock:
                if self._state != "RUNNING":
                    continue
                try:
                    readings = self._generator.generate()
                    from backend.app.database.connection import SessionLocal
                    from backend.app.services.monitoring_service import (
                        persist_readings,
                    )

                    db = SessionLocal()
                    try:
                        persist_readings(db, readings)
                        db.commit()
                        self._tick += 1
                    except Exception:
                        db.rollback()
                        raise
                    finally:
                        db.close()
                except Exception as exc:
                    print(f"[simulation] tick failed: {exc}")

    async def _cancel_task(self) -> None:
        """Cancel the background ticking task if currently running."""
        if self._ticking_task and not self._ticking_task.done():
            self._ticking_task.cancel()
            try:
                await self._ticking_task
            except asyncio.CancelledError:
                pass
        self._ticking_task = None

    async def _force_stopped(self) -> None:
        """Force simulation into STOPPED state with zero tick on startup/reset."""
        await self._cancel_task()
        try:
            self._generator.reset()
        except Exception:
            pass
        self._state = "STOPPED"
        self._tick = 0

    # ------------------------------------------------------------------
    # State and reading queries
    # ------------------------------------------------------------------

    def get_state(self) -> dict:
        """Return the current simulation state, tick counter, and readings count."""
        readings_count = getattr(
            self._generator,
            "readings_count",
            self._tick * 328 if self._tick else 0,
        )
        return {
            "state": self._state,
            "tick": self._tick,
            "readings_count": readings_count,
        }

    def get_engineer_readings(
        self,
        db: Optional[Session] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Fetch latest readings from database augmented with asset context."""
        from backend.app.database.connection import SessionLocal
        from backend.app.services.monitoring_service import get_recent_readings

        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        try:
            readings = get_recent_readings(db, limit=limit)
            return self._enrich_with_asset_context(readings, db=db)
        finally:
            if close_db:
                db.close()

    def _enrich_with_asset_context(
        self,
        readings: List[Dict],
        db: Optional[Session] = None,
    ) -> List[Dict]:
        """Enrich each reading dictionary with asset context {asset_id, name, type, status, city_name, zone_name}."""
        from backend.app.database.connection import SessionLocal
        from backend.app.models.asset import Asset
        from backend.app.models.city import City
        from backend.app.models.zone import Zone

        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        try:
            rows = (
                db.query(Asset, Zone, City)
                .join(Zone, Asset.zone_id == Zone.zone_id)
                .join(City, Zone.city_id == City.city_id)
                .all()
            )
            asset_map = {}
            for asset, zone, city in rows:
                context = {
                    "asset_id": asset.asset_id,
                    "name": asset.asset_name,
                    "type": asset.asset_type,
                    "status": asset.status,
                    "city_name": city.city_name,
                    "zone_name": zone.zone_name,
                }
                asset_map[asset.asset_name] = context
                asset_map[str(asset.asset_id)] = context
                asset_map[asset.asset_id] = context
        finally:
            if close_db:
                db.close()

        enriched = []
        for r in readings:
            item = dict(r)
            item["asset"] = asset_map.get(r.get("asset_id"), None)
            enriched.append(item)
        return enriched


simulation_service = SimulationService()

