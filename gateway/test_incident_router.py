from fastapi import FastAPI
from fastapi.testclient import TestClient
from gateway.incident_router import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_create_road_closure():
    resp = client.post(
        "/api/v1/simulations/test-sim/incident/closure",
        json={"u": 100, "v": 200, "penalty": 1e9, "reason": "oil_spill"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "applied"
    assert data["incident"]["u"] == 100
    assert data["incident"]["v"] == 200


def test_create_polygon_hazard():
    resp = client.post(
        "/api/v1/simulations/test-sim/incident/polygon",
        json={
            "vertices": [
                {"x": 0.0, "y": 0.0},
                {"x": 100.0, "y": 0.0},
                {"x": 100.0, "y": 100.0},
                {"x": 0.0, "y": 100.0},
            ],
            "penalty": 1e9,
            "label": "flooding",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "applied"
    assert data["incident"]["vertex_count"] == 4


def test_query_and_clear_incidents():
    resp = client.get("/api/v1/simulations/test-sim/incidents")
    assert resp.status_code == 200
    assert len(resp.json()["incidents"]) >= 2

    del_resp = client.delete("/api/v1/simulations/test-sim/incidents")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "cleared"

    resp2 = client.get("/api/v1/simulations/test-sim/incidents")
    assert len(resp2.json()["incidents"]) == 0
