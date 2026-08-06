"""PPO update loop shared by all intersection agents (Phase 7.5).

Implements generalized advantage estimation (GAE) and the clipped surrogate
objective over a per-agent rollout. Because the policy and value networks are
shared, every (agent, decision) pair is treated as an independent sample from
the same distribution — the decentralised, shared-weight MAPPO variant the
plan calls for (BR-5, TR-ML-05).
"""

from __future__ import annotations

import torch
import torch.nn.functional as F


def compute_gae(
    rewards: torch.Tensor,
    values: torch.Tensor,
    dones: torch.Tensor,
    gamma: float = 0.99,
    lam: float = 0.95,
) -> tuple:
    """Generalized advantage estimation over a single-agent trajectory."""
    advantages = torch.zeros_like(values)
    gae = torch.zeros_like(values[0])
    for t in reversed(range(len(rewards))):
        next_value = values[t + 1] if t + 1 < len(values) else torch.zeros_like(values[t])
        mask = 1.0 - dones[t]
        delta = rewards[t] + gamma * next_value * mask - values[t]
        gae = delta + gamma * lam * mask * gae
        advantages[t] = gae
    returns = advantages + values
    return advantages, returns


def ppo_update(
    policy,
    value_net,
    policy_opt,
    value_opt,
    obs: torch.Tensor,
    actions: torch.Tensor,
    old_logprobs: torch.Tensor,
    advantages: torch.Tensor,
    returns: torch.Tensor,
    clip_eps: float = 0.2,
    entropy_coef: float = 0.01,
    value_coef: float = 0.5,
    n_epochs: int = 4,
    batch_size: int = 256,
) -> tuple:
    """Run clipped PPO updates over one rollout; returns (policy, value) loss."""
    adv = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
    policy_loss = value_loss = 0.0
    n = len(obs)
    for _ in range(n_epochs):
        perm = torch.randperm(n)
        for start in range(0, n, batch_size):
            idx = perm[start : start + batch_size]
            o, a = obs[idx], actions[idx]
            old_lp, adv_b, ret = old_logprobs[idx], adv[idx], returns[idx]

            logp, entropy = policy.evaluate(o, a)
            ratio = torch.exp(logp - old_lp)
            surr1 = ratio * adv_b
            surr2 = torch.clamp(ratio, 1.0 - clip_eps, 1.0 + clip_eps) * adv_b
            policy_loss = -torch.min(surr1, surr2).mean() - entropy_coef * entropy.mean()

            values = value_net(o).squeeze(-1)
            value_loss = F.mse_loss(values, ret)

            policy_opt.zero_grad()
            policy_loss.backward()
            policy_opt.step()
            value_opt.zero_grad()
            value_loss.backward()
            value_opt.step()
    return policy_loss.item(), value_loss.item()
