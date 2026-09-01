"""Unit tests for the real-city graph loader (Phase 9.1)."""

from __future__ import annotations

import json

import numpy as np

from env.graph_loader import load_graph_json
from env.observation import OBSERVATION_DIM


def _write_graph(tmp_path, nodes, edges) -> str:
    path = tmp_path / "graph.json"
    path.write_text(json.dumps({"nodes": nodes, "edges": edges}))
    return str(path)


def _fixture_path(tmp_path) -> str:
    """A small city-style graph: two real intersections connected via a
    midpoint node, one with an extra dead-end leg, plus one isolated
    dead-end signal that must be filtered out."""
    nodes = [
        # 1001 (south) -> 2001 (midpoint) -> 1002 (north) -> 1003 (north)
        {"id": 1001, "lat": 48.000, "lon": 2.30, "zone_id": 1, "is_signal": True},
        {"id": 1002, "lat": 48.001, "lon": 2.30, "zone_id": 1, "is_signal": True},
        {"id": 1003, "lat": 48.002, "lon": 2.30, "zone_id": 2, "is_signal": True},
        # 1004 is an isolated dead-end signal with a single leg: filtered.
        {"id": 1004, "lat": 48.010, "lon": 2.31, "zone_id": 2, "is_signal": True},
        {"id": 2001, "lat": 48.0005, "lon": 2.30, "zone_id": 0, "is_signal": False},
        {"id": 2002, "lat": 48.001, "lon": 2.305, "zone_id": 0, "is_signal": False},
        {"id": 2003, "lat": 48.010, "lon": 2.3101, "zone_id": 0, "is_signal": False},
    ]
    edges = [
        {"u": 1001, "v": 2001, "length_m": 55.0, "lanes": 2},
        {"u": 2001, "v": 1002, "length_m": 55.0, "lanes": 2},
        {"u": 2001, "v": 1001, "length_m": 55.0, "lanes": 2},  # two-way street
        {"u": 1002, "v": 1003, "length_m": 111.0, "lanes": 2},
        {"u": 1003, "v": 1002, "length_m": 111.0, "lanes": 2},
        # dead-end leg from 1002
        {"u": 1002, "v": 2002, "length_m": 140.0, "lanes": 1},
        {"u": 2002, "v": 1002, "length_m": 140.0, "lanes": 1},
        # single leg for the doomed signal 1004
        {"u": 1004, "v": 2003, "length_m": 40.0, "lanes": 1},
    ]
    return _write_graph(tmp_path, nodes, edges)


def test_loads_real_city_format(tmp_path):
    graph = load_graph_json(_fixture_path(tmp_path))
    assert graph["num_intersections"] == 3
    assert set(graph["intersections"]) == {1001, 1002, 1003}
    assert graph["approach_names"] == ["N", "S", "E", "W"]
    assert graph["phases"] == [[0, 1], [2, 3]]


def test_isolated_dead_end_signal_filtered(tmp_path):
    graph = load_graph_json(_fixture_path(tmp_path))
    assert 1004 not in graph["intersections"]


def test_every_intersection_has_four_approaches(tmp_path):
    graph = load_graph_json(_fixture_path(tmp_path))
    for i in graph["intersections"]:
        assert len(graph["neighbors"][i]) == 4
        assert set(graph["neighbors"][i].keys()) == {"N", "S", "E", "W"}


def test_real_downstreams_resolved(tmp_path):
    graph = load_graph_json(_fixture_path(tmp_path))
    # 1001's approach toward 2001 (north) reaches 1002 via BFS midpoint.
    assert graph["neighbors"][1001]["N"] == 1002
    assert (1001, 1002) in graph["link_travel_s"]
    assert graph["link_travel_s"][(1001, 1002)] > 0.0
    assert graph["neighbors"][1002]["S"] == 1001
    assert graph["neighbors"][1002]["N"] == 1003


def test_phantom_approach_low_base_rate(tmp_path):
    graph = load_graph_json(_fixture_path(tmp_path))
    # 1002 has a real north (-> 1003) and south (-> 1001) downstream; the
    # dead-end east leg and the empty west direction are phantoms.
    i = 1002
    real = graph["base_rate"][i][graph["approach_names"].index("N")]
    phantom = graph["base_rate"][i][graph["approach_names"].index("E")]
    assert phantom < real  # phantom base rate is scaled down (0.3x)
    assert phantom > 0.0
    # Phantoms expose downstream None in a full 4-approach dict.
    assert graph["neighbors"][i]["E"] is None
    assert graph["neighbors"][i]["W"] is None


def test_zones_and_zone_map(tmp_path):
    graph = load_graph_json(_fixture_path(tmp_path))
    assert graph["zones"] == [1, 2]
    assert graph["zone_map"][1001] == 1
    assert graph["zone_map"][1002] == 1
    assert graph["zone_map"][1003] == 2
    assert len(graph["baseline_zone_wait"]) == len(graph["zones"])


def test_load_raises_without_signals(tmp_path):
    nodes = [{"id": 1, "lat": 0.0, "lon": 0.0, "zone_id": 0, "is_signal": False}]
    edges = []
    path = _write_graph(tmp_path, nodes, edges)
    try:
        load_graph_json(path)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_env_steps_on_loaded_graph(tmp_path):
    """NexusSimEnv must reset and step over a graph_loader output without
    crashing (the Phase 9 real-city path)."""
    from env import NexusSimEnv

    graph = load_graph_json(_fixture_path(tmp_path))
    env = NexusSimEnv(graph=graph, seed=0, episode_steps=10)
    obs, _ = env.reset()
    for i in obs:
        assert obs[i].shape == (OBSERVATION_DIM,)
    for _ in range(5):
        obs, rewards, _, truncated, info = env.step({i: 0 for i in obs})
        assert all(np.isfinite(o).all() for o in obs.values())
        assert all(k in info for k in ("mean_pressure", "equity", "gini"))
    assert truncated is False