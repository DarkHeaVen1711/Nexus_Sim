"""Transfer learning: fine-tune a trained policy from one city to another (Phase 9.3-9.5).

Loads a checkpoint trained on a source city, creates an environment for the
target city, and continues PPO training with a reduced learning rate.

The policy/value networks are reinitialised if obs_dim differs between cities
(source and target may have different numbers of approaches). When obs_dim
matches, weights are transferred directly.

``--resume latest`` (or a path to an existing transfer checkpoint) continues a
previously closed/interrupted transfer run from its last checkpoint; the
progress bar then doubles as an overall completion meter (episodes done in
the full budget, so resuming shows e.g. "40%|████| 200/500").

Example:
    python -m train.transfer --source toy --target piedmont --episodes 200 --lr 1e-4
    python -m train.transfer --source checkpoints/piedmont/19.pt --target toy --episodes 100
    python -m train.transfer --source checkpoints/toy/249.pt --target paris \\
        --episodes 500 --resume latest
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
from train.ppo import compute_gae, ppo_update
from train.rollout import collect_episode, evaluate_fixed_baseline
from train.train import build_models, latest_checkpoint

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
    if args_source.endswith(".pt"):
        if os.path.isfile(args_source):
            return args_source
        raise FileNotFoundError(f"Checkpoint path not found: {args_source}")
    ckpt_dir = os.path.join(ML_DIR, "checkpoints", args_source)
    path = latest_checkpoint(ckpt_dir)
    if path:
        return path
    raise FileNotFoundError(f"No checkpoint found for source '{args_source}' in {ckpt_dir}")


def _resolve_resume(resume_arg: str | None, checkpoint_dir: str) -> str | None:
    """Resolve --resume to a checkpoint path inside the target transfer dir."""
    if not resume_arg:
        return None
    if resume_arg == "latest":
        path = latest_checkpoint(checkpoint_dir)
        if path:
            return path
        raise FileNotFoundError(f"No checkpoint found to resume from in {checkpoint_dir}")
    if resume_arg.endswith(".pt"):
        if os.path.isfile(resume_arg):
            return resume_arg
        raise FileNotFoundError(f"Resume checkpoint path not found: {resume_arg}")
    raise FileNotFoundError(f"Resume target not recognised: {resume_arg}")


def load_checkpoint(path, policy, value_net, policy_opt, value_opt, device):
    ckpt = torch.load(path, map_location=device)
    policy.load_state_dict(ckpt["policy_state"])
    value_net.load_state_dict(ckpt["value_state"])
    policy_opt.load_state_dict(ckpt["policy_opt_state"])
    value_opt.load_state_dict(ckpt["value_opt_state"])
    return ckpt


def main() -> None:
    parser = argparse.ArgumentParser(description="Transfer learning between cities")
    parser.add_argument("--source", required=True,
                        help="Source city name or checkpoint .pt path")
    parser.add_argument("--target", required=True, help="Target city name")
    parser.add_argument("--episodes", type=int, default=200,
                        help="Total episodes in the budget (resume runs to this total)")
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
    parser.add_argument(
        "--resume", default=None,
        help="continue an existing transfer from its last checkpoint: 'latest' "
             "or a path to a .pt inside the target transfer dir",
    )
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device(args.device)

    src_path = _resolve_source(args.source)
    print(f"Source checkpoint: {src_path}")

    env = _load_env(args.target, args.episode_steps, args.seed)
    env.decision_interval = args.decision_interval
    obs_dim = env.observation_space.shape[0]
    print(f"Target: {args.target}  intersections={env.num_agents}  obs_dim={obs_dim}")

    # Sanitize source tag: use basename without extension for directory name.
    src_tag = os.path.splitext(os.path.basename(args.source))[0]
    checkpoint_dir = os.path.join(ML_DIR, "checkpoints", f"{src_tag}_to_{args.target}")
    os.makedirs(checkpoint_dir, exist_ok=True)

    resume_path = _resolve_resume(args.resume, checkpoint_dir)
    resume_ckpt = None
    start_ep = 0

    if resume_path:
        resume_ckpt = torch.load(resume_path, map_location=device)
        r_obs_dim = resume_ckpt["policy_state"]["fc1.weight"].shape[1]
        if r_obs_dim != obs_dim:
            raise ValueError(f"Resume checkpoint obs_dim {r_obs_dim} != env obs_dim {obs_dim}")
        r_hidden = resume_ckpt["policy_state"]["fc1.weight"].shape[0]
        policy, value_net = build_models(obs_dim, r_hidden, device)
        policy_opt = optim.Adam(policy.parameters(), lr=args.lr)
        value_opt = optim.Adam(value_net.parameters(), lr=args.lr)
        start_ep = load_checkpoint(resume_path, policy, value_net,
                                   policy_opt, value_opt, device)["episode"] + 1
        pct = 100.0 * start_ep / args.episodes
        print(f"Resumed transfer from {resume_path} "
              f"(episode {start_ep} of {args.episodes} — {pct:.1f}% complete)")
    else:
        ckpt = torch.load(src_path, map_location=device)
        src_obs_dim = ckpt["policy_state"]["fc1.weight"].shape[1]
        src_hidden = ckpt["policy_state"]["fc1.weight"].shape[0]
        if src_obs_dim == obs_dim:
            policy, value_net = build_models(obs_dim, src_hidden, device)
            policy.load_state_dict(ckpt["policy_state"])
            value_net.load_state_dict(ckpt["value_state"])
            print(f"Transferred weights (obs_dim={src_obs_dim}, hidden={src_hidden} match)")
        else:
            policy, value_net = build_models(obs_dim, args.hidden, device)
            print(f"obs_dim mismatch ({src_obs_dim} -> {obs_dim}); training from scratch")
        policy_opt = optim.Adam(policy.parameters(), lr=args.lr)
        value_opt = optim.Adam(value_net.parameters(), lr=args.lr)

    if start_ep >= args.episodes:
        print(f"Transfer already complete at {args.episodes} episodes; nothing to do.")
        return

    baseline = evaluate_fixed_baseline(env, n_episodes=5)
    print(f"Target Webster baseline: {baseline}")

    reward_scale = args.reward_scale
    if reward_scale <= 0.0 and resume_ckpt is not None:
        reward_scale = resume_ckpt.get("reward_scale", 0.0)
    if reward_scale <= 0.0:
        reward_scale = max(1.0, abs(baseline["episode_reward"]) / args.episode_steps)
    print(f"Reward scale: {reward_scale:.1f}")

    experiment = args.experiment or f"transfer-{args.source}-to-{args.target}"
    # Keep using the repo's file-based tracking store (mlruns/) instead of the
    # database backend MLflow now requires by default.
    os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    mlflow_uri = "file:///" + os.path.join(ML_DIR, "mlruns").replace("\\", "/")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment(experiment)

    with mlflow.start_run():
        params = {
            "source": args.source, "target": args.target, "source_checkpoint": src_path,
            "lr": args.lr, "episodes": args.episodes,
        }
        if resume_path:
            params["resumed_from"] = resume_path
        mlflow.log_params(params)
        mlflow.log_metrics({("baseline_" + k): v for k, v in baseline.items()})

        agents = sorted(env.graph["intersections"])
        total = args.episodes
        with tqdm(total=total, initial=start_ep,
                  desc=f"transfer {args.source} -> {args.target}",
                  unit="ep", dynamic_ncols=True, mininterval=1.0) as pbar:
            for episode in range(start_ep, total):
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

                if episode % args.log_interval == 0 or episode == total - 1:
                    pbar.set_postfix(reward=f"{summary['episode_reward']:.1f}",
                                     pressure=f"{summary['mean_pressure']:.3f}",
                                     gini=f"{summary['gini']:.3f}",
                                     complete=f"{100.0 * (episode + 1) / total:.1f}%")

                if episode % args.checkpoint_interval == 0 or episode == total - 1:
                    path = os.path.join(checkpoint_dir, "%d.pt" % episode)
                    torch.save({
                        "episode": episode,
                        "policy_state": policy.state_dict(),
                        "value_state": value_net.state_dict(),
                        "policy_opt_state": policy_opt.state_dict(),
                        "value_opt_state": value_opt.state_dict(),
                        "reward_scale": reward_scale,
                    }, path)
                    pbar.write(f"checkpoint: {path}")

                pbar.update(1)
        print(f"Transfer complete: {args.source} -> {args.target} "
              f"({total} episodes, reward={summary['episode_reward']:.1f})")


if __name__ == "__main__":
    main()