# NexusSim — Implementation Plan

**Version:** 1.0  
**Build style:** Bottom-up, phase-gated  
**Checkpoint rule:** Every phase ends with one demoable artifact. If the checkpoint isn't met, scope is cut before moving on — not after.

---

## Git Discipline (enforced throughout every phase)

```
RULE 1  No commit exceeds 100 line insertions.
        Split larger changes into logical sub-commits, each independently buildable.

RULE 2  Branch naming
        feature/<name>      new capability
        fix/<name>          bug fix
        refactor/<name>     internal restructure, no behaviour change
        data/<name>         pipeline or data work
        experiment/<name>   ML training runs, reward tuning

RULE 3  Pull Requests
        Any change whose total insertions across commits exceed 100 lines opens a PR.
        PR description: what changed · why · what was tested.
        All CI checks must pass before merge.
        No force-push to main.

RULE 4  Commit message format
        <type>(<scope>): <short summary>
        Types:  feat | fix | refactor | test | docs | chore
        Scopes: engine | pipeline | ml | dashboard | ci
```

---

## Phase 0 — Repository Skeleton & CI Foundation
**Duration:** 3–4 days  
**Goal:** Everything compiles, lints, and tests pass on a clean clone before a single line of real logic is written.  
**Checkpoint artifact:** `make test` passes on CI with placeholder stubs; `make demo` prints "NexusSim ready."

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 0.1 | Initialise repo: root `Makefile`, `README.md`, `.gitignore` | `feature/repo-init` | Pin tool versions in README immediately |
| 0.2 | Create directory skeleton: `engine/`, `pipeline/`, `ml/`, `dashboard/`, `docs/`, `data/` | `feature/directory-structure` | Empty `CMakeLists.txt`, `requirements.txt`, `package.json` placeholders |
| 0.3 | Set up C++ CMake build with GoogleTest; stub `main.cpp` that prints version string | `feature/engine-cmake-setup` | Confirm `cmake --build` works |
| 0.4 | Set up Python virtual env, `requirements.txt`, pytest config; stub passing test | `feature/python-env-setup` | One file: `pipeline/tests/test_stub.py` |
| 0.5 | Set up React + Vite + TypeScript + Tailwind; Vitest config; stub passing test | `feature/dashboard-scaffold` | `npm run test` passes |
| 0.6 | Add pre-commit config: clang-format, black, isort, eslint | `feature/pre-commit-hooks` | Hooks run on `git commit`; fail on format violation |
| 0.7 | Add GitHub Actions CI: build + lint + test all three subsystems on push | `feature/ci-github-actions` | One workflow file; runs on every push to any branch |
| 0.8 | Write `docs/` folder with symlinks to PRD, tech stack, user stories, this plan | `docs/project-docs` | Docs live in repo from day one |

---

## Phase 1 — Graph Loading & Basic City Geometry
**Duration:** 1 week  
**Goal:** The C++ engine can load a real city's road network from `graph.json` and log its structure correctly.  
**Checkpoint artifact:** `./engine --city chicago` prints node count, edge count, lane summary, and zone count for Chicago's real OSM graph.

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 1.1 | Write `pipeline/src/download.py`: fetch `.osm.pbf` for a city via osmnx config | `data/osm-download` | Chicago first; output to `data/chicago/raw.pbf` |
| 1.2 | Write `pipeline/src/clean.py`: simplify graph, extract largest SCC, remove dead ends | `data/osm-clean` | Log before/after node counts; unit test with a tiny synthetic graph |
| 1.3 | Write `pipeline/src/lanes.py`: full fallback chain with per-edge confidence score | `data/lane-inference` | Unit test each fallback level independently |
| 1.4 | Write `pipeline/src/zones.py`: tag each node with ward/zone ID from building density proxy | `data/zone-tagging` | Confidence-flagged; fallback to road-type zone if census missing |
| 1.5 | Write `pipeline/src/export.py`: assemble and write `graph.json` with documented schema | `data/graph-export` | Schema defined in `docs/graph_schema.md`; validated with jsonschema |
| 1.6 | Write C++ `Graph` class: adjacency list, node/edge structs loaded from `graph.json` | `feature/engine-graph-loader` | `< 100` insertions per commit; split into struct definitions + loader |
| 1.7 | Write unit tests for `Graph`: node count, edge count, connectivity, zone lookup | `feature/engine-graph-tests` | GoogleTest; run in CI |
| 1.8 | Add `cities.yaml` config; pipeline reads city from config not hardcoded strings | `refactor/pipeline-city-config` | Enables US-D07 (new city via config only) |

---

## Phase 2 — Agent System & Pathfinding
**Duration:** 1.5 weeks  
**Goal:** Typed agents spawn, find paths, and move through the graph. No rendering yet — validate via logged positions.  
**Checkpoint artifact:** Engine spawns 500 agents, each reaches its destination and logs journey time. No crashes over a 5-minute run.

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 2.1 | Define `Agent` base struct (SoA layout): position, velocity, type, state, path | `feature/agent-base-struct` | SoA: separate arrays per field, not array of structs |
| 2.2 | Implement A\* pathfinding on the `Graph`; precompute Euclidean heuristic on load | `feature/astar-pathfinding` | Unit test: known shortest path on a toy 10-node graph |
| 2.3 | Implement Intelligent Driver Model (IDM) for longitudinal movement per agent | `feature/idm-movement` | Parameters typed per vehicle class; unit test with two agents in a lane |
| 2.4 | Add typed agent subclasses: car, bus, auto-rickshaw, two-wheeler, pedestrian | `feature/agent-types` | Each overrides IDM params and lane-discipline factor |
| 2.5 | Implement agent spawner: reads OD demand matrix, spawns agents at source nodes on schedule | `feature/agent-spawner` | Stub OD matrix (uniform demand) for now; real OD in Phase 6 |
| 2.6 | Add chaos coefficient: scales lane-discipline factor globally; read from config | `feature/chaos-coefficient` | Default 0.3 for Indian cities, 0.1 for Chicago |
| 2.7 | Implement agent lifecycle: spawn → navigate → arrive → despawn; log journey times | `feature/agent-lifecycle` | Log to CSV: agent\_id, type, origin, destination, journey\_time\_ms |
| 2.8 | Thread pool: parallelise agent update tick across CPU cores | `feature/engine-thread-pool` | Use `std::thread`; benchmark with 500 vs 5000 agents |

---

## Phase 3 — Quadtree Spatial Index & Collision Avoidance
**Duration:** 1 week  
**Goal:** Engine handles 20,000 agents without frame drops by replacing O(N²) proximity checks with a Quadtree.  
**Checkpoint artifact:** Benchmark printout showing Quadtree ≥ 10× faster than naive loop at 10,000 agents (US-E01).

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 3.1 | Implement `Quadtree` class: insert, query radius, clear, rebuild per tick | `feature/quadtree-core` | Templated on coordinate type; unit test: insert 100 points, query radius |
| 3.2 | Integrate Quadtree into agent update loop: replace any O(N²) neighbour search | `feature/quadtree-integration` | Profile before/after at 1k agents to confirm speedup |
| 3.3 | Implement proximity-based deceleration: agents slow when a leading agent is within safe following distance | `feature/proximity-deceleration` | Uses Quadtree query; no brute force |
| 3.4 | Add lane-change logic: agent queries lateral neighbours before changing lanes | `feature/lane-change` | Respects per-agent lane-discipline parameter and chaos coefficient |
| 3.5 | Write `bench_quadtree.cpp`: benchmark at 1k / 5k / 10k / 20k agents, print table | `feature/quadtree-benchmark` | Output embedded in README; satisfies US-E01 |
| 3.6 | Stress test: 20,000 agents, 10-minute run, no crashes, no memory leaks (valgrind) | `fix/engine-stress-test` | If valgrind finds leaks, fix before moving to Phase 4 |
| 3.7 | Add frame-rate counter: log average fps and p95 tick time to stdout every 500 ticks | `feature/engine-fps-logger` | Target: ≥ 60 fps at 20k agents |
| 3.8 | Refactor agent SoA arrays to ensure cache-line alignment; measure impact | `refactor/soa-cache-alignment` | Use `alignas(64)`; benchmark before/after |

---

## Phase 4 — WebSocket Stream & Dashboard Map
**Duration:** 1.5 weeks  
**Goal:** Real agents moving on a real city map in the browser. First time the project looks like NexusSim.  
**Checkpoint artifact:** Screen recording of 5,000 agents moving through real Chicago OSM roads at 60 fps in the browser (US-D02).

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 4.1 | Define FlatBuffers schema for agent state delta: agent\_id, lat, lon, heading, type | `feature/flatbuffers-schema` | Schema in `engine/schemas/agent\_delta.fbs`; generate C++ + JS bindings |
| 4.2 | Integrate uWebSockets into engine: broadcast FlatBuffer delta frame every tick | `feature/engine-websocket-server` | Delta-only: skip agents with position change < threshold |
| 4.3 | Add level-of-detail culling: agents off the current map viewport update at 10 fps, not 60 | `feature/lod-culling` | Viewport bounds sent from dashboard to engine over WebSocket |
| 4.4 | React: set up WebSocket client hook; parse FlatBuffer binary frames | `feature/dashboard-ws-client` | TypeScript types generated from FlatBuffers schema |
| 4.5 | React: Mapbox GL (or Leaflet + WebGL) map base layer; centre on city coordinates from config | `feature/dashboard-map-base` | City coordinates from `cities.yaml` |
| 4.6 | React: render agent markers from WebSocket stream; colour by agent type | `feature/dashboard-agent-markers` | Use WebGL layer for performance; not SVG per-marker |
| 4.7 | React: reconnection logic; "Reconnecting…" overlay on WebSocket drop | `feature/dashboard-reconnect` | Exponential backoff; max 5 retries then "Connection lost" state |
| 4.8 | End-to-end smoke test: pipeline → engine → dashboard; manual checklist in `docs/e2e\_checklist.md` | `feature/e2e-smoke-test` | Checklist committed; run before every phase-end |

---

## Phase 5 — Fixed-Cycle Signal Baseline
**Duration:** 1 week  
**Goal:** Traffic signals exist, operate on Webster's fixed-cycle timing, and metrics are collected. This is the baseline everything else is measured against.  
**Checkpoint artifact:** Efficiency metrics panel shows citywide avg wait time and per-zone breakdown for a fixed-cycle Chicago run.

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 5.1 | Model signalised intersections: identify controlled nodes in graph; store phase state | `feature/signal-controller` | One `SignalController` per controlled node; state machine: green/yellow/red |
| 5.2 | Implement Webster's method: compute optimal fixed-cycle green splits from edge flow counts | `feature/webster-timing` | Compute once at startup from initial demand; unit test against known example |
| 5.3 | Integrate signal state into agent movement: agents stop at red, queue behind stop line | `feature/signal-agent-interaction` | Queue position tracked per lane per signal |
| 5.4 | Metrics collector: per-tick, record per-zone avg wait time, queue lengths, journey times | `feature/metrics-collector` | Write to ring buffer; read by WebSocket broadcaster |
| 5.5 | Add metrics to FlatBuffers schema and WebSocket stream | `feature/metrics-flatbuffers` | Extend schema; regenerate bindings |
| 5.6 | React efficiency view: citywide avg wait time card, top-5 congested corridors list | `feature/dashboard-efficiency-view` | Recharts bar chart for corridors |
| 5.7 | React equity view: per-zone wait time heatmap on the map; Gini coefficient gauge | `feature/dashboard-equity-view` | Colour scale: green (low wait) → red (high wait); Gini as a dial |
| 5.8 | Compute and display Gini coefficient from per-zone wait times; plain-language label | `feature/gini-coefficient` | Satisfies US-P04; label thresholds defined in `dashboard/src/constants.ts` |

---

## Phase 6 — Real Traffic Demand (OD Matrix)
**Duration:** 1 week  
**Goal:** Agent spawning is driven by real origin-destination demand from Uber Movement, not uniform random spawning.  
**Checkpoint artifact:** Validation report showing simulated Chicago corridor journey times within 25% of Uber Movement ground truth.

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 6.1 | Download and parse Uber Movement journey time data for Chicago | `data/uber-movement-chicago` | CSV → pandas; aggregate to ward-level OD pairs |
| 6.2 | Build OD demand matrix: origin zone → destination zone → hourly vehicle count | `data/od-matrix-chicago` | Output `data/chicago/od_matrix.json`; schema in docs |
| 6.3 | Update agent spawner: read OD matrix; spawn agents by zone pair at correct hourly rate | `feature/od-demand-spawner` | Replace uniform random spawner; parameterised by time-of-day |
| 6.4 | Calibrate IDM parameters per vehicle type against observed Chicago speeds from OSM speed tags | `data/idm-calibration-chicago` | Document chosen parameters in `data/chicago/calibration_notes.md` |
| 6.5 | Write validation script: compare simulated vs. Uber Movement corridor journey times | `feature/validation-script` | Output `data/chicago/validation_report.json`; satisfies US-D05, US-E05 |
| 6.6 | Run Paris OD pipeline: repeat steps 6.1–6.4 for Paris using OpenTraffic data | `data/od-matrix-paris` | Note data gaps; apply confidence-flagged fallbacks |
| 6.7 | Run Ahmedabad OD pipeline: use Smart Cities Mission / AMC data where available; fallback to building-density proxy | `data/od-matrix-ahmedabad` | Expect higher uncertainty; document in calibration notes |
| 6.8 | Update `cities.yaml` with OD data source per city; pipeline reads from config | `refactor/city-config-od-source` | Enables any future city to specify its own OD source |

---

## Phase 7 — MARL Training Environment
**Duration:** 1.5 weeks  
**Goal:** A Gym-compatible environment wrapping simulation state is built and tested. MAPPO can interact with it and produce non-random behaviour.  
**Checkpoint artifact:** MLflow shows a rising reward curve over 1,000 episodes on a small 4-intersection toy graph.

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 7.1 | Design observation space per agent: local queue lengths (4 lanes), neighbour pressures (4 neighbours), time-of-day | `feature/ml-observation-space` | Flat vector; shape documented in `ml/env/README.md` |
| 7.2 | Implement `reward.py`: pressure term and equity-weighted global term as separate functions | `feature/ml-reward-function` | Satisfies US-E03; unit tests in `ml/tests/test_reward.py` |
| 7.3 | Implement `NexusSimEnv`: Gym-compatible; `reset()`, `step()`, `observation_space`, `action_space` | `feature/ml-gym-env` | Wraps simulation state snapshot (read from engine output); no live C++ call during training |
| 7.4 | Build toy 4-intersection graph for rapid training iteration; hardcode demand for repeatability | `feature/ml-toy-graph` | Allows fast feedback loop without waiting for full Chicago graph |
| 7.5 | Implement MAPPO trainer: policy network (3-layer MLP), value network, PPO update loop | `feature/mappo-trainer` | One agent per intersection; shared policy weights initially |
| 7.6 | Integrate MLflow logging: episode reward, pressure term, equity term, Gini per checkpoint | `feature/mlflow-logging` | Satisfies US-D03 acceptance criteria |
| 7.7 | Implement checkpoint save/resume: save policy weights every 500 episodes | `feature/training-checkpoints` | `ml/checkpoints/<city>/<episode>.pt`; resume with `--resume` flag |
| 7.8 | Verify training stability on toy graph: reward rises above Webster baseline within 500 episodes | `experiment/mappo-toy-baseline` | If not converging, review reward scaling and learning rate before scaling up |

---

## Phase 8 — ONNX Export & C++ Inference Integration
**Duration:** 1 week  
**Goal:** Trained policy runs inside the C++ engine via ONNX Runtime, with no Python in the hot path.  
**Checkpoint artifact:** Engine runs in AI mode with ONNX policy; inference latency p95 ≤ 8 ms printed to stdout (US-E04).

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 8.1 | Write `ml/export/export_onnx.py`: export trained `.pt` checkpoint to `policy.onnx` | `feature/onnx-export` | Validate exported model produces same output as PyTorch model on 10 test inputs |
| 8.2 | Add ONNX Runtime C++ dependency to CMakeLists; link against `onnxruntime` | `feature/onnxruntime-cmake` | Pin ONNX Runtime version in CMakeLists comment |
| 8.3 | Write `InferenceEngine` C++ class: load `policy.onnx`, expose `batch_infer(observations) → actions` | `feature/cpp-inference-engine` | Wrap ONNX Runtime session; handle input/output tensor shapes |
| 8.4 | Implement shared-memory ring buffer between simulation loop and inference thread | `feature/inference-ring-buffer` | Lock-free single-producer single-consumer; unit tested independently |
| 8.5 | Integrate `InferenceEngine` into signal controller: replace Webster timing with ONNX policy output when `--policy` flag set | `feature/ai-signal-controller` | Fallback to Webster if ONNX load fails; logged as warning |
| 8.6 | Write `bench_inference.cpp`: 1000 batched inference calls, print min/max/p95 latency | `feature/inference-benchmark` | Satisfies US-E04; embedded in README |
| 8.7 | Add "AI mode / Baseline mode" label to dashboard; read from engine handshake message | `feature/dashboard-mode-label` | Engine sends mode in initial WebSocket handshake |
| 8.8 | Stress test AI mode: 20,000 agents, 10-minute run, measure fps degradation vs. baseline mode | `experiment/ai-mode-stress` | Target: < 5 fps drop vs. baseline mode |

---

## Phase 9 — Multi-City Training & Validation
**Duration:** 1.5 weeks  
**Goal:** MARL policy trained on Chicago generalises to Paris and Ahmedabad. Validation reports generated for all three.  
**Checkpoint artifact:** Side-by-side table: MARL vs. Webster on all three cities — avg wait time and Gini coefficient (US-E02).

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 9.1 | Train MARL policy on full Chicago graph (not toy); log to MLflow | `experiment/mappo-chicago-full` | Expect 2000–5000 episodes; run overnight |
| 9.2 | Generate Chicago validation report: simulated vs. Uber Movement journey times | `data/chicago-validation` | Target: avg error < 20%; document methodology |
| 9.3 | Transfer policy to Paris: fine-tune 500 episodes on Paris graph | `experiment/mappo-paris-finetune` | Transfer learning from Chicago; compare fine-tuned vs. from-scratch |
| 9.4 | Generate Paris validation report | `data/paris-validation` | Note any data quality gaps in calibration notes |
| 9.5 | Transfer policy to Ahmedabad: fine-tune 500 episodes; increase chaos coefficient | `experiment/mappo-ahmedabad-finetune` | Chaos coefficient 0.4; document sensitivity |
| 9.6 | Generate Ahmedabad validation report | `data/ahmedabad-validation` | Expect higher error than Chicago; document honestly |
| 9.7 | Compile comparison table: MARL vs. Webster across all 3 cities | `docs/comparison-table` | MD table in `docs/results.md`; also rendered in dashboard |
| 9.8 | Generate efficiency vs. equity tradeoff curve (vary β, log outcomes) | `experiment/beta-tradeoff-curve` | Satisfies US-D06; chart saved to `docs/figures/tradeoff_curve.png` |

---

## Phase 10 — Policy Toggles & Dashboard Polish
**Duration:** 1 week  
**Goal:** Non-technical users can use the dashboard. Policy toggles work. Export report works.  
**Checkpoint artifact:** 60-second screen recording demonstrating: toggle bus lane → simulation restarts → equity metrics improve → export PDF.

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 10.1 | Engine: accept policy toggle parameters at runtime (no restart): bus lane, congestion zone, EV ratio | `feature/engine-policy-toggles` | Hot-reload via WebSocket control message from dashboard |
| 10.2 | Engine: EV fleet ratio toggle reduces per-vehicle emission factor; recalculate emission metric | `feature/ev-fleet-toggle` | Emission metric added to metrics collector |
| 10.3 | React: policy toggle panel UI with switches and sliders; sends control message to engine | `feature/dashboard-policy-panel` | Satisfies US-P03 |
| 10.4 | React: before/after metric comparison panel shown after any policy toggle | `feature/dashboard-before-after` | Shows prev values greyed out alongside new values |
| 10.5 | React: tradeoff curve chart panel (interactive; hover shows efficiency/equity values) | `feature/dashboard-tradeoff-chart` | Data loaded from `docs/figures/tradeoff_curve.json` |
| 10.6 | React: city selector dropdown; loads correct graph and resets simulation | `feature/dashboard-city-selector` | Reads `cities.yaml` via a small config API endpoint |
| 10.7 | React: "Export Report" button; generates PDF client-side with metrics snapshot | `feature/dashboard-pdf-export` | Use `jsPDF`; satisfies US-P05 |
| 10.8 | Accessibility pass: keyboard navigation, colour contrast check, plain-language labels throughout | `fix/dashboard-accessibility` | Satisfies US-P04; use axe-core in Vitest |

---

## Phase 11 — Hardening, Docs & Demo
**Duration:** 1 week  
**Goal:** Project is reproducible from a clean clone. README is complete. All benchmark and validation results are committed.  
**Checkpoint artifact:** `make demo` works on a clean clone in under 30 minutes (US-E06).

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 11.1 | Write full README: project overview, quick start, architecture diagram, benchmark results, validation results | `docs/readme` | One command per setup step; no assumed knowledge |
| 11.2 | Add `make demo` target: runs pipeline on small pre-packaged Chicago mini-graph, builds engine, starts dashboard | `feature/make-demo` | Mini-graph (500 nodes) committed to repo so no download needed |
| 11.3 | Pin all dependency versions: CMake, Python packages, npm packages, ONNX Runtime | `chore/pin-dependencies` | `requirements.txt` with exact versions; `package-lock.json` committed |
| 11.4 | Commit all benchmark results: Quadtree vs. naive table, inference latency table | `docs/benchmark-results` | Markdown tables in `docs/benchmarks.md` |
| 11.5 | Commit all validation reports and tradeoff curve as static assets | `docs/validation-results` | `docs/results.md` links to all reports |
| 11.6 | Write ablation section: compare pressure reward vs. queue reward; equity-weighted vs. flat global term | `docs/ablation-study` | Key deliverable for ML interviewer; charts in `docs/figures/` |
| 11.7 | Final CI audit: all tests pass, all lint rules pass, no TODO comments in production paths | `chore/ci-final-audit` | `grep -r "TODO" engine/src ml/env` must return empty |
| 11.8 | Record and commit 60-second demo video (`docs/demo.mp4`); update README with thumbnail | `docs/demo-video` | Shows agents, policy toggle, equity view, export report |

---

## Phase 12 — Signal Policy Abstraction

**Duration:** 3–4 days
**Goal:** `SignalController` (fixed Webster's-formula logic) becomes one interchangeable implementation of a `SignalPolicy` interface, so Webster's, a fuzzy controller, and the ONNX/RL policy from Phase 8 can all run in the same binary and be swapped live, per intersection, with no restart. This phase is a prerequisite for Phase 13 (fuzzy) and for making Phase 8's AI mode toggle-able rather than a separate build.
**Checkpoint artifact:** Engine runs with `--signal-policy webster` (byte-identical behaviour to pre-refactor `main`), and a `"type":"policy_switch"` WebSocket message flips an intersection's active policy live, visible in the next broadcast frame.

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 12.1 | Define `SignalPolicy` interface: `tick(dt)`, `is_green(edge_id)`, `current_phase_index()`, `policy_name()` | `refactor/signal-policy-interface` | Pure virtual base class; no behaviour change yet |
| 12.2 | Extract existing `SignalController` logic into `WebsterPolicy : SignalPolicy`, byte-identical behaviour | `refactor/webster-policy-extract` | Existing `test_signal.cpp` must pass unmodified against the new class |
| 12.3 | Update `Simulation::signals_` to `unordered_map<int64_t, unique_ptr<SignalPolicy>>`; `init_signals()` builds `WebsterPolicy` by default | `refactor/simulation-policy-map` | No behaviour change; confirms the interface is sufficient |
| 12.4 | Add `mode`, per-intersection `signals[]` (phase index + state) to `broadcast_state()` JSON | `feature/broadcast-signal-state` | Additive; dashboard's `useWebSocket.ts` already ignores unknown keys |
| 12.5 | Extend `WebSocketServer` message dispatch: `"type":"policy_switch"` sets the active policy for one intersection or network-wide | `feature/policy-switch-message` | `WebSocketServer` needs a callback/reference into `Simulation` — it currently has none |
| 12.6 | Dashboard: `PolicyComparisonPanel.tsx` — dropdown per policy, sends `policy_switch`, shows before/after avg-wait/Gini | `feature/dashboard-policy-panel` | Mirrors existing `EquityOverlay.tsx` data-binding pattern |

---

## Phase 13 — Soft Computing: GA Calibration & Fuzzy Signal Controller

**Duration:** 1.5 weeks
**Goal:** Replace the manual, by-hand parameter search in `validate.py` with a genetic algorithm, and add a fuzzy-logic signal controller as a second non-learned strategy comparable against Webster's and the eventual RL policy.
**Checkpoint artifact:** `ga_calibration_report.json` showing a convergence curve (best/mean fitness per generation) and a winning parameter set that beats the manually-tuned MAPE from Phase 6; fuzzy controller runs live via `--signal-policy fuzzy` and appears in the `PolicyComparisonPanel`.

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 13.1 | Refactor `validate.py`'s parameter-sweep loop so `build_report()` is directly importable as a pure fitness function | `refactor/validate-fitness-fn` | No CLI behaviour change; unlocks reuse from the GA |
| 13.2 | Implement `pipeline/src/optimize_calibration.py`: real-valued chromosome `[speed_factor, route_spread, chaos, demand_scale]`, tournament selection, blend crossover, Gaussian mutation | `feature/ga-calibration-optimizer` | Population ~20, ~20–30 generations; bounds documented in module docstring |
| 13.3 | Parallelise fitness evaluation via `multiprocessing.Pool` — each eval is one independent `--fast --no-ws` engine subprocess | `feature/ga-parallel-eval` | No engine changes needed; subprocess calls are already independent |
| 13.4 | Write `data/<city>/ga_calibration_report.json`: best chromosome, per-generation best/mean fitness, final re-run `validation_report.json` | `feature/ga-report-output` | Feeds `CalibrationReportPanel.tsx` |
| 13.5 | Implement `engine/src/agent/FuzzyPolicy.h`: Mamdani inference over queue length + wait time (triangular membership), rule base, centroid defuzzification → green-time extension | `feature/fuzzy-signal-policy` | Implements the `SignalPolicy` interface from Phase 12 |
| 13.6 | Unit test `FuzzyPolicy`: membership function boundaries, rule firing, defuzzified output range | `feature/fuzzy-policy-tests` | GoogleTest; mirrors `test_signal.cpp` structure |
| 13.7 | Dashboard: `CalibrationReportPanel.tsx` — GA convergence chart (Recharts, matches `MetricsPanel.tsx` conventions) | `feature/dashboard-calibration-panel` | Reads the static JSON report, no live WS data needed |
| 13.8 | Ablation note: GA-tuned vs. manually-tuned MAPE, Webster vs. Fuzzy avg-wait/Gini | `docs/soft-computing-ablation` | Markdown table in `docs/results.md` |

---

## Phase 14 — Computer Vision: Real-World Congestion Classification

**Duration:** 1 week
**Goal:** Classify road-segment congestion from real color-coded traffic-tile imagery, as an independent real-world signal that feeds the GA fitness function and (later) RL reward shaping — kept entirely on the Python/pipeline side, never touching the C++ hot loop.
**Checkpoint artifact:** `data/<city>/cv_congestion.json` with per-zone, per-hour congestion levels; a comparison table of classical-threshold vs. CNN classification accuracy against a small hand-labeled validation set.

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 14.1 | Add `cv_bbox` per-city key to `cities.yaml` (lat/lon bounding box for tile capture) | `refactor/city-config-cv-bbox` | Follows the existing config-driven-per-city convention |
| 14.2 | Write `pipeline/src/cv_congestion.py`: fetch traffic-flow tiles/vectors via **Mapbox Traffic Tiles** or **TomTom Traffic Flow API** (documented, ToS-compliant; note in the module docstring that Google's Static Maps API has no scriptable live-traffic layer) | `data/cv-tile-fetch` | Requires an API key; document how to set it via env var, never commit it |
| 14.3 | Classical CV: HSV color-threshold bucketing of road-colored pixels within road-mask regions → congestion_level 0–3 | `feature/cv-classical-congestion` | No training data required; primary/production path |
| 14.4 | CNN comparison: small custom CNN or fine-tuned ResNet-18 (4-class) on a hand-labeled sample of tile crops | `experiment/cv-cnn-congestion` | Explicit "classical vs. learned" comparison for the coursework deliverable |
| 14.5 | Write `data/<city>/cv_congestion.json` (`{zone_id: {hour: {level, confidence, source}}}`) | `data/cv-congestion-export` | Consumed only by `optimize_calibration.py` and (later) `ml/env/reward.py` |
| 14.6 | Wire `cv_congestion.json` into the GA as an additional fitness term (sim zone wait/speed vs. CV-observed level), blended with MAPE | `feature/ga-cv-fitness-term` | Extends Phase 13's optimizer; both terms weighted, weight documented |
| 14.7 | Dashboard: `CongestionCVOverlay.tsx` — reuses the existing `EquityOverlay.tsx` zone-bubble pattern, colored by CV-observed congestion level | `feature/dashboard-cv-overlay` | Static per-hour data, not live-streamed |

---

## Phase 15 — Computer Vision: Synthetic Virtual Camera

**Duration:** 1 week
**Goal:** A live "virtual camera" demo feature: render a top-down view from the simulation's own agent stream and run real detection/counting on it — a genuine CV pipeline (not just re-displaying known agent positions), safe to build independently since it's read-only and outside the control path.
**Checkpoint artifact:** Live annotated video panel in the dashboard showing bounding boxes and a running vehicle count that tracks the actual simulated traffic in view.

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 15.1 | `ml/cv/virtual_camera.py`: WS client on the engine's existing agent stream; rasterize a top-down frame (roads from `graph.json`, agents as colored shapes by type) with Pillow/OpenCV | `feature/virtual-camera-render` | Reuses the existing `{"type":"bounds"}` outbound message as "another viewport client" |
| 15.2 | OpenCV contour/blob detection + color-based segmentation on the rendered frame → bounding boxes + count | `feature/virtual-camera-detection` | Detecting on the rendered pixels, not reading known state directly — genuine CV work |
| 15.3 | `ml/cv/virtual_camera_service.py`: small FastAPI/websockets server (new port 9003), streams annotated PNG (base64) + count JSON at ~1 Hz | `feature/virtual-camera-service` | Independent process; no engine or Simulation changes |
| 15.4 | Dashboard: `VirtualCameraPanel.tsx` — displays the live annotated feed | `feature/dashboard-camera-panel` | Polls/subscribes to the service, not the engine directly |
| 15.5 | Accuracy sanity check: detected count vs. ground-truth agent count in view, logged as a running error % | `experiment/camera-detection-accuracy` | Documents detection reliability for the coursework writeup |

---

## Phase 16 — NLP: Live Metrics Chat Interface

**Duration:** 1 week
**Goal:** A natural-language query interface over the dashboard's live metrics, answering questions like "which zone has the worst wait time right now" against actual current simulation state.
**Checkpoint artifact:** Chat panel in the dashboard answers a fixed set of held-out test queries correctly, sourced from live engine state, not stale/mocked data.

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 16.1 | `ml/nlp/chat_service.py`: FastAPI service that is itself a WS client of the engine, caching latest `metrics`/`zone_metrics`/`signals` | `feature/nlp-chat-service` | Keeps Python NLP deps out of the frontend bundle and out of the C++ hot path |
| 16.2 | Rule-based intent classifier: regex over a fixed intent set (worst_zone, avg_speed, active_agents, gini_explain, compare_policy, incident_status) | `feature/nlp-intent-rules` | Reliable baseline; unit-tested independently of the LLM path |
| 16.3 | Optional LLM tool-calling layer: same metric-lookup functions exposed as tools, falls back to rule-based when no API key configured | `feature/nlp-llm-toolcalling` | Gives a "classical NLP vs. LLM" comparison for the coursework; not a hard dependency for the core demo |
| 16.4 | `POST /chat` endpoint; response includes which intent/tool fired, for transparency in the UI | `feature/nlp-chat-endpoint` | |
| 16.5 | Dashboard: `ChatPanel.tsx` — calls `chat_service.py` directly over REST | `feature/dashboard-chat-panel` | |
| 16.6 | Held-out query test set + accuracy report (rule-based vs. LLM path) | `experiment/nlp-intent-accuracy` | Documents intent accuracy for the coursework deliverable |

---

## Phase 17 — NLP: Incident Reports → Simulation Mutation

**Duration:** 1 week
**Goal:** Free-text incident reports ("accident on Michigan Ave, lane closure") parse into a structured spec and mutate the *running* simulation — the clearest cross-subsystem demo, since RL and the dashboard both react automatically.
**Checkpoint artifact:** Submitting an incident report visibly changes agent routing/queueing on the map, appears in the dashboard's `incidents` list, and expires automatically after its stated duration.

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 17.1 | `ml/nlp/incident_parser.py`: pure function `parse(text, graph) -> IncidentSpec`; street-name gazetteer built from `graph.json` edge names, fuzzy-matched via `rapidfuzz` | `feature/nlp-incident-parser` | Independently unit-testable; small fixed vocabulary for type/severity |
| 17.2 | `chat_service.py` exposes `POST /incident`, forwards the parsed spec as `{"type":"incident", edges, severity, duration_s}` over WS to the engine | `feature/nlp-incident-endpoint` | Opens its own WS client connection to the engine, reusing the Phase 12 control-message pattern |
| 17.3 | Engine: `WebSocketServer` dispatch gains an `"incident"` branch; `Simulation::apply_incident()` stores a temporary per-edge speed/capacity multiplier, expired after `duration_s` of `sim_time_` | `feature/engine-apply-incident` | Reuses Pathfinder's existing stochastic edge-cost mechanism — no new pathfinding logic |
| 17.4 | Add `incidents[]` (active, with remaining duration) to `broadcast_state()` JSON | `feature/broadcast-incidents` | Extends Phase 12.4's schema addition |
| 17.5 | Dashboard: `IncidentReportPanel.tsx` — free-text box, shows active incidents and their effect on nearby zone metrics | `feature/dashboard-incident-panel` | |
| 17.6 | Unit tests: gazetteer resolution accuracy on ambiguous/misspelled street names; incident expiry correctness | `feature/nlp-incident-tests` | |

---

## Phase 18 — Cross-Subsystem Hardening & Integrated Demo

**Duration:** 1 week
**Goal:** All four subjects run together as one system from a clean clone; the demo shows every subsystem reacting to the others, not four isolated toggles.
**Checkpoint artifact:** Single end-to-end run — GA-tuned parameters + CV congestion overlay + RL/Fuzzy/Webster toggle + live chat + incident report — recorded in one continuous screen capture.

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 18.1 | Extend `make demo` to also launch `chat_service.py` and `virtual_camera_service.py`, run GA calibration on the pre-packaged mini-graph, load an RL checkpoint if present | `feature/make-demo-extended` | Falls back gracefully to Webster-only if no RL checkpoint is trained yet |
| 18.2 | Comparison writeup: Webster vs. Fuzzy vs. RL (avg wait, Gini per city); CV classical-vs-CNN accuracy; GA convergence; NLP intent accuracy | `docs/four-subject-results` | `docs/results.md`; the single artifact tying all four subjects together |
| 18.3 | End-to-end smoke checklist covering all four subsystems together, extending the existing `docs/e2e_checklist.md` from Phase 4.8 | `feature/e2e-checklist-v2` | Run before final submission |
| 18.4 | Record and commit an integrated demo video showing cross-subsystem reactions (incident → RL response → metrics update) | `docs/demo-video-integrated` | Supersedes the single-subsystem demo video from Phase 11.8 |

---

## Phase Summary

| Phase | What gets built | Checkpoint artifact |
|-------|----------------|---------------------|
| 0 | Repo skeleton, CI, pre-commit | `make test` passes on CI |
| 1 | OSM pipeline + C++ graph loader | Engine prints real Chicago graph stats |
| 2 | Agent system + pathfinding + IDM | 500 agents navigate, log journey times |
| 3 | Quadtree + collision + 20k agent scale | Benchmark: Quadtree ≥ 10× faster at 10k agents |
| 4 | WebSocket stream + dashboard map | 5k agents on Chicago map at 60 fps in browser |
| 5 | Signal baseline + metrics + equity view | Dashboard shows efficiency + equity panels |
| 6 | Real OD demand + validation | Chicago validation report within 25% error |
| 7 | MARL training environment + MAPPO | Rising reward curve on toy graph in MLflow |
| 8 | ONNX export + C++ inference | AI mode running; p95 inference ≤ 8 ms |
| 9 | Multi-city training + validation | MARL vs. Webster table across 3 cities |
| 10 | Policy toggles + dashboard polish | Full demo: toggle → metrics change → export PDF |
| 11 | Hardening + docs + demo | `make demo` works from clean clone in < 30 min |
| 12 | Signal policy abstraction (Webster/Fuzzy/RL hot-swap) | Live `policy_switch` message changes active controller, no restart |
| 13 | Soft computing: GA calibration + fuzzy controller | GA convergence report; fuzzy controller live via `--signal-policy fuzzy` |
| 14 | CV: real-world congestion classification | `cv_congestion.json`; classical-vs-CNN accuracy table |
| 15 | CV: synthetic virtual camera | Live annotated detection/count panel in dashboard |
| 16 | NLP: live metrics chat interface | Chat panel answers held-out queries from live state |
| 17 | NLP: incident reports mutate the sim | Incident report visibly changes routing/queueing on the map |
| 18 | Cross-subsystem hardening + integrated demo | One continuous recording showing all four subjects interacting |
