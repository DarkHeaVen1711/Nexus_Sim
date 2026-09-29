"""Phase 31 - Multinomial Naive Bayes Incident Categorizer (NLP-5).

Categorizes incoming incident reports into categories:
ACCIDENT, BREAKDOWN, ROADWORK, WEATHER_HAZARD, GENERAL_CONGESTION.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List


class NaiveBayesIncidentClassifier:
    """Multinomial Naive Bayes text classifier with Laplace smoothing."""

    CATEGORIES = ["ACCIDENT", "BREAKDOWN", "ROADWORK", "WEATHER_HAZARD", "GENERAL_CONGESTION"]

    KEYWORDS = {
        "ACCIDENT": ["crash", "collision", "hit", "flipped", "ambulance", "police", "pileup", "injury"],
        "BREAKDOWN": ["stalled", "broken", "engine", "smoke", "tire", "flat", "towed", "disabled", "stopped"],
        "ROADWORK": ["construction", "pothole", "crew", "cones", "lane closed", "resurfacing", "maintenance", "drilling"],
        "WEATHER_HAZARD": ["flood", "rain", "fog", "ice", "waterlogged", "tree fallen", "storm", "snow"],
        "GENERAL_CONGESTION": ["heavy", "slow", "delay", "gridlock", "jam", "backup", "crawling", "volume"],
    }

    def predict(self, text: str) -> Dict[str, Any]:
        """Classify report and return predicted class and posterior distribution."""
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        words = clean.split()

        scores: Dict[str, float] = {}
        for cat in self.CATEGORIES:
            # Prior log prob
            score = math.log(1.0 / len(self.CATEGORIES))
            kw_list = self.KEYWORDS[cat]
            for w in words:
                matches = sum(1 for kw in kw_list if kw in w or w in kw)
                # Likelihood with Laplace smoothing
                score += math.log((matches + 1.0) / (len(kw_list) + 20.0))
            scores[cat] = score

        # Softmax normalization for probabilities
        max_s = max(scores.values())
        exp_scores = {c: math.exp(s - max_s) for c, s in scores.items()}
        sum_exp = sum(exp_scores.values())
        probs = {c: round(exp_scores[c] / sum_exp, 3) for c in self.CATEGORIES}

        best_cat = max(probs, key=probs.get)
        confidence = probs[best_cat]

        return {
            "predicted_category": best_cat,
            "confidence": confidence,
            "category_probabilities": probs,
        }
