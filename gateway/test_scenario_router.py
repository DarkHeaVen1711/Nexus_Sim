from fastapi.testclient import TestClient
from gateway.scenario_orchestrator import ScenarioOrchestrator
from gateway.scenario_router import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_scenario_orchestrator_port_allocation():
    orch = ScenarioOrchestrator(base_port=9200, max_instances=5)
    p1 = orch.allocate_port()
    p2 = orch.allocate_port()
    assert p1 == 9200
    assert p2 == 9201

    orch.release_port(p1)
    p3 = orch.allocate_port()
    assert p3 == 9200


def test_fork_simulation_endpoint():
    resp = client.post(
        "/api/v1/simulations/sim-root/fork",
        json={"target_tick": 2400, "mutations": [{"type": "close_edge", "u": 1, "v": 2}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["parent_id"] == "sim-root"
    assert data["forked_at_tick"] == 2400
    assert "port" in data
    assert "ws_url" in data


def test_scrub_simulation_endpoint():
    resp = client.post(
        "/api/v1/simulations/sim-root/scrub",
        json={"target_tick": 1800},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["seek_tick"] == 1800
    assert data["restored"] is True
