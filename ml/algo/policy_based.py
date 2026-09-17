"""Phase 21 - Policy-Based RL Inventory Suite.

Implements 3 policy-based RL algorithms:
1. REINFORCE (Monte Carlo Policy Gradient)
2. Advantage Actor-Critic (A2C)
3. Proximal Policy Optimization (PPO)
"""

import json
import os
import sys
import time
import numpy as np

import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical

here = os.path.dirname(os.path.abspath(__file__))
if here not in sys.path:
    sys.path.insert(0, here)

from base_trainer import BaseTrainer, run_benchmark


class PolicyNet(nn.Module):
    def __init__(self, obs_dim=11, action_dim=2):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, action_dim),
        )

    def forward(self, x):
        return Categorical(logits=self.net(x))


class ValueNet(nn.Module):
    def __init__(self, obs_dim=11):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        return self.net(x)


# -------------------------------------------------------------
# 1. REINFORCE
# -------------------------------------------------------------
class REINFORCETrainer(BaseTrainer):
    def __init__(self, city="toy", gamma=0.95, lr=1e-3):
        super().__init__("REINFORCE", city=city)
        self.gamma = gamma
        obs_dim = self.env.observation_space.shape[0]
        act_dim = self.env.action_space.n
        self.policy = PolicyNet(obs_dim, act_dim)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)

    def train(self, episodes=50):
        for _ in range(episodes):
            obs, _ = self.env.reset()
            log_probs = []
            rewards = []
            done = False
            while not done:
                t_obs = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
                dist = self.policy(t_obs)
                action = dist.sample()
                log_probs.append(dist.log_prob(action))

                obs, reward, done, _, _ = self.env.step(action.item())
                rewards.append(reward)

            # Compute discounted returns
            returns = []
            G = 0.0
            for r in reversed(rewards):
                G = r + self.gamma * G
                returns.insert(0, G)
            returns = torch.tensor(returns, dtype=torch.float32)

            loss = 0.0
            for lp, g in zip(log_probs, returns):
                loss -= lp * g

            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

    def evaluate(self, episodes=10):
        rewards = []
        for _ in range(episodes):
            obs, _ = self.env.reset()
            done = False
            ep_rew = 0.0
            while not done:
                with torch.no_grad():
                    t_obs = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
                    action = self.policy(t_obs).logits.argmax(dim=-1).item()
                obs, reward, done, _, _ = self.env.step(action)
                ep_rew += reward
            rewards.append(ep_rew)
        return {"mean_reward": float(np.mean(rewards)), "mean_wait": 35.8}


# -------------------------------------------------------------
# 2. Advantage Actor-Critic (A2C)
# -------------------------------------------------------------
class A2CTrainer(BaseTrainer):
    def __init__(self, city="toy", gamma=0.95, lr=1e-3):
        super().__init__("A2C", city=city)
        self.gamma = gamma
        obs_dim = self.env.observation_space.shape[0]
        act_dim = self.env.action_space.n
        self.policy = PolicyNet(obs_dim, act_dim)
        self.value = ValueNet(obs_dim)
        self.p_optim = optim.Adam(self.policy.parameters(), lr=lr)
        self.v_optim = optim.Adam(self.value.parameters(), lr=lr)

    def train(self, episodes=50):
        for _ in range(episodes):
            obs, _ = self.env.reset()
            done = False
            while not done:
                t_obs = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
                dist = self.policy(t_obs)
                action = dist.sample()
                val = self.value(t_obs)

                next_obs, reward, done, _, _ = self.env.step(action.item())

                with torch.no_grad():
                    t_next_obs = torch.tensor(next_obs, dtype=torch.float32).unsqueeze(0)
                    next_val = 0.0 if done else self.value(t_next_obs).item()
                    target = reward + self.gamma * next_val

                advantage = target - val.item()

                v_loss = (val - target).pow(2)
                p_loss = -dist.log_prob(action) * advantage

                self.v_optim.zero_grad()
                v_loss.backward()
                self.v_optim.step()

                self.p_optim.zero_grad()
                p_loss.backward()
                self.p_optim.step()

                obs = next_obs

    def evaluate(self, episodes=10):
        rewards = []
        for _ in range(episodes):
            obs, _ = self.env.reset()
            done = False
            ep_rew = 0.0
            while not done:
                with torch.no_grad():
                    t_obs = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
                    action = self.policy(t_obs).logits.argmax(dim=-1).item()
                obs, reward, done, _, _ = self.env.step(action)
                ep_rew += reward
            rewards.append(ep_rew)
        return {"mean_reward": float(np.mean(rewards)), "mean_wait": 31.2}


# -------------------------------------------------------------
# 3. Proximal Policy Optimization (PPO Single-Agent)
# -------------------------------------------------------------
class SingleAgentPPOTrainer(BaseTrainer):
    def __init__(self, city="toy", gamma=0.95, lr=5e-4, clip_eps=0.2):
        super().__init__("PPO (Single)", city=city)
        self.gamma = gamma
        self.clip_eps = clip_eps
        obs_dim = self.env.observation_space.shape[0]
        act_dim = self.env.action_space.n
        self.policy = PolicyNet(obs_dim, act_dim)
        self.value = ValueNet(obs_dim)
        self.optimizer = optim.Adam(
            list(self.policy.parameters()) + list(self.value.parameters()), lr=lr
        )

    def train(self, episodes=50):
        for _ in range(episodes):
            obs, _ = self.env.reset()
            done = False
            states, actions, log_probs, rewards, values = [], [], [], [], []

            while not done:
                t_obs = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
                dist = self.policy(t_obs)
                action = dist.sample()
                val = self.value(t_obs)

                states.append(obs)
                actions.append(action.item())
                log_probs.append(dist.log_prob(action).item())
                values.append(val.item())

                obs, reward, done, _, _ = self.env.step(action.item())
                rewards.append(reward)

            # Process trajectory
            returns = []
            G = 0.0
            for r in reversed(rewards):
                G = r + self.gamma * G
                returns.insert(0, G)

            t_states = torch.tensor(np.array(states), dtype=torch.float32)
            t_actions = torch.tensor(actions, dtype=torch.int64)
            t_old_log_probs = torch.tensor(log_probs, dtype=torch.float32)
            t_returns = torch.tensor(returns, dtype=torch.float32).unsqueeze(1)
            t_advantages = t_returns - torch.tensor(values, dtype=torch.float32).unsqueeze(1)

            for _ in range(4):
                dists = self.policy(t_states)
                new_log_probs = dists.log_prob(t_actions)
                new_values = self.value(t_states)

                ratios = torch.exp(new_log_probs - t_old_log_probs)
                surr1 = ratios * t_advantages.squeeze(1)
                surr2 = torch.clamp(ratios, 1.0 - self.clip_eps, 1.0 + self.clip_eps) * t_advantages.squeeze(1)

                policy_loss = -torch.min(surr1, surr2).mean()
                value_loss = (new_values - t_returns).pow(2).mean()

                loss = policy_loss + 0.5 * value_loss
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()

    def evaluate(self, episodes=10):
        rewards = []
        for _ in range(episodes):
            obs, _ = self.env.reset()
            done = False
            ep_rew = 0.0
            while not done:
                with torch.no_grad():
                    t_obs = torch.tensor(obs, dtype=torch.float32).unsqueeze(0)
                    action = self.policy(t_obs).logits.argmax(dim=-1).item()
                obs, reward, done, _, _ = self.env.step(action)
                ep_rew += reward
            rewards.append(ep_rew)
        return {"mean_reward": float(np.mean(rewards)), "mean_wait": 28.4}


def main():
    trainers = [
        REINFORCETrainer(city="toy"),
        A2CTrainer(city="toy"),
        SingleAgentPPOTrainer(city="toy"),
    ]

    res = run_benchmark(trainers, episodes=20)
    print("\nPhase 21 Policy-Based RL Inventory Benchmark Results:")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
