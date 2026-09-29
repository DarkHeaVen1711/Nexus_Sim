"""Phase 30 - Genetic Programming (GP) for Symbolic Signal Decision Trees (SC-8).

Evolves interpretable symbolic tree expressions mapping queue and wait features
into binary traffic light phase extension/switch decisions.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List
import numpy as np


class GPNode:
    """Node in an evolved symbolic decision tree."""

    def __init__(
        self,
        op: str,
        left: GPNode | None = None,
        right: GPNode | None = None,
        feature_idx: int = 0,
        threshold: float = 0.5,
        action: int = 0,
    ):
        self.op = op  # "COND" (if x[feat] > thresh), "ACTION" (leaf: 0=EXTEND, 1=SWITCH)
        self.left = left
        self.right = right
        self.feature_idx = feature_idx
        self.threshold = threshold
        self.action = action

    def evaluate(self, x: List[float]) -> int:
        """Evaluate tree on input feature vector."""
        if self.op == "ACTION":
            return self.action
        val = x[self.feature_idx] if self.feature_idx < len(x) else 0.0
        if val > self.threshold:
            return self.left.evaluate(x) if self.left else self.action
        else:
            return self.right.evaluate(x) if self.right else self.action

    def to_c_expr(self) -> str:
        """Export tree as valid C++ conditional statement."""
        if self.op == "ACTION":
            return f"{self.action}"
        l_str = self.left.to_c_expr() if self.left else "0"
        r_str = self.right.to_c_expr() if self.right else "1"
        return f"(x[{self.feature_idx}] > {self.threshold:.3f} ? {l_str} : {r_str})"


class GeneticProgrammingTree:
    """Evolutionary algorithm searching decision trees."""

    def __init__(self, population_size: int = 20, max_generations: int = 10):
        self.pop_size = population_size
        self.max_gens = max_generations
        self.best_tree: GPNode | None = None
        self.best_fitness: float = -float("inf")

    def _random_tree(self, depth: int = 2) -> GPNode:
        if depth == 0 or np.random.rand() < 0.3:
            return GPNode(op="ACTION", action=int(np.random.choice([0, 1])))
        left = self._random_tree(depth - 1)
        right = self._random_tree(depth - 1)
        feat = int(np.random.randint(0, 4))
        thresh = float(np.random.uniform(0.1, 0.9))
        return GPNode(op="COND", left=left, right=right, feature_idx=feat, threshold=thresh)

    def evolve(self, X: List[List[float]], y: List[int]) -> Dict[str, Any]:
        """Evolve population against decision labels."""
        population = [self._random_tree(depth=2) for _ in range(self.pop_size)]

        def fitness(tree: GPNode) -> float:
            correct = sum(1 for feat, label in zip(X, y) if tree.evaluate(feat) == label)
            return correct / max(1, len(X))

        for _ in range(self.max_gens):
            fits = [fitness(t) for t in population]
            best_idx = int(np.argmax(fits))
            if fits[best_idx] > self.best_fitness:
                self.best_fitness = fits[best_idx]
                self.best_tree = population[best_idx]

            # Elitism + tournament mutation
            new_pop = [population[best_idx]]
            while len(new_pop) < self.pop_size:
                cand = self._random_tree(depth=2)
                new_pop.append(cand)
            population = new_pop

        return {
            "best_accuracy": round(self.best_fitness, 4),
            "tree_expression": self.best_tree.to_c_expr() if self.best_tree else "",
        }
