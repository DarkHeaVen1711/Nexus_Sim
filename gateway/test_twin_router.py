"""Test suite for NexusTwin 2-Stage Ingestion API (/api/v1/twin/*)."""

import os
import sys
import time
import pytest
from fastapi.testclient import TestClient

# Ensure repo root is on sys.path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from gateway.server import app

client = TestClient(app)


def test_list_twin_cities():
    """Verify listing synthesized twin cities."""
    resp = client.get("/api/v1/twin/cities")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_twin_search_validation():
    """Verify validation on empty search query."""
    resp = client.post("/api/v1/twin/search", json={"query": ""})
    assert resp.status_code == 400


def test_twin_search_initiation():
    """Verify initiating a search job returns a valid job_id."""
    resp = client.post(
        "/api/v1/twin/search",
        json={"query": "Shantigram, Ahmedabad", "workspace_id": "ws_test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert data["job_id"].startswith("twin_search_")
    assert data["status"] == "queued"
    assert "/api/v1/twin/progress/" in data["stream_url"]


def test_twin_upload_and_progress():
    """Verify uploading test-city.osm and tracking progress until completion."""
    test_osm = os.path.join(_REPO_ROOT, "postman", "test-city.osm")
    assert os.path.exists(test_osm), "test-city.osm fixture must exist"

    with open(test_osm, "rb") as f:
        resp = client.post(
            "/api/v1/twin/upload",
            files={"file": ("test_upload.osm", f, "application/xml")},
            data={"city_id": "test-twin-city-unit", "city_name": "Test Twin City Unit"},
        )

    assert resp.status_code == 200
    data = resp.json()
    job_id = data["job_id"]
    assert job_id.startswith("twin_upload_")

    # Poll progress for up to 5 seconds
    completed = False
    for _ in range(25):
        prog_resp = client.get(f"/api/v1/twin/progress/{job_id}")
        assert prog_resp.status_code == 200
        prog = prog_resp.json()
        if prog["status"] == "completed":
            completed = True
            assert prog["progress_pct"] == 100
            assert prog["stage"] == "COMPLETE"
            assert "result" in prog
            assert prog["result"]["node_count"] >= 2
            break
        elif prog["status"] == "failed":
            pytest.fail(f"Ingestion job failed: {prog.get('error')}")
        time.sleep(0.2)

    assert completed, "Upload job should complete in <= 5 seconds"

    # Verify city now appears in twin cities list
    cities_resp = client.get("/api/v1/twin/cities")
    assert cities_resp.status_code == 200
    cities = cities_resp.json()
    city_ids = [c.get("city_id") for c in cities]
    assert "test-twin-city-unit" in city_ids

    # Clean up test city via DELETE endpoint
    del_resp = client.delete("/api/v1/twin/cities/test-twin-city-unit")
    assert del_resp.status_code == 200
