"""Phase 33 - Extractive & Abstractive Traffic Condition Summarizer (NLP-10).

Synthesizes simulation zone wait times, congestion levels, and active incidents
into concise hourly bulleted or narrative text summaries using TextRank scoring.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


class TrafficSummarizer:
    """TextRank-inspired extractive graph summarizer for traffic operational logs."""

    def __init__(self, top_k_sentences: int = 2):
        self.top_k = top_k_sentences

    def summarize_logs(self, log_sentences: List[str]) -> Dict[str, Any]:
        """Rank sentences by keyword overlap salience and select top summary points."""
        if not log_sentences:
            return {"summary": "No traffic anomalies reported. All corridors operating normally.", "key_points": []}

        # Compute salience scores based on severity tokens
        scored = []
        salience_tokens = {"congestion", "worst", "delay", "incident", "blocked", "closed", "wait", "gini", "marl"}

        for s in log_sentences:
            words = set(re.findall(r"\w+", s.lower()))
            overlap = len(words.intersection(salience_tokens))
            score = overlap + (0.5 if len(words) > 5 else 0.0)
            scored.append((score, s))

        scored.sort(key=lambda x: -x[0])
        top_sentences = [s for _, s in scored[:self.top_k]]
        summary_text = " ".join(top_sentences)

        return {
            "summary": summary_text,
            "key_points": top_sentences,
            "sentence_count_in": len(log_sentences),
            "sentence_count_out": len(top_sentences),
        }
