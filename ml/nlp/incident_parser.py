"""Phase 17 - NLP Incident Report Parser & RapidFuzz Street Gazetteer.

Parses free-text incident descriptions into structured specs:
- edges: list[int]
- severity: float (0.0 to 1.0)
- duration_s: float (seconds)
- incident_type: str
"""

import json
import os
import re
import sys

try:
    from rapidfuzz import process, fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

here = os.path.dirname(os.path.abspath(__file__))
if here not in sys.path:
    sys.path.insert(0, here)


class IncidentParser:
    def __init__(self, graph_dict=None):
        self.street_gazetteer = {
            "michigan ave": [101, 102],
            "state street": [103, 104],
            "wacker drive": [105, 106],
            "grand ave": [107, 108],
            "chicago ave": [109, 110],
            "halsted st": [111, 112],
            "ashland ave": [113, 114],
        }

    def parse(self, text: str):
        q = text.lower()

        # Severity parsing
        severity = 0.5  # Moderate default
        if any(w in q for w in ["major", "severe", "block", "closed"]):
            severity = 0.9
        elif any(w in q for w in ["minor", "slight", "small", "stalled"]):
            severity = 0.3

        # Incident type
        itype = "accident"
        if "construction" in q or "work" in q:
            itype = "construction"
        elif "closure" in q or "blocked" in q:
            itype = "closure"
        elif "event" in q or "parade" in q:
            itype = "event"

        # Duration parsing (e.g. 5 minutes, 300s)
        duration_s = 300.0  # Default 5 minutes
        dur_match = re.search(r"(\d+)\s*(min|minute|sec|second)", q)
        if dur_match:
            val = float(dur_match.group(1))
            unit = dur_match.group(2)
            duration_s = val * 60.0 if "min" in unit else val

        # Street matching
        matched_edges = [101, 102]  # Default corridor target
        if HAS_RAPIDFUZZ:
            match = process.extractOne(q, self.street_gazetteer.keys(), scorer=fuzz.partial_ratio)
            if match and match[1] >= 60:
                matched_edges = self.street_gazetteer[match[0]]
        else:
            for sname, edges in self.street_gazetteer.items():
                if sname in q:
                    matched_edges = edges
                    break

        return {
            "type": itype,
            "severity": severity,
            "duration_s": duration_s,
            "edges": matched_edges,
            "description": text,
        }


def main():
    parser = IncidentParser()
    res = parser.parse("Major accident blocking Michigan Ave for 10 minutes")
    print(f"Parsed Incident Spec: {res}")


if __name__ == "__main__":
    main()
