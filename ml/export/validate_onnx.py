"""Parity validation of the exported ONNX policy (Phase 8.1).

The exported graph must produce the same logits as the PyTorch policy on
random inputs before it is trusted by the engine. Runs 10 seeded test
inputs through both models and compares with a tight tolerance.
"""

from __future__ import annotations

import numpy as np
import onnxruntime as ort
import torch

NUM_VALIDATION_INPUTS = 10


def validate_export(policy_path: str, obs_dim: int, hidden: int,
                    checkpoint_path: str, num_inputs: int = NUM_VALIDATION_INPUTS,
                    atol: float = 1e-4) -> bool:
    """Compare ONNX and PyTorch logits on random inputs; True when equal."""
    # Import here so export-only usage does not require onnxruntime.
    from export.export_onnx import load_policy

    policy = load_policy(checkpoint_path, obs_dim, hidden)
    session = ort.InferenceSession(policy_path, providers=["CPUExecutionProvider"])

    rng = np.random.default_rng(42)
    for i in range(num_inputs):
        x = rng.random((1, obs_dim)).astype(np.float32)

        with torch.no_grad():
            expected = policy(torch.from_numpy(x)).numpy()

        actual = session.run(["logits"], {"observations": x})[0]
        if not np.allclose(expected, actual, atol=atol):
            max_diff = float(np.max(np.abs(expected - actual)))
            print("MISMATCH input %d: max |torch - onnx| = %.3g" % (i, max_diff))
            return False

    print("ONNX/PyTorch parity OK on %d inputs (atol=%.0e)"
          % (num_inputs, atol))
    return True
