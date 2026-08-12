# NexusSim — Product Requirements Document

**Version:** 2.0  
**Status:** Active  
**Owner:** Vyom & Vatsal
**Last Updated:** August 2026

> **Revision notice.** v2.0 supersedes v1.0 (July 2026). It incorporates the scope
> confirmed in the latest documentation — `docs/NexusSim_Explained.md`, `docs/PRD.md`,
> `IMPLEMENTATION_PLAN.md` (Phases 12–18) and `TECH_STACK.md` — which extends the
> product from "engine + pipeline + dashboard" into **one integrated system covering
> four academic subjects: Reinforcement Learning, Computer Vision, NLP, and Soft
> Computing** (BR-1–BR-6). Requirement IDs (FR / NFR / TR / BR) are shared with
> `docs/NexusSim_Explained.md §3` and are traced to implementation phases in
> `IMPLEMENTATION_PLAN.md`.

---

## 1. Problem Statement

Urban traffic management in real cities is governed by static, rule-based signal timings that were calibrated decades ago and rarely updated. City administrators have no safe, cost-free way to test what happens if they add a bus lane, reroute freight, or implement congestion pricing — they make these decisions blind, or after expensive pilot programs that disrupt real commuters.

Additionally, most optimization tools treat "average commute time" as the sole success metric. This systematically benefits already well-connected, high-income zones while underserved neighborhoods — where residents are more dependent on public transit — see no improvement or get worse.

NexusSim solves both problems: it gives planners a high-fidelity, real-city sandbox where policy changes can be stress-tested before any real-world commitment, and it makes equity a first-class metric alongside efficiency. It also exists as a single, demonstrably integrated system in which four AI subject areas — RL, Computer Vision, NLP, and Soft Computing — cooperate on the same live simulation rather than living as four isolated demos (BR-3).

---

## 2. Goals

| Goal | Description | Phase(s) |
|------|-------------|----------|
| G1 | Simulate 20,000+ heterogeneous agents in a real city graph at 60 fps | 0–4 |
| G2 | Train a decentralized MARL policy that outperforms fixed-cycle signal timing | 7–9, 12 |
| G3 | Make equity — not just speed — a measurable, optimized output | 5, 9 |
| G4 | Support 3–4 structurally distinct real cities without code changes | 1, 6, 9 |
| G5 | Produce a policy dashboard that a non-technical administrator can read | 5, 10 |
| G6 | Make signal control pluggable so Webster's, fuzzy, and RL policies hot-swap at runtime | 12 |
| G7 | Replace manual calibration with a genetic algorithm; add a fuzzy-logic controller | 13 |
| G8 | Classify real-world road congestion from traffic imagery (classical + CNN) | 14 |
| G9 | Run a live synthetic "virtual camera" that detects/counts traffic on the sim's own output | 15 |
| G10 | Answer natural-language queries about live simulation state | 16 |
| G11 | Accept free-text incident reports that mutate the running simulation | 17 |
| G12 | Prove all four subjects interoperate in one continuous demo | 18 |

---

## 3. Non-Goals

- NexusSim does **not** connect to or control real traffic signal hardware
- NexusSim does **not** provide real-time live city monitoring
- NexusSim does **not** require proprietary city data to function (all sources are open)
- NexusSim is **not** a navigation or routing app for end users
- NexusSim does **not** script-scrape Google Maps' interactive traffic layer (ToS-violating; substitutes are Mapbox Traffic Tiles / TomTom Traffic Flow API — BR-6, NFR-6)
- Computer Vision / NLP are **not** full research contributions — depth is "medium," a mix of breadth and depth, not stubs and not dissertations (BR-2)
- RL is **not** full cooperative message-passing MARL and **not** a single centralized controller — it is independent per-intersection agents with a shared network-wide reward (BR-5)

---

## 4. Users

### Primary User — Urban Policy Researcher / Student Developer
Builds the system, interprets results, writes academic or policy reports. Needs full technical access. Also the audience for the four academic subjects: reads reward functions, GA convergence reports, CV accuracy tables, and NLP intent accuracy.

### Secondary User — Civil Administrator / Policy Audience
Views the dashboard. Needs plain-language metrics, no jargon. Interacts with policy toggles (add bus lane, increase congestion zone, switch to EV fleet, swap signal policy), live metrics chat, and incident reports.

### Evaluator — Technical Interviewer
Reviews code architecture, model design decisions, and validation methodology across all four subjects. Needs clean interfaces, documented choices, ablation results, and one integrated demo (Phase 18).

---

## 5. Core Features

### F1 — C++ Simulation Engine (Phases 0–4)
- Directed graph loaded from a cleaned OpenStreetMap export
- Agent types: car, bus, auto-rickshaw, two-wheeler, informal shuttle, pedestrian
- Quadtree spatial index for O(N log N) proximity detection
- Thread pool with Structure-of-Arrays (SoA) memory layout
- Outputs delta-compressed binary state stream over WebSocket
- OD-driven agent spawning from real trip demand (Phase 6)

### F2 — OSM Data Pipeline (Python) (Phases 1, 6)
- Downloads and cleans raw `.osm.pbf` files via `osmnx`
- Extracts largest strongly-connected component
- Lane-inference fallback chain with per-edge confidence scores
- Ward/equity-zone tagging from census or building-density proxy
- OD demand matrix per city: real measured feed (Socrata) or density-proxy fallback with `validation_safe: false`
- Outputs a single `graph.json` + `od_matrix.json` consumed by the C++ engine

### F3 — MARL Training Environment (Python / PyTorch) (Phase 7)
- Gym-compatible environment wrapping the simulation state
- Decentralized agents: one per signalised intersection (BR-5)
- Pressure-based local reward + equity-weighted global reward
- MAPPO (Multi-Agent Proximal Policy Optimization) trainer
- MLflow logging of reward, pressure term, equity term, Gini per checkpoint
- Exports trained policy to ONNX

### F4 — ONNX Inference in C++ (Phase 8)
- Loads ONNX policy graph via ONNX Runtime C++ API
- Batches all intersection state observations into one tensor call per tick
- Runs on a background thread; engine consumes via shared-memory ring buffer
- No live Python process in the simulation hot path

### F5 — React Dashboard (Phases 4, 5, 10)
- Real-time map rendered with Mapbox GL or Leaflet + WebGL
- Dual view toggle: Efficiency mode / Equity mode
- Policy toggles: bus lane, congestion pricing zone, EV fleet ratio, chaos coefficient
- Equity panel: per-zone wait times + Gini coefficient gauge
- Efficiency/equity tradeoff curve chart (varies β weight)
- Policy comparison panel (Phase 12), calibration report panel (Phase 13), CV overlay (Phase 14), virtual camera panel (Phase 15), chat panel (Phase 16), incident report panel (Phase 17)

### F6 — Validation Layer (Phases 6, 9)
- Calibrate simulation against real OD matrices (Chicago TNP / Socrata; OpenTraffic-decommissioned fallback documented)
- Compare simulated corridor journey times vs. ground truth per city
- Compute Gini coefficient across zones, reported per training checkpoint
- Machine-checked checkpoint: MAPE ≤ 25% AND ≥ 75% of corridors within 25%
- Support 3 validation cities: Chicago (grid), Paris (radial), Ahmedabad (organic); refuses to validate density-proxy matrices (circular-MAPE guard)

### F7 — Pluggable Signal Policies (Phase 12)
- `SignalPolicy` interface; Webster's extracted behavior-preserving as `WebsterPolicy`
- `--signal-policy webster|fuzzy|rl` at startup; live `policy_switch` WebSocket message flips an intersection or the whole network with no restart
- Broadcast gains `mode` and `signals[]`; dashboard gains `PolicyComparisonPanel.tsx`

### F8 — Soft Computing: GA Calibration + Fuzzy Controller (Phase 13)
- Genetic algorithm over `[speed_factor, route_spread, chaos, demand_scale]` using the existing validation checkpoint as fitness; parallel evaluation
- `ga_calibration_report.json` with convergence curve; GA-tuned MAPE ≤ manually-tuned MAPE
- `FuzzyPolicy.h`: Mamdani inference over queue length + wait time, centroid defuzzification; runs via `--signal-policy fuzzy`

### F9 — CV: Real-World Congestion Classification (Phase 14)
- Fetch traffic-flow tiles via Mapbox Traffic Tiles / TomTom Traffic Flow API (ToS-compliant)
- Classical HSV thresholding + CNN comparison on a small hand-labeled set
- `cv_congestion.json` per zone per hour; feeds the GA as an extra fitness term

### F10 — CV: Synthetic Virtual Camera (Phase 15)
- Top-down frame rendered from the live agent stream (roads + agents as colored shapes)
- Genuine OpenCV detection/counting on rendered pixels; independent service on port 9003
- Accuracy vs. ground-truth count logged as running error %

### F11 — NLP: Live Metrics Chat (Phase 16)
- FastAPI sidecar that is itself a WS client of the engine, caching latest metrics
- Rule-based intent classifier over a fixed intent set; optional LLM tool-calling layer falls back when no API key configured
- `POST /chat`; `ChatPanel.tsx` in the dashboard; held-out query accuracy report

### F12 — NLP: Incident Reports → Simulation Mutation (Phase 17)
- Free-text incident → structured spec via street-name gazetteer + fuzzy matching
- `POST /incident` forwards `{"type":"incident", edges, severity, duration_s}` to the engine
- `Simulation::apply_incident()` applies temporary per-edge speed/capacity multipliers that expire after `duration_s`; `incidents[]` added to broadcast

### F13 — Cross-Subsystem Integration (Phase 18)
- `make demo` launches chat + virtual-camera services, runs GA calibration on the mini-graph, loads RL checkpoint if present
- Single continuous demo: incident → RL reaction → metrics update, with CV/GA/chat live together
- Extended `docs/e2e_checklist.md` covering all four subjects together

---

## 6. Constraints

| Constraint | Detail |
|------------|--------|
| Language | Engine: C++17 (verified in `engine/CMakeLists.txt`; C++20 targeted where supported). ML/pipeline: Python 3.11+. Dashboard: React 18/19 + TypeScript + Vite |
| Data | All data sources must be open or freely accessible, and ToS-compliant (BR-6) |
| Performance | Engine must sustain 60 fps with 20,000 agents on a mid-range dev machine |
| Inference latency | ONNX inference batch must complete within p95 ≤ 8 ms per tick, off the hot path (NFR-4) |
| Subsystem isolation | ML/CV/NLP services are independent sidecar processes (own ports), never embedded in the dashboard bundle or the C++ engine (TR-6) |
| Config-driven | New cities and new per-city keys extend `pipeline/cities.yaml` only (FR-6, TR-7) |
| Commit discipline | No commit exceeds 100 line insertions. Feature branches required. PRs for large changes |
| Solo build | Architected for handoff: all subsystems behind documented interfaces |

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Simulation throughput | ≥ 20,000 agents at 60 fps, no frame drops over 10-minute runs |
| Quadtree vs. naive | ≥ 10× faster proximity search at 10,000 agents |
| MARL vs. baseline | ≥ 15% reduction in citywide average wait time vs. fixed-cycle baseline |
| Equity improvement | Gini coefficient across zones decreases by ≥ 10% vs. fixed-cycle baseline |
| Validation accuracy | Simulated corridor journey times within 20% (checkpoint: ≤ 25% MAPE AND ≥ 75% corridors within 25%) of Chicago TNP ground truth |
| ONNX inference latency | p95 ≤ 8 ms per tick; < 5 fps drop vs. baseline mode at 20k agents |
| Cities supported | Chicago, Paris, Ahmedabad all run from the same binary without code changes |
| Policy hot-swap | `policy_switch` changes visible behavior in the next broadcast frame, no restart |
| GA calibration | GA-tuned MAPE ≤ manually-tuned MAPE from Phase 6 |
| Fuzzy controller | Runs live via `--signal-policy fuzzy` |
| CV real-world | Classical-vs-CNN accuracy comparison table delivered per city |
| Virtual camera | Detected count tracks actual simulated traffic in view; error % logged |
| NLP chat | Correct answers on a held-out query test set (rule-based and LLM paths) |
| NLP incidents | Submitted incident visibly changes routing/queueing; expires after stated duration |
| Integration | One continuous recording showing incident → RL reaction → metrics update with all four subjects live |

---

## 8. Business / Academic Requirements

| ID | Requirement |
|----|-------------|
| BR-1 | The project SHALL demonstrably cover four academic subjects: RL, Computer Vision, NLP, Soft Computing |
| BR-2 | Depth per subject SHALL be "medium" — a mix of breadth and depth, not a minimal stub nor a full research contribution |
| BR-3 | The four subjects SHALL form one integrated system suitable for a single demo narrative, not four independently graded modules |
| BR-4 | Work SHALL be structured for parallel execution across a 3–4 person team with a shared foundation phase first |
| BR-5 | RL scope SHALL be independent per-intersection agents trained against a shared network-wide reward |
| BR-6 | The system SHALL NOT depend on data sources that violate third-party Terms of Service (no scripted scraping of Google Maps' live traffic layer) |

---

## 9. Risks

| Risk | Mitigation |
|------|------------|
| MARL training instability | Start with heuristic (Webster's method) baseline; MARL only needs to beat it, not be perfect |
| OSM data gaps in Ahmedabad | Confidence-scored fallback chain; documented uncertainty, not silent guessing |
| OpenTraffic decommissioned (Paris OD) | Density-proxy generator with `validation_safe: false`; validation refuses circular MAPE |
| Scope creep | Phase-gated development; each phase has one demoable checkpoint artifact |
| ONNX latency exceeds budget | Profile early in Phase 8; fall back to smaller policy network if needed |
| Google traffic-layer scraping temptation | Substituted with Mapbox Traffic Tiles / TomTom Traffic Flow API (BR-6, NFR-6) |
| Four isolated demos instead of one system | BR-3 enforced at Phase 18 with a single continuous integrated demo recording |
| Cross-service dependency sprawl | Sidecar pattern (TR-6); engine stays C++-only; dashboards consume via HTTP/WS |

---

## 10. Requirement Traceability

Full requirement-level traceability (FR-1…FR-15, NFR-1…NFR-7, TR-1…TR-7, BR-1…BR-6) with status and acceptance criteria lives in `docs/NexusSim_Explained.md §3`. Mapping to implementation phases is in `IMPLEMENTATION_PLAN.md`. Mapping to technical detail and interfaces is in `TRD.md`.
