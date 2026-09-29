"""Phase 31 - Citizen Sentiment Analysis Engine (NLP-3).

Analyzes citizen sentiment and frustration scores from community reports, tweets, and queries.
Computes compound sentiment [-1.0, 1.0] and frustration intensity [0.0, 1.0].
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


class TrafficSentimentAnalyzer:
    """Rule and lexicon-based sentiment analyzer tailored for urban transport feedback."""

    POSITIVE_WORDS = {
        "smooth", "fast", "clear", "flowing", "great", "improved", "quick", "safe",
        "on time", "efficient", "green", "good", "thank", "easy", "accessible"
    }

    NEGATIVE_WORDS = {
        "jam", "stuck", "blocked", "terrible", "awful", "delay", "late", "horrible",
        "gridlock", "accident", "crash", "pothole", "standstill", "rage", "broken",
        "worst", "hate", "waiting", "congestion", "chaos", "unacceptable", "bottleneck"
    }

    INTENSIFIERS = {"very", "extremely", "totally", "absolutely", "so", "completely"}

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Compute sentiment and urgency polarity scores."""
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        words = clean.split()

        pos_score = 0.0
        neg_score = 0.0
        multiplier = 1.0

        for i, w in enumerate(words):
            if w in self.INTENSIFIERS:
                multiplier = 1.5
                continue

            if w in self.POSITIVE_WORDS:
                pos_score += 1.0 * multiplier
                multiplier = 1.0
            elif w in self.NEGATIVE_WORDS:
                neg_score += 1.2 * multiplier
                multiplier = 1.0

        total = pos_score + neg_score
        if total == 0:
            compound = 0.0
            label = "NEUTRAL"
        else:
            compound = float((pos_score - neg_score) / (total + 1.0))
            if compound >= 0.15:
                label = "POSITIVE"
            elif compound <= -0.15:
                label = "NEGATIVE"
            else:
                label = "NEUTRAL"

        # Frustration intensity 0..1
        frustration = float(min(1.0, neg_score / 3.0))

        return {
            "text": text,
            "compound_sentiment": round(compound, 3),
            "sentiment_label": label,
            "frustration_intensity": round(frustration, 3),
            "urgent": frustration >= 0.7,
        }
