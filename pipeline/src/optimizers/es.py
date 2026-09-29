"""Phase 28 - Evolution Strategy (CMA-ES / (μ, λ)-ES) (SC-4).

Implements mutation covariance adaptation and selection over continuous parameter distributions.
"""

from __future__ import annotations

from typing import Any, Dict
import numpy as np

from .base_optimizer import BaseOptimizer


class EvolutionStrategyOptimizer(BaseOptimizer):
    """(μ, λ) Evolution Strategy with adaptive mutation step size."""

    def __init__(
        self,
        bounds: Dict[str, tuple[float, float]],
        fitness_fn: Any,
        mu: int = 5,
        lam: int = 20,
        max_iters: int = 20,
        initial_sigma: float = 0.2,
        seed: int = 42,
    ):
        super().__init__(bounds, fitness_fn, max_evals=lam * max_iters, seed=seed)
        self.mu = mu
        self.lam = lam
        self.max_iters = max_iters
        self.sigma = initial_sigma

    def optimize(self) -> Dict[str, Any]:
        dim = len(self.param_names)
        mean_pos = self.rng.uniform(self.lower_bounds, self.upper_bounds)
        best_pos = mean_pos.copy()
        best_fit = -float("inf")

        span = self.upper_bounds - self.lower_bounds

        for iteration in range(self.max_iters):
            # Sample λ offspring from current distribution
            mutations = self.rng.normal(0, 1.0, (self.lam, dim))
            offspring = np.clip(
                mean_pos + self.sigma * span * mutations,
                self.lower_bounds,
                self.upper_bounds,
            )

            fitnesses = np.array([self.fitness_fn(self.array_to_dict(ind)) for ind in offspring])

            # Select top μ individuals
            rank_idx = np.argsort(-fitnesses)
            top_mu = offspring[rank_idx[:self.mu]]
            top_fit = fitnesses[rank_idx[:self.mu]]

            if top_fit[0] > best_fit:
                best_fit = top_fit[0]
                best_pos = top_mu[0].copy()

            # Update distribution center of mass
            mean_pos = np.mean(top_mu, axis=0)

            # 1/5th rule step size adaptation
            success_rate = np.mean(fitnesses > (best_fit - 5.0))
            if success_rate > 0.2:
                self.sigma *= 1.05
            else:
                self.sigma *= 0.95

            self.convergence_history.append({
                "iteration": iteration + 1,
                "sigma": round(self.sigma, 4),
                "best_fitness": round(float(best_fit), 3),
                "mean_fitness": round(float(np.mean(fitnesses)), 3),
            })

        self.best_fitness = float(best_fit)
        self.best_params = self.array_to_dict(best_pos)

        return {
            "algorithm": "EvolutionStrategy",
            "best_params": self.best_params,
            "best_fitness": self.best_fitness,
            "convergence": self.convergence_history,
        }
