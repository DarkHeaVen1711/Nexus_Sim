"""Phase 32 - Named Entity Recognition (NER) for Traffic Incidents (NLP-7).

Extracts spatial anchors (STREET, HIGHWAY, MILE_MARKER), vehicle entities (VEHICLE_TYPE),
and temporal values (DURATION, TIME) from raw citizen or emergency incident reports.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


class TrafficNERExtractor:
    """Regex and pattern-based Named Entity Recognition tailored for transport networks."""

    # Lexicon patterns
    STREET_SUFFIXES = r"(?:Avenue|Ave|Street|St|Boulevard|Blvd|Road|Rd|Drive|Dr|Lane|Ln|Expressway|Hwy|Highway|Way|Parkway|Pkwy)"
    VEHICLE_TYPES = {"bus", "car", "truck", "semi", "ambulance", "motorcycle", "bike", "shuttle", "van", "suv"}

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract typed entities with character span offsets."""
        entities: List[Dict[str, Any]] = []

        # 1. Street names (e.g. Michigan Ave, Lake Shore Drive, 55th St)
        street_pattern = rf"\b(?:[A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)*)\s+{self.STREET_SUFFIXES}\b"
        for m in re.finditer(street_pattern, text, re.IGNORECASE):
            entities.append({
                "entity": m.group(0),
                "label": "LOCATION",
                "start": m.start(),
                "end": m.end(),
            })

        # 2. Vehicle types
        words = text.lower().split()
        for w in words:
            clean_w = re.sub(r"[^\w]", "", w)
            if clean_w in self.VEHICLE_TYPES:
                idx = text.lower().find(clean_w)
                entities.append({
                    "entity": clean_w,
                    "label": "VEHICLE",
                    "start": idx,
                    "end": idx + len(clean_w),
                })

        # 3. Durations (e.g. 30 mins, 2 hours, 45 seconds)
        duration_match = re.search(r"(\d+)\s*(?:minutes?|mins?|hours?|hrs?|seconds?|secs?)", text, re.IGNORECASE)
        if duration_match:
            entities.append({
                "entity": duration_match.group(0),
                "label": "DURATION",
                "start": duration_match.start(),
                "end": duration_match.end(),
            })

        # 4. Severity adjectives
        severity_match = re.search(r"\b(minor|moderate|major|severe|fatal|critical)\b", text, re.IGNORECASE)
        if severity_match:
            entities.append({
                "entity": severity_match.group(0),
                "label": "SEVERITY",
                "start": severity_match.start(),
                "end": severity_match.end(),
            })

        return {
            "text": text,
            "entity_count": len(entities),
            "entities": entities,
        }
