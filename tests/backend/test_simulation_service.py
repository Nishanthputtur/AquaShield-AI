"""
Tests for SimulationService lifecycle, background execution, and persistence.
"""

import asyncio
from fastapi import HTTPException
import pytest

from backend.app.services.simulation_service import simulation_service


def test_start_from_stopped():
    """Starting simulation from STOPPED state transitions state to RUNNING."""
    async def run():
        await simulation_service._force_stopped()
        res = await simulation_service.start()
        assert res["state"] == "RUNNING"
        await simulation_service.stop()

    asyncio.run(run())


def test_start_from_running():
    """Attempting to start an already RUNNING simulation raises 409 Conflict."""
    async def run():
        await simulation_service._force_stopped()
        await simulation_service.start()
        with pytest.raises(HTTPException) as exc_info:
            await simulation_service.start()
        assert exc_info.value.status_code == 409
        await simulation_service.stop()

    asyncio.run(run())


def test_pause_from_running():
    """Pausing a RUNNING simulation transitions state to PAUSED."""
    async def run():
        await simulation_service._force_stopped()
        await simulation_service.start()
        res = await simulation_service.pause()
        assert res["state"] == "PAUSED"
        await simulation_service.stop()

    asyncio.run(run())


def test_pause_from_stopped():
    """Pausing a STOPPED simulation raises 409 Conflict."""
    async def run():
        await simulation_service._force_stopped()
        with pytest.raises(HTTPException) as exc_info:
            await simulation_service.pause()
        assert exc_info.value.status_code == 409

    asyncio.run(run())


def test_resume_from_paused():
    """Resuming a PAUSED simulation transitions state back to RUNNING."""
    async def run():
        await simulation_service._force_stopped()
        await simulation_service.start()
        await simulation_service.pause()
        res = await simulation_service.resume()
        assert res["state"] == "RUNNING"
        await simulation_service.stop()

    asyncio.run(run())


def test_stop_from_running():
    """Stopping a RUNNING simulation transitions state to STOPPED and resets tick."""
    async def run():
        await simulation_service._force_stopped()
        await simulation_service.start()
        res = await simulation_service.stop()
        assert res["state"] == "STOPPED"
        assert res["tick"] == 0

    asyncio.run(run())


def test_reset_clears_state():
    """Resetting simulation clears in-memory events and sets state to STOPPED with tick 0."""
    async def run():
        await simulation_service._force_stopped()
        await simulation_service.start()
        res = await simulation_service.reset()
        assert res["state"] == "STOPPED"
        assert res["tick"] == 0

    asyncio.run(run())


def test_tick_generates_readings(monkeypatch):
    """Running simulation ticks generate and persist sensor readings to database."""
    async def run():
        monkeypatch.setenv("SIMULATION_TICK_SECONDS", "1")
        await simulation_service._force_stopped()

        from backend.app.database.connection import SessionLocal
        from backend.app.models.sensor import SensorReading

        db = SessionLocal()
        try:
            db.query(SensorReading).delete()
            db.commit()
        finally:
            db.close()

        await simulation_service.start()
        await asyncio.sleep(2.5)
        await simulation_service.stop()

        db = SessionLocal()
        try:
            count = db.query(SensorReading).count()
            assert count > 0
        finally:
            db.close()

    asyncio.run(run())


def test_restart_forces_stopped():
    """Calling _force_stopped() cancels any active task and sets state to STOPPED."""
    async def run():
        await simulation_service._force_stopped()
        await simulation_service.start()
        await simulation_service._force_stopped()
        state = simulation_service.get_state()
        assert state["state"] == "STOPPED"
        assert state["tick"] == 0

    asyncio.run(run())

