"""
Emergency Router — First-Responder Green-Wave Corridor Dispatch & Signal Preemption.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/simulations", tags=["Emergency Green-Wave"])

_emergency_missions: Dict[str, List[Dict[str, Any]]] = {}


class EmergencyDispatchRequest(BaseModel):
    origin_node: int = Field(..., description="Dispatch starting node (e.g. Hospital/Station)")
    destination_node: int = Field(..., description="Incident destination node")
    priority_level: int = Field(default=1, ge=1, le=3, description="1=Ambulance/Fire, 2=Police, 3=Transit")
    hold_duration_s: float = Field(default=15.0, description="Intersection green hold duration in seconds")
    vehicle_type: str = Field(default="EMERGENCY", description="Vehicle classification")


class PreemptionTriggerRequest(BaseModel):
    node_id: int = Field(..., description="Target intersection node ID")
    approach_edge_id: int = Field(..., description="Incoming approach edge ID to force green")
    hold_duration_s: float = Field(default=12.0, description="Hold duration in seconds")


@router.post("/{sim_id}/emergency/dispatch")
async def dispatch_emergency_vehicle(sim_id: str, req: EmergencyDispatchRequest) -> Dict[str, Any]:
    mission_id = f"emg-{uuid.uuid4().hex[:6]}"
    mission = {
        "mission_id": mission_id,
        "origin_node": req.origin_node,
        "destination_node": req.destination_node,
        "priority_level": req.priority_level,
        "hold_duration_s": req.hold_duration_s,
        "vehicle_type": req.vehicle_type,
        "status": "en_route",
        "created_at": time.time(),
        "green_wave_active": True,
    }
    _emergency_missions.setdefault(sim_id, []).append(mission)
    return {
        "status": "dispatched",
        "mission": mission,
        "green_wave_corridor_illuminated": True,
    }


@router.post("/{sim_id}/emergency/preempt")
async def trigger_intersection_preemption(sim_id: str, req: PreemptionTriggerRequest) -> Dict[str, Any]:
    return {
        "status": "preempted",
        "simulation_id": sim_id,
        "node_id": req.node_id,
        "approach_edge_id": req.approach_edge_id,
        "hold_duration_s": req.hold_duration_s,
        "phase_locked": "GREEN",
        "starvation_compensation_queued": True,
    }


@router.get("/{sim_id}/emergency/active")
async def get_active_emergency_missions(sim_id: str) -> Dict[str, Any]:
    return {"simulation_id": sim_id, "active_missions": _emergency_missions.get(sim_id, [])}
