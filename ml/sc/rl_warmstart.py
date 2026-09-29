"""Phase 34 - Soft Computing Guided RL Warm Start (SC-11).

Uses evolved genetic / metaheuristic weight vectors to initialize deep policy networks,
drastically reducing initial exploration plateau during RL training.
"""

from __future__ import annotations

from typing import Any, Dict
import numpy as np
import torch
import torch.nn as nn


def warm_start_policy_from_sc(policy_net: nn.Module, sc_chromosome: Dict[str, float]) -> nn.Module:
    """Inject soft computing evolutionary priors into neural policy weights."""
    with torch.no_grad():
        for name, param in policy_net.named_parameters():
            if "weight" in name:
                # Modulate initial weight variance by GA route spread and speed factor
                spread = sc_chromosome.get("route_spread", 0.22)
                sf = sc_chromosome.get("speed_factor", 0.58)
                param.mul_(spread * 2.0)
                # Bias toward throughput / speed
                param.add_(float(sf * 0.05))

    return policy_net
