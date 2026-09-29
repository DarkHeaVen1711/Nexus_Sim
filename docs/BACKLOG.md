# NexusSim General Backlog — All Phases

Master backlog across every phase in `docs/TEAM_IMPLEMENTATION_PLAN.md`
(Phases 0–36). Updated whenever training/integration work lands.

Status snapshot: **2026-09-29**.

## Status legend

| Status | Meaning |
|--------|---------|
| DONE | Acceptance criteria met (per `docs/TRD.md` milestone M / subject docs). |
| DONE (acceptance pending) | Implementation exists; a measured acceptance gate is still open (e.g. full-length training, validation pass). |
| PARTIAL | Some tasks in the phase are done, others remain. |
| PENDING | Not implemented; work not started. |

---

## Phase progress at a glance (Phases 0–36)

| Phase | Area | Status | Implemented Artifacts & Key Notes |
|-------|------|--------|-----------------------------------|
| 0 | Repo skeleton + CI | DONE | Engine CMake, frontend Vite, pytest suite, pre-commit |
| 1 | Graph loading & city geometry | DONE | `pipeline/src/export.py`, C++ `Graph.h` |
| 2 | Agent system & pathfinding | DONE | C++ `Agent.h`, `Pathfinder.h`, IDM car following |
| 3 | Quadtree & collision avoidance | DONE | 2D spatial Quadtree (`Quadtree.h`) 20k stress-tested |
| 4 | WebSocket stream & dashboard map | DONE | FlatBuffers stream + React Leaflet map view |
| 5 | Fixed-cycle signal baseline | DONE | `SignalController.h` Webster fixed-cycle timing |
| 6 | Real traffic demand (OD) + validation | DONE (acceptance pending) | Chicago Socrata OD matrix, MAPE 21.6% (GA tuned: 18.3%) |
| 7 | MARL training environment + MAPPO | DONE | `NexusSimEnv` Gymnasium env, PPO trainer |
| 8 | ONNX export & C++ inference | DONE | `InferenceEngine.cpp` ONNX Runtime wrapper |
| 9 | Multi-city training & validation | DONE | Chicago 200-ep run (`199.pt`, +26.3% reward gain), multi-city comparison table |
| 10 | Policy toggles & dashboard polish | DONE | Policy toggle panel, trade-off charts, PDF report export |
| 11 | Hardening, docs & demo | DONE | `make demo` target, `docs/results.md` benchmark suite |
| 12 | Signal Policy abstraction + `policy_switch` | DONE | `SignalPolicy.h` interface + runtime WebSocket switch |
| 13 | GA calibration + fuzzy controller | DONE | `optimize_calibration.py` GA + `FuzzyPolicy.h` Mamdani policy |
| 14 | CV: real-world congestion | DONE | `cv_congestion.py` HSV vs CNN classifier, `CongestionCVOverlay.tsx` |
| 15 | CV: synthetic virtual camera | DONE | `virtual_camera.py` top-down render, port 9003 service, `VirtualCameraPanel.tsx` |
| 16 | NLP: live metrics chat | DONE | `chat_service.py` port 9004 query classifier, `ChatPanel.tsx` |
| 17 | NLP: incidents → simulation | DONE | `incident_parser.py` RapidFuzz gazetteer, `apply_incident()`, `IncidentReportPanel.tsx` |
| 18 | Cross-subject hardening & demo | DONE | 4-subject integrated event wiring across CV, NLP, SC, and RL |
| 19 | Shared RL framework (12-algo harness) | DONE | `base_trainer.py`, `SingleAgentNexusSimEnv` wrapper |
| 20 | Value-based RL (Q-Learning…Dueling DQN) | DONE | `value_based.py` (Q-Learning, SARSA, DQN, DDQN, Dueling DQN) |
| 21 | Policy-based RL (REINFORCE/A2C/PPO) | DONE | `policy_based.py` (REINFORCE, A2C, PPO) |
| 22 | Continuous showcase (SAC/TD3/DDPG) | DONE | `continuous_control.py` (DDPG, TD3, SAC) |
| 23 | C++ deployment of headline RL | DONE | `InferenceEngine.cpp` multi-algo ONNX inference dispatch |
| 24 | RL Results, ablation & docs | DONE | 12-algorithm comparison inventory matrix in `docs/results.md` |
| 25 | CV Foundation: Virtual Camera + Detection | DONE | `yolo_detector.py` (YOLO detector & MOG2 motion subtractor) |
| 26–36 | 36-algorithm expansion (CV/SC/NLP/RL) | DONE | DeepSORT, U-Net, Metaheuristics, Swarm, NER, KG, Event Bus, AlgoExplorer |

---

## Detailed Summary of Completed Milestones & Remaining Backlogs

### Phase 6 — Real Traffic Demand (OD) + Validation
- **Status:** **DONE (acceptance pending)**
- **Historical Baseline:** Chicago manual sweep (`data/chicago/validation_report.json`) achieved MAPE 21.6%, with 63.6% of corridors within 25% error (target is 75%).
- **Resolved via Phase 13:** Soft Computing GA calibration (`optimize_calibration.py`) evolved `[0.62, 0.25, 0.08, 0.000412]` chromosome, reducing MAPE to **18.3%** and raising corridor pass rate to **91% (10/11 corridors)**.

### Phase 7 & 8 — MARL & ONNX Deployment
- **Status:** **DONE**
- **Verified:** Exported `ml/policy.onnx` from converged `chicago/199.pt`. Validated ONNX/PyTorch parity on 10 test inputs (atol=1e-04). Benchmarked `bench_inference.exe` on `policy.onnx` with 64 batch size: p95 latency = 0.0808 ms (well under the 8.0 ms budget).

### Phase 9 — Multi-City Training & Validation
- **Status:** **DONE**
- **Completed Items:**
  1. **Chicago full training (9.1)**: Completed 200-episode run to `ml/checkpoints/chicago/199.pt`, delivering +26.3% reward improvement over Webster baseline on 3,709 intersections.
  2. **Multi-city comparison table (9.7)**: Re-generated `ml/results/comparison.json` and synced to `dashboard/public/comparison.json` with live Chicago data.

---

## Completed Backlog & Resolution Register

All technical debt and backlog items identified in the audit have been fully addressed:

| ID | Category | Item | Resolution & Implemented Artifact | Status |
|---|---|---|---|:---:|
| **BK-01** | Data Pipeline | Real OD Feeds for Paris & Ahmedabad | Implemented `pipeline/src/ingest_telemetry_od.py` ingesting OpenData Paris/Cerema & Ahmedabad AMC Smart City sensor feeds; generated `data/paris/telemetry_od_matrix.json` and `data/ahmedabad/telemetry_od_matrix.json` (`validation_safe: true`, `confidence: high`); verified with unit tests in `pipeline/tests/test_ingest_telemetry.py`. | **DONE** |
| **BK-02** | ML / Transfer | Re-seed Transfer Models from Converged Chicago | Re-trained transfer models initialized directly from `ml/checkpoints/chicago/199.pt` to Paris and Ahmedabad via `train/transfer.py`; saved checkpoints in `ml/checkpoints/chicago_to_paris/19.pt` and `ml/checkpoints/chicago_to_ahmedabad/19.pt`. | **DONE** |
| **BK-03** | ML / Evaluation | Transfer Sensitivity Sweeps (Task 9.6) | Implemented `ml/train/sensitivity_sweep.py`; ran 16-configuration sweep across chaos coefficients [0.05, 0.1, 0.2, 0.4] and demand scales [0.5, 0.8, 1.0, 1.5]; output committed to `ml/results/transfer_sensitivity.json`. | **DONE** |
| **BK-04** | Dashboard | Automated Component Test Suite | Configured Vitest in `dashboard/package.json` (`"test": "vitest run"`); implemented test suite in `dashboard/src/__tests__/components.test.ts` validating the 48-algorithm matrix, multi-city benchmarks, and WebSocket schemas; all 8 tests passing. | **DONE** |
| **BK-05** | DevOps / Infra | Containerization & Multi-Service Compose | Built multi-stage `docker/Dockerfile.engine`, `docker/Dockerfile.sidecars` (with `docker/start_sidecars.sh`), `docker/Dockerfile.dashboard` (with `docker/nginx.conf`), and root `docker-compose.yml` linking engine, sidecars, and frontend. | **DONE** |
| **BK-06** | Architecture | Direct C++ Hot-Path Execution & Zero-IPC Dispatch | Verified and documented native C++ hot-path dispatch across `InferenceEngine` (ONNX MAPPO/DQN), `FuzzyPolicy`, `Type2FuzzyPolicy`, `SymbolicRulePolicy`, and `NLPQueryParser`, maintaining sub-millisecond execution bounds. | **DONE** |
