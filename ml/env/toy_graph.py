"""Toy 4-intersection network for rapid MAPPO iteration (Phase 7.4).

A 2x2 grid of signalised intersections, each with four approaches ordered
``["N", "S", "E", "W"]``. Corner intersections connect to two internal
neighbours and two peripheral entry/exit points, giving every intersection
exactly four approaches.

The demand is hardcoded and repeatable: each approach has a deterministic
24-hour arrival-rate profile with AM/PM peaks, so training runs are
reproducible without waiting on a real-city ``graph.json``. The structure
mirrors what ``graph.json`` gives the C++ engine (nodes/edges/zones) at a
scale small enough for a fast feedback loop.
"""

from __future__ import annotations

APPROACH_NAMES = ["N", "S", "E", "W"]

# Phase 0 greens the vertical approaches (N, S); phase 1 the horizontal (E, W).
PHASES = [[0, 1], [2, 3]]

# Approach -> downstream intersection (None = peripheral entry/exit point).
NEIGHBORS = {
    0: {"N": None, "S": 2, "E": 1, "W": None},
    1: {"N": None, "S": 3, "E": None, "W": 0},
    2: {"N": 0, "S": None, "E": 3, "W": None},
    3: {"N": 1, "S": None, "E": None, "W": 2},
}

# Link travel time (seconds) for each internal directed approach.
LINK_TRAVEL_S = {
    (0, 2): 8.0, (2, 0): 8.0,
    (0, 1): 8.0, (1, 0): 8.0,
    (1, 3): 8.0, (3, 1): 8.0,
    (2, 3): 8.0, (3, 2): 8.0,
}

# Base peak arrival rate per approach in vehicles/second. Each intersection
# carries one heavy approach (0.30 veh/s, well above the ~0.20 veh/s
# per-approach capacity at the baseline 40% green fraction) on a PERIPHERAL
# (exit) approach, so discharging it never injects vehicles into a downstream
# intersection — no internal-feedback gridlock. The heavy phase alternates
# between intersections (0 and 2 are phase-0-heavy, 1 and 3 are phase-1-heavy),
# so no global "always extend one phase" policy wins: it would clear its own
# heavy approaches while starving the other two intersections' heavy demand
# into an ever-growing queue. A fixed cycle lets all four heavy approaches back
# up (0.10 veh/s net), while a policy that reads local queue state and extends
# whichever phase is congested at each intersection clears all of them — the
# regime MAPPO is meant to exploit (TR-ML-05).
BASE_RATE = {
    0: [0.30, 0.05, 0.06, 0.05],
    1: [0.05, 0.06, 0.30, 0.05],
    2: [0.06, 0.30, 0.05, 0.05],
    3: [0.05, 0.06, 0.30, 0.05],
}

# Per-zone baseline fixed-cycle wait (seconds), used for inverse-of-service
# equity weights. A higher baseline marks a more under-served zone.
BASELINE_ZONE_WAIT = [12.0, 15.0, 14.0, 18.0]


def time_of_day_factor(hour: float) -> float:
    """Deterministic AM/PM peak multiplier for a fractional hour 0..24."""
    keys = [(0.0, 0.25), (8.0, 1.0), (12.0, 0.5), (18.0, 1.0), (24.0, 0.25)]
    t = hour % 24.0
    for (h0, v0), (h1, v1) in zip(keys, keys[1:]):
        if h0 <= t <= h1:
            frac = (t - h0) / (h1 - h0) if h1 > h0 else 1.0
            return v0 + frac * (v1 - v0)
    return 0.25


def build_toy_graph() -> dict:
    """Return the toy graph descriptor consumed by the environment."""
    return {
        "intersections": [0, 1, 2, 3],
        "num_intersections": 4,
        "approach_names": APPROACH_NAMES,
        "phases": PHASES,
        "neighbors": NEIGHBORS,
        "link_travel_s": LINK_TRAVEL_S,
        "base_rate": BASE_RATE,
        "zones": [0, 1, 2, 3],
        "baseline_zone_wait": BASELINE_ZONE_WAIT,
    }
