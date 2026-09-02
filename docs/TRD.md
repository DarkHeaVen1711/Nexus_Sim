# NexusSim ΓÇö Technical Requirements Document (TRD)

**Version:** 1.0  
**Status:** Active  
**Owner:** Vyom & Vatsal<br>
**Last Updated:** August 2026

> **Source of truth.** This TRD is written against the latest documentation and
> verified codebase state: `PRD.md` v2.0, `TECH_STACK.md`,
> `docs/TEAM_IMPLEMENTATION_PLAN.md`, `docs/graph_schema.md`, `docs/od_matrix_schema.md`,
> `docs/e2e_checklist.md`, and the working tree of the `engine/`, `pipeline/`, `ml/`,
> and `dashboard/` directories. Functional/business requirement IDs (FR, NFR, BR) are
> defined in this document; `TR-*` extends that set with module-level technical
> requirements and is traceable to implementation-plan tasks.

---

## 1. Purpose and Scope

NexusSim is a real-city traffic simulation used to stress-test urban policy changes
and to train/compare adaptive signal control. It is one integrated system spanning
four academic subjects ΓÇö Reinforcement Learning, Computer Vision, NLP, and Soft
Computing (BR-1, BR-3).

This document specifies the **technical** requirements: the system's architecture,
module-by-module requirements, interface contracts, data schemas, non-functional
targets, and the verification each requirement maps to. It is the contract between
the product intent (`PRD.md`) and the implementation plan (`TEAM_IMPLEMENTATION_PLAN.md`).

**Scope:** engine, pipeline, ML, dashboard, and the four-subject extensions
(Phases 12ΓÇô18). **Out of scope:** real signal hardware control, live city monitoring,
end-user navigation.

---

## 2. Referenced Documents

| Ref | Document | Purpose |
|-----|----------|---------|
| [1] | `PRD.md` (v2.0) | Product goals, features, success metrics |
| [2] | `docs/TRD.md` | FR/NFR/TR/BR requirements (this document) |
| [3] | `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phase-gated team build plan (tasks, branches, checkpoints) |
| [4] | `TECH_STACK.md` | Technology decisions and rationale |
| [5] | `docs/graph_schema.md` | `graph.json` schema |
| [6] | `docs/od_matrix_schema.md` | `od_matrix.json` schema |
| [7] | `docs/e2e_checklist.md` | End-to-end smoke checks |
| [8] | `README.md` | Setup, quick start, run flags |

---

## 3. System Architecture

```
pipeline/ (Python)                engine/ (C++17)                 dashboard/ (React+TS)
ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ                 ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ               ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
download.py ΓåÆ clean.py            Graph.h / GraphLoader.cpp       useWebSocket.ts
  ΓåÆ lanes.py ΓåÆ zones.py             loads graph.json                ws://localhost:9001
  ΓåÆ export.py ΓåÆ graph.json        Simulation.h                    Map.tsx (Leaflet)
download_od.py ΓåÆ od_matrix.py       .tick(dt) every 0.1s          MetricsPanel.tsx
  ΓåÆ od_matrix.json                 IDM.h car-following            EquityOverlay.tsx
od_proxy.py (density proxy)        Pathfinder.h A* + stochastic   PolicyComparisonPanel.tsx
validate.py                        Quadtree.h spatial index       CalibrationReportPanel.tsx
optimize_calibration.py (GA)       SignalPolicy.h (Phase 12)      CongestionCVOverlay.tsx
cv_congestion.py (Phase 14)        InferenceEngine.h (ONNX)       VirtualCameraPanel.tsx
                                   WebSocketServer.h (uWebSockets) ChatPanel.tsx
                                                                    IncidentReportPanel.tsx
ml/ (Python sidecars, Phases 15ΓÇô17)
  cv/virtual_camera.py ΓåÆ service (port 9003)
  nlp/chat_service.py ΓåÆ REST /chat, /incident (port 9004)
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
`PLANNED` (implementation-plan Phases 12ΓÇô18 or later phases), or `TARGET`
(non-functional target to be demonstrated). Traceability to FR/NFR/BR and to plan
phases is given per row.

### 4.1 Engine (C++17) ΓÇö `engine/`

| ID | Requirement | Status | Maps to | Plan |
|----|-------------|--------|---------|------|
| TR-ENG-01 | Build with C++17, CMake ΓëÑ 3.25, Ninja; tests via GoogleTest; no behavior change between refactors is acceptable without a green test suite | DONE | TR-1 | Ph 0 |
| TR-ENG-02 | Load a city graph from `graph.json` per [5]; expose adjacency list, node/edge structs, per-node `zone_id`, per-edge lanes/length | DONE | FR-1, FR-6 | Ph 1 |
| TR-ENG-03 | Spawn and move heterogeneous agents (car, bus, auto-rickshaw, two-wheeler, pedestrian) with per-type IDM parameters; chaos coefficient scales lane discipline from config | DONE | FR-1 | Ph 2 |
| TR-ENG-04 | Route via A* with optional stochastic diversity (`compute_path_stochastic`) | DONE | FR-2 | Ph 2 |
| TR-ENG-05 | Quadtree spatial index rebuilt each tick; agents query leading/lateral neighbours via radius query (no O(N┬▓)) | DONE | NFR-3 | Ph 3 |
| TR-ENG-06 | Structure-of-Arrays (SoA) agent storage, `alignas(64)`, parallel agent updates via `std::async` chunking over CPU cores | DONE | NFR-1/2 | Ph 2ΓÇô3 |
| TR-ENG-07 | OD-driven spawning from `od_matrix.json` at correct time-of-day rate; graceful random fallback when no OD present | DONE | FR-1 | Ph 6 |
| TR-ENG-08 | Fixed-cycle signals via Webster's formula computed once at startup; agents queue at red | DONE | ΓÇö | Ph 5 |
| TR-ENG-09 | **Pluggable `SignalPolicy` interface** (`tick`, `is_green`, `current_phase_index`, `policy_name`); Webster's extracted as `WebsterPolicy` byte-identically; `init_signals()` builds policies via `unique_ptr` | PLANNED | FR-7 | Ph 12 |
| TR-ENG-10 | **Live `policy_switch` control message** flips one intersection or network-wide policy with no restart, visible in next broadcast frame | PLANNED | FR-7 | Ph 12.5 |
| TR-ENG-11 | **`FuzzyPolicy`** implementing `SignalPolicy`: Mamdani inference over queue length + wait time, centroid defuzzification ΓåÆ green-time extension | PLANNED | FR-10 | Ph 13.5 |
| TR-ENG-12 | **ONNX inference off the hot path**: load `policy.onnx`, batch all intersection observations into one tensor call per decision tick, background thread + shared-memory ring buffer, p95 Γëñ 8 ms | DONE (infra); parity/p95 gate pending a trained policy | FR-8, NFR-4, TR-5 | Ph 8 |
| TR-ENG-13 | **`apply_incident(edges, severity, duration_s)`**: temporary per-edge speed/capacity multipliers expiring on `sim_time_`; reuse Pathfinder's existing stochastic edge-cost mechanism | PLANNED | FR-14 | Ph 17.3 |
| TR-ENG-14 | Metrics: per-tick avg speed/wait, per-zone wait, Gini every 10 ticks; `avg_tick_ms`/`p95_tick_ms` for perf logging | DONE | FR-3, NFR-2 | Ph 5 |
| TR-ENG-15 | WebSocket server (uWebSockets) on port 9001; broadcast JSON state frame; accept `bounds` and (Ph 12/17) `policy_switch`/`incident` messages | DONE | FR-5 | Ph 4 |

### 4.2 Pipeline (Python 3.11) ΓÇö `pipeline/`

| ID | Requirement | Status | Maps to | Plan |
|----|-------------|--------|---------|------|
| TR-PIPE-01 | Download OSM via `osmnx` per city from `pipeline/cities.yaml`; clean: largest SCC, remove dead ends, log before/after node counts | DONE | FR-6 | Ph 1 |
| TR-PIPE-02 | Lane inference fallback chain (OSM tag ΓåÆ road-type table ΓåÆ width├╖3.3m ΓåÆ default) with per-edge `confidence` field | DONE | FR-6, TR-7 | Ph 1 |
| TR-PIPE-03 | Zone tagging from census or building-density proxy with confidence flag | DONE | G3 | Ph 1 |
| TR-PIPE-04 | Export `graph.json` conforming to [5]; validated with jsonschema | DONE | TR-2 | Ph 1 |
| TR-PIPE-05 | OD matrix: real measured feed (Chicago Socrata TNP) ΓåÆ `od_matrix.json`; density-proxy fallback (`od_proxy.py`) emits `confidence: low` and `validation_safe: false` per [6] | DONE | FR-4 | Ph 6 |
| TR-PIPE-06 | `validate.py` computes per-corridor simulated-vs-observed MAPE and a machine-checked checkpoint: `MAPE Γëñ 25% AND ΓëÑ 75% corridors within 25%`; **refuses** proxy matrices (circular-MAPE guard) | DONE | FR-4, NFR-7 | Ph 6 |
| TR-PIPE-07 | **GA calibration** `optimize_calibration.py`: real-valued chromosome `[speed_factor, route_spread, chaos, demand_scale]`, tournament selection, blend crossover, Gaussian mutation, `multiprocessing.Pool` parallel eval (independent `--fast --no-ws` engine subprocesses), output `ga_calibration_report.json` | PLANNED | FR-9 | Ph 13 |
| TR-PIPE-08 | **CV congestion** `cv_congestion.py`: fetch traffic tiles via Mapbox Traffic Tiles / TomTom Traffic Flow API (ToS-compliant, key via env var, never committed); classical HSV thresholding + CNN comparison; `cv_congestion.json` per zone per hour; feeds GA as blended fitness term | PLANNED | FR-11, BR-6, NFR-6 | Ph 14 |

### 4.3 ML (Python) ΓÇö `ml/`

| ID | Requirement | Status | Maps to | Plan |
|----|-------------|--------|---------|------|
| TR-ML-01 | Gym-compatible `NexusSimEnv` (`reset`, `step`, observation/action spaces) wrapping engine state snapshots ΓÇö no live C++ call during training | DONE | FR-8 | Ph 7.3 |
| TR-ML-02 | Observation: per-approach queue length (from quadtree), current phase, time in phase, time of day, neighbor pressure | DONE | FR-8 | Ph 7.1 |
| TR-ML-03 | Action space `{EXTEND current phase, SWITCH to next phase}` at phase boundaries (matches `SignalController` state machine granularity) | DONE | BR-5 | Ph 7 |
| TR-ML-04 | Reward = `╬▒ ├ù pressure_i + ╬▓ ├ù equity_global`; equity term reuses engine Gini/zone wait metrics; ╬▒/╬▓ tunable, tradeoff curve a deliverable | DONE | FR-8, G3 | Ph 7.2 |
| TR-ML-05 | MAPPO trainer: 3-layer MLP policy + value network, shared initial weights, one independent agent per intersection | DONE | FR-8, BR-5 | Ph 7.5 |
| TR-ML-06 | MLflow logging (episode reward, pressure, equity, Gini); checkpoint save/resume every 500 episodes | DONE | US-D03 | Ph 7.6ΓÇô7.7 |
| TR-ML-06b | **Multi-city MARL** `env/graph_loader.py` parses real `data/<city>/graph.json` (29,733-node Chicago ΓåÆ 3,709 signal intersections, 77 zones); `train.py --city` trains any city; `train/transfer.py` fine-tunes to Paris/Ahmedabad; `train/evaluate.py` writes multi-city MARL-vs-Webster table to `ml/results/comparison.json`; CI runs `ml/tests` | DONE (train/eval infra); full Chicago run pending | G4, FR-8 | Ph 9 |
| TR-ML-07 | ONNX export (`export_onnx.py`) validated to match PyTorch outputs on 10 test inputs | DONE | FR-8, TR-5 | Ph 8.1 |
| TR-ML-08 | **Virtual camera** `cv/virtual_camera.py`: WS client on engine stream, rasterize top-down frame (roads from `graph.json`, agents as colored shapes), OpenCV contour/blob + color segmentation detection on rendered pixels; service on port 9003 streams annotated PNG + count; accuracy vs ground truth logged | PLANNED | FR-12 | Ph 15 |
| TR-ML-09 | **NLP chat** `nlp/chat_service.py`: FastAPI sidecar, WS client of engine caching latest metrics; rule-based intent classifier (fixed intent set) + optional LLM tool-calling with graceful fallback when no API key; `POST /chat` | PLANNED | FR-13 | Ph 16 |
| TR-ML-10 | **NLP incidents** `nlp/incident_parser.py`: `parse(text, graph) -> IncidentSpec` via street-name gazetteer + `rapidfuzz` fuzzy match; `POST /incident` forwards `{"type":"incident", edges, severity, duration_s}` to engine | PLANNED | FR-14 | Ph 17.1ΓÇô17.2 |
| TR-ML-11 | **Shared RL framework** `BaseTrainer` interface + common CLI; `ml/algo/configs.yaml` per-algorithm hyperparameters; `benchmark.py` comparison table | PLANNED | FR-16 | Ph 19 |
| TR-ML-12 | **Single-agent wrapper** `ml/env/single_agent.py` wrapping multi-agent `NexusSimEnv` as a Gym env so DQN/PPO/A2C/Q-Learning train on the same signal task | PLANNED | FR-16 | Ph 19.3 |
| TR-ML-13 | **Eval harness** `ml/eval/report.py`: per-algorithm report vs. Webster baseline (reward, pressure, equity, Gini, avg wait, % change) ΓåÆ `ml/results/<algo>/eval_report.json` | PLANNED | FR-16 | Ph 19.4 |
| TR-ML-14 | **Tabular value-based RL** Q-Learning + SARSA on a shared state discretizer (queue buckets/phase), ╬╡-greedy | PLANNED | FR-16 | Ph 20.1ΓÇô20.2 |
| TR-ML-15 | **Deep value-based RL** DQN, DDQN, Dueling DQN (replay buffer, target network, double estimator, dueling head) | PLANNED | FR-16 | Ph 20.3ΓÇô20.5 |
| TR-ML-16 | **Policy-based RL** REINFORCE with baseline, A2C, single-agent PPO (reuses `ppo_update`/`compute_gae`) | PLANNED | FR-16 | Ph 21 |
| TR-ML-17 | **Continuous showcase** SAC, TD3, DDPG via Stable-Baselines3 on `Pendulum-v1`, returns logged to MLflow | PLANNED | FR-16 | Ph 22 |
| TR-ML-18 | **Multi-algorithm ONNX deployment** `export_onnx.py` generalized to PPO/DQN; `InferenceEngine` `--algo` dispatch; `SignalPolicy::RLPolicy` keyed by algorithm; DQN inference = argmax over Q outputs | PLANNED | FR-16, FR-8, NFR-4 | Ph 23 |
| TR-ML-19 | **RL inventory + ablation docs** 12-algorithm table and ablation (value vs. policy, on/off-policy, tabular vs. neural) in `docs/results.md` | PLANNED | FR-16 | Ph 24 |

### 4.4 Dashboard (React + TypeScript) ΓÇö `dashboard/`

| ID | Requirement | Status | Maps to | Plan |
|----|-------------|--------|---------|------|
| TR-DASH-01 | WebSocket client hook with exponential-backoff reconnection capped at `MAX_RECONNECT_DELAY_MS`; tolerates unknown broadcast keys | DONE | FR-5, NFR-5 | Ph 4.2, 4.7 |
| TR-DASH-02 | Leaflet map base from city config; agent markers colored by type; LOD culling via `bounds` message | DONE | FR-5 | Ph 4.3ΓÇô4.6 |
| TR-DASH-03 | Efficiency view (avg wait, top-5 congested corridors) and Equity view (per-zone heatmap bubbles, Gini gauge, plain-language labels) | DONE | G3, US-P02/P04 | Ph 5.6ΓÇô5.8 |
| TR-DASH-04 | Policy toggle panel ΓåÆ control message to engine; before/after metric comparison; tradeoff curve chart; city selector; PDF export | PLANNED | G5 | Ph 10 |
| TR-DASH-05 | **`PolicyComparisonPanel.tsx`**: per-policy dropdown sends `policy_switch`, shows before/after avg-wait/Gini | PLANNED | FR-7 | Ph 12.6 |
| TR-DASH-06 | **`CalibrationReportPanel.tsx`**: GA convergence chart from static JSON | PLANNED | FR-9 | Ph 13.7 |
| TR-DASH-07 | **`CongestionCVOverlay.tsx`**: zone bubbles colored by CV-observed congestion (static per-hour data) | PLANNED | FR-11 | Ph 14.7 |
| TR-DASH-08 | **`VirtualCameraPanel.tsx`**: live annotated feed from virtual-camera service | PLANNED | FR-12 | Ph 15.4 |
| TR-DASH-09 | **`ChatPanel.tsx`**: REST calls to `chat_service.py` | PLANNED | FR-13 | Ph 16.5 |
| TR-DASH-10 | **`IncidentReportPanel.tsx`**: free-text box, active incidents list, effect on zone metrics | PLANNED | FR-14 | Ph 17.5 |

---

## 5. Interface Contracts

### 5.1 Engine WebSocket protocol (port 9001)

**Outbound state frame** (JSON, per tick ΓÇö additive-only per NFR-5):

```json
{
  "tick": 0,
  "agents": [{ "id": 0, "lat": 0.0, "lon": 0.0, "heading": 0.0, "type": "car", "speed": 0.0 }],
  "metrics": { "avg_speed": 0.0, "active_agents": 0, "completed_agents": 0, "avg_wait_time": 0.0, "gini_coefficient": 0.0 },
  "zone_metrics": [{ "zone_id": 0, "wait_time": 0.0 }]
}
```

Planned additive fields (Phases 12/17):
- `"mode": "webster" | "fuzzy" | "rl"` and `"signals": [{ "id": 0, "phase": 0, "state": "green" }]`
- `"incidents": [{ "edges": [0], "severity": 0.5, "remaining_s": 10.0 }]`

**Inbound messages:**
- `{"type":"bounds", min_lat, min_lon, max_lat, max_lon}` ΓÇö viewport LOD culling (DONE)
- `{"type":"city", "city":"<id>"}` ΓÇö start a simulation for a city. Honored only
  while the engine is idle: once a city is running (even paused) the request is
  **ignored** and no switch occurs (single-simulation lock) until reset/stop.
- `{"type":"get_city"}` ΓÇö answered with `{"type":"city_loaded","city":"<id>|null"}` (DONE)
- `{"type":"pause"}` / `{"type":"resume"}` ΓÇö freeze / continue the running
  simulation in place; engine broadcasts `{"type":"paused"}` / `{"type":"resumed"}`
- `{"type":"restart"}` ΓÇö tear down and reload the **same** city from scratch
  (a fresh `{"type":"city_loaded"}` follows on reload)
- `{"type":"reset"}` (alias `stop`) ΓÇö stop the run and return the engine to
  idle, which unlocks city selection; broadcasts `{"type":"stopped"}`
- `{"type":"policy_switch", "intersection_id": 0 | null, "policy": "webster|fuzzy|rl"}` (PLANNED, Ph 12.5)
- `{"type":"incident", "edges": [0], "severity": 0.5, "duration_s": 10.0}` (PLANNED, Ph 17.3)

### 5.2 `graph.json` (per [5])

`nodes[{id, lat, lon, zone_id}]` + `edges[{u, v, length_m, lanes}]`, plus per-edge lane `confidence` where inferred. Consumed by `GraphLoader`.

### 5.3 `od_matrix.json` (per [6])

OriginΓÇôdestination demand keyed by zone pair with hourly rates. `socrata` matrices carry `validation_safe: true`; `od_proxy.py` output carries `method: gravity-density-proxy`, `confidence: low`, `validation_safe: false` and MUST be refused by `validate.py` (TR-PIPE-06).

### 5.4 ONNX policy interface (TR-ENG-12, TR-ML-07)

- Input: batched observation tensor over all intersections (shape documented in `ml/env/README.md`).
- Output: per-intersection action logits over `{EXTEND, SWITCH}`.
- Consumed by `InferenceEngine.h` (C++/ONNX Runtime); no Python in the hot path (TR-5, NFR-4).

### 5.5 Sidecar services (TR-6)

| Service | Port | Protocol | Consumes | Produces |
|---------|------|----------|----------|----------|
| virtual-camera (`ml/cv/`) | 9003 | WS/HTTP | engine WS stream + `graph.json` | annotated PNG (base64) + detection count JSON @ ~1 Hz |
| NLP chat (`ml/nlp/chat_service.py`) | 9004 (proposed default ΓÇö not fixed by plan) | HTTP REST | engine WS stream (cached metrics) | `POST /chat`, `POST /incident` responses |

---

## 6. Non-Functional Technical Requirements

| ID | Requirement | Target / Criteria | Plan / Evidence |
|----|-------------|-------------------|-----------------|
| NFR-1 | Long-run stability at scale | ΓëÑ 20,000 agents, no crash over extended runs | `engine/tests/test_stress.cpp` (20k agents, 500 ticks) |
| NFR-2 | Throughput | 60 fps at 20k agents on mid-range dev machine; `avg_tick_ms`/`p95_tick_ms` logged | Ph 3.7; `Simulation::avg_tick_ms()` |
| NFR-3 | Spatial index | Quadtree ΓëÑ 10├ù faster than naive O(N┬▓) at 10k agents | `engine/bench/bench_quadtree.cpp` |
| NFR-4 | Inference latency | p95 Γëñ 8 ms per decision tick; never blocks the real-time loop | Ph 8.6; `bench_inference.cpp` |
| NFR-5 | Protocol extensibility | New broadcast fields additive; existing dashboard consumers unaffected | `useWebSocket.ts` ignores unknown keys (verified) |
| NFR-6 | Data-source compliance | All external sources ToS-compliant; no scripted Google Maps live-traffic scraping | Ph 14.2 module docstring; BR-6 |
| NFR-7 | Validation accuracy preserved | MAPE Γëñ 25% AND ΓëÑ 75% corridors within 25%; GA/CV integrations must not regress it | `validate.py` checkpoint; `test_od_proxy.py` guard |
| NFR-8 | Reproducibility | `make demo` from clean clone < 30 min; all deps pinned | Ph 11; `package-lock.json`, pinned `requirements.txt` |
| NFR-9 | Test completeness | `make test` (GoogleTest + pytest + Vitest) green in < 3 min; CI gate on every push/PR | Ph 0, 11.7 |
| NFR-10 | Config-driven cities | New city or per-city key = edit `pipeline/cities.yaml` only | Ph 1.8, 6.8; root `cities.yaml` is a pointer stub |

---

## 7. Data Requirements

| Data | Source | Schema | Notes |
|------|--------|--------|-------|
| Road network | OpenStreetMap via `osmnx` | [5] `graph.json` | Cleaned, largest SCC, lane confidence |
| OD demand | Chicago Socrata TNP; density proxy for Paris/Ahmedabad | [6] `od_matrix.json` | Proxy flagged `validation_safe: false` |
| Ground truth journey times | Chicago TNP | `validation_report.json` | Used by `validate.py` checkpoint |
| Calibration search space | Manual Phase 6 sweep | `ga_calibration_report.json` | GA output (Ph 13) |
| Congestion tiles | Mapbox Traffic Tiles / TomTom Traffic Flow | `cv_congestion.json` | ToS-compliant; API key via env var (Ph 14) |
| Trained policy | PyTorch ΓåÆ ONNX | `policy.onnx` | Validated vs PyTorch outputs (Ph 8) |
| City config | `pipeline/cities.yaml` | YAML | Single source of truth (TR-7) |

---

## 8. Environments

| Env | Stack | Notes |
|-----|-------|-------|
| Windows dev | MSYS2 MinGW-w64 GCC 13+, CMake ΓëÑ 3.25, Ninja, Python 3.11+, Node 18+ | `run.bat`; MinGW test DLLs on PATH for `ctest` |
| Linux/macOS dev | GCC 11+/Clang 14+, CMake, Ninja, Python 3.11+, Node 18+ | `make test`, `make demo` |
| CI | GitHub Actions `ubuntu-latest` | build + lint + test all three subsystems on push/PR |
| Sidecars | Python 3.11 + FastAPI/OpenCV | Ports 9003/9004; separate venv deps |

---

## 9. Verification and Acceptance Mapping

Each requirement above is accepted via its plan-phase checkpoint artifact
(`TEAM_IMPLEMENTATION_PLAN.md` Phase Summary) and the phase-gated `docs/e2e_checklist.md`:

| Phase | Checkpoint artifact | Verifies |
|-------|---------------------|----------|
| 3 | Quadtree benchmark table | NFR-3, TR-ENG-05 |
| 6 | Chicago `validation_report.json` with `passes_checkpoint` | FR-4, NFR-7, TR-PIPE-06 |
| 8 | `bench_inference.cpp` p95 Γëñ 8 ms | NFR-4, TR-ENG-12, TR-ML-07 |
| 9 | MARL-vs-Webster table across 3 cities in `ml/results/comparison.json` rendered by dashboard `ComparisonPanel`; `ml/tests` green in CI | G4, FR-8, TR-ML-06b |
| 11 | `make demo` clean-clone < 30 min | NFR-8 |
| 12 | `policy_switch` visible in next frame, byte-identical Webster extraction | FR-7, TR-ENG-09/10 |
| 13 | `ga_calibration_report.json`; fuzzy live via `--signal-policy fuzzy` | FR-9/10, TR-PIPE-07, TR-ENG-11 |
| 14 | `cv_congestion.json` + classical-vs-CNN accuracy table | FR-11, TR-PIPE-08, NFR-6 |
| 15 | Live annotated detection panel, count error % logged | FR-12, TR-ML-08 |
| 16 | Held-out query accuracy (rule-based vs LLM) | FR-13, TR-ML-09 |
| 17 | Incident visibly mutates routing, expires correctly | FR-14, TR-ENG-13, TR-ML-10 |
| 18 | One continuous integrated demo (incident ΓåÆ RL ΓåÆ metrics, all four subjects live) | BR-1ΓÇôBR-3, TR-DASH-05ΓÇª10 |
| 19 | `benchmark.py` comparison table + MLflow (12-algorithm harness) | FR-16, TR-ML-11/12/13 |
| 20 | 5 value-based algorithms trained with eval reports vs. Webster | FR-16, TR-ML-14/15 |
| 21 | 3 policy-based algorithms trained; 8 signal-control algorithms in comparison | FR-16, TR-ML-16 |
| 22 | SAC/TD3/DDPG return curves on Pendulum-v1 | FR-16, TR-ML-17 |
| 23 | `--signal-policy rl --algo dqn` runs; p95 Γëñ 8 ms | FR-16, FR-8, NFR-4, TR-ML-18 |
| 24 | 12-algorithm table + ablation in `docs/results.md` | FR-16, TR-ML-19 |

---

## 10. Traceability Matrix (summary)

| Requirement (PRD goal / BR) | Primary technical requirements | Key phases |
|------------------------------|-------------------------------|------------|
| G1 (20k agents @ 60 fps) | TR-ENG-05/06, NFR-1/2/3 | 3, 4 |
| G2 (MARL beats baseline) | TR-ML-01ΓÇª07, TR-ENG-09/12 | 7, 8, 12 |
| G3 (equity measurable) | TR-ENG-14, TR-DASH-03, TR-ML-04 | 5, 9 |
| G4 (multi-city) | TR-PIPE-01ΓÇª05, NFR-10 | 1, 6, 9 |
| G6 (pluggable signals) | TR-ENG-09/10, TR-DASH-05 | 12 |
| G7 (GA + fuzzy) | TR-PIPE-07, TR-ENG-11 | 13 |
| G8 (CV real-world) | TR-PIPE-08, TR-DASH-07 | 14 |
| G9 (virtual camera) | TR-ML-08, TR-DASH-08 | 15 |
| G10 (NLP chat) | TR-ML-09, TR-DASH-09 | 16 |
| G11 (incidents) | TR-ENG-13, TR-ML-10, TR-DASH-10 | 17 |
| G12 (integration) | all TR, e2e checklist v2 | 18 |
| G13 (12 RL algorithms) | TR-ML-11ΓÇª19 | 19ΓÇô24 |
| BR-1ΓÇªBR-6 | TR-ML-01ΓÇª10, TR-PIPE-07/08, TR-ENG-09/11/13, TR-DASH-05ΓÇª10 | 12ΓÇô18 |

Full FR/NFR/TR/BR definitions with acceptance criteria: `docs/TRD.md ┬º4`.
