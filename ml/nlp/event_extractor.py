"""Phase 32 - Structured Incident Event Tuple Extraction (NLP-8).

Converts free-form incident reports and NER outputs into standardized execution tuples:
  (Action, Location, Severity, Duration_s, Speed_Multiplier)
ready for direct invocation via C++ engine apply_incident().
"""

from __future__ import annotations

import re
from typing import Any, Dict, List
from .ner_extractor import TrafficNERExtractor


class TrafficEventExtractor:
    """Extracts machine-actionable event tuples from text."""

    def __init__(self):
        self.ner = TrafficNERExtractor()

    def extract_event(self, text: str) -> Dict[str, Any]:
        ner_res = self.ner.extract_entities(text)
        entities = ner_res["entities"]

        location = "UNKNOWN"
        for ent in entities:
            if ent["label"] == "LOCATION":
                location = ent["entity"]
                break

        # Action determination
        action = "ROAD_BLOCKAGE"
        if re.search(r"lane closed|closure|blocked", text, re.IGNORECASE):
            action = "LANE_CLOSURE"
        elif re.search(r"crash|accident|collision", text, re.IGNORECASE):
            action = "COLLISION"
        elif re.search(r"construction|repair|work", text, re.IGNORECASE):
            action = "CONSTRUCTION"

        # Severity & speed multiplier
        severity_val = 0.5
        speed_mult = 0.5
        if re.search(r"severe|major|critical|total", text, re.IGNORECASE):
            severity_val = 0.9
            speed_mult = 0.1  # 90% slowdown
        elif re.search(r"minor|slight", text, re.IGNORECASE):
            severity_val = 0.2
            speed_mult = 0.8  # 20% slowdown

        # Duration in seconds
        duration_s = 600.0  # default 10 mins
        dur_match = re.search(r"(\d+)\s*(mins?|minutes?|hours?|hrs?)", text, re.IGNORECASE)
        if dur_match:
            val = float(dur_match.group(1))
            unit = dur_match.group(2).lower()
            if "h" in unit:
                duration_s = val * 3600.0
            else:
                duration_s = val * 60.0

        return {
            "event_tuple": {
                "action": action,
                "location": location,
                "severity": severity_val,
                "duration_s": duration_s,
                "speed_multiplier": speed_mult,
            },
            "raw_text": text,
            "executable_for_engine": location != "UNKNOWN",
        }
