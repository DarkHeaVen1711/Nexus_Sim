"""Unit tests for the observation-space builder (TR-ML-02, Phase 7.1)."""

import numpy as np
import pytest

from env.observation import OBSERVATION_DIM, build_observation


def _obs(**overrides):
    kwargs = dict(
        queues=[10, 20, 30, 40],
        phase=0.0,
        time_in_phase=0.5,
        time_of_day=0.5,
        neighbor_pressure=[1, 2, 3, 4],
        max_queue=50.0,
    )
    kwargs.update(overrides)
    return build_observation(**kwargs)


def test_observation_dimension():
    assert _obs().shape == (OBSERVATION_DIM,)


def test_observation_all_in_unit_range():
    assert np.all(_obs() >= 0.0)
    assert np.all(_obs() <= 1.0)


def test_queues_normalized_by_max_queue():
    obs = _obs()
    np.testing.assert_allclose(obs[:4], [0.2, 0.4, 0.6, 0.8])


def test_scalar_features_are_passthrough():
    obs = _obs(phase=1.0, time_in_phase=0.25, time_of_day=0.75)
    assert obs[4] == 1.0
    assert obs[5] == 0.25
    assert obs[6] == 0.75


def test_neighbor_pressure_normalized():
    obs = _obs()
    np.testing.assert_allclose(obs[7:], [0.02, 0.04, 0.06, 0.08])


def test_observation_is_float32():
    assert _obs().dtype == np.float32


@pytest.mark.parametrize("bad", [[1, 2], [1, 2, 3, 4, 5]])
def test_wrong_queue_length_raises(bad):
    with pytest.raises(ValueError):
        _obs(queues=bad)


def test_wrong_neighbor_pressure_length_raises():
    with pytest.raises(ValueError):
        _obs(neighbor_pressure=[1, 2, 3])
