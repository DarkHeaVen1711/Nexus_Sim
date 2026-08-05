"""Tests for the building-density-proxy OD generator (Phases 6.6 / 6.7)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from od_proxy import (  # noqa: E402
    DIURNAL_PROFILE,
    CONGESTION_PROFILE,
    build_proxy_matrix,
    zone_stats,
)


def _graph(nodes):
    return {"nodes": nodes, "edges": []}


def _node(nid, lat, lon, zone_id):
    return {"id": nid, "lat": lat, "lon": lon, "zone_id": zone_id,
            "is_signal": False}


def _two_zone_graph():
    """Two zones: zone 1 has 3 nodes, zone 2 has 1 node."""
    return _graph([
        _node(1, 41.90, -87.65, 1),
        _node(2, 41.91, -87.65, 1),
        _node(3, 41.92, -87.65, 1),
        _node(4, 41.99, -87.70, 2),
    ])


# ---------------------------------------------------------------- profiles

def test_diurnal_profile_sums_to_one():
    assert len(DIURNAL_PROFILE) == 24
    assert sum(DIURNAL_PROFILE) == pytest.approx(1.0, abs=1e-9)


def test_congestion_profile_is_24h_and_never_speeds_traffic_up():
    assert len(CONGESTION_PROFILE) == 24
    # A congestion multiplier below 1.0 would mean travel is *faster* than free
    # flow, which is not physical for this model.
    assert all(c >= 1.0 for c in CONGESTION_PROFILE)


def test_peak_hours_are_slower_than_overnight():
    assert CONGESTION_PROFILE[8] > CONGESTION_PROFILE[3]   # AM peak vs 03:00
    assert CONGESTION_PROFILE[17] > CONGESTION_PROFILE[3]  # PM peak vs 03:00


# -------------------------------------------------------------- zone_stats

def test_zone_stats_counts_mass_and_averages_centroid():
    stats = zone_stats(_two_zone_graph())
    assert set(stats) == {1, 2}
    assert stats[1]["mass"] == 3
    assert stats[2]["mass"] == 1
    # Zone 1's centroid is the mean of its three nodes.
    assert stats[1]["lat"] == pytest.approx(41.91)
    assert stats[1]["lon"] == pytest.approx(-87.65)


def test_zone_stats_skips_untagged_zone_zero():
    """zone_id 0 is export.py's 'no zone' sentinel, not a real zone."""
    stats = zone_stats(_graph([
        _node(1, 41.90, -87.65, 0),
        _node(2, 41.91, -87.65, 1),
        _node(3, 41.92, -87.65, 2),
    ]))
    assert 0 not in stats
    assert set(stats) == {1, 2}


# ------------------------------------------------------- matrix generation

def test_requires_at_least_two_zones():
    with pytest.raises(ValueError, match="at least 2 tagged zones"):
        build_proxy_matrix(_graph([_node(1, 41.9, -87.6, 1)]), "nowhere")


def test_matrix_matches_schema_1_0_shape():
    m = build_proxy_matrix(_two_zone_graph(), "testville")
    for key in ("schema_version", "city", "zone_count", "units", "zones", "od"):
        assert key in m, "missing schema-1.0 key: %s" % key
    assert m["schema_version"] == "1.0"
    assert m["city"] == "testville"
    assert m["zone_count"] == 2
    assert isinstance(m["zones"], dict)
    assert isinstance(m["od"], list)


def test_zone_keys_are_strings_like_the_real_matrix():
    """The engine indexes zones by string key (see od_matrix.py)."""
    m = build_proxy_matrix(_two_zone_graph(), "testville")
    assert all(isinstance(k, str) for k in m["zones"])
    assert set(m["zones"]) == {"1", "2"}


def test_od_entries_have_24h_arrays():
    m = build_proxy_matrix(_two_zone_graph(), "testville")
    assert m["od"], "expected at least one OD pair"
    for e in m["od"]:
        assert len(e["hourly"]) == 24
        assert len(e["hourly_tt"]) == 24
        assert all(v >= 0 for v in e["hourly"])
        assert all(v > 0 for v in e["hourly_tt"])


def test_total_demand_is_conserved():
    """Every generated trip must come from the zone-mass budget."""
    graph = _two_zone_graph()
    m = build_proxy_matrix(graph, "testville", trips_per_node=4.0)
    total = sum(sum(e["hourly"]) for e in m["od"])
    expected = len(graph["nodes"]) * 4.0
    # Small shortfall is allowed: negligible pairs are dropped by design.
    assert total <= expected + 1e-6
    assert total == pytest.approx(expected, rel=0.02)


def test_trips_per_node_scales_demand_linearly():
    g = _two_zone_graph()
    a = sum(sum(e["hourly"]) for e in build_proxy_matrix(
        g, "t", trips_per_node=2.0)["od"])
    b = sum(sum(e["hourly"]) for e in build_proxy_matrix(
        g, "t", trips_per_node=4.0)["od"])
    # Tolerance accommodates per-hour rounding to 4dp, which is relatively
    # coarser on the smaller matrix.
    assert b == pytest.approx(2 * a, rel=1e-3)


def test_gravity_model_favours_near_and_heavy_zones():
    """Closer, denser zone pairs must attract more trips than distant, light
    ones -- the defining property of a gravity model."""
    graph = _graph([
        # Zone 1: heavy (3 nodes)
        _node(1, 41.900, -87.650, 1),
        _node(2, 41.901, -87.650, 1),
        _node(3, 41.902, -87.650, 1),
        # Zone 2: light (1 node), very close to zone 1
        _node(4, 41.905, -87.650, 2),
        # Zone 3: light (1 node), far away
        _node(5, 42.400, -87.650, 3),
    ])
    m = build_proxy_matrix(graph, "t")
    flows = {(e["origin"], e["destination"]): sum(e["hourly"])
             for e in m["od"]}
    # A pair absent from the matrix was pruned as negligible, i.e. zero flow.
    near = flows.get((1, 2), 0.0)
    far = flows.get((1, 3), 0.0)
    # 1->2 (near) should carry far more demand than 1->3 (far), same masses.
    assert near > far


def test_intra_zone_distance_scales_with_zone_size():
    """Regression guard. Intra-zone distance must come from the zone's own
    radius, not a flat floor: with a flat floor the gravity term exploded and
    94% of Chicago's trips landed inside a single zone (real share: 11.1%),
    which would have left the road network almost empty."""
    # Two identically-massed zones, but zone 1's nodes are spread ~10x wider.
    graph = _graph([
        _node(1, 41.900, -87.650, 1),
        _node(2, 41.950, -87.650, 1),   # zone 1 is large
        _node(3, 42.300, -87.650, 2),
        _node(4, 42.305, -87.650, 2),   # zone 2 is small
    ])
    stats = zone_stats(graph)
    assert stats[1]["radius_m"] > stats[2]["radius_m"] * 5

    flows = {(e["origin"], e["destination"]): sum(e["hourly"])
             for e in build_proxy_matrix(graph, "t")["od"]}
    # Equal mass, but the physically larger zone means longer internal trips,
    # so it must generate *less* intra-zone demand than the compact one.
    assert flows.get((1, 1), 0.0) < flows.get((2, 2), 0.0)


def _intra_zone_share(matrix):
    total = sum(sum(e["hourly"]) for e in matrix["od"])
    intra = sum(sum(e["hourly"]) for e in matrix["od"]
                if e["origin"] == e["destination"])
    return intra / total if total else 0.0


def test_proxy_reproduces_real_chicago_intra_zone_share():
    """Calibration regression, run against real data.

    INTRA_ZONE_FACTOR was tuned so the proxy reproduces the intra-zone trip
    share of Chicago's *measured* OD matrix. Before that calibration the proxy
    reported 94% intra-zone against a real 11.1%, which would have left the road
    network essentially empty. This test fails if that calibration drifts.

    Skips when the Chicago data files are absent (e.g. a fresh clone or CI
    without the data/ directory populated).
    """
    import json

    root = os.path.join(os.path.dirname(__file__), "..", "..")
    graph_path = os.path.join(root, "data", "chicago", "graph.json")
    real_path = os.path.join(root, "data", "chicago", "od_matrix.json")
    if not (os.path.isfile(graph_path) and os.path.isfile(real_path)):
        pytest.skip("Chicago data not present; calibration check skipped")

    with open(graph_path) as f:
        graph = json.load(f)
    with open(real_path) as f:
        real = json.load(f)
    if real.get("validation_safe") is False:
        pytest.skip("Chicago matrix is itself a proxy; nothing to calibrate to")

    observed = _intra_zone_share(real)
    modelled = _intra_zone_share(build_proxy_matrix(graph, "chicago"))

    assert modelled == pytest.approx(observed, abs=0.03), (
        "proxy intra-zone share %.1f%% has drifted from the measured %.1f%% -- "
        "re-calibrate INTRA_ZONE_FACTOR" % (100 * modelled, 100 * observed))


def test_output_is_deterministic():
    g = _two_zone_graph()
    assert build_proxy_matrix(g, "t") == build_proxy_matrix(g, "t")


# ------------------------------------------------------------- provenance

def test_matrix_is_flagged_as_low_confidence_proxy():
    m = build_proxy_matrix(_two_zone_graph(), "testville")
    assert m["method"] == "gravity-density-proxy"
    assert m["confidence"] == "low"
    assert m["validation_safe"] is False
    assert all(e["confidence"] == "low" for e in m["od"])


def test_model_parameters_are_recorded_for_later_calibration():
    m = build_proxy_matrix(_two_zone_graph(), "testville")
    params = m["model_parameters"]
    for key in ("mass_exponent", "distance_exponent", "free_flow_mps",
                "detour_factor", "trips_per_node_per_day", "mass_proxy"):
        assert key in params


def test_validate_py_refuses_a_proxy_matrix():
    """Guard against a circular validation: proxy journey times are modelled,
    so a MAPE computed against them would be meaningless."""
    import json
    import tempfile

    from validate import _load_od_matrix

    m = build_proxy_matrix(_two_zone_graph(), "testville")
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(m, f)
        with pytest.raises(SystemExit, match="circular"):
            _load_od_matrix(path)
    finally:
        os.unlink(path)


def test_validate_py_still_accepts_a_real_matrix():
    import json
    import tempfile

    from validate import _load_od_matrix

    real = {"schema_version": "1.0", "od": [], "zones": {}}
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(real, f)
        assert _load_od_matrix(path)["schema_version"] == "1.0"
    finally:
        os.unlink(path)
