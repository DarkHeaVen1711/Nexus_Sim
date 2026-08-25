"""Export a trained MAPPO policy checkpoint to ONNX (Phase 8.1, US-E04).

Loads the ``policy_state`` weights saved by ``train/train.py`` into the
``PolicyNetwork`` and traces it to ``policy.onnx`` with a dynamic batch
axis, so the C++ engine (Phase 8.3) can run one batched inference call per
simulation tick for every signalised intersection.

The exported graph emits raw logits over ``{EXTEND, SWITCH}``; the engine
applies argmax (greedy policy) itself.

Example:
    python -m export.export_onnx --checkpoint checkpoints/toy/499.pt \
        --output policy.onnx
"""

from __future__ import annotations

import argparse
import os
import sys

import torch

EXPORT_DIR = os.path.abspath(os.path.dirname(__file__))
ML_DIR = os.path.dirname(EXPORT_DIR)
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

from models import PolicyNetwork

OPSET_VERSION = 17


def load_policy(checkpoint_path: str, obs_dim: int, hidden: int,
                device: str = "cpu") -> PolicyNetwork:
    """Rebuild the policy network and load trained weights from a checkpoint."""
    policy = PolicyNetwork(obs_dim, hidden=hidden).to(device)
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=True)
    if "policy_state" in ckpt:
        ckpt = ckpt["policy_state"]
    policy.load_state_dict(ckpt)
    policy.eval()
    return policy


def export_checkpoint(checkpoint_path: str, output_path: str,
                      obs_dim: int, hidden: int,
                      device: str = "cpu") -> str:
    """Trace the policy network to ONNX and write it to ``output_path``."""
    policy = load_policy(checkpoint_path, obs_dim, hidden, device)
    dummy = torch.zeros(1, obs_dim, device=device)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    torch.onnx.export(
        policy,
        (dummy,),
        output_path,
        opset_version=OPSET_VERSION,
        # Legacy TorchScript tracer: stable graph shape, no onnxscript dep.
        dynamo=False,
        input_names=["observations"],
        output_names=["logits"],
        dynamic_axes={
            "observations": {0: "batch"},
            "logits": {0: "batch"},
        },
    )
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export MAPPO policy to ONNX")
    parser.add_argument("--checkpoint", required=True,
                        help="trained .pt checkpoint (see train/train.py)")
    parser.add_argument("--output", default=os.path.join(ML_DIR, "policy.onnx"),
                        help="where to write policy.onnx")
    parser.add_argument("--obs-dim", type=int, default=11,
                        help="observation dimension used at training time")
    parser.add_argument("--hidden", type=int, default=64,
                        help="hidden layer width used at training time")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--skip-validation", action="store_true",
                        help="skip the 10-input ONNX/PyTorch parity check")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = export_checkpoint(args.checkpoint, args.output,
                             args.obs_dim, args.hidden, args.device)
    size_kb = os.path.getsize(path) / 1024.0
    print("Exported %s (%.1f KB)" % (path, size_kb))

    ok = True
    if not args.skip_validation:
        from export.validate_onnx import validate_export
        ok = validate_export(path, args.obs_dim, args.hidden, args.checkpoint)
    if not ok:
        print("ERROR: exported model failed validation; refusing to ship it")
        sys.exit(1)


if __name__ == "__main__":
    main()
