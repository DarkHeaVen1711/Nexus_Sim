"""Phase 19 - Shared RL Algorithm Framework Base Classes & Benchmark Harness.

Provides BaseTrainer interface, single-agent Gym wrapper, configs parser, and
comparative benchmarking harness for the 12-algorithm inventory.
"""

import abc
import json
import os
import sys
import time
import numpy as np

import gymnasium as gym
from gymnasium import spaces

here = os.path.dirname(os.path.abspath(__file__))
ml_root = os.path.dirname(here)
if ml_root not in sys.path:
    sys.path.insert(0, ml_root)

from env.nexus_sim_env import NexusSimEnv


class SingleAgentNexusSimEnv(gym.Env):
    """Wraps multi-agent NexusSimEnv into single-agent view for tabular & standard RL algorithms."""

    def __init__(self, city="toy"):
        super().__init__()
        self.env = NexusSimEnv()
        self.observation_space = self.env.observation_space
        self.action_space = self.env.action_space

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        obs, info = self.env.reset(seed=seed, options=options)
        # Flatten multi-agent observation to agent 0 for single-agent algorithms
        first_obs = list(obs.values())[0] if isinstance(obs, dict) else obs[0]
        return first_obs, info

    def step(self, action):
        # Broadcast action to all agent intersections
        actions = {agent_id: action for agent_id in range(self.env.num_agents)}
        obs, reward, terminated, truncated, info = self.env.step(actions)
        first_obs = list(obs.values())[0] if isinstance(obs, dict) else obs[0]
        mean_reward = sum(reward.values()) if isinstance(reward, dict) else float(np.mean(reward))
        done = terminated or truncated
        return first_obs, mean_reward, done, False, info


class BaseTrainer(abc.ABC):
    """Abstract base class for all 12 RL algorithms in NexusSim inventory."""

    def __init__(self, algo_name: str, city: str = "toy"):
        self.algo_name = algo_name
        self.city = city
        self.env = SingleAgentNexusSimEnv(city=city)

    @abc.abstractmethod
    def train(self, episodes: int = 100):
        pass

    @abc.abstractmethod
    def evaluate(self, episodes: int = 10):
        pass


def run_benchmark(trainers, episodes=50):
    results = {}
    print(f"=== Starting RL Algorithm Benchmark ({len(trainers)} algorithms) ===")

    for trainer in trainers:
        t0 = time.time()
        print(f"Training {trainer.algo_name}...")
        trainer.train(episodes=episodes)
        eval_res = trainer.evaluate(episodes=10)
        elapsed = time.time() - t0

        results[trainer.algo_name] = {
            "mean_reward": round(eval_res["mean_reward"], 2),
            "mean_wait": round(eval_res["mean_wait"], 1),
            "training_time_s": round(elapsed, 2),
        }
        print(f"[{trainer.algo_name}] Mean Reward: {eval_res['mean_reward']:.2f}, Avg Wait: {eval_res['mean_wait']:.1f}s ({elapsed:.1f}s)")

    return results


def main():
    print("Shared RL Algorithm Framework (Phase 19) initialized.")


if __name__ == "__main__":
    main()
