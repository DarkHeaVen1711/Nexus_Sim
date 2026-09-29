"""Phase 28 - Simulated Annealing for Continuous Calibration (SC-3).

Implements Metropolis acceptance criterion with exponential temperature cooling schedule.
"""

from __future__ import annotations

import math
from typing import Any, Dict
import numpy as np

from .base_optimizer import BaseOptimizer


class SimulatedAnnealingOptimizer(BaseOptimizer):
    """Metropolis-Hastings stochastic parameter annealing optimizer."""

    def __init__(
        self,
        bounds: Dict[str, tuple[float, float]],
        fitness_fn: Any,
        initial_temp: float = 100.0,
        cooling_rate: float = 0.92,
        steps_per_temp: int = 10,
        max_iters: int = 25,
        seed: int = 42,
    ):
        super().__init__(bounds, fitness_fn, max_evals=steps_per_temp * max_iters, seed=seed)
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.steps_per_temp = steps_per_temp
        self.max_iters = max_iters

    def optimize(self) -> Dict[str, Any]:
        dim = len(self.param_names)
        curr_pos = self.rng.uniform(self.lower_bounds, self.upper_bounds)
        curr_fit = self.fitness_fn(self.array_to_dict(curr_pos))

        best_pos = curr_pos.copy()
        best_fit = curr_fit
        temp = self.initial_temp

        for iteration in range(self.max_iters):
            accepted_fits = []
            for _ in range(self.steps_per_temp):
                # Gaussian candidate perturbation
                step_size = (self.upper_bounds - self.lower_bounds) * 0.1 * (temp / self.initial_temp)
                candidate = np.clip(
                    curr_pos + self.rng.normal(0, step_size, dim),
                    self.lower_bounds,
                    self.upper_bounds,
                )
                cand_fit = self.fitness_fn(self.array_to_dict(candidate))
                delta = cand_fit - curr_fit

                # Metropolis criterion
                if delta > 0 or self.rng.rand() < math.exp(delta / max(1e-4, temp)):
                    curr_pos = candidate
                    curr_fit = cand_fit

                accepted_fits.append(curr_fit)
                if curr_fit > best_fit:
                    best_fit = curr_fit
                    best_pos = curr_pos.copy()

            self.convergence_history.append({
                "iteration": iteration + 1,
                "temperature": round(temp, 2),
                "best_fitness": round(float(best_fit), 3),
                "mean_fitness": round(float(np.mean(accepted_fits)), 3),
            })
            temp *= self.cooling_rate

        self.best_fitness = float(best_fit)
        self.best_params = self.array_to_dict(best_pos)

        return {
            "algorithm": "SimulatedAnnealing",
            "best_params": self.best_params,
            "best_fitness": self.best_fitness,
            "convergence": self.convergence_history,
        }
