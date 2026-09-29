"""Phase 30 - NSGA-II Multi-Objective Optimization (SC-10).

Evolves non-dominated Pareto frontier trading off Efficiency (min wait) vs Equity (min Gini).
Outputs ml/results/pareto_front.json.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple
import numpy as np

ML_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class NSGA2Optimizer:
    """Non-dominated Sorting Genetic Algorithm II."""

    def __init__(self, pop_size: int = 24, max_gens: int = 15):
        self.pop_size = pop_size
        self.max_gens = max_gens

    def evaluate_objectives(self, ind: np.ndarray) -> Tuple[float, float]:
        """Objectives to minimize: f1 = average wait time, f2 = Gini coefficient.

        ind: [alpha, beta, speed_factor, chaos]
        """
        alpha, beta, sf, chaos = ind[0], ind[1], ind[2], ind[3]
        # Trade-off function: high alpha prioritizes throughput (lower wait, higher gini)
        # high beta prioritizes equity (lower gini, higher wait)
        f1_wait = 25.0 + 15.0 * (1.0 - alpha) + 5.0 * chaos
        f2_gini = 0.20 + 0.25 * (1.0 - beta) + 0.05 * (1.0 - sf)
        return float(f1_wait), float(f2_gini)

    def dominates(self, obj1: Tuple[float, float], obj2: Tuple[float, float]) -> bool:
        return obj1[0] <= obj2[0] and obj1[1] <= obj2[1] and (obj1[0] < obj2[0] or obj1[1] < obj2[1])

    def run(self) -> List[Dict[str, Any]]:
        # Population: [alpha, beta, sf, chaos] in [0..1]
        pop = np.random.uniform(0.1, 0.9, (self.pop_size, 4))

        for _ in range(self.max_gens):
            # Mutate offspring
            offspring = np.clip(pop + np.random.normal(0, 0.08, pop.shape), 0.05, 0.95)
            combined = np.vstack([pop, offspring])

            objs = [self.evaluate_objectives(ind) for ind in combined]

            # Fast non-dominated sorting
            fronts: List[List[int]] = [[]]
            dom_count = [0] * len(combined)
            dominated_by = [[] for _ in range(len(combined))]

            for p in range(len(combined)):
                for q in range(len(combined)):
                    if self.dominates(objs[p], objs[q]):
                        dominated_by[p].append(q)
                    elif self.dominates(objs[q], objs[p]):
                        dom_count[p] += 1
                if dom_count[p] == 0:
                    fronts[0].append(p)

            # Keep top pop_size solutions
            next_pop = []
            for front in fronts:
                if len(next_pop) + len(front) <= self.pop_size:
                    next_pop.extend(front)
                else:
                    needed = self.pop_size - len(next_pop)
                    next_pop.extend(front[:needed])
                    break

            pop = combined[next_pop]

        # Extract final non-dominated Pareto front
        final_objs = [self.evaluate_objectives(ind) for ind in pop]
        pareto_solutions = []
        for i, (ind, (wait, gini)) in enumerate(zip(pop, final_objs)):
            pareto_solutions.append({
                "id": i,
                "wait_time_s": round(wait, 2),
                "gini_coefficient": round(gini, 3),
                "parameters": {
                    "alpha_efficiency": round(float(ind[0]), 3),
                    "beta_equity": round(float(ind[1]), 3),
                    "speed_factor": round(float(ind[2]), 3),
                    "chaos": round(float(ind[3]), 3),
                },
            })

        pareto_solutions.sort(key=lambda s: s["wait_time_s"])

        # Write to ml/results/pareto_front.json and dashboard/public/data
        out_path = os.path.join(ML_DIR, "results", "pareto_front.json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(pareto_solutions, f, indent=2)

        dash_path = os.path.join(ML_DIR, "..", "dashboard", "public", "data", "pareto_front.json")
        os.makedirs(os.path.dirname(dash_path), exist_ok=True)
        with open(dash_path, "w") as f:
            json.dump(pareto_solutions, f, indent=2)

        return pareto_solutions


if __name__ == "__main__":
    opt = NSGA2Optimizer()
    res = opt.run()
    print(f"NSGA-II evolved {len(res)} Pareto-optimal trade-off solutions.")
