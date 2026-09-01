"""Deterministic micro traffic simulator for the toy network (TR-ML-01).

Steps the 2x2 grid in fixed ``dt`` sub-steps: per-approach Poisson arrivals
from the hardcoded demand, saturation-flow discharge through green
approaches, and link travel times for vehicles moving between intersections.
Tracks per-approach queue and accumulated waiting so the environment can
compute the pressure and equity reward terms (TR-ML-04).

The simulation is pure Python and runs offline — no live C++ engine call
during training (TR-5), matching the plan's "wraps simulation state snapshot".
"""

from __future__ import annotations

import numpy as np

from .controller import IntersectionController
from .toy_graph import PHASES, build_toy_graph, time_of_day_factor


class TrafficSim:
    """Network-level simulator over the 2x2 toy graph."""

    def __init__(
        self,
        graph: dict,
        seed: int = 0,
        dt: float = 1.0,
        decision_interval: float = 5.0,
        start_hour: float = 8.0,
    ):
        self.graph = graph
        self.dt = dt
        self.decision_interval = decision_interval
        self.start_hour = start_hour
        self.rng = np.random.default_rng(seed)
        self.sim_time = 0.0
        self.intersections = graph["intersections"]
        self.controllers = {
            i: IntersectionController(decision_interval) for i in self.intersections
        }
        self.queues = {i: [0] * 4 for i in self.intersections}
        self.wait_acc = {i: [0.0] * 4 for i in self.intersections}
        self.travelling = []
        self.completed = 0
        self._arrivals = {i: [0] * 4 for i in self.intersections}
        self._accumulate_arrivals()

    def _rate(self, intersection: int, approach: int, hour: float) -> float:
        base = self.graph["base_rate"][intersection][approach]
        return base * time_of_day_factor(hour)

    def _accumulate_arrivals(self) -> None:
        """Deterministically seed upcoming arrivals for the whole episode."""
        for i in self.intersections:
            for a in range(4):
                self._arrivals[i][a] = 0

    def _hour(self) -> float:
        return (self.start_hour + self.sim_time / 3600.0) % 24.0

    def _step_arrivals(self) -> None:
        hour = self._hour()
        for i in self.intersections:
            for a in range(4):
                rate = self._rate(i, a, hour)
                arrivals = self.rng.poisson(rate * self.dt)
                if arrivals > 0:
                    self.queues[i][a] += int(arrivals)

    def _step_discharge(self) -> None:
        saturation = 0.5  # vehicles/second discharged through a green approach
        for i in self.intersections:
            controller = self.controllers[i]
            for a in range(4):
                if not controller.is_green(a, PHASES):
                    continue
                discharge = min(self.queues[i][a], saturation * self.dt)
                if discharge <= 0:
                    continue
                self.queues[i][a] -= discharge
                downstream = self.graph["neighbors"][i][
                    self.graph["approach_names"][a]
                ]
                if downstream is None:
                    self.completed += discharge
                else:
                    travel = self.graph["link_travel_s"][(i, downstream)]
                    self.travelling.append((self.sim_time + travel, downstream, a))

    def _step_travel(self) -> None:
        arrived = [t for t in self.travelling if t[0] <= self.sim_time]
        self.travelling = [t for t in self.travelling if t[0] > self.sim_time]
        for _, downstream, approach in arrived:
            self.queues[downstream][approach] += 1

    def _step_wait(self) -> None:
        for i in self.intersections:
            for a in range(4):
                self.wait_acc[i][a] += self.queues[i][a] * self.dt

    def _snapshot_interval_metrics(self) -> dict:
        avg_queue = {}
        zone_wait = {}
        interval = self.decision_interval
        for i in self.intersections:
            per_approach = [acc / interval for acc in self.wait_acc[i]]
            zone_wait[i] = float(sum(per_approach))
            avg_queue[i] = zone_wait[i]
            self.wait_acc[i] = [0.0] * 4
        return {"avg_queue": avg_queue, "zone_wait": zone_wait}

    def step(self, actions: dict) -> dict:
        """Advance one decision interval; apply ``actions`` at phase boundaries."""
        for i in self.intersections:
            if self.controllers[i].is_decision_ready():
                self.controllers[i].apply_action(actions.get(i, 0))

        n_sub = int(round(self.decision_interval / self.dt))
        for _ in range(n_sub):
            for i in self.intersections:
                self.controllers[i].step(self.dt)
            self._step_arrivals()
            self._step_discharge()
            self._step_travel()
            self._step_wait()
            self.sim_time += self.dt

        interval = self._snapshot_interval_metrics()
        interval["queues"] = {i: list(q) for i, q in self.queues.items()}
        interval["phase"] = {i: c.phase for i, c in self.controllers.items()}
        interval["time_in_phase"] = {
            i: c.time_in_phase for i, c in self.controllers.items()
        }
        interval["sim_time"] = self.sim_time
        interval["completed"] = self.completed
        return interval


def neighbor_pressures(graph: dict, queues: dict) -> dict:
    """Queue on each neighbour's approach feeding back toward this intersection.

    For approach ``a`` at intersection ``i`` leading to downstream ``d``, the
    neighbour pressure is the queue at ``d`` on the approach that points back
    at ``i``. Peripheral approaches contribute zero.
    """
    result = {}
    for i in graph["intersections"]:
        pressures = []
        for a, name in enumerate(graph["approach_names"]):
            downstream = graph["neighbors"][i][name]
            if downstream is None:
                pressures.append(0.0)
            else:
                incoming = next(
                    (
                        nm
                        for nm in graph["approach_names"]
                        if graph["neighbors"][downstream][nm] == i
                    ),
                    None,
                )
                if incoming is not None:
                    pressures.append(float(queues[downstream][graph["approach_names"].index(incoming)]))
                else:
                    # No approach at the downstream intersection points back at
                    # ``i`` (common on real, asymmetric city graphs). Fall back
                    # to the downstream intersection's mean queue so the
                    # observation still reflects downstream congestion.
                    pressures.append(float(np.mean(queues[downstream])))
        result[i] = pressures
    return result


def _demo() -> None:
    graph = build_toy_graph()
    sim = TrafficSim(graph, seed=1)
    for _ in range(20):
        actions = {i: 0 for i in graph["intersections"]}
        m = sim.step(actions)
    print("zone_wait:", m["zone_wait"], "queues:", m["queues"])


if __name__ == "__main__":
    _demo()
