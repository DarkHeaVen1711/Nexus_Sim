"""Tests for real-asymmetric-graph pressure computation (Phase 9.3-9.4).

Real city graphs are not the symmetric 2x2 toy grid: an intersection may
lead to a downstream whose approaches do not point back at it. The
``neighbor_pressures`` fallback must handle those without crashing
(TR-ML-02 observation builds call it every decision step).
"""

from __future__ import annotations

import numpy as np
import pytest

from env.traffic_sim import TrafficSim, neighbor_pressures


def _asymmetric_graph() -> dict:
    """Two intersections; A feeds B, but B's approaches never point back at A.

    B instead leads onward to C (also not pointing back at B in some dirs),
    so the "incoming approach that points back" lookup fails and the mean-queue
    fallback is required.
    """
    intersections = [10, 20, 30]
    return {
        "intersections": intersections,
        "approach_names": ["N", "S", "E", "W"],
        "phases": [[0, 1], [2, 3]],
        # A(10) -N-> B(20); B(20) -N-> C(30); C(30) dead end.
        "neighbors": {
            10: {"N": 20, "S": None, "E": None, "W": None},
            20: {"N": 30, "S": None, "E": None, "W": None},
            30: {"N": None, "S": None, "E": None, "W": None},
        },
        "link_travel_s": {(10, 20): 8.0, (20, 30): 8.0},
        "base_rate": {
            10: [0.2, 0.05, 0.05, 0.05],
            20: [0.2, 0.05, 0.05, 0.05],
            30: [0.1, 0.05, 0.05, 0.05],
        },
        "zones": [1, 2, 3],
        "baseline_zone_wait": [15.0, 15.0, 15.0],
    }


def test_neighbor_pressures_falls_back_on_asymmetric_graph():
    graph = _asymmetric_graph()
    queues = {
        10: [5.0, 1.0, 1.0, 1.0],
        20: [3.0, 7.0, 7.0, 7.0],  # mean = 6.0
        30: [9.0, 1.0, 1.0, 1.0],  # mean = 3.0
    }
    pressures = neighbor_pressures(graph, queues)

    # A(10)'s N approach -> B(20). B has no approach pointing back at A (its
    # S is None), so the fallback is B's mean queue = (3+7+7+7)/4 = 6.0.
    assert pressures[10][0] == pytest.approx(6.0)

    # B(20)'s N approach -> C(30). C has no approach pointing back at B, so
    # the fallback is C's mean queue = (9+1+1+1)/4 = 3.0.
    assert pressures[20][0] == pytest.approx(3.0)

    # Peripheral (None downstream) approaches contribute zero.
    assert pressures[10][1] == 0.0
    assert pressures[10][2] == 0.0
    assert pressures[10][3] == 0.0


def test_neighbor_pressures_uses_exact_approach_when_symmetric():
    graph = _asymmetric_graph()
    # Give B a south approach back at A to exercise the exact-match path.
    graph["neighbors"][20]["S"] = 10
    graph["link_travel_s"].setdefault((20, 10), 8.0)
    queues = {10: [5.0] * 4, 20: [3.0, 9.0, 7.0, 7.0], 30: [9.0, 1.0, 1.0, 1.0]}
    pressures = neighbor_pressures(graph, queues)
    # B's south approach (index 1) points back at A -> A sees B's queue[1]=9.
    assert pressures[10][0] == pytest.approx(9.0)


def test_traffic_sim_steps_on_asymmetric_graph():
    graph = _asymmetric_graph()
    sim = TrafficSim(graph, seed=1)
    actions = {i: 0 for i in graph["intersections"]}
    for _ in range(20):
        m = sim.step(actions)
    # Deterministic run must not raise and must report metrics for all agents.
    assert set(m["queues"].keys()) == {10, 20, 30}
    assert m["sim_time"] > 0.0


def test_neighbor_pressures_result_shapes():
    graph = _asymmetric_graph()
    queues = {i: [0.0] * 4 for i in graph["intersections"]}
    pressures = neighbor_pressures(graph, queues)
    for i in graph["intersections"]:
        assert len(pressures[i]) == 4
        assert all(np.isfinite(p) for p in pressures[i])