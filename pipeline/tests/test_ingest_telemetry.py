"""Tests for Paris & Ahmedabad open telemetry OD ingestion (BK-01)."""

import os
import sys
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ingest_telemetry_od import haversine_distance_m, generate_telemetry_od, DATA_DIR


def test_haversine_distance_calculation():
    # Distance between two Paris coordinates (~400m apart)
    d = haversine_distance_m(48.8566, 2.3522, 48.8570, 2.3550)
    assert 150.0 < d < 300.0


def test_paris_telemetry_od_generation():
    graph_path = os.path.join(DATA_DIR, "paris", "graph.json")
    if not os.path.isfile(graph_path):
        pytest.skip("Paris road graph not present (gitignored); telemetry OD ingestion test skipped")
    res = generate_telemetry_od("paris")
    assert res["city"] == "paris"
    assert res["validation_safe"] is True
    assert res["confidence"] == "high"
    assert len(res["od_pairs"]) == 64
    assert res["zone_count"] == 8


def test_ahmedabad_telemetry_od_generation():
    graph_path = os.path.join(DATA_DIR, "ahmedabad", "graph.json")
    if not os.path.isfile(graph_path):
        pytest.skip("Ahmedabad road graph not present (gitignored); telemetry OD ingestion test skipped")
    res = generate_telemetry_od("ahmedabad")
    assert res["city"] == "ahmedabad"
    assert res["validation_safe"] is True
    assert res["confidence"] == "high"
    assert len(res["od_pairs"]) == 36
    assert res["zone_count"] == 6


def test_synthetic_telemetry_od_generation():
    # Synthetic test to guarantee CI validation without external gitignored city data
    synthetic_nodes = [
        {"id": i, "lat": 48.85 + (i * 0.001), "lon": 2.35 + (i * 0.001), "zone_id": (i % 4) + 1}
        for i in range(12)
    ]
    res = generate_telemetry_od("paris", graph={"nodes": synthetic_nodes, "edges": []})
    assert res["city"] == "paris"
    assert res["validation_safe"] is True
    assert res["confidence"] == "high"
    assert res["zone_count"] == 4
    assert len(res["od_pairs"]) == 16
