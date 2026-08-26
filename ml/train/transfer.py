"""Transfer learning: fine-tune a trained policy from one city to another (Phase 9.3-9.5).

Loads a checkpoint trained on a source city, creates an environment for the
target city, and continues PPO training with a reduced learning rate.

The policy/value networks are reinitialised if obs_dim differs between cities
(source and target may have different numbers of approaches). When obs_dim
matches, weights are transferred directly.

Example:
    python -m train.transfer --source toy --target piedmont --episodes 200 --lr 1e-4
    python -m train.transfer --source checkpoints/piedmont/19.pt --target toy --episodes 100
"""

from __future__ import annotations

import argparse
import os
import sys

import mlflow
import numpy as np
import torch
import torch.optim as optim

ML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

from env import NexusSimEnv, build_toy_graph
from env.graph_loader import load_graph_json
from models import PolicyNetwork, ValueNetwork
from train.ppo import compute_gae, ppo_update
from train.rollout import collect_episode, evaluate_fixed_baseline
from train.train import build_models, latest_checkpoint, load_checkpoint

_CPU = os.environ.get("NEXUS_TORCH_THREADS", "1")
torch.set_num_threads(int(_CPU))


def _load_env(city: str, episode_steps: int = 100, seed: int = 0) -> NexusSimEnv:
    if city == "toy":
        graph = build_toy_graph()
    else:
        graph_path = os.path.join(ML_DIR, "..", "data", city, "graph.json")
        if not os.path.isfile(graph_path):
            raise FileNotFoundError(f"No graph.json for {city}: {graph_path}")
        graph = load_graph_json(graph_path)
    return NexusSimEnv(graph=graph, seed=seed, episode_steps=episode_steps)


def _resolve_source(args_source: str) -> str:
    """Return a checkpoint path. Accepts a city name or a direct .pt path."""
    if args_source.endswith(".pt") and os.path.isfile(args_source):
        return args_source
    ckpt_dir = os.path.join(ML_DIR, "checkpoints", args_source)
    path = latest_checkpoint(ckpt_dir)
    if path:
        return path
    raise FileNotFoundError(f"No checkpoint found for source '{args_source}' in {ckpt_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Transfer learning between cities")
    parser.add_argument("--source", required=True,
                        help="Source city name or checkpoint .pt path")
    parser.add_argument("--target", required=True, help="Target city name")
    parser.add_argument("--episodes", type=int, default=200)
    parser.add_argument("--lr", type=float, default=1e-4,
                        help="Fine-tuning learning rate (lower than training)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--gamma", type=float, default=0.95)
    parser.add_argument("--lam", type=float, default=0.95)
    parser.add_argument("--clip-eps", type=float, default=0.2)
    parser.add_argument("--entropy-coef", type=float, default=0.003)
    parser.add_argument("--episode-steps", type=int, default=100)
    parser.add_argument("--decision-interval", type=float, default=5.0)
    parser.add_argument("--checkpoint-interval", type=int, default=50)
    parser.add_argument("--log-interval", type=int, default=10)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--experiment", default=None)
    parser.add_argument("--reward-scale", type=float, default=0.0)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device(args.device)

    src_path = _resolve_source(args.source)
    print(f"Source checkpoint: {src_path}")

    env = _load_env(args.target, args.episode_steps, args.seed)
    obs_dim = env.observation_space.shape[0]
    print(f"Target: {args.target}  intersections={env.num_agents}  obs_dim={obs_dim}")

    policy, value_net = build_models(obs_dim, args.hidden, device)
    policy_opt = optim.Adam(policy.parameters(), lr=args.lr)
    value_opt = optim.Adam(value_net.parameters(), lr=args.lr)

    ckpt = torch.load(src_path, map_location=device)
    src_obs_dim = ckpt["policy_state"]["fc1.weight"].shape[1]
    if src_obs_dim == obs_dim:
        policy.load_state_dict(ckpt["policy_state"])
        value_net.load_state_dict(ckpt["value_state"])
        print(f"Transferred weights (obs_dim={src_obs_dim} matches)")
    else:
        print(f"obs_dim mismatch ({src_obs_dim} -> {obs_dim}); training from scratch")

    checkpoint_dir = os.path.join(ML_DIR, "checkpoints", f"{args.source}_to_{args.target}")
    os.makedirs(checkpoint_dir, exist_ok=True)

    baseline = evaluate_fixed_baseline(env, n_episodes=5)
    print(f"Target Webster baseline: {baseline}")

    reward_scale = args.reward_scale
    if reward_scale <= 0.0:
        reward_scale = max(1.0, abs(baseline["episode_reward"]) / args.episode_steps)
    print(f"Reward scale: {reward_scale:.1f}")

    experiment = args.experiment or f"transfer-{args.source}-to-{args.target}"
    mlflow_uri = "file:///" + os.path.join(ML_DIR, "mlruns").replace("\\", "/")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment(experiment)

    with mlflow.start_run():
        mlflow.log_params({
            "source": args.source, "target": args.target, "source_checkpoint": src_path,
            "lr": args.lr, "episodes": args.episodes,
        })
        mlflow.log_metrics({("baseline_" + k): v for k, v in baseline.items()})

        agents = sorted(env.graph["intersections"])
        for episode in range(args.episodes):
            batch = {
                i: {"obs": [], "act": [], "logp": [], "adv": [], "ret": []}
                for i in agents
            }
            rollout = collect_episode(env, policy, value_net, device)
            summary = rollout["summary"]
            for i in agents:
                tensors = rollout["tensors"][i]
                scaled_rewards = tensors["rew"] / reward_scale
                advantages, returns = compute_gae(
                    scaled_rewards, tensors["val"], tensors["done"],
                    args.gamma, args.lam,
                )
                batch[i]["obs"].append(tensors["obs"])
                batch[i]["act"].append(tensors["act"])
                batch[i]["logp"].append(tensors["logp"])
                batch[i]["adv"].append(advantages)
                batch[i]["ret"].append(returns)

            for i in agents:
                ppo_update(
                    policy, value_net, policy_opt, value_opt,
                    torch.cat(batch[i]["obs"]),
                    torch.cat(batch[i]["act"]),
                    torch.cat(batch[i]["logp"]),
                    torch.cat(batch[i]["adv"]),
                    torch.cat(batch[i]["ret"]),
                    clip_eps=args.clip_eps, entropy_coef=args.entropy_coef,
                    n_epochs=4, batch_size=256,
                )

            mlflow.log_metrics({
                "episode_reward": summary["episode_reward"],
                "pressure": summary["mean_pressure"],
                "equity": summary["equity"],
                "gini": summary["gini"],
            }, step=episode)

            if episode % args.log_interval == 0 or episode == args.episodes - 1:
                print("episode %d reward=%.1f pressure=%.3f gini=%.3f" %
                      (episode, summary["episode_reward"],
                       summary["mean_pressure"], summary["gini"]))

            if episode % args.checkpoint_interval == 0 or episode == args.episodes - 1:
                path = os.path.join(checkpoint_dir, "%d.pt" % episode)
                torch.save({
                    "episode": episode,
                    "policy_state": policy.state_dict(),
                    "value_state": value_net.state_dict(),
                    "policy_opt_state": policy_opt.state_dict(),
                    "value_opt_state": value_opt.state_dict(),
                }, path)
                print(f"  checkpoint: {path}")

    print(f"\nTransfer complete: {args.source} -> {args.target}")


if __name__ == "__main__":
    main()
