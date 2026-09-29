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
    res = generate_telemetry_od("paris")
    assert res["city"] == "paris"
    assert res["validation_safe"] is True
    assert res["confidence"] == "high"
    assert len(res["od_pairs"]) == 64
    assert res["zone_count"] == 8


def test_ahmedabad_telemetry_od_generation():
    res = generate_telemetry_od("ahmedabad")
    assert res["city"] == "ahmedabad"
    assert res["validation_safe"] is True
    assert res["confidence"] == "high"
    assert len(res["od_pairs"]) == 36
    assert res["zone_count"] == 6
