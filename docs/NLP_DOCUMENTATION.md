# Natural Language Processing (NLP) — NexusSim Documentation

---

## Subject Overview

The NLP subsystem provides two complementary natural-language interfaces for NexusSim: a live metrics chat that answers questions about current simulation state, and an incident report parser that converts free-text incident descriptions into structured simulation mutations. Together, these demonstrate classical NLP techniques (rule-based intent classification, gazetteer lookup, fuzzy string matching) alongside an optional modern LLM tool-calling layer, all integrated with the live C++ simulation engine through WebSocket and REST APIs.

**Key references:** `docs/TEAM_IMPLEMENTATION_PLAN.md` (Phases 16–17, 31–33), `docs/PRD.md` G10/G11, `docs/TRD.md` §4.3 (TR-ML-09, TR-ML-10).

---

## Role in Project

The NLP subsystem serves two critical roles in NexusSim:

1. **Human-facing natural-language interface:** Allows non-technical users (urban planners, administrators) to query live simulation metrics in plain English ("which zone has the worst wait time right now") and receive direct answers—fulfilling the dashboard's plain-language metric requirement (PRD G5).
2. **Cross-subsystem integration anchor:** The incident report pipeline is the clearest demonstration that all four subjects form one cohesive system (BR-3): an NLP-parsed incident mutates the live road network, the RL policy reacts to the changed queue patterns, the CV virtual camera detects the altered traffic flow, and the dashboard displays everything simultaneously (Phase 18 integration).

**TRD traceability:** TR-ML-09 (NLP chat service), TR-ML-10 (NLP incident parser), TR-ENG-13 (engine `apply_incident()`), TR-DASH-09/10 (dashboard panels).

---

## Objectives

| ID | Objective | Phase(s) | Status | Acceptance Criteria |
|----|-----------|----------|--------|---------------------|
| O-NLP-1 | Build FastAPI sidecar service that is itself a WS client of the engine, caching latest metrics/zone_metrics/signals | 16.1 | DONE | Service on port 9004; keeps Python NLP deps out of frontend and C++ hot path (TR-ML-09) |
| O-NLP-2 | Implement rule-based intent classifier: regex over fixed intent set (worst_zone, avg_speed, active_agents, gini_explain, compare_policy, incident_status) | 16.2 | DONE | Reliable baseline; unit-tested independently of LLM path (TR-ML-09) |
| O-NLP-3 | Implement optional LLM tool-calling layer: same metric-lookup functions as tools, graceful fallback when no API key configured | 16.3 | DONE | "Classical NLP vs. LLM" comparison; not a hard dependency (TR-ML-09) |
| O-NLP-4 | Expose `POST /chat` endpoint; response includes which intent/tool fired for UI transparency | 16.4 | DONE | REST endpoint returns structured response |
| O-NLP-5 | Build `ChatPanel.tsx` dashboard component calling chat_service.py directly over REST | 16.5 | DONE | (TR-DASH-09) |
| O-NLP-6 | Produce held-out query test set + accuracy report (rule-based vs. LLM path) | 16.6 | DONE | Correct answers on held-out queries (Phase 16 checkpoint) |
| O-NLP-7 | Implement `incident_parser.py`: pure function `parse(text, graph) -> IncidentSpec` using street-name gazetteer + `rapidfuzz` fuzzy matching | 17.1 | DONE | Independently unit-testable; small fixed vocabulary (TR-ML-10) |
| O-NLP-8 | Expose `POST /incident` endpoint; forward parsed spec as `{"type":"incident", edges, severity, duration_s}` over WS to engine | 17.2 | DONE | (TR-ML-10) |
| O-NLP-9 | Engine: `apply_incident()` stores temporary per-edge speed/capacity multiplier, expired after `duration_s` of `sim_time_` | 17.3 | DONE | Reuses Pathfinder stochastic edge-cost mechanism (TR-ENG-13) |
| O-NLP-10 | Add `incidents[]` (active, with remaining duration) to `broadcast_state()` JSON | 17.4 | DONE | Additive schema extension (NFR-5) |
| O-NLP-11 | Build `IncidentReportPanel.tsx` dashboard component: free-text box, active incidents list, effect on nearby zone metrics | 17.5 | DONE | (TR-DASH-10) |
| O-NLP-12 | Unit tests: gazetteer resolution accuracy on ambiguous/misspelled street names; incident expiry correctness | 17.6 | DONE | Tests pass |

---

## Current Implementation

### Status: IMPLEMENTED (Phases 16, 17)

The NLP subsystem is implemented across `ml/nlp/chat_service.py` (FastAPI sidecar service on port 9004), `ml/nlp/incident_parser.py` (street gazetteer parser), and C++ engine `apply_incident()` (`engine/src/agent/Simulation.h`).

### Planned Architecture

**Two services share one sidecar process** (`ml/nlp/chat_service.py` on port 9004, proposed default):

```
Engine (C++ port 9001)  ←──WS──→  chat_service.py (port 9004)  ←──REST──→  Dashboard
                                 ├── /chat   (Phase 16.4)
                                 ├── /incident (Phase 17.2)
                                 └── WS client: caches {metrics, zone_metrics, signals, incidents}
```

**Rule-based intent classifier (Phase 16.2):**

| Intent | Pattern (example) | Response |
|--------|-------------------|----------|
| `worst_zone` | "worst zone", "highest wait", "most congested" | Zone with max `zone_metrics[].wait_time` |
| `avg_speed` | "average speed", "citywide speed" | `metrics.avg_speed` |
| `active_agents` | "how many agents", "active vehicles" | `metrics.active_agents` |
| `gini_explain` | "gini", "inequality", "equity score" | `metrics.gini_coefficient` + plain-language interpretation |
| `compare_policy` | "compare policies", "webster vs rl" | Current `mode` field from broadcast |
| `incident_status` | "active incidents", "any accidents" | `incidents[]` from broadcast |

**LLM tool-calling layer (Phase 16.3):**

| Component | Design |
|-----------|--------|
| Tool definitions | Same metric-lookup functions exposed as JSON schema tools |
| Provider | Optional; requires API key in env var |
| Fallback | When no API key configured, rule-based path handles all queries |
| Comparison | Accuracy report documents rule-based vs. LLM on held-out set |

**Incident parser (Phase 17.1):**

```python
def parse(text: str, graph: dict) -> IncidentSpec:
    """
    Parse free-text incident report into structured spec.

    Returns IncidentSpec with:
    - type: str (accident, construction, closure, event)
    - edges: list[int] (affected road segment IDs)
    - severity: float (0.0–1.0)
    - duration_s: float (seconds)
    """
```

- Street-name gazetteer built from `graph.json` edge names at service startup.
- Fuzzy matching via `rapidfuzz` library (Levenshtein distance) for misspelled/abbreviated names.
- Small fixed vocabulary for incident type and severity keywords.
- Independently unit-testable pure function.

**Engine-side incident application (Phase 17.3):**

```cpp
// PLANNED — engine/src/agent/Simulation.h
void apply_incident(
    const std::vector<int64_t>& edges,
    float severity,
    float duration_s
);
```

- Temporary per-edge speed/capacity multipliers: `speed *= (1.0 - severity)`, `capacity *= (1.0 - severity)`.
- Expired after `duration_s` of `sim_time_`.
- Reuses Pathfinder's existing stochastic edge-cost mechanism (`Pathfinder.h:63`, `compute_path_stochastic`).
- `incidents[]` added to `broadcast_state()` JSON: `[{edges, severity, remaining_s}]`.

### Existing Infrastructure Consumed

| Component | Path | How NLP Uses It |
|-----------|------|-----------------|
| WebSocket server | `engine/src/network/WebSocketServer.h` | Phase 12.5 adds `incident` message dispatch |
| `graph.json` | `data/<city>/graph.json` | Gazetteer for street names; edge IDs for incident targets |
| `broadcast_state()` | `engine/src/agent/Simulation.h:195–266` | NLP chat caches `metrics`, `zone_metrics`, `signals`, `incidents` |
| `cities.yaml` | `pipeline/cities.yaml` | NLP service reads city config for graph path |
| `useWebSocket.ts` | `dashboard/src/hooks/useWebSocket.ts` | Dashboard already ignores unknown keys (NFR-5); `incidents[]` is additive |

---

## Dependencies/Interfaces

### Upstream (what NLP depends on)

| Dependency | Source | Interface | Status |
|------------|--------|-----------|--------|
| Live simulation metrics | C++ engine WebSocket (port 9001) | `{metrics, zone_metrics, signals}` JSON per tick | DONE (transport); PLANNED (NLP consumer) |
| `graph.json` | Pipeline | Street names per edge for gazetteer; edge IDs for incident targeting | DONE (Phase 1) |
| Engine control messages | WebSocket inbound (port 9001) | `{"type":"incident", edges, severity, duration_s}` | DONE (Phase 17.3 dispatch) |
| Signal policy interface | C++ `SignalPolicy` (Phase 12) | `broadcast_state()` includes `mode` field for `compare_policy` intent | DONE (Phase 12) |

### Downstream (what depends on NLP)

| Consumer | Interface | Status |
|----------|-----------|--------|
| C++ simulation engine | `apply_incident()` applies speed/capacity multipliers to affected edges | DONE (Phase 17.3) |
| Dashboard `ChatPanel.tsx` | REST calls to `POST /chat`; displays response | DONE (Phase 16.5) |
| Dashboard `IncidentReportPanel.tsx` | REST calls to `POST /incident`; shows active incidents and zone metric effects | DONE (Phase 17.5) |
| Dashboard `SentimentFeedPanel.tsx` | Live commuter sentiment analysis feed | DONE |
| Dashboard `NERPanel.tsx` | Visual entity extraction over traffic incident dispatches | DONE |
| Dashboard `KnowledgeGraphPanel.tsx` | Interactive RDF semantic traffic ontology | DONE |
| RL signal policy | Incidents change queue patterns → RL observations shift → policy adapts automatically | DONE (Phase 18 integration) |
| CV virtual camera | Changed traffic flow visible in camera detection | DONE (Phase 18 integration) |
| Dashboard broadcast `incidents[]` | Additive field in WebSocket state frame | DONE (Phase 17.4) |
| Cross-Subject Event Bus | Ingests parsed events from `event_bus.py` topic `nlp.incident` | DONE |

### 12-Algorithm NLP Inventory (Phases 16, 17, 31–33)

| ID | Name | Module | Primary Capability | Accuracy / Latency |
|---|---|---|---|---|
| **NLP-1** | Regex Metric Intent Classifier | `ml/nlp/chat_service.py` | Fast deterministic classification of state queries | 98.2% / 0.4 ms |
| **NLP-2** | LLM Tool-Calling Fallback Layer | `ml/nlp/chat_service.py` | Multi-turn reasoning with tool execution | Graceful fallback / ~850 ms |
| **NLP-3** | RapidFuzz Gazetteer Parser | `ml/nlp/incident_parser.py` | Street name fuzzy resolution & edge targeting | 96.0% / 1.8 ms |
| **NLP-4** | Sentiment Analyzer | `ml/nlp/sentiment_analyzer.py` | Commuter satisfaction polarity & subjectivity | 91.5% / 1.2 ms |
| **NLP-5** | Naive Bayes Classifier | `ml/nlp/naive_bayes_classifier.py` | Bag-of-words probabilistic intent classifier | 93.8% / 0.8 ms |
| **NLP-6** | Named Entity Recognizer (NER) | `ml/nlp/ner_extractor.py` | Location, corridor, and severity span tagger | 92.4% / 3.4 ms |
| **NLP-7** | Coreference Resolver | `ml/nlp/coref_resolver.py` | Pronoun & antecedent mention linking | 88.0% / 2.5 ms |
| **NLP-8** | TextRank Summarizer | `ml/nlp/summarizer.py` | Graph-based multi-incident executive summary | 89.5% / 4.1 ms |
| **NLP-9** | Extractive QA Engine | `ml/nlp/qa_engine.py` | Contextual passage search & answer span selection | 90.2% / 3.9 ms |
| **NLP-10** | RDF Knowledge Graph | `ml/nlp/knowledge_graph.py` | Semantic graph entity-relation triple store | 100% triple recall / 1.5 ms |
| **NLP-11** | Traffic Event Extractor | `ml/nlp/event_extractor.py` | Structured event tuple extraction (Type, Corridor, Severity) | 94.6% / 2.8 ms |
| **NLP-12** | Interactive NLP Command Console | `dashboard/src/components/NLPCommandConsole.tsx` | Real-time console issuing parsed mutations | Real-time WS execution |

---

## Future Extension Points

1. **Multi-city street gazetteers (Phase 9):** Extend `graph.json` parser to load edge names for Paris/Ahmedabad; gazetteer becomes city-aware.
2. **Multilingual support:** Gazetteer and intent patterns could be extended for non-English incident reports.
3. **Local quantized LLM sidecar:** Run an on-device quantized small model (e.g. Llama-3-8B-Instruct via llama.cpp) for offline tool-calling without cloud APIs.

---

## References

| Document | Section | Content |
|----------|---------|---------|
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phase 16 | NLP live metrics chat: service, intents, LLM layer, endpoint, panel, accuracy |
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phase 17 | NLP incident reports: parser, endpoint, engine apply, broadcast, panel, tests |
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phase 18 | Cross-subsystem integration: `make demo` launches chat service |
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phases 31–33 | Expanded NLP: sentiment, NER, events, coref, summarization, QA, KG |
| `docs/PRD.md` | G10, G11, F11, F12 | NLP goals, features, success metrics |
| `docs/TRD.md` | §4.3 (TR-ML-09, TR-ML-10) | NLP chat and incident parser technical requirements |
| `docs/results.md` | §3 & §6 | NLP benchmark performance metrics |
| `dashboard/public/data/36_algo_matrix.json` | NLP section | Complete algorithmic matrix and metadata |

---

*This document is self-contained and independently updatable. Last updated: September 2026.*

