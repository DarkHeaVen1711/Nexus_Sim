"""Policy and value networks for the shared-weight MARL agents (TR-ML-05).

Both networks are 3-layer MLPs (TECH_STACK.md §Subsystem 3) shared across all
intersection agents. The policy outputs a categorical distribution over
``{EXTEND, SWITCH}``; the value network regresses the expected return for GAE.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class PolicyNetwork(nn.Module):
    """Categorical policy over the two-phase signal actions."""

    def __init__(self, obs_dim: int, hidden: int = 64, n_actions: int = 2):
        super().__init__()
        self.fc1 = nn.Linear(obs_dim, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.fc3 = nn.Linear(hidden, n_actions)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x)

    def sample_action(self, obs: torch.Tensor) -> tuple:
        """Sample one action per observation; returns (actions, log_probs)."""
        probs = torch.distributions.Categorical(logits=self.forward(obs))
        action = probs.sample()
        return action, probs.log_prob(action)

    def evaluate(self, obs: torch.Tensor, actions: torch.Tensor) -> tuple:
        """Log-probabilities and entropies for given observations/actions."""
        probs = torch.distributions.Categorical(logits=self.forward(obs))
        return probs.log_prob(actions), probs.entropy()


class ValueNetwork(nn.Module):
    """Shared state-value network used for advantage estimation."""

    def __init__(self, obs_dim: int, hidden: int = 64):
        super().__init__()
        self.fc1 = nn.Linear(obs_dim, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.fc3 = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x)
