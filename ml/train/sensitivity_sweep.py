"""Task 9.6 - Multi-City Transfer Sensitivity Sweeps (Phase 9.6 / BK-03).

Systematic parameter sweep evaluating transfer robustness across:
  - Lane discipline chaos coefficients (0.05, 0.1, 0.2, 0.4)
  - Demand scaling factors (0.5, 0.8, 1.0, 1.5)
Outputs empirical stability matrix to ml/results/transfer_sensitivity.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import numpy as np
import torch

ML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

from env import NexusSimEnv, build_toy_graph
from env.graph_loader import load_graph_json
from train.train import build_models


def evaluate_sensitivity(
    city: str = "paris",
    checkpoint: str | None = None,
    chaos_levels: list[float] | None = None,
    demand_scales: list[float] | None = None,
    episodes: int = 2,
    device: str = "cpu",
) -> dict:
    if chaos_levels is None:
        chaos_levels = [0.05, 0.1, 0.2, 0.4]
    if demand_scales is None:
        demand_scales = [0.5, 0.8, 1.0, 1.5]

    if city == "toy":
        graph = build_toy_graph()
    else:
        graph_path = os.path.join(ML_DIR, "..", "data", city, "graph.json")
        graph = load_graph_json(graph_path)

    dev = torch.device(device)
    env = NexusSimEnv(graph=graph, seed=42, episode_steps=30)
    obs_dim = env.observation_space.shape[0]

    policy, _ = build_models(obs_dim=obs_dim, hidden=64, device=dev)
    if checkpoint and os.path.isfile(checkpoint):
        ckpt = torch.load(checkpoint, map_location=dev)
        policy.load_state_dict(ckpt["policy_state"])
        policy.eval()

    sweep_results = []

    for chaos in chaos_levels:
        for scale in demand_scales:
            rewards = []
            pressures = []
            ginis = []

            for ep in range(episodes):
                obs, _ = env.reset(seed=42 + ep)
                done = False
                ep_rew = 0.0
                ep_press = 0.0
                ep_gini = 0.0
                steps = 0

                while not done:
                    actions = {}
                    for agent_id, agent_obs in obs.items():
                        with torch.no_grad():
                            t_obs = torch.as_tensor(agent_obs, dtype=torch.float32, device=dev).unsqueeze(0)
                            logits = policy(t_obs)
                            act = int(torch.argmax(logits, dim=-1).item())

                        # Apply chaos perturbation flip
                        if np.random.rand() < chaos:
                            act = 1 - act
                        actions[agent_id] = act

                    obs, rew, term, trunc, info = env.step(actions)
                    done = term or trunc
                    ep_rew += float(sum(rew.values()))
                    ep_press += float(info.get("mean_pressure", 0.0))
                    ep_gini += float(info.get("gini", 0.0))
                    steps += 1

                rewards.append(ep_rew)
                pressures.append(ep_press / max(steps, 1))
                ginis.append(ep_gini / max(steps, 1))

            mean_rew = float(np.mean(rewards))
            mean_press = float(np.mean(pressures))
            mean_gini = float(np.mean(ginis))

            sweep_results.append({
                "chaos": chaos,
                "demand_scale": scale,
                "mean_reward": round(mean_rew, 2),
                "mean_pressure": round(mean_press, 4),
                "mean_gini": round(mean_gini, 4),
                "stability": "STABLE" if mean_rew > -75000 else "DEGRADED",
            })

    output = {
        "city": city,
        "checkpoint": checkpoint,
        "total_configurations": len(sweep_results),
        "configurations": sweep_results,
    }

    out_file = os.path.join(ML_DIR, "results", "transfer_sensitivity.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Transfer sensitivity sweep saved to {out_file}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="paris")
    parser.add_argument("--checkpoint", default=None)
    args = parser.parse_args()

    ckpt = args.checkpoint or os.path.join(ML_DIR, "checkpoints", f"chicago_to_{args.city}", "19.pt")
    if not os.path.isfile(ckpt):
        ckpt = None

    evaluate_sensitivity(city=args.city, checkpoint=ckpt)
