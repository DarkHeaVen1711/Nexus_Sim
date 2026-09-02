"""Unit tests for the Phase 9.3-9.7 helper paths (transfer + evaluate)."""

from __future__ import annotations

import os
import sys

import pytest
import torch

ML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

from train.evaluate import _load_env as eval_load_env
from train.rollout import evaluate_fixed_baseline
from train.train import build_models, latest_checkpoint
from train.transfer import _load_env as transfer_load_env
from train.transfer import _resolve_source
from train.transfer import _resolve_resume, load_checkpoint


def test_transfer_unknown_city_raises():
    with pytest.raises(FileNotFoundError):
        transfer_load_env("ghost-city")


def test_transfer_toy_env_loads():
    env = transfer_load_env("toy", episode_steps=20)
    assert env.num_agents == 4
    assert env.observation_space.shape == (11,)


def test_evaluate_toy_env_loads():
    env = eval_load_env("toy", episode_steps=20)
    assert env.num_agents == 4


def test_evaluate_unknown_city_raises():
    with pytest.raises(FileNotFoundError):
        eval_load_env("ghost-city")


def test_resolve_source_direct_path(tmp_path):
    p = tmp_path / "ckpt.pt"
    torch.save({"episode": 0}, p)
    assert _resolve_source(str(p)) == str(p)


def test_resolve_source_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        _resolve_source(str(tmp_path / "nope.pt"))


def test_resolve_source_unknown_city_raises(tmp_path):
    # No checkpoints/<city> trees exist for a ghost city.
    with pytest.raises(FileNotFoundError):
        _resolve_source("ghost-city")


def test_baseline_runs_short_episode():
    """evaluate_fixed_baseline (used by transfer/evaluate) works end-to-end."""
    env = eval_load_env("toy", episode_steps=20)
    result = evaluate_fixed_baseline(env, n_episodes=2)
    assert set(result.keys()) == {
        "episode_reward", "mean_pressure", "equity", "gini",
    }
    assert result["episode_reward"] < 0.0
    assert "gini" in result


def test_resolve_resume_none():
    assert _resolve_resume(None, "irrelevant") is None


def test_resolve_resume_latest(tmp_path):
    # Numerically highest episode wins even if lexically last is different.
    torch.save({"episode": 20}, tmp_path / "20.pt")
    torch.save({"episode": 5}, tmp_path / "5.pt")
    assert _resolve_resume("latest", str(tmp_path)) == str(tmp_path / "20.pt")


def test_resolve_resume_no_checkpoints_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        _resolve_resume("latest", str(tmp_path))


def test_resolve_resume_direct_path(tmp_path):
    p = tmp_path / "ckpt.pt"
    torch.save({"episode": 7}, p)
    assert _resolve_resume(str(p), "irrelevant") == str(p)


def test_resolve_resume_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        _resolve_resume(str(tmp_path / "missing.pt"), "irrelevant")


def test_resume_checkpoint_roundtrip(tmp_path):
    """A saved transfer checkpoint can reload policy/value/opt states + episode."""
    import torch.optim as optim

    policy, value_net = build_models(11, 32, torch.device("cpu"))
    policy_opt = optim.Adam(policy.parameters(), lr=1e-4)
    value_opt = optim.Adam(value_net.parameters(), lr=1e-4)
    path = tmp_path / "199.pt"
    torch.save({
        "episode": 199,
        "policy_state": policy.state_dict(),
        "value_state": value_net.state_dict(),
        "policy_opt_state": policy_opt.state_dict(),
        "value_opt_state": value_opt.state_dict(),
        "reward_scale": 123.0,
    }, path)

    pol2, val2 = build_models(11, 32, torch.device("cpu"))
    pol2_opt = optim.Adam(pol2.parameters(), lr=1e-4)
    val2_opt = optim.Adam(val2.parameters(), lr=1e-4)
    ckpt = load_checkpoint(path, pol2, val2, pol2_opt, val2_opt, torch.device("cpu"))
    assert ckpt["episode"] == 199
    assert ckpt["reward_scale"] == 123.0