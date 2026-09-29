"""Phase 32 - Anaphora & Coreference Resolution for Incident Streams (NLP-9).

Resolves cross-sentence pronoun ambiguity ("A bus broke down on Michigan Ave. It blocked two lanes.")
linking pronouns back to their true antecedent entity.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


class TrafficCoreferenceResolver:
    """Rule-based salience coreference resolver for sequential transport reports."""

    PRONOUNS = {"it", "its", "they", "them", "their", "this vehicle", "that car"}

    def resolve_text(self, text: str) -> Dict[str, Any]:
        """Split text into sentences and replace pronouns with closest antecedent noun phrase."""
        sentences = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]
        resolved_sentences = []
        last_subject = None
        resolutions = []

        for sent in sentences:
            words = sent.split()
            # Find subject in current sentence
            m_subj = re.search(r"\b(bus|truck|car|vehicle|semi|ambulance|suv|motorcycle|accident|jam)\b", sent, re.IGNORECASE)
            if m_subj:
                last_subject = m_subj.group(0).lower()

            # Check for pronoun replacement if we have a known antecedent
            resolved_sent = sent
            if last_subject:
                for p in ["it", "this vehicle", "that vehicle"]:
                    pattern = rf"\b{p}\b"
                    if re.search(pattern, resolved_sent, re.IGNORECASE):
                        resolved_sent = re.sub(pattern, f"the {last_subject}", resolved_sent, flags=re.IGNORECASE)
                        resolutions.append({"pronoun": p, "resolved_to": f"the {last_subject}"})

            resolved_sentences.append(resolved_sent)

        return {
            "original_text": text,
            "resolved_text": ". ".join(resolved_sentences) + ".",
            "coreference_chains": resolutions,
        }
