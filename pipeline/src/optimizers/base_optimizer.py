"""Phase 28 - Base Continuous Parameter Optimizer Interface (SC-1..4).

Standardizes search spaces, evaluation protocols, and bounds for GA, PSO, SA, and ES.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Tuple
import numpy as np


class BaseOptimizer(ABC):
    """Abstract base class for metaheuristic calibration optimizers."""

    def __init__(
        self,
        bounds: Dict[str, Tuple[float, float]],
        fitness_fn: Callable[[Dict[str, float]], float],
        max_evals: int = 100,
        seed: int = 42,
    ):
        self.bounds = bounds
        self.param_names = list(bounds.keys())
        self.lower_bounds = np.array([bounds[k][0] for k in self.param_names], dtype=np.float64)
        self.upper_bounds = np.array([bounds[k][1] for k in self.param_names], dtype=np.float64)
        self.fitness_fn = fitness_fn
        self.max_evals = max_evals
        self.rng = np.random.RandomState(seed)

        self.best_params: Dict[str, float] = {}
        self.best_fitness: float = -float("inf")
        self.convergence_history: List[Dict[str, float]] = []

    def array_to_dict(self, arr: np.ndarray) -> Dict[str, float]:
        """Convert float numpy array into parameter dictionary."""
        clipped = np.clip(arr, self.lower_bounds, self.upper_bounds)
        return {name: float(clipped[i]) for i, name in enumerate(self.param_names)}

    @abstractmethod
    def optimize(self) -> Dict[str, Any]:
        """Execute optimization run and return results dictionary."""
        pass
