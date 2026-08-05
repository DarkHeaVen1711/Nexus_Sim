# NexusSim — Technical Requirements Document (TRD)

**Version:** 1.0  
**Status:** Active  
**Owner:** Vyom  
**Last Updated:** August 2026

> **Source of truth.** This TRD is written against the latest documentation and
> verified codebase state: `docs/NexusSim_Explained.md` (verified, code-cited),
> `PRD.md` v2.0, `TECH_STACK.md`, `IMPLEMENTATION_PLAN.md` (Phases 0–18),
> `docs/graph_schema.md`, `docs/od_matrix_schema.md`, `docs/e2e_checklist.md`, and
> the working tree of the `engine/`, `pipeline/`, `ml/`, and `dashboard/`
> directories. Functional/business requirement IDs (FR, NFR, BR) are shared with
> `docs/NexusSim_Explained.md §3`; `TR-*` in this document extends that set with
> module-level technical requirements and is traceable to implementation-plan tasks.

---

## 1. Purpose and Scope

NexusSim is a real-city traffic simulation used to stress-test urban policy changes
and to train/compare adaptive signal control. It is one integrated system spanning
four academic subjects — Reinforcement Learning, Computer Vision, NLP, and Soft
Computing (BR-1, BR-3).

This document specifies the **technical** requirements: the system's architecture,
module-by-module requirements, interface contracts, data schemas, non-functional
targets, and the verification each requirement maps to. It is the contract between
the product intent (`PRD.md`) and the implementation plan (`IMPLEMENTATION_PLAN.md`).

**Scope:** engine, pipeline, ML, dashboard, and the four-subject extensions
(Phases 12–18). **Out of scope:** real signal hardware control, live city monitoring,
end-user navigation.

---

## 2. Referenced Documents

| Ref | Document | Purpose |
|-----|----------|---------|
| [1] | `PRD.md` (v2.0) | Product goals, features, success metrics |
| [2] | `docs/NexusSim_Explained.md` | Code-verified architecture + FR/NFR/TR/BR requirements |
| [3] | `IMPLEMENTATION_PLAN.md` | Phase-gated build plan (tasks, branches, checkpoints) |
| [4] | `TECH_STACK.md` | Technology decisions and rationale |
| [5] | `docs/graph_schema.md` | `graph.json` schema |
| [6] | `docs/od_matrix_schema.md` | `od_matrix.json` schema |
| [7] | `docs/e2e_checklist.md` | End-to-end smoke checks |
| [8] | `README.md` | Setup, quick start, run flags |

---

## 3. System Architecture

```
pipeline/ (Python)                engine/ (C++17)                 dashboard/ (React+TS)
─────────────────                 ─────────────────               ─────────────────────
download.py → clean.py            Graph.h / GraphLoader.cpp       useWebSocket.ts
  → lanes.py → zones.py             loads graph.json                ws://localhost:9001
  → export.py → graph.json        Simulation.h                    Map.tsx (Leaflet)
download_od.py → od_matrix.py       .tick(dt) every 0.1s          MetricsPanel.tsx
  → od_matrix.json                 IDM.h car-following            EquityOverlay.tsx
od_proxy.py (density proxy)        Pathfinder.h A* + stochastic   PolicyComparisonPanel.tsx
validate.py                        Quadtree.h spatial index       CalibrationReportPanel.tsx
optimize_calibration.py (GA)       SignalPolicy.h (Phase 12)      CongestionCVOverlay.tsx
cv_congestion.py (Phase 14)        InferenceEngine.h (ONNX)       VirtualCameraPanel.tsx
                                   WebSocketServer.h (uWebSockets) ChatPanel.tsx
                                                                    IncidentReportPanel.tsx
ml/ (Python sidecars, Phases 15–17)
  cv/virtual_camera.py → service (port 9003)
  nlp/chat_service.py → REST /chat, /incident (port 9004)
```

**Key architectural rules**
- The engine is the only writer of simulation truth; everything else is a consumer of
  its WebSocket stream (FR-5, verified: `Simulation::tick()`, `broadcast_state()`).
- ML/CV/NLP run as **independent sidecar processes** (TR-6), never in the C++ hot path
  and never in the frontend bundle.
- New broadcast fields are **additive only** (NFR-5): `useWebSocket.ts` ignores unknown
  keys, so additions never break the dashboard.
- Per-city variation is **config, not code** (FR-6, TR-7): `pipeline/cities.yaml` is the
  single source of truth; the root `cities.yaml` is a pointer stub.

---

## 4. Module Technical Requirements

Each requirement is `TR-<module>-<n>`. Status is `DONE` (built in the working tree),
`PLANNED` (implementation-plan Phases 12–18 or later phases), or `TARGET`
(non-functional target to be demonstrated). Traceability to FR/NFR/BR and to plan
phases is given per row.

### 4.1 Engine (C++17) — `engine/`

| ID | Requirement | Status | Maps to | Plan |
|----|-------------|--------|---------|------|
| TR-ENG-01 | Build with C++17, CMake ≥ 3.25, Ninja; tests via GoogleTest; no behavior change between refactors is acceptable without a green test suite | DONE | TR-1 | Ph 0 |
| TR-ENG-02 | Load a city graph from `graph.json` per [5]; expose adjacency list, node/edge structs, per-node `zone_id`, per-edge lanes/length | DONE | FR-1, FR-6 | Ph 1 |
| TR-ENG-03 | Spawn and move heterogeneous agents (car, bus, auto-rickshaw, two-wheeler, pedestrian) with per-type IDM parameters; chaos coefficient scales lane discipline from config | DONE | FR-1 | Ph 2 |
| TR-ENG-04 | Route via A* with optional stochastic diversity (`compute_path_stochastic`) | DONE | FR-2 | Ph 2 |
| TR-ENG-05 | Quadtree spatial index rebuilt each tick; agents query leading/lateral neighbours via radius query (no O(N²)) | DONE | NFR-3 | Ph 3 |
| TR-ENG-06 | Structure-of-Arrays (SoA) agent storage, `alignas(64)`, parallel agent updates via `std::async` chunking over CPU cores | DONE | NFR-1/2 | Ph 2–3 |
| TR-ENG-07 | OD-driven spawning from `od_matrix.json` at correct time-of-day rate; graceful random fallback when no OD present | DONE | FR-1 | Ph 6 |
| TR-ENG-08 | Fixed-cycle signals via Webster's formula computed once at startup; agents queue at red | DONE | — | Ph 5 |
| TR-ENG-09 | **Pluggable `SignalPolicy` interface** (`tick`, `is_green`, `current_phase_index`, `policy_name`); Webster's extracted as `WebsterPolicy` byte-identically; `init_signals()` builds policies via `unique_ptr` | PLANNED | FR-7 | Ph 12 |
| TR-ENG-10 | **Live `policy_switch` control message** flips one intersection or network-wide policy with no restart, visible in next broadcast frame | PLANNED | FR-7 | Ph 12.5 |
| TR-ENG-11 | **`FuzzyPolicy`** implementing `SignalPolicy`: Mamdani inference over queue length + wait time, centroid defuzzification → green-time extension | PLANNED | FR-10 | Ph 13.5 |
| TR-ENG-12 | **ONNX inference off the hot path**: load `policy.onnx`, batch all intersection observations into one tensor call per decision tick, background thread + shared-memory ring buffer, p95 ≤ 8 ms | PLANNED | FR-8, NFR-4, TR-5 | Ph 8 |
| TR-ENG-13 | **`apply_incident(edges, severity, duration_s)`**: temporary per-edge speed/capacity multipliers expiring on `sim_time_`; reuse Pathfinder's existing stochastic edge-cost mechanism | PLANNED | FR-14 | Ph 17.3 |
| TR-ENG-14 | Metrics: per-tick avg speed/wait, per-zone wait, Gini every 10 ticks; `avg_tick_ms`/`p95_tick_ms` for perf logging | DONE | FR-3, NFR-2 | Ph 5 |
| TR-ENG-15 | WebSocket server (uWebSockets) on port 9001; broadcast JSON state frame; accept `bounds` and (Ph 12/17) `policy_switch`/`incident` messages | DONE | FR-5 | Ph 4 |

### 4.2 Pipeline (Python 3.11) — `pipeline/`

| ID | Requirement | Status | Maps to | Plan |
|----|-------------|--------|---------|------|
| TR-PIPE-01 | Download OSM via `osmnx` per city from `pipeline/cities.yaml`; clean: largest SCC, remove dead ends, log before/after node counts | DONE | FR-6 | Ph 1 |
| TR-PIPE-02 | Lane inference fallback chain (OSM tag → road-type table → width÷3.3m → default) with per-edge `confidence` field | DONE | FR-6, TR-7 | Ph 1 |
| TR-PIPE-03 | Zone tagging from census or building-density proxy with confidence flag | DONE | G3 | Ph 1 |
| TR-PIPE-04 | Export `graph.json` conforming to [5]; validated with jsonschema | DONE | TR-2 | Ph 1 |
| TR-PIPE-05 | OD matrix: real measured feed (Chicago Socrata TNP) → `od_matrix.json`; density-proxy fallback (`od_proxy.py`) emits `confidence: low` and `validation_safe: false` per [6] | DONE | FR-4 | Ph 6 |
| TR-PIPE-06 | `validate.py` computes per-corridor simulated-vs-observed MAPE and a machine-checked checkpoint: `MAPE ≤ 25% AND ≥ 75% corridors within 25%`; **refuses** proxy matrices (circular-MAPE guard) | DONE | FR-4, NFR-7 | Ph 6 |
| TR-PIPE-07 | **GA calibration** `optimize_calibration.py`: real-valued chromosome `[speed_factor, route_spread, chaos, demand_scale]`, tournament selection, blend crossover, Gaussian mutation, `multiprocessing.Pool` parallel eval (independent `--fast --no-ws` engine subprocesses), output `ga_calibration_report.json` | PLANNED | FR-9 | Ph 13 |
| TR-PIPE-08 | **CV congestion** `cv_congestion.py`: fetch traffic tiles via Mapbox Traffic Tiles / TomTom Traffic Flow API (ToS-compliant, key via env var, never committed); classical HSV thresholding + CNN comparison; `cv_congestion.json` per zone per hour; feeds GA as blended fitness term | PLANNED | FR-11, BR-6, NFR-6 | Ph 14 |
