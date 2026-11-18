"""
Simulation Pydantic schemas for AquaShield AI.

Matching CONTRACT.md Section 4.6 and 4.7.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

SimulationStateLiteral = Literal["RUNNING", "PAUSED", "STOPPED"]
SimulationActionLiteral = Literal["start", "pause", "resume", "stop", "reset"]


class SimulationResponse(BaseModel):
    """Current simulation lifecycle state and tick counter.

    Matches CONTRACT.md Section 4.6 and 4.7.
    """

    model_config = ConfigDict(from_attributes=True)

    state: SimulationStateLiteral
    tick: int


# Alias for explicit state response naming
SimulationStateResponse = SimulationResponse
