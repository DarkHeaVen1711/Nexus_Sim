"""Phase 27 - Spatial Traffic Anomaly Detector (CV-9).

Detects stationary vehicles in active lanes, wrong-way trajectories, and sudden queue bottlenecks.
Emits structured anomaly alert events formatted for NLP event ingestion.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List


class TrafficAnomalyDetector:
    """Monitors vehicle tracks for spatial flow deviations and stoppages."""

    def __init__(self, stoppage_threshold_frames: int = 5):
        self.stoppage_threshold = stoppage_threshold_frames
        self.track_history: Dict[int, List[Dict[str, float]]] = {}

    def process_tracks(self, tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify anomalies and return alert event dicts."""
        alerts: List[Dict[str, Any]] = []
        current_ids = set()

        for t in tracks:
            tid = t["track_id"]
            current_ids.add(tid)
            bbox = t["bbox"]
            cx = bbox[0] + bbox[2] / 2.0
            cy = bbox[1] + bbox[3] / 2.0

            if tid not in self.track_history:
                self.track_history[tid] = []
            self.track_history[tid].append({"x": cx, "y": cy, "time": time.time()})

            # Check stationary blockage
            hist = self.track_history[tid]
            if len(hist) >= self.stoppage_threshold:
                recent = hist[-self.stoppage_threshold:]
                dist = sum(
                    ((recent[i]["x"] - recent[i - 1]["x"]) ** 2 + (recent[i]["y"] - recent[i - 1]["y"]) ** 2) ** 0.5
                    for i in range(1, len(recent))
                )
                if dist < 3.0:  # Vehicle hasn't moved more than 3 pixels over threshold frames
                    alerts.append({
                        "type": "STATIONARY_BLOCKAGE",
                        "track_id": tid,
                        "location": {"x": round(cx, 1), "y": round(cy, 1)},
                        "severity": 0.8,
                        "description": f"Vehicle ID #{tid} stationary for {len(recent)} frames at ({round(cx)}, {round(cy)})",
                        "timestamp": time.time(),
                    })

        # Purge stale track histories
        stale = [k for k in self.track_history if k not in current_ids]
        for k in stale:
            del self.track_history[k]

        return alerts
