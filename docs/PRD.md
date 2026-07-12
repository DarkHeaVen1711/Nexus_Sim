# NexusSim — Product Requirements Document

**Version:** 1.0  
**Status:** Active  
**Owner:** Vyom  
**Last Updated:** July 2026

---

## 1. Problem Statement

Urban traffic management in real cities is governed by static, rule-based signal timings that were calibrated decades ago and rarely updated. City administrators have no safe, cost-free way to test what happens if they add a bus lane, reroute freight, or implement congestion pricing — they make these decisions blind, or after expensive pilot programs that disrupt real commuters.

Additionally, most optimization tools treat "average commute time" as the sole success metric. This systematically benefits already well-connected, high-income zones while underserved neighborhoods — where residents are more dependent on public transit — see no improvement or get worse.

NexusSim solves both problems: it gives planners a high-fidelity, real-city sandbox where policy changes can be stress-tested before any real-world commitment, and it makes equity a first-class metric alongside efficiency.

---

## 2. Goals

| Goal | Description |
|------|-------------|
| G1 | Simulate 20,000+ heterogeneous agents in a real city graph at 60 fps |
| G2 | Train a decentralized MARL policy that outperforms fixed-cycle signal timing |
| G3 | Make equity — not just speed — a measurable, optimized output |
| G4 | Support 3–4 structurally distinct real cities without code changes |
| G5 | Produce a policy dashboard that a non-technical administrator can read |

---

## 3. Non-Goals

- NexusSim does **not** connect to or control real traffic signal hardware
- NexusSim does **not** provide real-time live city monitoring
- NexusSim does **not** require proprietary city data to function (all sources are open)
- NexusSim is **not** a navigation or routing app for end users

---

## 4. Users

### Primary User — Urban Policy Researcher / Student Developer
Builds the system, interprets results, writes academic or policy reports. Needs full technical access.

### Secondary User — Civil Administrator / Policy Audience
Views the dashboard. Needs plain-language metrics, no jargon. Interacts with policy toggles (add bus lane, increase congestion zone, switch to EV fleet).

### Evaluator — Technical Interviewer
Reviews code architecture, model design decisions, and validation methodology. Needs clean interfaces, documented choices, and ablation results.

---

## 5. Core Features

### F1 — C++ Simulation Engine
- Directed graph loaded from a cleaned OpenStreetMap export
- Agent types: car, bus, auto-rickshaw, two-wheeler, informal shuttle, pedestrian
- Quadtree spatial index for O(N log N) proximity detection
- Thread pool with Structure-of-Arrays (SoA) memory layout
- Outputs delta-compressed binary state stream over WebSocket

### F2 — OSM Data Pipeline (Python)
- Downloads and cleans raw `.osm.pbf` files via `osmnx`
- Extracts largest strongly-connected component
- Lane-inference fallback chain with per-edge confidence scores
- Ward/equity-zone tagging from census or building-density proxy
- Outputs a single `graph.json` consumed by the C++ engine

### F3 — MARL Training Environment (Python / PyTorch)
- Gym-compatible environment wrapping the simulation state
- Decentralized agents: one per signalised intersection
- Pressure-based local reward + equity-weighted global reward
- MAPPO (Multi-Agent Proximal Policy Optimization) trainer
- Exports trained policy to ONNX

### F4 — ONNX Inference in C++
- Loads ONNX policy graph via ONNX Runtime C++ API
- Batches all intersection state observations into one tensor call per tick
- Runs on a background thread; engine consumes via shared-memory ring buffer
- No live Python process in the simulation hot path

### F5 — React Dashboard
- Real-time map rendered with Mapbox GL or Leaflet + WebGL
- Dual view toggle: Efficiency mode / Equity mode
- Policy toggles: bus lane, congestion pricing zone, EV fleet ratio, chaos coefficient
- Equity panel: per-zone wait times + Gini coefficient gauge
- Efficiency/equity tradeoff curve chart (varies β weight)

### F6 — Validation Layer
- Calibrate simulation against real OD matrices (Uber Movement, OpenTraffic)
- Compare simulated corridor journey times vs. ground truth per city
- Compute Gini coefficient across zones, reported per training checkpoint
- Support 3 validation cities: Chicago (grid), Paris (radial), Ahmedabad (organic)

---

## 6. Constraints

| Constraint | Detail |
|------------|--------|
| Language | Engine: C++20. ML pipeline: Python 3.11+. Dashboard: React 18 |
| Data | All data sources must be open or freely accessible |
| Performance | Engine must sustain 60 fps with 20,000 agents on a mid-range dev machine |
| Inference latency | ONNX inference batch must complete within 8 ms per tick |
| Commit discipline | No commit exceeds 100 line insertions. Feature branches required. PRs for large changes |
| Solo build | Architected for handoff: all three subsystems behind documented interfaces |

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Simulation throughput | ≥ 20,000 agents at 60 fps, no frame drops over 10-minute runs |
| MARL vs. baseline | ≥ 15% reduction in citywide average wait time vs. fixed-cycle baseline |
| Equity improvement | Gini coefficient across zones decreases by ≥ 10% vs. fixed-cycle baseline |
| Validation accuracy | Simulated corridor journey times within 20% of Uber Movement ground truth |
| Cities supported | Chicago, Paris, Ahmedabad all run from the same binary without code changes |

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| MARL training instability | Start with heuristic (Webster's method) baseline; MARL only needs to beat it, not be perfect |
| OSM data gaps in Ahmedabad | Confidence-scored fallback chain; documented uncertainty, not silent guessing |
| Scope creep | Phase-gated development; each phase has one demoable checkpoint artifact |
| ONNX latency exceeds budget | Profile early in Phase 4; fall back to smaller policy network if needed |
