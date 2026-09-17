from __future__ import annotations

import numpy as np

from .controller import ACTION_EXTEND, ACTION_SWITCH
from .toy_graph import PHASES, time_of_day_factor

_APPROACH_NAMES = ["N", "S", "E", "W"]
_SATURATION = 0.5


class VectorizedTrafficSim:
    """Numpy-vectorized simulator for large graphs (3k+ intersections)."""

    def __init__(self, graph: dict, seed: int = 0, dt: float = 1.0,
                 decision_interval: float = 5.0, start_hour: float = 8.0):
        self.graph = graph
        self.dt = dt
        self.decision_interval = decision_interval
        self.start_hour = start_hour
        self.rng = np.random.default_rng(seed)

        self.intersections = np.array(graph["intersections"], dtype=np.int64)
        self.N = len(self.intersections)
        self.id_to_idx = {int(i): idx for idx, i in enumerate(self.intersections)}

        self.sim_time = 0.0
        self.completed = 0.0

        self.queues = np.zeros((self.N, 4), dtype=np.float64)
        self.wait_acc = np.zeros((self.N, 4), dtype=np.float64)

        self.phase = np.zeros(self.N, dtype=np.int32)
        self.ctrl_state = np.zeros(self.N, dtype=np.int32)  # 0=GREEN,1=YELLOW,2=RED
        self.timer = np.full(self.N, decision_interval, dtype=np.float64)
        self.time_in_phase = np.zeros(self.N, dtype=np.float64)

        self.yellow_time = 3.0
        self.red_clearance = 2.0

        base_rates = np.array([graph["base_rate"][int(i)] for i in self.intersections])
        self.base_rate = base_rates.astype(np.float64)

        self._build_adjacency(graph)
        self._build_green_mask()

    def _build_adjacency(self, graph: dict):
        names = _APPROACH_NAMES
        n = self.N
        self.downstream_idx = np.full((n, 4), -1, dtype=np.int64)
        self.link_travel = np.zeros((n, 4), dtype=np.float64)
        self.has_downstream = np.zeros((n, 4), dtype=np.bool_)

        for idx, iid in enumerate(self.intersections):
            for a, name in enumerate(names):
                ds = graph["neighbors"].get(int(iid), {}).get(name)
                if ds is not None and ds in self.id_to_idx:
                    self.downstream_idx[idx, a] = self.id_to_idx[ds]
                    self.has_downstream[idx, a] = True
                    self.link_travel[idx, a] = graph["link_travel_s"].get(
                        (int(iid), ds), graph["link_travel_s"].get((iid, ds), 10.0))

        self.back_approach = np.full((n, 4), -1, dtype=np.int64)
        for idx, iid in enumerate(self.intersections):
            for a, name in enumerate(names):
                ds_id = graph["neighbors"].get(int(iid), {}).get(name)
                if ds_id is None:
                    continue
                if ds_id not in self.id_to_idx:
                    continue
                ds_idx = self.id_to_idx[ds_id]
                for a2, nm2 in enumerate(names):
                    if graph["neighbors"].get(int(ds_id), {}).get(nm2) == int(iid):
                        self.back_approach[idx, a] = a2
                        break

    def _build_green_mask(self):
        green0 = np.zeros((self.N, 4), dtype=np.bool_)
        green1 = np.zeros((self.N, 4), dtype=np.bool_)
        for a in PHASES[0]:
            green0[:, a] = True
        for a in PHASES[1]:
            green1[:, a] = True
        self.green_masks = [green0, green1]

    def reset(self):
        self.sim_time = 0.0
        self.completed = 0.0
        self.queues[:] = 0
        self.wait_acc[:] = 0
        self.phase[:] = 0
        self.ctrl_state[:] = 0
        self.timer[:] = self.decision_interval
        self.time_in_phase[:] = 0.0

    def build_observations_vec(self, decision_interval: float) -> np.ndarray:
        """Build (N, 11) observation matrix, all numpy — no dicts."""
        MAX_QUEUE = 50.0
        pressures = self.neighbor_pressures_vec()
        tod = ((self.start_hour + self.sim_time / 3600.0) % 24.0) / 24.0
        norm_tip = np.minimum(1.0, self.time_in_phase / decision_interval)
        obs = np.zeros((self.N, 11), dtype=np.float32)
        obs[:, 0:4] = self.queues / MAX_QUEUE
        obs[:, 4] = self.phase.astype(np.float32)
        obs[:, 5] = norm_tip.astype(np.float32)
        obs[:, 6] = tod
        obs[:, 7:11] = pressures / MAX_QUEUE
        return obs

    def snapshot_queues(self) -> dict:
        """Return queues as a dict-of-lists for compatibility."""
        return {int(self.intersections[i]): list(self.queues[i]) for i in range(self.N)}

    def snapshot_vecs(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return queues_arr, phase_arr, tip_arr for vectorized obs."""
        return self.queues.copy(), self.phase.copy(), self.time_in_phase.copy()

    def neighbor_pressures_vec(self) -> np.ndarray:
        """Vectorized neighbor pressure computation returning (N, 4) array."""
        pressures = np.zeros((self.N, 4), dtype=np.float64)
        has_ds = self.has_downstream
        bp = self.back_approach
        valid_bp = has_ds & (bp >= 0)
        ds_idx = self.downstream_idx[valid_bp]
        bp_a = bp[valid_bp]
        rows = np.where(valid_bp)
        pressures[rows[0], rows[1]] = self.queues[ds_idx, bp_a]
        return pressures

    def step(self, actions: dict) -> dict:
        act_arr = np.zeros(self.N, dtype=np.int32)
        for idx, iid in enumerate(self.intersections):
            act_arr[idx] = actions.get(int(iid), 0)

        decision_ready = (self.ctrl_state == 0) & (self.timer <= 0.0)
        extend_mask = decision_ready & (act_arr == ACTION_EXTEND)
        switch_mask = decision_ready & (act_arr == ACTION_SWITCH)

        self.timer[extend_mask] = self.decision_interval
        self.time_in_phase[extend_mask] = 0.0

        self.ctrl_state[switch_mask] = 1
        self.timer[switch_mask] = self.yellow_time
        self.time_in_phase[switch_mask] = 0.0

        n_sub = int(round(self.decision_interval / self.dt))
        for _ in range(n_sub):
            self._substep()
        return self._snapshot()

    def _substep(self):
        green_all = np.zeros((self.N, 4), dtype=np.bool_)
        for p_val in [0, 1]:
            mask = self.phase == p_val
            green_all[mask] = self.green_masks[p_val][mask]

        hour = (self.start_hour + self.sim_time / 3600.0) % 24.0
        tod_factor = time_of_day_factor(hour)
        rates = self.base_rate * tod_factor * self.dt
        arrivals = self.rng.poisson(np.clip(rates, 0, None)).astype(np.float64)
        self.queues += arrivals

        can_discharge = green_all & (self.ctrl_state[:, None] == 0)
        discharge_amt = np.minimum(self.queues, _SATURATION * self.dt)
        discharge_amt *= can_discharge

        self.queues -= discharge_amt

        discharged_int = np.floor(discharge_amt).astype(np.int64)
        has_ds = self.has_downstream
        ds_idx = self.downstream_idx[has_ds]
        arriving = discharged_int[has_ds]

        self.completed += float(discharged_int[~has_ds].sum())
        self.queues[~has_ds] = np.maximum(self.queues[~has_ds], 0)

        if ds_idx.size > 0:
            ds_approaches = np.broadcast_to(np.arange(4), (self.N, 4))[has_ds]
            np.add.at(self.queues, (ds_idx, ds_approaches), arriving)

        self.wait_acc += self.queues * self.dt
        self.sim_time += self.dt

        self.timer -= self.dt
        self.time_in_phase += self.dt

        yellow_done = (self.ctrl_state == 1) & (self.timer <= 0.0)
        self.ctrl_state[yellow_done] = 2
        self.timer[yellow_done] = self.red_clearance

        red_done = (self.ctrl_state == 2) & (self.timer <= 0.0)
        self.phase[red_done] = 1 - self.phase[red_done]
        self.ctrl_state[red_done] = 0
        self.timer[red_done] = self.decision_interval
        self.time_in_phase[red_done] = 0.0

        timer_at_zero = (self.ctrl_state == 0) & (self.timer < 0.0)
        self.timer[timer_at_zero] = 0.0

    def _snapshot(self) -> dict:
        interval = self.decision_interval
        zone_wait_arr = self.wait_acc.sum(axis=1) / interval
        zone_wait = {int(self.intersections[i]): float(zone_wait_arr[i]) for i in range(self.N)}
        avg_queue = zone_wait.copy()
        self.wait_acc[:] = 0.0

        queues_dict = {int(self.intersections[i]): list(self.queues[i]) for i in range(self.N)}
        phase_dict = {int(self.intersections[i]): int(self.phase[i]) for i in range(self.N)}
        tip_dict = {int(self.intersections[i]): float(self.time_in_phase[i]) for i in range(self.N)}

        return {
            "avg_queue": avg_queue,
            "zone_wait": zone_wait,
            "queues": queues_dict,
            "phase": phase_dict,
            "time_in_phase": tip_dict,
            "sim_time": self.sim_time,
            "completed": self.completed,
        }
