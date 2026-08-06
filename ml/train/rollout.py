"""Episode rollout collection and the Webster-style fixed-cycle baseline.

``collect_episode`` steps one environment episode and returns per-agent
trajectories ready for GAE/PPO. ``FixedCycleBaseline`` is a stateful
controller that holds each green phase for a fixed number of decision
intervals before switching — the classical non-adaptive baseline the learned
policy is measured against (Phase 7.8).
"""

from __future__ import annotations

import numpy as np
import torch


class FixedCycleBaseline:
    """Holds each phase ``switch_every`` decision intervals, then switches."""

    def __init__(self, env, switch_every: int = 4):
        self.switch_every = switch_every
        self.extends = {i: 0 for i in range(env.num_agents)}

    def reset(self) -> None:
        for key in self.extends:
            self.extends[key] = 0

    def act(self, obs: dict) -> dict:
        actions = {}
        for i, o in obs.items():
            at_boundary = o[5] >= 0.999
            if at_boundary and self.extends[i] >= self.switch_every - 1:
                actions[i] = 1
                self.extends[i] = 0
            else:
                actions[i] = 0
                if at_boundary:
                    self.extends[i] += 1
        return actions


def evaluate_fixed_baseline(env, n_episodes: int = 10, switch_every: int = 4) -> dict:
    """Mean episode reward/pressure/equity/gini under the fixed-cycle policy.

    ``episode_reward`` is the summed reward over one episode; ``mean_pressure``,
    ``equity`` and ``gini`` are per-step averages (accumulated across every
    step of every episode, then divided by the step count), so they are directly
    comparable to the per-step metrics logged during training.
    """
    baseline = FixedCycleBaseline(env, switch_every=switch_every)
    totals = {"episode_reward": 0.0, "mean_pressure": 0.0, "equity": 0.0, "gini": 0.0}
    n_steps = 0
    for _ in range(n_episodes):
        baseline.reset()
        obs, _ = env.reset()
        done = False
        ep_reward = 0.0
        while not done:
            actions = baseline.act(obs)
            obs, rewards, _, truncated, info = env.step(actions)
            ep_reward += sum(rewards.values()) / env.num_agents
            totals["mean_pressure"] += info["mean_pressure"]
            totals["equity"] += info["equity"]
            totals["gini"] += info["gini"]
            n_steps += 1
            done = truncated
        totals["episode_reward"] += ep_reward
    totals["episode_reward"] /= n_episodes
    if n_steps > 0:
        for key in ("mean_pressure", "equity", "gini"):
            totals[key] /= n_steps
    return totals


def collect_episode(env, policy, value_net, device) -> dict:
    """Step one episode; return per-agent buffers concatenated into tensors."""
    agents = sorted(env.graph["intersections"])
    per_agent = {i: {"obs": [], "act": [], "logp": [], "rew": [], "val": [], "done": []}
                 for i in agents}

    obs, _ = env.reset()
    done = False
    ep_reward = 0.0
    pressure_sum = equity_sum = gini_sum = 0.0
    n_decisions = 0
    while not done:
        obs_t = torch.from_numpy(
            np.stack([obs[i] for i in agents])
        ).float().to(device)
        with torch.no_grad():
            actions, log_probs = policy.sample_action(obs_t)
            values = value_net(obs_t).squeeze(-1)

        action_map = {i: int(actions[idx].item()) for idx, i in enumerate(agents)}
        next_obs, rewards, terminated, truncated, info = env.step(action_map)
        for idx, i in enumerate(agents):
            per_agent[i]["obs"].append(obs_t[idx])
            per_agent[i]["act"].append(torch.tensor(action_map[i]))
            per_agent[i]["logp"].append(log_probs[idx])
            per_agent[i]["rew"].append(rewards[i])
            per_agent[i]["val"].append(values[idx])
            per_agent[i]["done"].append(terminated or truncated)

        ep_reward += sum(rewards.values()) / env.num_agents
        pressure_sum += info["mean_pressure"]
        equity_sum += info["equity"]
        gini_sum += info["gini"]
        n_decisions += 1
        obs = next_obs
        done = truncated

    tensors = {}
    for i in agents:
        tensors[i] = {
            "obs": torch.stack(per_agent[i]["obs"]),
            "act": torch.stack(per_agent[i]["act"]),
            "logp": torch.stack(per_agent[i]["logp"]),
            "rew": torch.tensor(per_agent[i]["rew"], dtype=torch.float32),
            "val": torch.stack(per_agent[i]["val"]),
            "done": torch.tensor(per_agent[i]["done"], dtype=torch.float32),
        }
    summary = {
        "episode_reward": ep_reward,
        "mean_pressure": pressure_sum / max(1, n_decisions),
        "equity": equity_sum / max(1, n_decisions),
        "gini": gini_sum / max(1, n_decisions),
        "n_decisions": n_decisions,
    }
    return {"tensors": tensors, "summary": summary}
