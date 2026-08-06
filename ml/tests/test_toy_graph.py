"""Unit tests for the toy 4-intersection graph (Phase 7.4)."""

from env.toy_graph import (
    APPROACH_NAMES,
    NEIGHBORS,
    PHASES,
    build_toy_graph,
    time_of_day_factor,
)


def test_graph_has_four_intersections():
    graph = build_toy_graph()
    assert graph["num_intersections"] == 4
    assert graph["intersections"] == [0, 1, 2, 3]


def test_every_intersection_has_four_approaches():
    graph = build_toy_graph()
    for i in graph["intersections"]:
        assert len(graph["neighbors"][i]) == 4
        assert list(graph["neighbors"][i].keys()) == APPROACH_NAMES


def test_phases_cover_all_approaches():
    covered = [a for phase in PHASES for a in phase]
    assert sorted(covered) == [0, 1, 2, 3]


def test_peripheral_and_internal_links():
    assert NEIGHBORS[0]["N"] is None
    assert NEIGHBORS[0]["W"] is None
    assert NEIGHBORS[0]["S"] == 2
    assert NEIGHBORS[0]["E"] == 1


def test_internal_links_are_symmetric():
    for (u, v), t in build_toy_graph()["link_travel_s"].items():
        assert (v, u) in build_toy_graph()["link_travel_s"]
        assert t > 0


def test_base_rate_defined_for_all_approaches():
    graph = build_toy_graph()
    for i in graph["intersections"]:
        assert len(graph["base_rate"][i]) == 4


def test_time_of_day_peaks():
    assert abs(time_of_day_factor(8.0) - 1.0) < 1e-9
    assert abs(time_of_day_factor(18.0) - 1.0) < 1e-9
    assert abs(time_of_day_factor(12.0) - 0.5) < 1e-9
    assert abs(time_of_day_factor(0.0) - 0.25) < 1e-9
