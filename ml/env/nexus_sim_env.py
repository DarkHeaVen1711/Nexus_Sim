"""Gym-compatible ``NexusSimEnv`` (TR-ML-01, Phase 7.3).

Wraps the offline ``TrafficSim`` micro-simulator into the standard
``gymnasium.Env`` interface (``reset``/``step``/``observation_space``/
``action_space``). One RL agent controls each signalised intersection
(``num_agents`` = 4), and the observation/action/reward contracts follow
TR-ML-02/03/04.

No live C++ engine call happens during training — the environment runs on
state snapshots produced by the Python simulator (TR-5).
"""

from __future__ import annotations

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from .observation import OBSERVATION_DIM, build_observation
from .reward import baseline_zone_weights, combined_reward
from .toy_graph import build_toy_graph
from .traffic_sim import TrafficSim, neighbor_pressures

MAX_QUEUE = 50.0
N_PHASES = 2


class NexusSimEnv(gym.Env):
    """Multi-agent environment for adaptive signal control on the toy grid."""

    metadata = {"render_modes": ["ascii"]}

    def __init__(
        self,
        graph: dict | None = None,
        seed: int = 0,
        alpha: float = 1.0,
        beta: float = 1.0,
        decision_interval: float = 5.0,
        episode_steps: int = 100,
        start_hour: float = 8.0,
        render_mode: str | None = None,
    ):
        self.graph = graph if graph is not None else build_toy_graph()
        self.num_agents = len(self.graph["intersections"])
        self.alpha = alpha
        self.beta = beta
        self.decision_interval = decision_interval
        self.episode_steps = episode_steps
        self.start_hour = start_hour
        self.render_mode = render_mode

        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(OBSERVATION_DIM,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(2)

        zone_weights_list = baseline_zone_weights(self.graph["baseline_zone_wait"])
        zone_weights_by_zone = {z: w for z, w in zip(self.graph["zones"], zone_weights_list)}
        zone_map = self.graph.get("zone_map", {i: i for i in self.graph["intersections"]})
        self.zone_weights = {i: zone_weights_by_zone[zone_map[i]] for i in self.graph["intersections"]}
        self.seed = seed

        self.sim = None
        self.step_count = 0

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self.seed = int(seed)
        self.sim = TrafficSim(
            self.graph,
            seed=self.seed,
            decision_interval=self.decision_interval,
            start_hour=self.start_hour,
        )
        self.step_count = 0
        obs = self._observe()
        return obs, {}

    def step(self, actions: dict):
        if self.sim is None:
            raise RuntimeError("reset() must be called before step()")
        metrics = self.sim.step(actions)
        self.step_count += 1

        pressure_terms = [
            -float(sum(metrics["queues"][i])) for i in self.graph["intersections"]
        ]
        zone_waits = [metrics["zone_wait"][i] for i in self.graph["intersections"]]
        weights = [self.zone_weights[i] for i in self.graph["intersections"]]
        reward_out = combined_reward(
            pressure_terms, zone_waits, self.alpha, self.beta, weights
        )
        rewards = {
            i: r for i, r in zip(self.graph["intersections"], reward_out["rewards"])
        }

        truncated = self.step_count >= self.episode_steps
        obs = self._observe(metrics)
        info = {
            "mean_pressure": reward_out["mean_pressure"],
            "equity": reward_out["equity"],
            "gini": reward_out["gini"],
            "zone_wait": zone_waits,
            "completed": metrics["completed"],
        }
        if self.render_mode == "ascii":
            self._render()
        return obs, rewards, False, truncated, info

    def _observe(self, metrics: dict | None = None):
        if metrics is None:
            metrics = {
                "queues": self.sim.queues,
                "phase": {i: c.phase for i, c in self.sim.controllers.items()},
                "time_in_phase": {
                    i: c.time_in_phase for i, c in self.sim.controllers.items()
                },
                "sim_time": self.sim.sim_time,
            }
        pressures = neighbor_pressures(self.graph, metrics["queues"])
        time_of_day = (self.start_hour + metrics["sim_time"] / 3600.0) % 24.0 / 24.0
        obs = {}
        for i in self.graph["intersections"]:
            time_in_phase = metrics["time_in_phase"][i]
            norm_time_in_phase = min(1.0, time_in_phase / self.decision_interval)
            obs[i] = build_observation(
                queues=metrics["queues"][i],
                phase=float(metrics["phase"][i]),
                time_in_phase=norm_time_in_phase,
                time_of_day=time_of_day,
                neighbor_pressure=pressures[i],
                max_queue=MAX_QUEUE,
            )
        return obs

    def _render(self) -> None:
        lines = []
        for i in self.graph["intersections"]:
            c = self.sim.controllers[i]
            lines.append(
                "I%d phase=%d %s queue=%s" % (i, c.phase, c.state, self.sim.queues[i])
            )
        print("\n".join(lines))
