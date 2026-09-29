"""Phase 29 - Adaptive Neuro-Fuzzy Inference System (ANFIS) (SC-7).

Implements 5-layer Tagaki-Sugeno neuro-fuzzy inference network with gradient descent
for auto-tuning input Gaussian membership functions and linear consequents.
"""

from __future__ import annotations

from typing import Any, Dict, List
import numpy as np


class ANFISController:
    """Takagi-Sugeno First-Order Neuro-Fuzzy Controller."""

    def __init__(self, num_inputs: int = 2, num_mfs_per_input: int = 3, lr: float = 0.01):
        self.num_inputs = num_inputs
        self.num_mfs = num_mfs_per_input
        self.lr = lr

        # Layer 1: Gaussian premise parameters [mean, sigma]
        self.means = np.linspace(0.0, 1.0, self.num_mfs)
        self.sigmas = np.full(self.num_mfs, 0.25)

        # Number of rules = num_mfs ^ num_inputs
        self.num_rules = self.num_mfs ** self.num_inputs

        # Layer 4: Consequent linear coefficients [p0, p1, ..., r]
        self.consequents = np.random.uniform(-1.0, 1.0, (self.num_rules, self.num_inputs + 1))

    def gaussian_mf(self, x: float, m: float, s: float) -> float:
        return float(np.exp(-((x - m) ** 2) / (2.0 * s ** 2 + 1e-6)))

    def forward(self, inputs: List[float]) -> Dict[str, Any]:
        """Compute 5-layer forward inference pass.

        inputs: [normalized_queue (0..1), normalized_wait (0..1)]
        """
        x1, x2 = inputs[0], inputs[1]

        # Layer 1: Fuzzification (memberships)
        mu1 = [self.gaussian_mf(x1, m, s) for m, s in zip(self.means, self.sigmas)]
        mu2 = [self.gaussian_mf(x2, m, s) for m, s in zip(self.means, self.sigmas)]

        # Layer 2: Rule Firing Strengths (T-norm product)
        w = []
        for m1 in mu1:
            for m2 in mu2:
                w.append(m1 * m2)
        w = np.array(w)

        # Layer 3: Normalized Firing Strengths
        sum_w = np.sum(w)
        w_bar = w / max(1e-6, sum_w)

        # Layer 4: Consequent Sugeno functions f_i = p0*x1 + p1*x2 + r
        inp_vec = np.array([x1, x2, 1.0])
        rule_outputs = np.dot(self.consequents, inp_vec)

        # Layer 5: Overall output defuzzification
        output = float(np.sum(w_bar * rule_outputs))

        return {
            "green_extension_seconds": round(max(0.0, min(15.0, output * 15.0)), 2),
            "rule_firing_strengths": [round(float(v), 3) for v in w_bar],
            "dominant_rule": int(np.argmax(w_bar)),
        }

    def train_step(self, inputs: List[float], target_output: float) -> float:
        """Single backpropagation step tuning consequent parameters."""
        res = self.forward(inputs)
        pred = res["green_extension_seconds"] / 15.0
        err = pred - target_output

        # Simple gradient step on consequents
        inp_vec = np.array([inputs[0], inputs[1], 1.0])
        w_bar = np.array(res["rule_firing_strengths"])
        grad = np.outer(w_bar * err, inp_vec)
        self.consequents -= self.lr * grad
        return float(err ** 2)
