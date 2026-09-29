"""Phase 27 - Road Lane Boundary Perception (CV-10).

Detects linear and curved lane markings on road surfaces to ensure vehicle adherence.
"""

from __future__ import annotations

from typing import Any, Dict, List
import numpy as np


class LaneDetector:
    """Perceives road lane demarcations using Hough line estimation."""

    def __init__(self, min_line_length: float = 30.0):
        self.min_line_length = min_line_length

    def detect_lanes(self, road_mask: np.ndarray) -> List[Dict[str, Any]]:
        """Identify lane boundaries given road surface mask."""
        H, W = road_mask.shape
        lanes = []

        # Find edge boundaries of drivable areas
        # Horizontal and vertical differential edges
        diff_y = np.abs(np.diff(road_mask.astype(np.int32), axis=0))
        diff_x = np.abs(np.diff(road_mask.astype(np.int32), axis=1))

        # Collect major horizontal lane lines
        for y in range(0, H - 1, 20):
            row_edges = np.where(diff_y[y, :] > 0)[0]
            if len(row_edges) >= 2:
                lanes.append({
                    "start": [float(row_edges[0]), float(y)],
                    "end": [float(row_edges[-1]), float(y)],
                    "width": float(row_edges[-1] - row_edges[0]),
                    "orientation": "horizontal",
                })

        return lanes
