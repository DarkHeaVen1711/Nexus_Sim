# NexusSim General Backlog — All Phases

Master backlog across every phase in `docs/TEAM_IMPLEMENTATION_PLAN.md`
(Phases 0–36). Updated whenever training/integration work lands.

Status snapshot: **2026-09-17**.

## Status legend

| Status | Meaning |
|--------|---------|
| DONE | Acceptance criteria met (per `docs/TRD.md` milestone M / subject docs). |
| DONE (acceptance pending) | Implementation exists; a measured acceptance gate is still open (e.g. full-length training, validation pass). |
| PARTIAL | Some tasks in the phase are done, others remain. |
| PENDING | Not implemented; work not started. |

---

## Phase progress at a glance (Phases 0–25)

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
| 9 | Multi-city training & validation | PARTIAL | Chicago full training & multi-city transfer learning |
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
| 26–36 | 36-algorithm expansion (CV/SC/NLP/RL) | PENDING | Out of current scope |

---

## Detailed Summary of Remaining / Pending Items in Phases 1–25

### Phase 6 — Real Traffic Demand (OD) + Validation
- **Status:** **DONE (acceptance pending)**
- **Pending Item:** Chicago `passes_checkpoint: false` in raw Phase 6 manual sweep (`data/chicago/validation_report.json` within-25% target is 63.6% vs 75% required).
- **Resolved via Phase 13:** Soft Computing GA calibration (`optimize_calibration.py`) evolved `[0.62, 0.25, 0.08, 0.000412]` chromosome, reducing MAPE to **18.3%** and raising corridor pass rate to **91% (10/11 corridors)**.

### Phase 7 & 8 — MARL & ONNX Deployment
- **Status:** **DONE (infra)**
- **Pending Item:** Verification of ONNX inference against full overnight multi-thousand episode Chicago run checkpoint (`chicago/199.pt`).

### Phase 9 — Multi-City Training & Validation
- **Status:** **PARTIAL**
- **Pending Items:**
  1. **Chicago full training (9.1)**: Overnight 2,000–5,000 episode training run completion.
  2. **Multi-city comparison table (9.7)**: Re-generate `ml/results/comparison.json` with final Chicago checkpoint once overnight training completes.