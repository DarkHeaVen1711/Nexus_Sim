"""Phase 28 - Particle Swarm Optimization (PSO) for Continuous Calibration (SC-2).

Implements swarm particle kinematics with inertia, cognitive, and social acceleration components.
"""

from __future__ import annotations

from typing import Any, Dict
import numpy as np

from .base_optimizer import BaseOptimizer


class ParticleSwarmOptimizer(BaseOptimizer):
    """Swarm intelligence optimizer for continuous simulation parameters."""

    def __init__(
        self,
        bounds: Dict[str, tuple[float, float]],
        fitness_fn: Any,
        num_particles: int = 15,
        max_iters: int = 20,
        w: float = 0.7,
        c1: float = 1.5,
        c2: float = 1.5,
        seed: int = 42,
    ):
        super().__init__(bounds, fitness_fn, max_evals=num_particles * max_iters, seed=seed)
        self.num_particles = num_particles
        self.max_iters = max_iters
        self.w = w
        self.c1 = c1
        self.c2 = c2

    def optimize(self) -> Dict[str, Any]:
        dim = len(self.param_names)
        # Initialize positions and velocities
        positions = self.rng.uniform(self.lower_bounds, self.upper_bounds, (self.num_particles, dim))
        velocities = self.rng.uniform(
            -(self.upper_bounds - self.lower_bounds) * 0.1,
            (self.upper_bounds - self.lower_bounds) * 0.1,
            (self.num_particles, dim),
        )

        pbest_pos = positions.copy()
        pbest_fit = np.full(self.num_particles, -float("inf"))
        gbest_pos = positions[0].copy()
        gbest_fit = -float("inf")

        for iteration in range(self.max_iters):
            mean_fit = 0.0
            for i in range(self.num_particles):
                p_dict = self.array_to_dict(positions[i])
                fit = self.fitness_fn(p_dict)
                mean_fit += fit

                if fit > pbest_fit[i]:
                    pbest_fit[i] = fit
                    pbest_pos[i] = positions[i].copy()

                if fit > gbest_fit:
                    gbest_fit = fit
                    gbest_pos = positions[i].copy()

            mean_fit /= self.num_particles
            self.convergence_history.append({
                "iteration": iteration + 1,
                "best_fitness": round(float(gbest_fit), 3),
                "mean_fitness": round(float(mean_fit), 3),
            })

            # Update particle velocities and positions
            r1 = self.rng.rand(self.num_particles, dim)
            r2 = self.rng.rand(self.num_particles, dim)
            velocities = (
                self.w * velocities
                + self.c1 * r1 * (pbest_pos - positions)
                + self.c2 * r2 * (gbest_pos - positions)
            )
            positions = np.clip(positions + velocities, self.lower_bounds, self.upper_bounds)

        self.best_fitness = float(gbest_fit)
        self.best_params = self.array_to_dict(gbest_pos)

        return {
            "algorithm": "PSO",
            "best_params": self.best_params,
            "best_fitness": self.best_fitness,
            "convergence": self.convergence_history,
        }
