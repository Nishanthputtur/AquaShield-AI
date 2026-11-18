"""
Simulation control endpoints for AquaShield AI.

Matching CONTRACT.md Section 4.6 and 4.7.
Authorized role: Engineer only.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.dependencies import require_role
from backend.app.schemas.simulation import (
    SimulationActionLiteral,
    SimulationResponse,
)
from backend.app.services.simulation_service import simulation_service

router = APIRouter(
    prefix="/api/v1/simulation",
    tags=["simulation"],
    dependencies=[Depends(require_role("Engineer"))],
)


@router.post("/{action}", response_model=SimulationResponse)
async def control_simulation(action: SimulationActionLiteral):
    """Control virtual simulation lifecycle.

    Accepts exactly: start, pause, resume, stop, reset.
    Any other action is rejected with HTTP 422.
    """
    if action == "start":
        res = await simulation_service.start()
    elif action == "pause":
        res = await simulation_service.pause()
    elif action == "resume":
        res = await simulation_service.resume()
    elif action == "stop":
        res = await simulation_service.stop()
    elif action == "reset":
        res = await simulation_service.reset()
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid action '{action}'. Permitted actions: start, pause, resume, stop, reset.",
        )
    return SimulationResponse(state=res["state"], tick=res["tick"])


@router.get("/state", response_model=SimulationResponse)
def get_simulation_state():
    """Retrieve current simulation state and tick counter.

    Authorized for Engineer role only.
    """
    state_data = simulation_service.get_state()
    return SimulationResponse(
        state=state_data["state"],
        tick=state_data["tick"],
    )
