"""Unit tests for the Gym-compatible environment (TR-ML-01, Phase 7.3)."""

import numpy as np

from env import NexusSimEnv
from env.observation import OBSERVATION_DIM


def _make_env(**kwargs):
    kwargs.setdefault("seed", 3)
    kwargs.setdefault("episode_steps", 20)
    return NexusSimEnv(**kwargs)


def test_observation_space_box():
    env = _make_env()
    assert env.observation_space.shape == (OBSERVATION_DIM,)
    assert env.observation_space.low.min() == 0.0
    assert env.observation_space.high.max() == 1.0


def test_action_space_discrete_two():
    env = _make_env()
    assert env.action_space.n == 2


def test_reset_returns_obs_and_info():
    env = _make_env()
    obs, info = env.reset()
    assert sorted(obs.keys()) == [0, 1, 2, 3]
    assert all(o.shape == (OBSERVATION_DIM,) for o in obs.values())
    assert info == {}


def test_step_returns_full_tuple():
    env = _make_env()
    obs, _ = env.reset()
    actions = {i: 0 for i in obs}
    out = env.step(actions)
    assert len(out) == 5
    next_obs, rewards, terminated, truncated, info = out
    assert sorted(rewards.keys()) == [0, 1, 2, 3]
    assert terminated is False
    assert isinstance(info, dict)


def test_episode_truncates_at_horizon():
    env = _make_env(episode_steps=5)
    obs, _ = env.reset()
    done = False
    steps = 0
    while not done:
        obs, _, _, done, _ = env.step({i: 0 for i in obs})
        steps += 1
    assert steps == 5


def test_rewards_are_negative_when_queues_build():
    env = _make_env()
    obs, _ = env.reset()
    rewards = None
    for _ in range(10):
        obs, rewards, _, _, _ = env.step({i: 0 for i in obs})
    assert all(r < 0.0 for r in rewards.values())


def test_deterministic_seed_reproducible():
    a = _make_env(seed=11)
    b = _make_env(seed=11)
    obs_a, _ = a.reset()
    obs_b, _ = b.reset()
    for i in obs_a:
        np.testing.assert_array_equal(obs_a[i], obs_b[i])


def test_step_before_reset_raises():
    env = _make_env()
    try:
        env.step({0: 0, 1: 0, 2: 0, 3: 0})
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


def test_controller_phases_cycle_with_switch_action():
    env = _make_env()
    obs, _ = env.reset()
    phases = set()
    for _ in range(10):
        obs, _, _, _, _ = env.step({i: 1 for i in obs})
        phases.add(obs[0][4])
    assert len(phases) > 1
