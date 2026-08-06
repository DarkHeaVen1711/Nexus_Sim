"""Reward terms for the MARL signal-control agents (TR-ML-04, US-E03).

The per-agent reward is a weighted combination of a local pressure term and a
network-wide equity term (TECH_STACK.md §Subsystem 3):

    reward_i = alpha * pressure_i + beta * equity_global

    pressure_i      : local term — negative total queued vehicles at intersection
                      i. A large queue is bad, so reward maximisation pushes it
                      toward zero.
    equity_global   : network term — negative weighted sum of per-zone average
                      wait, where each zone weight is the inverse of that zone's
                      baseline service level. Under-served zones therefore
                      penalise the shared reward more, which is what makes the
                      controller equity-aware rather than speed-only.

Both terms are computed in separate functions so an evaluator can read them
independently (US-E03). Alpha/beta are tunable; their tradeoff curve is a Phase
9 deliverable.
"""

from __future__ import annotations

from typing import List, Optional, Sequence


def gini_coefficient(values: Sequence[float]) -> float:
    """Gini coefficient of inequality over a sequence of zone metrics."""
    v = [float(x) for x in values]
    n = len(v)
    if n <= 1:
        return 0.0
    total = sum(v)
    if total <= 0.0:
        return 0.0
    diff = sum(abs(a - b) for a in v for b in v)
    return diff / (2.0 * n * total)


def local_pressure(queues: Sequence[float]) -> float:
    """Local pressure term for one intersection.

    Defined as the negative total queue across the intersection's approaches:
    the larger the backlog, the stronger the penalty. Returns 0 for an empty
    intersection, negative otherwise.
    """
    return -float(sum(queues))


def baseline_zone_weights(
    baseline_waits: Sequence[float],
    normalize: bool = True,
) -> List[float]:
    """Inverse-of-service-level zone weights for the equity term.

    A zone whose baseline (fixed-cycle) wait is high is under-served and must
    weigh more heavily in the shared equity term. An epsilon floor avoids
    division by zero for perfectly served zones.
    """
    weights = [1.0 / (float(w) + 1e-3) for w in baseline_waits]
    if normalize:
        total = sum(weights)
        if total > 0.0:
            weights = [w / total for w in weights]
    return weights


def equity_term(
    zone_waits: Sequence[float],
    zone_weights: Optional[Sequence[float]] = None,
) -> float:
    """Network-wide equity term: negative weighted sum of per-zone waits.

    With the default equal weights this is simply the negative mean zone wait;
    passing inverse-service-level weights (see ``baseline_zone_weights``) makes
    under-served zones dominate the penalty.
    """
    waits = [float(w) for w in zone_waits]
    n = len(waits)
    if n == 0:
        return 0.0
    if zone_weights is None:
        weights = [1.0 / n] * n
    else:
        weights = [float(w) for w in zone_weights]
    return -sum(w * wait for w, wait in zip(weights, waits))


def combined_reward(
    pressure_terms: Sequence[float],
    zone_waits: Sequence[float],
    alpha: float,
    beta: float,
    zone_weights: Optional[Sequence[float]] = None,
) -> dict:
    """Combine local pressure and equity terms into per-agent rewards.

    Returns the per-agent reward list plus the components (mean pressure,
    equity term, Gini) so a trainer can log each piece separately (US-D03).
    """
    equity = equity_term(zone_waits, zone_weights)
    rewards = [
        alpha * pressure + beta * equity for pressure in pressure_terms
    ]
    return {
        "rewards": rewards,
        "mean_pressure": (
            sum(pressure_terms) / len(pressure_terms) if pressure_terms else 0.0
        ),
        "equity": equity,
        "gini": gini_coefficient(zone_waits),
    }
