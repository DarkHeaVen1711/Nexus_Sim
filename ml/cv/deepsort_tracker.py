"""Phase 26 - DeepSORT Multi-Object Tracking Engine (CV-4).

Implements Kalman filtering for bounding box state propagation and cosine
appearance similarity matching for persistent vehicle ID tracking across camera frames.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Tuple
import numpy as np


class KalmanBoxTracker:
    """Kalman filter state estimator for single bounding box [x, y, w, h]."""

    count = 0

    def __init__(self, bbox: List[float], appearance_feat: np.ndarray | None = None):
        # State: [x_center, y_center, width, height, vx, vy, vw, vh]
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1

        xc = bbox[0] + bbox[2] / 2.0
        yc = bbox[1] + bbox[3] / 2.0
        w = max(1.0, float(bbox[2]))
        h = max(1.0, float(bbox[3]))

        self.x = np.array([xc, yc, w, h, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
        self.time_since_update = 0
        self.hits = 1
        self.hit_streak = 1
        self.age = 0
        self.appearance_feat = appearance_feat

    def predict(self) -> List[float]:
        """Advance state by constant-velocity model."""
        self.x[0] += self.x[4]
        self.x[1] += self.x[5]
        self.x[2] += self.x[6]
        self.x[3] += self.x[7]

        self.age += 1
        if self.time_since_update > 0:
            self.hit_streak = 0
        self.time_since_update += 1
        return self.get_state()

    def update(self, bbox: List[float], appearance_feat: np.ndarray | None = None) -> None:
        """Update state from observation with measurement residual."""
        self.time_since_update = 0
        self.hits += 1
        self.hit_streak += 1

        xc = bbox[0] + bbox[2] / 2.0
        yc = bbox[1] + bbox[3] / 2.0
        w = max(1.0, float(bbox[2]))
        h = max(1.0, float(bbox[3]))

        meas = np.array([xc, yc, w, h], dtype=np.float32)
        res = meas - self.x[:4]

        # Simple Kalman gain update
        gain_pos = 0.7
        gain_vel = 0.3
        self.x[:4] += gain_pos * res
        self.x[4:] += gain_vel * res

        if appearance_feat is not None:
            if self.appearance_feat is None:
                self.appearance_feat = appearance_feat
            else:
                # Exponential running average of appearance feature
                self.appearance_feat = 0.8 * self.appearance_feat + 0.2 * appearance_feat
                norm = np.linalg.norm(self.appearance_feat)
                if norm > 1e-6:
                    self.appearance_feat /= norm

    def get_state(self) -> List[float]:
        """Convert [xc, yc, w, h] back to [x, y, w, h]."""
        w = max(1.0, float(self.x[2]))
        h = max(1.0, float(self.x[3]))
        x = self.x[0] - w / 2.0
        y = self.x[1] - h / 2.0
        return [float(x), float(y), w, h]


def compute_iou(bb_test: List[float], bb_gt: List[float]) -> float:
    """Compute Intersection over Union between two [x, y, w, h] boxes."""
    xx1 = max(bb_test[0], bb_gt[0])
    yy1 = max(bb_test[1], bb_gt[1])
    xx2 = min(bb_test[0] + bb_test[2], bb_gt[0] + bb_gt[2])
    yy2 = min(bb_test[1] + bb_test[3], bb_gt[1] + bb_gt[3])

    w = max(0.0, xx2 - xx1)
    h = max(0.0, yy2 - yy1)
    intersection = w * h

    area_test = max(1e-6, bb_test[2] * bb_test[3])
    area_gt = max(1e-6, bb_gt[2] * bb_gt[3])
    union = area_test + area_gt - intersection
    return float(intersection / union) if union > 0 else 0.0


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine distance in range [0, 1]."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-6 or norm_b < 1e-6:
        return 1.0
    sim = np.dot(a, b) / (norm_a * norm_b)
    return float(1.0 - max(-1.0, min(1.0, sim)))


class DeepSortTracker:
    """Multi-target vehicle tracker with appearance cosine distance gating."""

    def __init__(self, max_age: int = 10, min_hits: int = 1, iou_threshold: float = 0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.trackers: List[KalmanBoxTracker] = []

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Update tracker states given current frame detections.

        detections item: {"bbox": [x, y, w, h], "confidence": float, "appearance": np.ndarray (optional)}
        """
        # Predict positions
        for trk in self.trackers:
            trk.predict()

        # Match detections to active tracks
        matched_indices = []
        unmatched_dets = list(range(len(detections)))
        unmatched_trks = list(range(len(self.trackers)))

        if len(self.trackers) > 0 and len(detections) > 0:
            iou_matrix = np.zeros((len(detections), len(self.trackers)), dtype=np.float32)
            for d, det in enumerate(detections):
                for t, trk in enumerate(self.trackers):
                    iou = compute_iou(det["bbox"], trk.get_state())
                    # If appearance features present, blend appearance distance
                    if det.get("appearance") is not None and trk.appearance_feat is not None:
                        cos_dist = cosine_distance(det["appearance"], trk.appearance_feat)
                        score = 0.6 * iou + 0.4 * (1.0 - cos_dist)
                    else:
                        score = iou
                    iou_matrix[d, t] = score

            # Greedy bipartite matching
            while True:
                if iou_matrix.size == 0 or np.max(iou_matrix) < self.iou_threshold:
                    break
                d, t = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
                if iou_matrix[d, t] < self.iou_threshold:
                    break
                matched_indices.append((d, t))
                iou_matrix[d, :] = -1.0
                iou_matrix[:, t] = -1.0
                if d in unmatched_dets:
                    unmatched_dets.remove(d)
                if t in unmatched_trks:
                    unmatched_trks.remove(t)

        # Update matched trackers
        for d, t in matched_indices:
            det = detections[d]
            self.trackers[t].update(det["bbox"], det.get("appearance"))

        # Create new trackers for unmatched detections
        for d in unmatched_dets:
            det = detections[d]
            self.trackers.append(KalmanBoxTracker(det["bbox"], det.get("appearance")))

        # Filter active results and dead tracks
        active_results = []
        remaining_trackers = []
        for trk in self.trackers:
            if trk.time_since_update <= self.max_age:
                remaining_trackers.append(trk)
                if trk.hits >= self.min_hits:
                    active_results.append({
                        "track_id": trk.id,
                        "bbox": trk.get_state(),
                        "hits": trk.hits,
                        "age": trk.age,
                    })

        self.trackers = remaining_trackers
        return active_results
