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
from train.transfer import _load_env as transfer_load_env
from train.transfer import _resolve_source


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