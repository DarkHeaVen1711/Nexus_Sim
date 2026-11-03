"""
Multi-Modal Router — Fleet Taxonomy Breakdown & EV Charging Depot Telemetry.
"""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/simulations", tags=["Multi-Modal & EV Infrastructure"])

# Default mock charging stations for Chicago baseline
_DEFAULT_CHARGING_STATIONS = [
    {"node_id": 105, "name": "Loop Fast Charger Hub", "total_stalls": 8, "occupied_stalls": 3, "charge_rate_kw": 150.0},
    {"node_id": 312, "name": "Near North Depot", "total_stalls": 6, "occupied_stalls": 5, "charge_rate_kw": 50.0},
    {"node_id": 840, "name": "West Loop Rapid Stalls", "total_stalls": 10, "occupied_stalls": 2, "charge_rate_kw": 150.0},
]


class ChargingStationCreate(BaseModel):
    node_id: int = Field(..., description="Graph node for charging station location")
    name: str = Field(..., description="Depot name")
    total_stalls: int = Field(default=4, ge=1, description="Number of charging bays")
    charge_rate_kw: float = Field(default=50.0, description="Charging speed in kW")


@router.get("/{sim_id}/charging-stations")
async def get_charging_stations(sim_id: str) -> Dict[str, Any]:
    return {"simulation_id": sim_id, "stations": _DEFAULT_CHARGING_STATIONS}


@router.get("/{sim_id}/multimodal/fleet-breakdown")
async def get_fleet_breakdown(sim_id: str) -> Dict[str, Any]:
    return {
        "simulation_id": sim_id,
        "fleet_distribution": {
            "CAR": {"count": 14200, "share": 0.71, "avg_speed_kmh": 32.4},
            "BUS": {"count": 850, "share": 0.04, "avg_speed_kmh": 22.1, "tsp_extensions": 42},
            "BIKE": {"count": 1800, "share": 0.09, "avg_speed_kmh": 16.8},
            "PEDESTRIAN": {"count": 2150, "share": 0.11, "avg_speed_kmh": 4.5},
            "EV": {"count": 980, "share": 0.05, "avg_soc": 0.68, "charging_count": 34},
            "EMERGENCY": {"count": 20, "share": 0.001, "green_wave_active": True},
        },
    }
