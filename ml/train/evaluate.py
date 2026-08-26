"""Multi-city MARL vs Webster fixed-cycle evaluation (Phase 9.7).

Loads a trained checkpoint (or uses the fixed-cycle baseline) and evaluates
it on one or more cities, printing a side-by-side comparison table.

Example:
    python -m train.evaluate --cities piedmont --checkpoint checkpoints/piedmont/19.pt
    python -m train.evaluate --cities toy piedmont --episodes 20
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

ML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

from env import NexusSimEnv, build_toy_graph
from env.graph_loader import load_graph_json
from models import PolicyNetwork, ValueNetwork
from train.rollout import FixedCycleBaseline, evaluate_fixed_baseline


def _load_env(city: str, episode_steps: int = 100) -> NexusSimEnv:
    if city == "toy":
        graph = build_toy_graph()
    else:
        graph_path = os.path.join(ML_DIR, "..", "data", city, "graph.json")
        if not os.path.isfile(graph_path):
            raise FileNotFoundError(f"No graph.json for {city}: {graph_path}")
        graph = load_graph_json(graph_path)
    return NexusSimEnv(graph=graph, seed=0, episode_steps=episode_steps)


def _eval_marl(env: NexusSimEnv, checkpoint_path: str, n_episodes: int = 20,
               device: str = "cpu") -> dict:
    obs_dim = env.observation_space.shape[0]
    policy = PolicyNetwork(obs_dim).to(device)
    value_net = ValueNetwork(obs_dim).to(device)
    ckpt = torch.load(checkpoint_path, map_location=device)
    policy.load_state_dict(ckpt["policy_state"])
    value_net.load_state_dict(ckpt["value_state"])
    policy.eval()

    from train.rollout import collect_episode
    totals = {"episode_reward": 0.0, "mean_pressure": 0.0, "equity": 0.0, "gini": 0.0}
    n_steps = 0
    for _ in range(n_episodes):
        rollout = collect_episode(env, policy, value_net, device)
        s = rollout["summary"]
        totals["episode_reward"] += s["episode_reward"]
        totals["mean_pressure"] += s["mean_pressure"]
        totals["equity"] += s["equity"]
        totals["gini"] += s["gini"]
        n_steps += 1
    totals["episode_reward"] /= n_episodes
    if n_steps > 0:
        for k in ("mean_pressure", "equity", "gini"):
            totals[k] /= n_steps
    return totals


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-city evaluation")
    parser.add_argument("--cities", nargs="+", default=["toy", "piedmont"])
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--checkpoint", default=None,
                        help="Path to MARL checkpoint (.pt); omit for baseline-only")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    rows = []
    for city in args.cities:
        print(f"\n--- {city} ---")
        env = _load_env(city, episode_steps=100)
        print(f"  intersections={env.num_agents}  obs_dim={env.observation_space.shape[0]}")

        baseline = evaluate_fixed_baseline(env, n_episodes=args.episodes)
        print(f"  Webster: reward={baseline['episode_reward']:.1f}  "
              f"pressure={baseline['mean_pressure']:.3f}  gini={baseline['gini']:.3f}")

        row = {"city": city, "intersections": env.num_agents, "webster": baseline}

        if args.checkpoint and os.path.isfile(args.checkpoint):
            marl = _eval_marl(env, args.checkpoint, args.episodes, args.device)
            print(f"  MARL:    reward={marl['episode_reward']:.1f}  "
                  f"pressure={marl['mean_pressure']:.3f}  gini={marl['gini']:.3f}")
            improvement = ((marl["episode_reward"] - baseline["episode_reward"])
                           / abs(baseline["episode_reward"]) * 100)
            print(f"  Improvement: {improvement:+.1f}%")
            row["marl"] = marl
            row["improvement_pct"] = improvement
        rows.append(row)

    out_path = os.path.join(ML_DIR, "results", "comparison.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
