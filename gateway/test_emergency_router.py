from fastapi import FastAPI
from fastapi.testclient import TestClient
from gateway.emergency_router import router as emergency_router
from gateway.multimodal_router import router as multimodal_router

app = FastAPI()
app.include_router(emergency_router)
app.include_router(multimodal_router)
client = TestClient(app)


def test_emergency_dispatch():
    resp = client.post(
        "/api/v1/simulations/test-city/emergency/dispatch",
        json={"origin_node": 101, "destination_node": 505, "priority_level": 1, "hold_duration_s": 20.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "dispatched"
    assert data["green_wave_corridor_illuminated"] is True
    assert data["mission"]["origin_node"] == 101


def test_emergency_intersection_preempt():
    resp = client.post(
        "/api/v1/simulations/test-city/emergency/preempt",
        json={"node_id": 500, "approach_edge_id": 42, "hold_duration_s": 15.0},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "preempted"
    assert data["phase_locked"] == "GREEN"
    assert data["starvation_compensation_queued"] is True


def test_multimodal_fleet_breakdown():
    resp = client.get("/api/v1/simulations/test-city/multimodal/fleet-breakdown")
    assert resp.status_code == 200
    fleet = resp.json()["fleet_distribution"]
    assert "CAR" in fleet
    assert "BUS" in fleet
    assert "EV" in fleet
    assert "EMERGENCY" in fleet
    assert fleet["EV"]["avg_soc"] > 0.0


def test_charging_stations_telemetry():
    resp = client.get("/api/v1/simulations/test-city/charging-stations")
    assert resp.status_code == 200
    stations = resp.json()["stations"]
    assert len(stations) >= 3
    assert stations[0]["total_stalls"] > 0
