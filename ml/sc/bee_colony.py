"""Phase 29 - Artificial Bee Colony (ABC) for Signal Split Optimization (SC-6).

Models employed, onlooker, and scout bees searching multi-phase green timing splits.
"""

from __future__ import annotations

from typing import Any, Dict, List
import numpy as np


class ArtificialBeeColonyOptimizer:
    """ABC algorithm for multi-phase signal cycle green-split optimization."""

    def __init__(
        self,
        num_phases: int = 4,
        colony_size: int = 20,
        max_cycles: int = 15,
        limit: int = 5,
        cycle_time: float = 90.0,
    ):
        self.num_phases = num_phases
        self.colony_size = colony_size
        self.max_cycles = max_cycles
        self.limit = limit
        self.cycle_time = cycle_time
        self.num_employed = colony_size // 2

    def optimize(self, phase_demands: List[float]) -> Dict[str, Any]:
        """Evolve green phase allocations matching relative approach demands."""
        demands = np.array(phase_demands, dtype=np.float32)
        total_demand = max(1.0, float(np.sum(demands)))

        # Food sources: green times per phase summing to cycle_time
        food_sources = np.random.dirichlet(np.ones(self.num_phases), size=self.num_employed) * self.cycle_time
        trials = np.zeros(self.num_employed, dtype=np.int32)

        def eval_fitness(splits: np.ndarray) -> float:
            # Fitness measures alignment between green time and traffic demand
            ideal = (demands / total_demand) * self.cycle_time
            loss = float(np.sum((splits - ideal) ** 2))
            return 1.0 / (1.0 + loss)

        fitness = np.array([eval_fitness(fs) for fs in food_sources])

        best_idx = int(np.argmax(fitness))
        best_split = food_sources[best_idx].copy()
        best_fitness = fitness[best_idx]

        for _ in range(self.max_cycles):
            # Employed bees phase
            for i in range(self.num_employed):
                k = np.random.choice([j for j in range(self.num_employed) if j != i])
                phi = np.random.uniform(-1.0, 1.0, self.num_phases)
                v = np.clip(food_sources[i] + phi * (food_sources[i] - food_sources[k]), 5.0, self.cycle_time)
                v = (v / np.sum(v)) * self.cycle_time
                f_v = eval_fitness(v)
                if f_v > fitness[i]:
                    food_sources[i] = v
                    fitness[i] = f_v
                    trials[i] = 0
                else:
                    trials[i] += 1

            # Onlooker bees phase
            probs = fitness / np.sum(fitness)
            for _ in range(self.num_employed):
                i = int(np.random.choice(range(self.num_employed), p=probs))
                k = np.random.choice([j for j in range(self.num_employed) if j != i])
                phi = np.random.uniform(-1.0, 1.0, self.num_phases)
                v = np.clip(food_sources[i] + phi * (food_sources[i] - food_sources[k]), 5.0, self.cycle_time)
                v = (v / np.sum(v)) * self.cycle_time
                f_v = eval_fitness(v)
                if f_v > fitness[i]:
                    food_sources[i] = v
                    fitness[i] = f_v
                    trials[i] = 0
                else:
                    trials[i] += 1

            # Scout bees phase
            for i in range(self.num_employed):
                if trials[i] > self.limit:
                    food_sources[i] = np.random.dirichlet(np.ones(self.num_phases)) * self.cycle_time
                    fitness[i] = eval_fitness(food_sources[i])
                    trials[i] = 0

            cur_best = int(np.argmax(fitness))
            if fitness[cur_best] > best_fitness:
                best_fitness = fitness[cur_best]
                best_split = food_sources[cur_best].copy()

        return {
            "optimal_splits_seconds": [round(float(s), 1) for s in best_split],
            "cycle_time": self.cycle_time,
            "best_fitness": round(float(best_fitness), 4),
        }
