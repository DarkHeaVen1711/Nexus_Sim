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
from .vectorized_sim import VectorizedTrafficSim

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
        if self.num_agents > 100:
            self.sim = VectorizedTrafficSim(
                self.graph,
                seed=self.seed,
                decision_interval=self.decision_interval,
                start_hour=self.start_hour,
            )
        else:
            self.sim = TrafficSim(
                self.graph,
                seed=self.seed,
                decision_interval=self.decision_interval,
                start_hour=self.start_hour,
            )
        if isinstance(self.sim, VectorizedTrafficSim):
            # Zone weights per simulation index, resolved once per episode
            # instead of once per step.
            self._zone_weights_list = [
                self.zone_weights[int(iid)] for iid in self.sim.intersections
            ]
        self.step_count = 0
        obs = self._observe()
        return obs, {}

    def step(self, actions: dict):
        if self.sim is None:
            raise RuntimeError("reset() must be called before step()")

        if isinstance(self.sim, VectorizedTrafficSim):
            return self._step_vectorized(actions)

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
            "avg_wait": metrics.get("avg_wait_seconds", 0.0),
            "mean_wait": metrics.get("mean_wait", metrics.get("avg_wait_seconds", 0.0)),
            "mean_corridor": metrics.get("mean_corridor", 0.0),
        }
        if self.render_mode == "ascii":
            self._render()
        return obs, rewards, False, truncated, info

    def _step_vectorized(self, actions: dict):
        metrics = self.sim.step(actions)
        self.step_count += 1

        from .reward import combined_reward as _cr
        # The vectorized sim already exposes per-intersection arrays in
        # simulation-index order, so no per-intersection dict rebuild is
        # needed here.
        pressure_terms = (-self.sim.queues.sum(axis=1)).tolist()
        zone_waits = metrics["zone_wait"].tolist()
        weights = self._zone_weights_list
        reward_out = _cr(pressure_terms, zone_waits, self.alpha, self.beta, weights)
        rewards_arr = reward_out["rewards"]
        ids = self.sim.intersections
        rewards = {int(ids[i]): rewards_arr[i] for i in range(self.sim.N)}

        truncated = self.step_count >= self.episode_steps
        obs_arr = self.sim.build_observations_vec(self.decision_interval)
        obs = {int(ids[i]): obs_arr[i] for i in range(self.sim.N)}
        info = {
            "mean_pressure": reward_out["mean_pressure"],
            "equity": reward_out["equity"],
            "gini": reward_out["gini"],
            "zone_wait": zone_waits,
            "completed": metrics["completed"],
            "avg_wait": metrics.get("avg_wait_seconds", 0.0),
            "mean_wait": metrics.get("mean_wait", metrics.get("avg_wait_seconds", 0.0)),
            "mean_corridor": metrics.get("mean_corridor", 0.0),
        }
        return obs, rewards, False, truncated, info

    def _observe(self, metrics: dict | None = None):
        if isinstance(self.sim, VectorizedTrafficSim):
            obs_arr = self.sim.build_observations_vec(self.decision_interval)
            agents = self.graph["intersections"]
            obs = {int(agents[i]): obs_arr[i] for i in range(self.sim.N)}
            return obs
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
