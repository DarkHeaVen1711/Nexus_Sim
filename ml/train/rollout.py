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
        self.extends = {i: 0 for i in env.graph["intersections"]}

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
    """Step one episode; return agent-major tensors.

    All tensors are ``[num_agents, horizon]`` (obs is ``[num_agents, horizon,
    obs_dim]``) so GAE/PPO can run as a single vectorised pass over the whole
    city instead of one Python loop per intersection.
    """
    agents = sorted(env.graph["intersections"])
    n_agents = len(agents)

    obs_buf, act_buf, logp_buf, val_buf, rew_buf, done_buf = (
        [], [], [], [], [], []
    )

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

        act_t = torch.as_tensor([action_map[i] for i in agents],
                                dtype=torch.int64, device=device)
        rew_t = torch.as_tensor([rewards[i] for i in agents],
                                dtype=torch.float32, device=device)
        dones_t = torch.full((n_agents,), float(terminated or truncated),
                             dtype=torch.float32, device=device)

        obs_buf.append(obs_t)
        act_buf.append(act_t)
        logp_buf.append(log_probs)
        val_buf.append(values)
        rew_buf.append(rew_t)
        done_buf.append(dones_t)

        ep_reward += sum(rewards.values()) / env.num_agents
        pressure_sum += info["mean_pressure"]
        equity_sum += info["equity"]
        gini_sum += info["gini"]
        n_decisions += 1
        obs = next_obs
        done = truncated

    tensors = {
        "obs": torch.stack(obs_buf, dim=1),
        "act": torch.stack(act_buf, dim=1),
        "logp": torch.stack(logp_buf, dim=1),
        "rew": torch.stack(rew_buf, dim=1),
        "val": torch.stack(val_buf, dim=1),
        "done": torch.stack(done_buf, dim=1),
    }
    summary = {
        "episode_reward": ep_reward,
        "mean_pressure": pressure_sum / max(1, n_decisions),
        "equity": equity_sum / max(1, n_decisions),
        "gini": gini_sum / max(1, n_decisions),
        "n_decisions": n_decisions,
    }
    return {"tensors": tensors, "summary": summary}
