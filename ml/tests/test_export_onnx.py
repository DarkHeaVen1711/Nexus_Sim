"""Unit tests for ONNX export and parity validation (Phase 8.1)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ort = pytest.importorskip("onnxruntime")

ML_DIR = Path(__file__).resolve().parents[1]
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from export.export_onnx import export_checkpoint  # noqa: E402
from export.validate_onnx import validate_export  # noqa: E402

OBS_DIM = 11


def _tiny_checkpoint(tmp_path: Path) -> str:
    """Save a minimal random policy checkpoint the way train.py does."""
    from models import PolicyNetwork

    policy = PolicyNetwork(OBS_DIM, hidden=16)
    path = tmp_path / "ckpt.pt"
    torch.save({"policy_state": policy.state_dict(), "episode": 3}, path)
    return str(path)


def test_export_creates_loadable_model(tmp_path):
    ckpt = _tiny_checkpoint(tmp_path)
    out = tmp_path / "policy.onnx"
    export_checkpoint(ckpt, str(out), OBS_DIM, hidden=16)
    assert out.is_file()
    session = ort.InferenceSession(str(out), providers=["CPUExecutionProvider"])
    names = {i.name for i in session.get_inputs()}
    assert names == {"observations"}


def test_export_batch_axis_is_dynamic(tmp_path):
    ckpt = _tiny_checkpoint(tmp_path)
    out = str(tmp_path / "policy.onnx")
    export_checkpoint(ckpt, out, OBS_DIM, hidden=16)
    session = ort.InferenceSession(out, providers=["CPUExecutionProvider"])
    for batch in (1, 4, 7):
        x = np.random.rand(batch, OBS_DIM).astype(np.float32)
        logits = session.run(["logits"], {"observations": x})[0]
        assert logits.shape == (batch, 2)


def test_validate_export_passes_for_matching_weights(tmp_path):
    ckpt = _tiny_checkpoint(tmp_path)
    out = str(tmp_path / "policy.onnx")
    export_checkpoint(ckpt, out, OBS_DIM, hidden=16)
    assert validate_export(out, OBS_DIM, hidden=16, checkpoint_path=ckpt)


def test_validate_export_fails_for_wrong_hidden_size(tmp_path):
    """A policy rebuilt with mismatched weights must not pass validation."""
    ckpt = _tiny_checkpoint(tmp_path)
    out = str(tmp_path / "policy.onnx")
    export_checkpoint(ckpt, out, OBS_DIM, hidden=16)
    assert not validate_export(out, OBS_DIM, hidden=32, checkpoint_path=None
                               if False else _wrong_ckpt(tmp_path))


def _wrong_ckpt(tmp_path: Path) -> str:
    from models import PolicyNetwork

    policy = PolicyNetwork(OBS_DIM, hidden=32)
    path = tmp_path / "wrong.pt"
    torch.save({"policy_state": policy.state_dict()}, path)
    return str(path)
