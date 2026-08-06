"""NexusSim MARL environment (Phase 7).

Exposes the Gym-compatible environment wrapping simulation state snapshots,
plus the standalone reward and observation modules that TR-ML-01..04 require.
"""

from .nexus_sim_env import NexusSimEnv, MAX_QUEUE, N_PHASES
from .reward import (
    combined_reward,
    equity_term,
    local_pressure,
    gini_coefficient,
)
from .toy_graph import build_toy_graph

__all__ = [
    "NexusSimEnv",
    "MAX_QUEUE",
    "N_PHASES",
    "combined_reward",
    "equity_term",
    "local_pressure",
    "gini_coefficient",
    "build_toy_graph",
]
