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
| O-NLP-1 | Build FastAPI sidecar service that is itself a WS client of the engine, caching latest metrics/zone_metrics/signals | 16.1 | PLANNED | Service on port 9004; keeps Python NLP deps out of frontend and C++ hot path (TR-ML-09) |
| O-NLP-2 | Implement rule-based intent classifier: regex over fixed intent set (worst_zone, avg_speed, active_agents, gini_explain, compare_policy, incident_status) | 16.2 | PLANNED | Reliable baseline; unit-tested independently of LLM path (TR-ML-09) |
| O-NLP-3 | Implement optional LLM tool-calling layer: same metric-lookup functions as tools, graceful fallback when no API key configured | 16.3 | PLANNED | "Classical NLP vs. LLM" comparison; not a hard dependency (TR-ML-09) |
| O-NLP-4 | Expose `POST /chat` endpoint; response includes which intent/tool fired for UI transparency | 16.4 | PLANNED | REST endpoint returns structured response |
| O-NLP-5 | Build `ChatPanel.tsx` dashboard component calling chat_service.py directly over REST | 16.5 | PLANNED | (TR-DASH-09) |
| O-NLP-6 | Produce held-out query test set + accuracy report (rule-based vs. LLM path) | 16.6 | PLANNED | Correct answers on held-out queries (Phase 16 checkpoint) |
| O-NLP-7 | Implement `incident_parser.py`: pure function `parse(text, graph) -> IncidentSpec` using street-name gazetteer + `rapidfuzz` fuzzy matching | 17.1 | PLANNED | Independently unit-testable; small fixed vocabulary (TR-ML-10) |
| O-NLP-8 | Expose `POST /incident` endpoint; forward parsed spec as `{"type":"incident", edges, severity, duration_s}` over WS to engine | 17.2 | PLANNED | (TR-ML-10) |
| O-NLP-9 | Engine: `apply_incident()` stores temporary per-edge speed/capacity multiplier, expired after `duration_s` of `sim_time_` | 17.3 | PLANNED | Reuses Pathfinder stochastic edge-cost mechanism (TR-ENG-13) |
| O-NLP-10 | Add `incidents[]` (active, with remaining duration) to `broadcast_state()` JSON | 17.4 | PLANNED | Additive schema extension (NFR-5) |
| O-NLP-11 | Build `IncidentReportPanel.tsx` dashboard component: free-text box, active incidents list, effect on nearby zone metrics | 17.5 | PLANNED | (TR-DASH-10) |
| O-NLP-12 | Unit tests: gazetteer resolution accuracy on ambiguous/misspelled street names; incident expiry correctness | 17.6 | PLANNED | Tests pass |

---

## Current Implementation

### Status: NOT YET IMPLEMENTED

The NLP subsystem is entirely **PLANNED** (Phases 16–17). No Python NLP source files exist in the repository. The following describes the designed architecture from the implementation plan and TRD.

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
| Engine control messages | WebSocket inbound (port 9001) | `{"type":"incident", edges, severity, duration_s}` | PLANNED (Phase 17.3 dispatch) |
| Signal policy interface | C++ `SignalPolicy` (Phase 12) | `broadcast_state()` includes `mode` field for `compare_policy` intent | PLANNED (Phase 12) |

### Downstream (what depends on NLP)

| Consumer | Interface | Status |
|----------|-----------|--------|
| C++ simulation engine | `apply_incident()` applies speed/capacity multipliers to affected edges | PLANNED (Phase 17.3) |
| Dashboard `ChatPanel.tsx` | REST calls to `POST /chat`; displays response | PLANNED (Phase 16.5) |
| Dashboard `IncidentReportPanel.tsx` | REST calls to `POST /incident`; shows active incidents and zone metric effects | PLANNED (Phase 17.5) |
| RL signal policy | Incidents change queue patterns → RL observations shift → policy adapts automatically | PLANNED (Phase 17 → 18 integration; no direct code dependency) |
| CV virtual camera | Changed traffic flow visible in camera detection | PLANNED (Phase 18 integration; no direct code dependency) |
| Dashboard broadcast `incidents[]` | Additive field in WebSocket state frame | PLANNED (Phase 17.4) |

### External dependencies (planned)

| Package | Purpose | Required? |
|---------|---------|-----------|
| `fastapi` | REST API framework for `/chat` and `/incident` | Yes |
| `uvicorn` | ASGI server for FastAPI | Yes |
| `rapidfuzz` | Fuzzy string matching for street names | Yes |
| `websockets` | WebSocket client to connect to engine | Yes |
| OpenAI API key (or compatible) | Optional LLM tool-calling layer | No (graceful fallback) |

---

## Future Extension Points

1. **Multi-city street gazetteers (Phase 9):** Extend `graph.json` parser to load edge names for Paris/Ahmedabad; gazetteer becomes city-aware.
2. **Richer intent set:** Add intents for "show tradeoff curve", "export report", "switch to equity view" that trigger dashboard actions via REST callbacks.
3. **Conversational context:** Maintain short conversation history for multi-turn queries ("what about the worst zone's wait time trend?").
4. **Incident severity calibration:** Use historical incident data (if available) to map natural-language severity descriptions ("minor fender-bender" vs. "major highway closure") to calibrated severity floats.
5. **Cross-subject chat:** NLP chat could query RL training status ("how is the RL policy performing?"), CV congestion data ("what does the camera see?"), or GA calibration progress ("is the GA converged?")—all via the same intent classifier pattern.
6. **Multilingual support:** Gazetteer and intent patterns could be extended for non-English incident reports.
7. **WebSocket streaming for chat:** Replace request-response REST with WebSocket for lower-latency streaming responses (useful if LLM path generates long responses).

---

## References

| Document | Section | Content |
|----------|---------|---------|
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phase 16 | NLP live metrics chat: service, intents, LLM layer, endpoint, panel, accuracy |
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phase 17 | NLP incident reports: parser, endpoint, engine apply, broadcast, panel, tests |
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phase 18.1–18.4 | Cross-subsystem integration: `make demo` launches chat service |
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phases 31–33 | Expanded NLP: sentiment, NER, events, coref, summarization, QA, KG |
| `docs/PRD.md` | G10, G11, F11, F12 | NLP goals, features, success metrics |
| `docs/TRD.md` | §4.3 (TR-ML-09, TR-ML-10) | NLP chat and incident parser technical requirements |
| `docs/TRD.md` | §4.1 (TR-ENG-13) | Engine `apply_incident()` technical requirement |
| `docs/TRD.md` | §4.4 (TR-DASH-09, TR-DASH-10) | Dashboard NLP panel requirements |
| `docs/TRD.md` | §5.1 | WebSocket protocol: inbound `incident` message, outbound `incidents[]` |
| `docs/TECH_STACK.md` | §Subsystem 2 | Python sidecar pattern for non-real-time services |

---

*This document is self-contained and independently updatable. Changes to other subject documentation files do not require changes here, and vice versa. Last updated: August 2026.*
