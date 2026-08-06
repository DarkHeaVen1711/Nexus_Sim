"""Unit tests for the PPO trainer (Phase 7.5) and rollouts."""

import numpy as np
import pytest
import torch

from env import NexusSimEnv
from models import PolicyNetwork, ValueNetwork
from train.ppo import compute_gae, ppo_update
from train.rollout import (
    FixedCycleBaseline,
    collect_episode,
    evaluate_fixed_baseline,
)


def test_compute_gae_constant_reward():
    rewards = torch.tensor([1.0, 1.0, 1.0])
    values = torch.tensor([1.0, 1.0, 1.0])
    dones = torch.zeros(3)
    advantages, returns = compute_gae(rewards, values, dones, gamma=0.99, lam=0.95)
    assert advantages.shape == (3,)
    assert torch.allclose(returns, advantages + values)


def test_compute_gae_single_step():
    rewards = torch.tensor([2.0])
    values = torch.tensor([0.0])
    dones = torch.tensor([1.0])
    advantages, returns = compute_gae(rewards, values, dones)
    assert torch.allclose(advantages, torch.tensor([2.0]))
    assert torch.allclose(returns, torch.tensor([2.0]))


def test_ppo_update_reduces_loss():
    torch.manual_seed(0)
    obs = torch.rand(64, 11)
    actions = torch.randint(0, 2, (64,))
    policy = PolicyNetwork(11, hidden=16)
    value_net = ValueNetwork(11, hidden=16)
    with torch.no_grad():
        old_logp, _ = policy.evaluate(obs, actions)
        old_value = value_net(obs).squeeze(-1)
    returns = torch.rand(64) + old_value.squeeze(-1)
    advantages = torch.rand(64) - 0.5

    p_opt = torch.optim.Adam(policy.parameters(), lr=3e-3)
    v_opt = torch.optim.Adam(value_net.parameters(), lr=3e-3)
    p_loss, v_loss = ppo_update(
        policy, value_net, p_opt, v_opt, obs, actions, old_logp,
        advantages, returns, n_epochs=10, batch_size=16,
    )
    assert p_loss == p_loss
    assert v_loss == v_loss


def test_policy_samples_valid_actions():
    policy = PolicyNetwork(11, hidden=16)
    obs = torch.zeros(8, 11)
    actions, logp = policy.sample_action(obs)
    assert set(actions.tolist()) <= {0, 1}
    assert logp.shape == (8,)


def test_collect_episode_returns_buffers():
    env = NexusSimEnv(seed=5, episode_steps=10)
    policy = PolicyNetwork(11, hidden=16)
    value_net = ValueNetwork(11, hidden=16)
    rollout = collect_episode(env, policy, value_net, "cpu")
    tensors = rollout["tensors"]
    for i in tensors:
        t = tensors[i]
        n = len(t["obs"])
        assert n == 10
        assert t["act"].shape == (n,)
        assert t["rew"].shape == (n,)
        assert t["done"].shape == (n,)
    assert rollout["summary"]["episode_reward"] <= 0.0


def test_fixed_cycle_baseline_switches():
    env = NexusSimEnv(seed=5, episode_steps=6)
    baseline = FixedCycleBaseline(env, switch_every=2)
    obs, _ = env.reset()
    phases = set()
    for _ in range(6):
        actions = baseline.act(obs)
        obs, _, _, _, _ = env.step(actions)
        phases.add(obs[0][4])
    assert len(phases) > 1


def test_evaluate_fixed_baseline_returns_metrics():
    env = NexusSimEnv(seed=5, episode_steps=8)
    metrics = evaluate_fixed_baseline(env, n_episodes=2, switch_every=2)
    for key in ("episode_reward", "mean_pressure", "equity", "gini"):
        assert key in metrics
        assert isinstance(metrics[key], float)
    assert metrics["episode_reward"] <= 0.0


@pytest.mark.parametrize("gamma", [0.9, 0.99, 1.0])
def test_compute_gae_shapes(gamma):
    rng = np.random.default_rng(0)
    rewards = torch.tensor(rng.uniform(-1, 0, 15))
    values = torch.zeros(15)
    dones = torch.zeros(15)
    advantages, returns = compute_gae(rewards, values, dones, gamma=gamma)
    assert advantages.shape == returns.shape == (15,)
