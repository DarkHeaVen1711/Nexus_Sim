"""Phase 29 - Ant Colony System (ACS) for Dynamic Vehicle Rerouting (SC-5).

Implements distributed pheromone deposit, evaporation, and stochastic path selection
to balance congested road segments and compute updated edge weights.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import numpy as np


class AntColonyRouter:
    """Pheromone-based distributed route optimizer."""

    def __init__(
        self,
        nodes: List[int],
        edges: List[Tuple[int, int, float]],  # (u, v, base_cost)
        num_ants: int = 15,
        alpha: float = 1.0,  # Pheromone sensitivity
        beta: float = 2.0,   # Distance/heuristic sensitivity
        evaporation_rate: float = 0.15,
        q: float = 100.0,
    ):
        self.nodes = nodes
        self.edges = edges
        self.num_ants = num_ants
        self.alpha = alpha
        self.beta = beta
        self.rho = evaporation_rate
        self.q = q

        # Edge adjacency and pheromone tables
        self.adj: Dict[int, List[Tuple[int, float]]] = {u: [] for u in nodes}
        self.pheromones: Dict[Tuple[int, int], float] = {}
        self.edge_costs: Dict[Tuple[int, int], float] = {}

        for u, v, cost in edges:
            self.adj[u].append((v, cost))
            self.pheromones[(u, v)] = 1.0
            self.edge_costs[(u, v)] = cost

    def optimize_routes(self, origin: int, destination: int, iterations: int = 10) -> Dict[str, Any]:
        """Evolve ant colony paths from origin to destination."""
        best_path: List[int] = []
        best_cost = float("inf")

        for _ in range(iterations):
            paths = []
            costs = []

            for _ in range(self.num_ants):
                curr = origin
                visited = {curr}
                path = [curr]
                total_cost = 0.0

                while curr != destination and len(visited) < len(self.nodes):
                    neighbors = [v for v, _ in self.adj.get(curr, []) if v not in visited]
                    if not neighbors:
                        break

                    # Probability distribution proportional to tau^alpha * eta^beta
                    probs = []
                    for n in neighbors:
                        tau = self.pheromones.get((curr, n), 1.0) ** self.alpha
                        eta = (1.0 / max(1.0, self.edge_costs.get((curr, n), 10.0))) ** self.beta
                        probs.append(tau * eta)

                    total_p = sum(probs)
                    if total_p == 0:
                        probs = [1.0 / len(neighbors)] * len(neighbors)
                    else:
                        probs = [p / total_p for p in probs]

                    next_node = int(np.random.choice(neighbors, p=probs))
                    total_cost += self.edge_costs.get((curr, next_node), 10.0)
                    visited.add(next_node)
                    path.append(next_node)
                    curr = next_node

                if curr == destination:
                    paths.append(path)
                    costs.append(total_cost)
                    if total_cost < best_cost:
                        best_cost = total_cost
                        best_path = path

            # Evaporate pheromones
            for edge in self.pheromones:
                self.pheromones[edge] *= (1.0 - self.rho)

            # Deposit pheromone along successful paths
            for p, c in zip(paths, costs):
                deposit = self.q / max(1.0, c)
                for i in range(len(p) - 1):
                    e = (p[i], p[i + 1])
                    if e in self.pheromones:
                        self.pheromones[e] += deposit

        return {
            "origin": origin,
            "destination": destination,
            "best_path": best_path,
            "best_cost": round(best_cost, 2),
            "updated_edge_weights": {f"{u}->{v}": round(self.pheromones[(u, v)], 3) for u, v in self.pheromones},
        }
