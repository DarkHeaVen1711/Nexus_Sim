# NexusSim General Backlog — All Phases

Master backlog across every phase in `docs/TEAM_IMPLEMENTATION_PLAN.md`
(Phases 0–36). Updated whenever training/integration work lands.

Status snapshot: **2026-11-19** (audited against `main @ 67f021d`, 2026-11-04).
This replaces the 2026-09-29 snapshot. Statuses below are based on code/artifact
checks, not only on phase-completion claims in other docs.

## Status legend

| Status | Meaning |
|--------|---------|
| DONE | Acceptance criteria met and evidenced by committed code/artifacts. |
| DONE (acceptance pending) | Implementation exists; a measured acceptance gate is still open (e.g. full-length training, validation pass, clean-clone demo). |
| PARTIAL | Some tasks in the phase are done; the rest are not verified or not wired into the runtime. |
| REOPENED | Previously marked DONE, but a later audit found required acceptance work missing. |
| PENDING | Not implemented; work not started. |

---

## Phase progress at a glance (Phases 0–36)

| Phase | Area | Status | Implemented Artifacts & Key Notes |
|-------|------|--------|-----------------------------------|
| 0 | Repo skeleton + CI | REOPENED | Engine CMake, frontend Vite, pytest suite, pre-commit present; **0.9 `docs/adr/template.md` and 0.10 `CONTRIBUTING.md` still missing.** |
| 1 | Graph loading & city geometry | DONE | `pipeline/src/export.py`, C++ `Graph.h` |
| 2 | Agent system & pathfinding | DONE | C++ `Agent.h`, `Pathfinder.h`, IDM car following |
| 3 | Spatial index & collision avoidance | DONE | Counting-sort uniform grid (`SpatialGrid.h`), 20k stress-tested; quadtree retained for benchmark comparison |
| 4 | WebSocket stream & dashboard map | DONE | FlatBuffers schema + React Leaflet map view (live path is JSON WS; FlatBuffers compiled but unused by design) |
| 5 | Fixed-cycle signal baseline | DONE | `SignalController.h` Webster fixed-cycle timing |
| 6 | Real traffic demand (OD) + validation | DONE (acceptance pending) | Chicago Socrata OD matrix; MAPE figures conflict (18.3% / 15.4% vs 21.6%); validation checkpoint still `false` (63.6% < 75%) |
| 7 | MARL training environment + MAPPO | DONE | `NexusSimEnv` Gymnasium env, PPO trainer, Chicago `199.pt` checkpoint |
| 8 | ONNX export & C++ inference | DONE (acceptance pending) | `InferenceEngine.cpp` ONNX Runtime wrapper, CPU hot path verified; CUDA provider unfinished/crash-prone; p95 reported across five conflicting ranges |
| 9 | Multi-city training & validation | PARTIAL | Chicago checkpoints + `comparison.json` Chicago row exist; Paris/Ahmedabad rows absent; transfer deltas conflict across docs; OD provenance contested |
| 10 | Policy toggles & dashboard polish | DONE | Policy toggle panel, trade-off charts, PDF report export |
| 11 | Hardening, docs & demo | DONE (acceptance pending) | `make demo` target, `docs/results.md`; demo does not start gateway/sidecars or prove clean-clone <30 min (M2/IC-2) |
| 12 | Signal Policy abstraction + `policy_switch` | DONE | `SignalPolicy.h` interface + runtime WebSocket switch |
| 13 | GA calibration + fuzzy controller | DONE (acceptance pending) | `optimize_calibration.py` GA + `FuzzyPolicy.h`; CV fitness consumption unconfirmed; GA result numbers inconsistent |
| 14 | CV: real-world congestion | REOPENED | `cv_congestion.py` + `CongestionCVOverlay.tsx` exist, but synthetic tiles / random labels, no held-out dataset or live Mapbox/TomTom fetch |
| 15 | CV: synthetic virtual camera | DONE (acceptance pending) | `virtual_camera.py`, port 9003 service, `VirtualCameraPanel.tsx`; grey-grid render + REST request/response, not verified 1 Hz stream |
| 16 | NLP: live metrics chat | REOPENED | `chat_service.py` port 9004 + `ChatPanel.tsx`; live-data path and LLM tool-calling layer unconfirmed (`fallback_llm_stub`) |
| 17 | NLP: incidents → simulation | DONE (acceptance pending) | `incident_parser.py` RapidFuzz gazetteer, `apply_incident()`, `IncidentReportPanel.tsx`; gazetteer edge IDs hard-coded |
| 18 | Cross-subject hardening & demo | PARTIAL | Event bus broker exists; live CV→NLP→SC→RL wiring and the 4-subject recording are not evidenced |
| 19 | Shared RL framework (12-algo harness) | DONE (acceptance pending) | `base_trainer.py`, `SingleAgentNexusSimEnv`; `benchmark.py`, `configs.yaml`, `report.py`, `--algos all` absent |
| 20 | Value-based RL (Q-Learning…Dueling DQN) | DONE (acceptance pending) | `value_based.py` implemented; toy-grid only, `mean_wait` catalog/None |
| 21 | Policy-based RL (REINFORCE/A2C/PPO) | DONE (acceptance pending) | `policy_based.py` implemented; toy-grid only |
| 22 | Continuous showcase (SAC/TD3/DDPG) | DONE (acceptance pending) | `continuous_control.py` on Pendulum-v1 only, not signal control |
| 23 | C++ deployment of headline RL | PARTIAL | ONNX MAPPO runtime path verified; multi-algo `--algo` dispatch not evidenced; PDF audit marks MARL-in-engine pending |
| 24 | RL Results, ablation & docs | DONE (acceptance pending) | 12-algorithm table in `docs/results.md`, but wait/Gini figures are catalog values, not re-measured |
| 25 | CV Foundation: Virtual Camera + Detection | PARTIAL | `yolo_detector.py` present; no model weights, no measured accuracy |
| 26–27 | CV Advanced / Motion (DeepSORT, U-Net, Mask R-CNN, optical flow, anomaly, lanes, crowd) | PARTIAL | Module files present; not wired into live pipeline, no weights/validation |
| 28–30 | SC expansion (PSO, SA, CMA-ES, ACS, ABC, ANFIS, GP, rough sets, NSGA-II) | PARTIAL | Modules present; not wired into live signal-control loop, metrics unverified |
| 31–33 | NLP expansion (NER, coref, summarization, QA, KG, event extraction) | PARTIAL | Module files + panels present; stubs and no held-out validation |
| 34 | Cross-subject integration | PARTIAL | Broker + subject services exist; full chain not verified |
| 35 | Unified Dashboard Algo Explorer | PARTIAL | Explorer mounted, 48-algo matrix rendered; named `CVPanel/SCPanel/NLPPanel/RLPanel/ComparisonView` components absent |
| 36 | Results, benchmarks & documentation | PARTIAL | Tables exist; numbers conflict across docs and remain catalog-caveated; final demo video/clean-clone proof not in repo |

---

## Detailed summary of completed milestones & remaining backlogs

### Phase 6 — Real Traffic Demand (OD) + Validation
- **Status:** **DONE (acceptance pending)**
- **Historical baseline:** `data/chicago/validation_report.json` reports MAPE 21.6%, `within_25_pct: 63.6`, `passes_checkpoint: false` against the ≥75% corridor target (`docs/e2e_checklist.md:96-99`).
- **GA result (conflicting):** `docs/results.md:38-39` still reports 18.3% MAPE and a 91% (10/11) pass rate; the older `BACKLOG` claim of 91% is **withdrawn** by `docs/NEXUS-SIM-DOCUMENTATION.md:913-926` (the artifact has no corridor field). `dashboard/public/data/chicago/ga_calibration_report.json:5-15` reports N=20, chromosome `[0.58, 0.22, 0.08, 0.000412]`, 15.4% vs 22.8% MAPE; `docs/JOURNAL_PAPER_ANSWERS.md:24,470` says keep 8/11 (72.7%).
- **Open:** re-run validation on one consistent zone-id space and publish `passes_checkpoint: true` with matching artifacts.

### Phase 7 & 8 — MARL & ONNX Deployment
- **Status:** **DONE (acceptance pending)**
- **Verified:** `ml/policy.onnx` exported from `ml/checkpoints/chicago/199.pt`; ONNX/PyTorch parity on 10 inputs (atol=1e-4); CPU p95 0.0808 ms historically and 0.040–0.133 ms over five idle runs (`docs/evidence/p8_onnx_provider.md:83-87`).
- **Open:** reported p95 ranges disagree across `docs/results.md`, `docs/evidence/p5_dashboard_and_providers.md`, `docs/evidence/p8_onnx_provider.md`, `docs/AI_STRESS_REPORT.md`, and the journal docs (one max of 18.92 ms exceeds the 8 ms budget). CUDA EP attempted and failed safe; explicit `--provider cuda` can hard-crash (`docs/evidence/p8_onnx_provider.md:4-6,49-81`). Use `auto`/CPU until resolved.

### Phase 9 — Multi-City Training & Validation
- **Status:** **PARTIAL**
- **Completed items:** Chicago checkpoints `0/4/52/104/152/199.pt` exist; `ml/results/comparison.json` includes a Chicago row and is synced to `dashboard/public/comparison.json`.
- **Open:** Paris/Ahmedabad rows absent; short-eval transfer results are negative in `docs/JOURNAL_PAPER_DATA.md:157-160` but positive in `docs/JOURNAL_PAPER_ANSWERS.md:241-254`; OD provenance is contested (telemetry feeds vs "strictly gravity-density proxy").

### Time-Machine & XAI (production blueprints, `docs/futureplanning.md`)
- **Status:** **PARTIAL — reopened from "COMPLETED" claims**
- `SnapshotRingBuffer`, snapshot tests, routers, and UI shells exist, but `engine/src/agent/Simulation.h` has no restore/dump integration; `gateway/scenario_router.py:55-68` returns hard-coded scrub results; `gateway/scenario_orchestrator.py:73-96` registers metadata only; `dashboard/src/components/Map.tsx:421-430` supplies no scrub/fork callbacks.
- `XaiInspectionDrawer.tsx` derives values from queue arithmetic with `Math.random()` fallback and hard-coded MAPPO figures; no XAI gateway endpoints or engine telemetry exist.
- **Open:** either wire these end-to-end or downgrade the `[COMPLETED]` markers in `docs/futureplanning.md:639-661`.

---

## Open acceptance gates (OG)

| ID | Gate | Current evidence |
|---|---|---|
| **OG-01** | Chicago `passes_checkpoint: true` (≥75% of corridors within 25%) | `data/chicago/validation_report.json:17-20` → `63.6`, `false` |
| **OG-02** | AI-stress <5 fps drop over 10 minutes | `docs/AI_STRESS_REPORT.md:4,23` → random-weight `−5.1`; addendum used `--duration 1` |
| **OG-03** | CUDA execution provider end-to-end | `docs/evidence/p8_onnx_provider.md:4-6,49-81`; GPU-ORT path in `engine/build_cuda/CMakeCache.txt:511` no longer exists |
| **OG-04** | Recorded e2e checklist run | All boxes unticked in `docs/e2e_checklist.md`; test inventory says 56 CTests/183 tests; actual `ctest -N` = 79, README = 173 + 52 Postman |
| **OG-05** | PRD ≥15% wait reduction / ≥10% Gini improvement | `docs/PRD.md:182-183`; not published; Chicago Gini rose 0.286→0.331 |
| **OG-06** | Time-machine runtime wiring | Snapshot buffer/tests exist, but no engine restore/dump, real fork, or dashboard callbacks |
| **OG-07** | XAI telemetry endpoints & real values | No `gateway/xai_router.py`, no `/inspect/intersection/{id}`; drawer values synthesized |
| **OG-08** | Phase 0 governance + plan CI checks | `docs/adr/`, `CONTRIBUTING.md` absent; clang-format/tidy, 20k stress, black/isort, eslint, main-only e2e, nightly jobs not explicit in CI |
| **OG-09** | M2/IC-2 clean-clone `make demo` <30 min | `Makefile:28-30` builds/launches engine only; no gateway/sidecars or timing proof |
| **OG-10** | Catalog accuracy/latency re-measurement (CV/SC/NLP, 12/48 tables) | `docs/evidence/p3_benchmark_provenance.md:57-62`; `docs/results.md:58-61,84-89` |
| **OG-11** | Postman/doc parity | JSON has 14 folders / 63 requests (A–O); on-disk YAML folders stop at K; docs still say 11 folders / 52 requests |
| **OG-12** | Re-run pipeline suite / CI status | `docs/NEXUS-SIM-DOCUMENTATION.md:841-847,959-961` reports 1 failing `test_od_proxy.py` and red CI as of 2026-10-24; needs re-check against current tree |

---

## Documentation-sync backlog (DS)

| ID | Item | Action |
|---|---|---|
| **DS-01** | `PROGRESS_REPORT.txt:223-241` | Remove the five "still pending" items; all are marked DONE in this backlog. |
| **DS-02** | Root `README.md:274-284,310` | Update test totals and Postman count to A–O / 63 requests; reconcile with OG-04. |
| **DS-03** | `Nexus_Sim_*_Overview.md` decks | Remove "Phases 26–36 PENDING" and now-resolved gap claims. |
| **DS-04** | `docs/README.md:7-50` | Index `docs/evidence/`, journal docs; refresh the 2026-10-24 verification note. |
| **DS-05** | Journal/results numbers | Reconcile reward equation (IPPO vs MAPPO naming), transfer sign flip, GA artifact, latency ranges, intersection counts, PyTorch version, Piedmont count. |
| **DS-06** | `docs/NEXUS-SIM-DOCUMENTATION.md` | Mark sections stale where artifacts now exist (Algo Explorer, Docker, `199.pt`, Chicago comparison row, Vitest suite); re-verify pipeline/CI claims. |
| **DS-07** | `TEAM_IMPLEMENTATION_PLAN.md:5` / `futureplanning.md:639-661` | Resolve "Draft — Pending Approval" vs "authoritative"; align `[COMPLETED]` blueprints with actual partial state. |
| **DS-08** | CLI flags & harness | Replace documented `--signal-policy` / `--algo` with `--signal-mode`; mark `benchmark.py`, `configs.yaml`, `report.py`, `--algos all` as missing. |
| **DS-09** | Deleted-doc references | Remove citations to `TEST_LOG.md` and `USER_STORIES.md` from the PDF and `RL_DOCUMENTATION.md`, or restore the files. |

---

## Completed backlog & resolution register

Statuses revised on 2026-11-19 where later audits contradicted the original resolution.

| ID | Category | Item | Resolution & Implemented Artifact | Status |
|---|---|---|---|:---:|
| **BK-01** | Data Pipeline | Real OD Feeds for Paris & Ahmedabad | `pipeline/src/ingest_telemetry_od.py` and generated telemetry OD matrices exist; provenance contested (synthetic gravity proxy vs telemetry) in `docs/JOURNAL_PAPER_ANSWERS.md:475-490`. | **DONE (acceptance pending)** |
| **BK-02** | ML / Transfer | Re-seed Transfer Models from Converged Chicago | Checkpoints `chicago_to_paris/19.pt`, `chicago_to_ahmedabad/19.pt` exist; evaluation deltas conflict across docs. | **DONE (acceptance pending)** |
| **BK-03** | ML / Evaluation | Transfer Sensitivity Sweeps (Task 9.6) | `ml/train/sensitivity_sweep.py` + `ml/results/transfer_sensitivity.json`. | **DONE** |
| **BK-04** | Dashboard | Automated Component Test Suite | Vitest configured; 8 tests pass, but they assert JSON/schema shapes rather than React component rendering. | **PARTIAL** |
| **BK-05** | DevOps / Infra | Containerization & Multi-Service Compose | Dockerfiles and `docker-compose.yml` exist; no verified build/run recorded (master doc's "no containerization" claim is stale). | **DONE (acceptance pending)** |
| **BK-06** | Architecture | Direct C++ Hot-Path Execution & Zero-IPC Dispatch | ONNX MAPPO path verified; broader multi-algo dispatch not evidenced (`evidence/p3_benchmark_provenance.md:10-12`; PDF audit R1). | **PARTIAL** |
| **BK-07** | Engine / Core | Deterministic State Ring-Buffer & Serialization | `SnapshotBuffer.h` + 6 GoogleTests; not wired into `Simulation.h`. | **DONE (acceptance pending)** |
| **BK-08** | Engine / Routing | Dynamic Edge Penalty & Spatial Polygon Incidents | `Graph::set_edge_penalty`, `PolygonHazard::contains_point`, A* integration; 7 GoogleTests. | **DONE** |
| **BK-09** | Engine / Signals | Emergency Green-Wave Corridor Preemption | `SignalController::trigger_green_wave`, hold buffer, anti-starvation, chaining; 5 GoogleTests. | **DONE** |
| **BK-10** | Engine / Agents | Multi-Modal Kinematics & EV Charging Dwell | `Agent.h` SoA expansion, `simulate_ev_consumption`, charging reroute, dwell state machine; 5 GoogleTests. | **DONE** |
| **BK-11** | Gateway & UI | Multi-Engine Orchestrator, Incident Studio & Postman | Routers/UI/Folders M–O exist; fork/scrub remain metadata-only and Postman counts in docs are stale. | **DONE (acceptance pending)** |
