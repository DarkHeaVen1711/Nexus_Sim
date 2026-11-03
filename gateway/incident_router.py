"""
Incident Router — Dynamic Road Closures & Spatial Polygon Disaster Ingestion.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/simulations", tags=["Dynamic Incidents"])

# In-memory incident store per simulation
_incident_registry: Dict[str, List[Dict[str, Any]]] = {}


class PointModel(BaseModel):
    x: float
    y: float


class RoadClosureRequest(BaseModel):
    u: int = Field(..., description="Start node ID of edge")
    v: int = Field(..., description="End node ID of edge")
    penalty: float = Field(default=1e9, description="Cost multiplier; 1e9 = impassable")
    reason: Optional[str] = Field(default="accident", description="Closure rationale")


class PolygonHazardRequest(BaseModel):
    vertices: List[PointModel] = Field(..., min_items=3, description="Polygon boundary points")
    penalty: float = Field(default=1e9, description="Cost multiplier for interior edges")
    label: Optional[str] = Field(default="disaster_zone", description="Hazard description")


@router.post("/{sim_id}/incident/closure")
async def create_road_closure(sim_id: str, req: RoadClosureRequest) -> Dict[str, Any]:
    incident_id = f"inc-{uuid.uuid4().hex[:6]}"
    record = {
        "id": incident_id,
        "type": "road_closure",
        "u": req.u,
        "v": req.v,
        "penalty": req.penalty,
        "reason": req.reason,
        "created_at": time.time(),
    }
    _incident_registry.setdefault(sim_id, []).append(record)
    return {"status": "applied", "incident": record}


@router.post("/{sim_id}/incident/polygon")
async def create_polygon_hazard(sim_id: str, req: PolygonHazardRequest) -> Dict[str, Any]:
    incident_id = f"poly-{uuid.uuid4().hex[:6]}"
    record = {
        "id": incident_id,
        "type": "polygon_hazard",
        "vertex_count": len(req.vertices),
        "vertices": [{"x": p.x, "y": p.y} for p in req.vertices],
        "penalty": req.penalty,
        "label": req.label,
        "created_at": time.time(),
    }
    _incident_registry.setdefault(sim_id, []).append(record)
    return {"status": "applied", "incident": record}


@router.get("/{sim_id}/incidents")
async def get_active_incidents(sim_id: str) -> Dict[str, Any]:
    return {"simulation_id": sim_id, "incidents": _incident_registry.get(sim_id, [])}


@router.delete("/{sim_id}/incidents")
async def clear_all_incidents(sim_id: str) -> Dict[str, Any]:
    cleared_count = len(_incident_registry.get(sim_id, []))
    _incident_registry[sim_id] = []
    return {"status": "cleared", "simulation_id": sim_id, "cleared_count": cleared_count}
