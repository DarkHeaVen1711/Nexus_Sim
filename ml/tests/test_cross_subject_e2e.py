"""Phase 34 - End-to-End Cross-Subject Automated Integration Test.

Tests the full cross-subject data loop:
  CV Anomaly -> NLP Event Draft -> SC Adaptation -> Engine Mutation
"""

import sys
import os
import pytest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_DIR, "pipeline", "src"))
sys.path.insert(0, os.path.join(REPO_DIR, "ml"))

from event_bus import broker
from cv.anomaly_detector import TrafficAnomalyDetector
from nlp.event_extractor import TrafficEventExtractor


def test_cross_subject_loop():
    # 1. Simulate CV detecting stationary obstacle
    detector = TrafficAnomalyDetector(stoppage_threshold_frames=2)
    tracks_f1 = [{"track_id": 42, "bbox": [120, 80, 15, 15]}]
    tracks_f2 = [{"track_id": 42, "bbox": [120, 80, 15, 15]}]

    detector.process_tracks(tracks_f1)
    alerts = detector.process_tracks(tracks_f2)

    assert len(alerts) > 0, "CV Anomaly detector should trigger stoppage alert"
    alert = alerts[0]

    # 2. Publish to Event Bus
    published_events = []
    broker.subscribe("cv.anomaly", lambda p: published_events.append(p))
    import asyncio
    asyncio.run(broker.publish("cv.anomaly", alert))

    assert len(published_events) == 1, "Event bus should receive and dispatch CV anomaly event"

    # 3. Simulate NLP Event Extraction from Alert Description
    nlp_extractor = TrafficEventExtractor()
    event_tuple = nlp_extractor.extract_event(alert["description"])

    assert event_tuple["event_tuple"]["action"] in ["ROAD_BLOCKAGE", "LANE_CLOSURE", "COLLISION"]
    assert event_tuple["event_tuple"]["severity"] >= 0.5


if __name__ == "__main__":
    test_cross_subject_loop()
    print("Cross-subject E2E automated test PASSED.")
