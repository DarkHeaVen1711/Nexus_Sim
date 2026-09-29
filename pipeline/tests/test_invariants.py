"""Domain-specific mathematical and schema invariants for NexusSim Data Pipeline."""

import math
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ingest_telemetry_od import DIURNAL_HOURLY, HOURLY_CONGESTION, haversine_distance_m, generate_telemetry_od
from od_proxy import DIURNAL_PROFILE, CONGESTION_PROFILE


class TestMathematicalInvariants:
    def test_diurnal_probability_conservation(self):
        """In NexusSim, hourly diurnal profiles must integrate to 1.0 over 24 hours."""
        sum_proxy = sum(DIURNAL_PROFILE)
        sum_telemetry = sum(DIURNAL_HOURLY)
        assert len(DIURNAL_PROFILE) == 24
        assert len(DIURNAL_HOURLY) == 24
        assert math.isclose(sum_proxy, 1.0, abs_tol=1e-7), f"Proxy diurnal sum {sum_proxy} != 1.0"
        assert math.isclose(sum_telemetry, 1.0, abs_tol=1e-7), f"Telemetry diurnal sum {sum_telemetry} != 1.0"

    def test_congestion_factor_physics(self):
        """Congestion factors represent travel time delay and must never be < 1.0 (free flow)."""
        assert all(f >= 1.0 for f in CONGESTION_PROFILE), "Found proxy congestion factor < 1.0"
        assert all(f >= 1.0 for f in HOURLY_CONGESTION), "Found telemetry congestion factor < 1.0"

    def test_haversine_metric_space_axioms(self):
        """Haversine distance must satisfy metric space axioms: non-negativity, identity, symmetry, triangle inequality."""
        p_chicago = (41.8781, -87.6298)
        p_paris = (48.8566, 2.3522)
        p_ahmedabad = (23.0225, 72.5714)

        # 1. Identity of indiscernibles: d(x, x) == 0
        assert math.isclose(haversine_distance_m(p_paris[0], p_paris[1], p_paris[0], p_paris[1]), 0.0, abs_tol=1e-4)

        # 2. Symmetry: d(x, y) == d(y, x)
        d_cp = haversine_distance_m(p_chicago[0], p_chicago[1], p_paris[0], p_paris[1])
        d_pc = haversine_distance_m(p_paris[0], p_paris[1], p_chicago[0], p_chicago[1])
        assert math.isclose(d_cp, d_pc, rel_tol=1e-6)

        # 3. Triangle inequality: d(x, z) <= d(x, y) + d(y, z)
        d_pa = haversine_distance_m(p_paris[0], p_paris[1], p_ahmedabad[0], p_ahmedabad[1])
        d_ca = haversine_distance_m(p_chicago[0], p_chicago[1], p_ahmedabad[0], p_ahmedabad[1])
        assert d_ca <= (d_cp + d_pa) + 1.0  # Numerical epsilon


class TestSchemaAndConservationInvariants:
    def test_synthetic_trip_conservation(self):
        """Sum of flow across all 24h intervals must be non-zero and conserve positive trip flow."""
        nodes = [
            {"id": i, "lat": 48.85 + (i * 0.002), "lon": 2.35 + (i * 0.002), "zone_id": (i % 3) + 1}
            for i in range(9)
        ]
        od_matrix = generate_telemetry_od("paris", graph={"nodes": nodes, "edges": []})

        assert od_matrix["schema_version"] == "1.0"
        assert od_matrix["zone_count"] == 3
        assert len(od_matrix["od_pairs"]) == 9

        total_trips = sum(sum(pair["hourly_demand"]) for pair in od_matrix["od_pairs"])
        assert total_trips > 0.0, "Total generated demand must be strictly positive"

        # Check all hourly tt >= free flow journey time
        for pair in od_matrix["od_pairs"]:
            dist = pair["distance_m"]
            base_tt = dist / 8.5  # Paris base speed 8.5 m/s
            for tt in pair["hourly_tt"]:
                assert tt >= base_tt * 0.99, f"Journey time {tt}s violates free flow lower bound {base_tt}s"
