"""MAPPO training driver (Phase 7.5-7.7, US-D03).

Runs the shared-weight MAPPO trainer against the toy environment, logging
episode reward / pressure / equity / Gini to MLflow every episode and writing
checkpoints every ``--checkpoint-interval`` episodes to
``ml/checkpoints/<city>/<episode>.pt``.

Example:
    python -m train.train --city toy --episodes 1000 --alpha 1.0 --beta 1.0
    python -m train.train --city toy --episodes 500 --resume latest
"""

from __future__ import annotations

import argparse
import os
import sys

import mlflow
import numpy as np
import torch
import torch.optim as optim
from tqdm import tqdm

ML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

from env import NexusSimEnv, build_toy_graph
from env.graph_loader import load_graph_json
from models import PolicyNetwork, ValueNetwork
from train.ppo import compute_gae, ppo_update
from train.rollout import collect_episode, evaluate_fixed_baseline

_CPU = os.environ.get("NEXUS_TORCH_THREADS", "1")
torch.set_num_threads(int(_CPU))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MAPPO signal-control training")
    parser.add_argument("--city", default="toy", help="graph/city to train on")
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--gamma", type=float, default=0.95)
    parser.add_argument("--lam", type=float, default=0.95)
    parser.add_argument("--clip-eps", type=float, default=0.2)
    parser.add_argument("--entropy-coef", type=float, default=0.003)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.0)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--decision-interval", type=float, default=5.0)
    parser.add_argument("--episode-steps", type=int, default=100)
    parser.add_argument("--checkpoint-interval", type=int, default=500)
    parser.add_argument("--log-interval", type=int, default=10)
    parser.add_argument(
        "--episodes-per-update", type=int, default=4,
        help="number of episodes collected before each PPO update; >1 batches "
             "GAE advantages across episodes, cutting the variance from the "
             "stochastic continuation and stabilising the value net "
             "(--episodes always counts total episodes)",
    )
    parser.add_argument("--checkpoint-dir", default=None)
    parser.add_argument("--resume", default=None, help="path or 'latest'")
    parser.add_argument("--baseline-episodes", type=int, default=10)
    parser.add_argument("--experiment", default=None)
    parser.add_argument("--device", default="cpu")
    parser.add_argument(
        "--reward-scale", type=float, default=0.0,
        help="divisor for per-step rewards before GAE/PPO so returns are O(1); "
             "0.0 (default) auto-scales from the fixed-cycle baseline "
             "(|baseline episode reward| / episode_steps)",
    )
    return parser.parse_args()


def build_models(obs_dim, hidden, device):
    policy = PolicyNetwork(obs_dim, hidden=hidden).to(device)
    value_net = ValueNetwork(obs_dim, hidden=hidden).to(device)
    return policy, value_net


def load_checkpoint(path, policy, value_net, policy_opt, value_opt, device):
    ckpt = torch.load(path, map_location=device)
    policy.load_state_dict(ckpt["policy_state"])
    value_net.load_state_dict(ckpt["value_state"])
    policy_opt.load_state_dict(ckpt["policy_opt_state"])
    value_opt.load_state_dict(ckpt["value_opt_state"])
    return ckpt.get("episode", 0) + 1


def latest_checkpoint(checkpoint_dir):
    if not os.path.isdir(checkpoint_dir):
        return None
    candidates = [int(f[:-3]) for f in os.listdir(checkpoint_dir) if f.endswith(".pt")]
    return os.path.join(checkpoint_dir, "%d.pt" % max(candidates)) if candidates else None


def main() -> None:
    args = parse_args()
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device(args.device)

    graph = build_toy_graph()
    if args.city != "toy":
        data_dir = os.path.join(ML_DIR, "..", "data", args.city)
        graph_path = os.path.join(data_dir, "graph.json")
        if not os.path.isfile(graph_path):
            print("WARNING: %s not found; falling back to toy graph" % graph_path)
        else:
            graph = load_graph_json(graph_path)
            print("Loaded %s: %d intersections, %d zones" %
                  (args.city, graph["num_intersections"], len(graph["zones"])))
    env = NexusSimEnv(
        graph=graph,
        seed=args.seed,
        alpha=args.alpha,
        beta=args.beta,
        decision_interval=args.decision_interval,
        episode_steps=args.episode_steps,
    )

    policy, value_net = build_models(env.observation_space.shape[0], args.hidden, device)
    policy_opt = optim.Adam(policy.parameters(), lr=args.lr)
    value_opt = optim.Adam(value_net.parameters(), lr=args.lr)

    checkpoint_dir = args.checkpoint_dir or os.path.join(ML_DIR, "checkpoints", args.city)
    os.makedirs(checkpoint_dir, exist_ok=True)

    baseline = evaluate_fixed_baseline(env, args.baseline_episodes)
    print("Fixed-cycle baseline:", baseline)

    reward_scale = args.reward_scale
    if reward_scale <= 0.0:
        reward_scale = max(1.0, abs(baseline["episode_reward"]) / args.episode_steps)
    print("Reward scale:", reward_scale)

    experiment = args.experiment or "mappo-%s" % args.city
    # Keep using the repo's file-based tracking store (mlruns/) instead of the
    # database backend MLflow now requires by default.
    os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    mlflow_uri = "file:///" + os.path.join(ML_DIR, "mlruns").replace("\\", "/")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment(experiment)

    with mlflow.start_run():
        params = dict(vars(args))
        params["reward_scale"] = reward_scale
        mlflow.log_params(params)
        mlflow.log_metrics({("baseline_" + k): v for k, v in baseline.items()})

        start_ep = 0
        if args.resume:
            path = args.resume if args.resume != "latest" else latest_checkpoint(checkpoint_dir)
            if path and os.path.isfile(path):
                start_ep = load_checkpoint(path, policy, value_net, policy_opt, value_opt, device)
                pct = 100.0 * start_ep / args.episodes
                print("Resumed from %s (episode %d of %d — %.1f%% complete)"
                      % (path, start_ep, args.episodes, pct))
            else:
                print("No checkpoint found to resume from; training from scratch")

        if start_ep >= args.episodes:
            print("Training already complete at %d episodes; nothing to do." % args.episodes)
            return

        agents = sorted(env.graph["intersections"])
        episode = start_ep
        next_log = start_ep
        next_ckpt = start_ep
        pbar = tqdm(total=args.episodes, initial=start_ep, desc=f"mappo {args.city}",
                    unit="ep", dynamic_ncols=True, mininterval=1.0)
        while episode < args.episodes:
            batch = {
                i: {"obs": [], "act": [], "logp": [], "adv": [], "ret": []}
                for i in agents
            }
            summaries = []
            n_collect = min(args.episodes_per_update, args.episodes - episode)
            for _ in range(n_collect):
                rollout = collect_episode(env, policy, value_net, device)
                summaries.append(rollout["summary"])
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
                episode += 1
            pbar.update(n_collect)

            total_p_loss = total_v_loss = 0.0
            for i in agents:
                p_loss, v_loss = ppo_update(
                    policy, value_net, policy_opt, value_opt,
                    torch.cat(batch[i]["obs"]),
                    torch.cat(batch[i]["act"]),
                    torch.cat(batch[i]["logp"]),
                    torch.cat(batch[i]["adv"]),
                    torch.cat(batch[i]["ret"]),
                    clip_eps=args.clip_eps, entropy_coef=args.entropy_coef,
                    n_epochs=4, batch_size=256,
                )
                total_p_loss += p_loss
                total_v_loss += v_loss

            summary = {k: sum(s[k] for s in summaries) / len(summaries)
                       for k in summaries[0]}
            step = episode - 1
            mlflow.log_metrics({
                "episode_reward": summary["episode_reward"],
                "pressure": summary["mean_pressure"],
                "equity": summary["equity"],
                "gini": summary["gini"],
                "policy_loss": total_p_loss / len(agents),
                "value_loss": total_v_loss / len(agents),
            }, step=step)

            if step >= next_log or step == args.episodes - 1:
                pbar.set_postfix(reward=f"{summary['episode_reward']:.1f}",
                                 pressure=f"{summary['mean_pressure']:.3f}",
                                 equity=f"{summary['equity']:.1f}",
                                 gini=f"{summary['gini']:.3f}",
                                 complete=f"{100.0 * (step + 1) / args.episodes:.1f}%")
                next_log = max(next_log + args.log_interval, step + 1)

            if step >= next_ckpt or step == args.episodes - 1:
                path = os.path.join(checkpoint_dir, "%d.pt" % step)
                torch.save({
                    "episode": step,
                    "policy_state": policy.state_dict(),
                    "value_state": value_net.state_dict(),
                    "policy_opt_state": policy_opt.state_dict(),
                    "value_opt_state": value_opt.state_dict(),
                    "alpha": args.alpha,
                    "beta": args.beta,
                }, path)
                mlflow.log_artifact(path)
                pbar.write("checkpoint saved: %s" % path)
                next_ckpt = max(next_ckpt + args.checkpoint_interval, step + 1)
        pbar.close()
        print(f"Training complete: mappo {args.city} "
              f"({args.episodes} episodes, reward={summary['episode_reward']:.1f})")


if __name__ == "__main__":
    main()
