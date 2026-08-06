"""Unit tests for the reward terms (US-E03, TR-ML-04, Phase 7.2)."""

from env.reward import (
    baseline_zone_weights,
    combined_reward,
    equity_term,
    gini_coefficient,
    local_pressure,
)


def test_pressure_zero_queue_is_zero():
    assert local_pressure([0, 0, 0, 0]) == 0.0


def test_pressure_grows_negative_with_queue():
    assert local_pressure([1, 0, 0, 0]) == -1.0
    assert local_pressure([3, 2, 0, 1]) == -6.0
    assert local_pressure([1, 0, 0, 0]) < local_pressure([0, 0, 0, 0])


def test_equity_uniform_weights_is_negative_mean():
    waits = [2.0, 4.0, 6.0]
    assert abs(equity_term(waits) - (-4.0)) < 1e-9


def test_equity_high_weight_dominates():
    waits = [10.0, 1.0]
    w_bad = [1.0, 0.0]
    w_good = [0.0, 1.0]
    assert equity_term(waits, w_bad) < equity_term(waits, w_good)


def test_equity_empty_input():
    assert equity_term([]) == 0.0


def test_baseline_zone_weights_are_inverse_service():
    weights = baseline_zone_weights([5.0, 20.0], normalize=False)
    assert weights[0] > weights[1]
    assert abs(weights[0] - 1.0 / 5.0) < 1e-4


def test_baseline_zone_weights_normalize():
    weights = baseline_zone_weights([5.0, 20.0])
    assert abs(sum(weights) - 1.0) < 1e-9


def test_combined_reward_pressure_only():
    out = combined_reward([-1.0, -2.0], [3.0, 3.0], alpha=1.0, beta=0.0)
    assert out["rewards"] == [-1.0, -2.0]


def test_combined_reward_equity_only():
    waits = [4.0, 8.0]
    out = combined_reward([-1.0, -2.0], waits, alpha=0.0, beta=1.0)
    eq = equity_term(waits)
    assert abs(out["rewards"][0] - eq) < 1e-9
    assert abs(out["rewards"][1] - eq) < 1e-9


def test_combined_reward_returns_components():
    out = combined_reward([-1.0, -2.0, -3.0], [1.0, 2.0, 3.0], 1.0, 1.0)
    assert abs(out["mean_pressure"] - (-2.0)) < 1e-9
    assert out["gini"] > 0.0
    assert len(out["rewards"]) == 3


def test_gini_uniform_is_zero():
    assert gini_coefficient([5.0, 5.0, 5.0]) == 0.0


def test_gini_extreme_is_high():
    assert gini_coefficient([0.0, 0.0, 100.0]) > 0.5


def test_gini_small_inputs():
    assert gini_coefficient([]) == 0.0
    assert gini_coefficient([42.0]) == 0.0
    assert gini_coefficient([0.0, 0.0]) == 0.0
