"""Observation space design for one intersection agent (TR-ML-02, Phase 7.1).

Each agent observes a flat, normalised vector (shape documented in
``ml/env/README.md``):

    [queue_N, queue_S, queue_E, queue_W,       # 4 per-approach queue lengths
     phase,                                    # current phase index (0.0 / 1.0)
     time_in_phase,                            # seconds in phase, normalised
     time_of_day,                              # hour-of-day, normalised 0..1
     pressure_N, pressure_S, pressure_E, pressure_W]  # 4 neighbour pressures

Total dimension = 11. All entries live in [0, 1] so the values map directly
onto a Box observation space with no re-scaling.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np

OBSERVATION_DIM = 11
NUM_APPROACHES = 4


def build_observation(
    queues: Sequence[float],
    phase: float,
    time_in_phase: float,
    time_of_day: float,
    neighbor_pressure: Sequence[float],
    max_queue: float,
) -> np.ndarray:
    """Build the flat observation vector for one intersection agent."""
    if len(queues) != NUM_APPROACHES:
        raise ValueError("queues must have length %d" % NUM_APPROACHES)
    if len(neighbor_pressure) != NUM_APPROACHES:
        raise ValueError(
            "neighbor_pressure must have length %d" % NUM_APPROACHES
        )
    return np.array(
        [q / max_queue for q in queues]
        + [float(phase), float(time_in_phase), float(time_of_day)]
        + [p / max_queue for p in neighbor_pressure],
        dtype=np.float32,
    )
