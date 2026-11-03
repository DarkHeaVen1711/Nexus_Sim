"""
Scenario Router — REST Endpoints for Deterministic Time-Machine & What-If Branching.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .scenario_orchestrator import orchestrator

router = APIRouter(prefix="/api/v1/simulations", tags=["Scenarios & Time-Machine"])


class ForkRequest(BaseModel):
    target_tick: int = Field(..., ge=0, description="Historic tick to branch from")
    mutations: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list,
        description="List of what-if mutations (e.g. policy switches, closures)",
    )
    label: Optional[str] = Field(default="branched_scenario", description="Scenario label")


class ScrubRequest(BaseModel):
    target_tick: int = Field(..., ge=0, description="Target tick to seek simulation state to")


@router.get("")
async def list_simulations() -> Dict[str, Any]:
    return {"simulations": orchestrator.list_instances()}


@router.post("/{sim_id}/fork")
async def fork_simulation(sim_id: str, req: ForkRequest) -> Dict[str, Any]:
    try:
        child = orchestrator.fork_scenario(
            parent_id=sim_id,
            target_tick=req.target_tick,
            mutations=req.mutations,
        )
        return {
            "status": "success",
            "simulation_id": child.simulation_id,
            "parent_id": child.parent_id,
            "forked_at_tick": child.forked_at_tick,
            "port": child.port,
            "ws_url": f"ws://localhost:{child.port}",
            "mutations_applied": len(child.mutations),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
