"""Load a real city ``graph.json`` into the internal ML graph format.

Parses the C++ engine's ``data/<city>/graph.json`` (nodes with
``{id, lat, lon, zone_id, is_signal}`` and edges with
``{u, v, length_m, lanes}``) and produces the dict consumed by
``NexusSimEnv`` / ``TrafficSim``.

Approach directions are derived from edge geometry (compass bearing).
Every intersection is standardised to 4 approaches ``["N","S","E","W"]``
to keep the observation dimension at 11 — directions with no incoming
edge get zero base-rate and ``None`` downstream (phantom approach).
"""

from __future__ import annotations

import json
import math
from collections import defaultdict, deque
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DIRECTIONS = ["N", "S", "E", "W"]

# Bearing ranges (degrees, clockwise from north)
#   N: 315–45  |  E: 45–135  |  S: 135–225  |  W: 225–315
_BEARING_RANGES: list[tuple[str, float, float]] = [
    ("N", 315.0, 45.0),
    ("E", 45.0, 135.0),
    ("S", 135.0, 225.0),
    ("W", 225.0, 315.0),
]

# Average urban speed for travel-time estimation (m/s ≈ 40 km/h)
_AVG_SPEED_MS = 11.1

# Default per-approach arrival rate (veh/s) when OD data is unavailable
_DEFAULT_BASE_RATE = 0.10

# Maximum BFS hops when searching for the next downstream signalised node
_MAX_BFS_HOPS = 15

# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial compass bearing from point 1 → point 2 in degrees [0, 360)."""
    d_lon = math.radians(lon2 - lon1)
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    x = math.sin(d_lon) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(d_lon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def _bearing_to_dir(bearing: float) -> str:
    """Map a compass bearing to one of N / S / E / W."""
    for name, lo, hi in _BEARING_RANGES:
        if lo > hi:  # wraps around 0°
            if bearing >= lo or bearing < hi:
                return name
        elif lo <= bearing < hi:
            return name
    return "N"


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two lat/lon points."""
    R = 6_371_000.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# BFS helper
# ---------------------------------------------------------------------------


def _bfs_next_signal(
    start: int,
    adj: dict[int, list[tuple[int, float]]],
    signal_set: set[int],
    max_hops: int = _MAX_BFS_HOPS,
    blocked: set[int] | None = None,
) -> tuple[int | None, float]:
    """BFS from *start*; return ``(next_signal_id, total_length_m)`` or
    ``(None, 0)`` if none is reachable within *max_hops*.

    ``blocked`` nodes can never be *traversed* (they are seeded in
    ``visited``). For approach resolution the origin signal is blocked so a
    dead-end leg cannot loop back through its own intersection to resolve a
    downstream signal behind it as a phantom.
    """
    visited: set[int] = {start} | (blocked or set())
    queue: deque[tuple[int, float, int]] = deque([(start, 0.0, 0)])
    while queue:
        node, dist, hops = queue.popleft()
        if hops > 0 and node in signal_set:
            return node, dist
        if hops >= max_hops:
            continue
        for neighbour, length in adj.get(node, []):
            if neighbour not in visited:
                visited.add(neighbour)
                queue.append((neighbour, dist + length, hops + 1))
    return None, 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_graph_json(path: str | Any, default_base_rate: float = _DEFAULT_BASE_RATE) -> dict:
    """Load ``data/<city>/graph.json`` and return the ML graph descriptor.

    The returned dict is compatible with ``NexusSimEnv`` and ``TrafficSim``.
    Every intersection is padded to exactly 4 approaches ``["N","S","E","W"]``
    so that ``OBSERVATION_DIM`` remains 11.
    """
    with open(path) as f:
        data = json.load(f)

    nodes: dict[int, dict] = {n["id"]: n for n in data["nodes"]}
    edges: list[dict] = data["edges"]

    # --- adjacency (directed, length only) ---------------------------------
    adj: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for e in edges:
        adj[e["u"]].append((e["v"], e["length_m"]))

    # --- signalised node set -----------------------------------------------
    signal_ids = {n["id"] for n in data["nodes"] if n.get("is_signal")}
    if not signal_ids:
        raise ValueError(f"No signalised nodes in {path}")

    # --- per-signal approach / downstream resolution -----------------------
    intersections: list[int] = []
    neighbors: dict[int, dict[str, int | None]] = {}
    link_travel_s: dict[tuple[int, int], float] = {}
    base_rate: dict[int, list[float]] = {}

    for sid in sorted(signal_ids):
        s_node = nodes[sid]

        # All nodes adjacent to this signal (in or out)
        connected: set[int] = set()
        for e in edges:
            if e["u"] == sid:
                connected.add(e["v"])
            elif e["v"] == sid:
                connected.add(e["u"])

        # Group connected nodes by bearing FROM the signal
        dir_nodes: dict[str, list[int]] = defaultdict(list)
        for nid in connected:
            n_node = nodes[nid]
            brg = _bearing_deg(s_node["lat"], s_node["lon"], n_node["lat"], n_node["lon"])
            dir_nodes[_bearing_to_dir(brg)].append(nid)

        # For each direction find the downstream signalised node (BFS)
        approach_info: dict[str, tuple[int | None, float]] = {}
        for d, nlist in dir_nodes.items():
            downstream: int | None = None
            travel_m = 0.0
            for nid in nlist:
                if nid in signal_ids and nid != sid:
                    downstream = nid
                    travel_m = _haversine_m(s_node["lat"], s_node["lon"],
                                            nodes[nid]["lat"], nodes[nid]["lon"])
                    break
                nxt, dist = _bfs_next_signal(nid, adj, signal_ids - {sid},
                                             blocked={sid})
                if nxt is not None:
                    downstream = nxt
                    travel_m = dist
                    break
            approach_info[d] = (downstream, travel_m)

        # Skip dead-end signals: no reachable downstream signal and fewer than
        # 2 connected nodes (isolated or single-link intersections).
        if sum(1 for d, (ds, _) in approach_info.items() if ds is not None) < 1 and len(connected) < 2:
            continue

        # Always build 4-approach dict (phantom = None downstream)
        neighbors[sid] = {}
        for d in _DIRECTIONS:
            if d in approach_info:
                ds, tm = approach_info[d]
                neighbors[sid][d] = ds
                if ds is not None:
                    link_travel_s[(sid, ds)] = tm / _AVG_SPEED_MS
            else:
                neighbors[sid][d] = None

        base_rate[sid] = [
            default_base_rate if d in approach_info and approach_info[d][0] is not None
            else default_base_rate * 0.3  # low but non-zero for phantoms
            for d in _DIRECTIONS
        ]
        intersections.append(sid)

    if not neighbors:
        raise ValueError(f"No usable signalised intersections in {path}")

    # --- phases: N+S vs E+W (2-phase fixed cycle) -------------------------
    phases = [[0, 1], [2, 3]]  # N=0 S=1 E=2 W=3

    # --- zones & baseline wait ---------------------------------------------
    zone_nodes: dict[int, list[int]] = defaultdict(list)
    for sid in intersections:
        zid = nodes[sid].get("zone_id", 0)
        zone_nodes[zid].append(sid)

    zones = sorted(zone_nodes.keys())
    baseline_zone_wait = [15.0 + len(zone_nodes[z]) * 2.0 for z in zones]
    zone_map = {sid: nodes[sid].get("zone_id", 0) for sid in intersections}

    return {
        "intersections": intersections,
        "num_intersections": len(intersections),
        "approach_names": _DIRECTIONS,
        "phases": phases,
        "neighbors": neighbors,
        "link_travel_s": link_travel_s,
        "base_rate": base_rate,
        "zones": zones,
        "baseline_zone_wait": baseline_zone_wait,
        "zone_map": zone_map,
    }
