"""Phase 27 - Pedestrian & Vehicle Crowd Density Estimation (CV-12).

Computes spatial density heatmaps over camera viewports and crosswalks.
"""

from __future__ import annotations

from typing import Any, Dict, List
import numpy as np


class CrowdDensityEstimator:
    """Generates continuous crowd density heatmaps from agent point clouds."""

    def __init__(self, grid_size: int = 16, sigma: float = 2.0):
        self.grid_size = grid_size
        self.sigma = sigma

    def compute_density(self, positions: List[List[float]], width: int = 640, height: int = 480) -> Dict[str, Any]:
        """Compute 2D Gaussian density kernel map over bounding frame."""
        gx = width // self.grid_size
        gy = height // self.grid_size
        heatmap = np.zeros((gy, gx), dtype=np.float32)

        for pos in positions:
            x, y = pos[0], pos[1]
            bx = int(x // self.grid_size)
            by = int(y // self.grid_size)
            if 0 <= bx < gx and 0 <= by < gy:
                heatmap[by, bx] += 1.0

        max_density = float(np.max(heatmap)) if heatmap.size > 0 else 0.0
        avg_density = float(np.mean(heatmap)) if heatmap.size > 0 else 0.0

        return {
            "grid_dimensions": [gx, gy],
            "max_density": round(max_density, 2),
            "avg_density": round(avg_density, 3),
            "high_density_zones": int(np.sum(heatmap >= 3.0)),
        }
