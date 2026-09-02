# NexusSim General Backlog — All Phases

Master backlog across every phase in `docs/TEAM_IMPLEMENTATION_PLAN.md`
(Phases 0–36). Updated whenever training/integration work lands.

Status snapshot: **2026-09-02**.

## Status legend

| Status | Meaning |
|--------|---------|
| DONE | Acceptance criteria met (per `docs/TRD.md` milestone M / subject docs). |
| DONE (acceptance pending) | Implementation exists; a measured acceptance gate is still open (e.g. full-length training, validation pass). |
| PARTIAL | Some tasks in the phase are done, others remain. |
| PENDING | Not implemented; work not started. |

---

## Phase progress at a glance

| Phase | Area | Status | Key pending items |
|-------|------|--------|-------------------|
| 0 | Repo skeleton + CI | DONE | — |
| 1 | Graph loading & city geometry | DONE | — |
| 2 | Agent system & pathfinding | DONE | — |
| 3 | Quadtree & collision avoidance | DONE | — |
| 4 | WebSocket stream & dashboard map | DONE | — |
| 5 | Fixed-cycle signal baseline | DONE | — |
| 6 | Real traffic demand (OD) + validation | DONE (acceptance pending) | Chicago `passes_checkpoint: false` |
| 7 | MARL training environment + MAPPO | PARTIAL | O-RL-5 toy reward ≥ Webster not shown |
| 8 | ONNX export & C++ inference | DONE (acceptance pending) | Parity/p95 gate pending a trained model |
| 9 | Multi-city training & validation | PARTIAL | Chicago 9.1 training, validation 9.2/9.6, transfer from final model 9.5, 3-city comparison table 9.7 — see Phase 9 section below |
| 10 | Policy toggles & dashboard polish | PARTIAL | Policy toggle panel, before/after + tradeoff charts, PDF export (blocked on Phase 12) |
| 11 | Hardening, docs & demo | PARTIAL | `make demo`, benchmark/ablation write-ups |
| 12 | Signal Policy abstraction + `policy_switch` | PENDING | TR-ENG-09/10, TR-DASH-05 |
| 13 | GA calibration + fuzzy controller | PENDING | TR-PIPE-07, TR-ENG-11, TR-DASH-06 |
| 14 | CV: real-world congestion | PENDING | TR-PIPE-08, TR-DASH-07 |
| 15 | CV: synthetic virtual camera | PENDING | TR-ML-08, TR-DASH-08 |
| 16 | NLP: live metrics chat | PENDING | TR-ML-09, TR-DASH-09 |
| 17 | NLP: incidents → simulation | PENDING | TR-ENG-13, TR-ML-10, TR-DASH-10 |
| 18 | Cross-subject hardening & demo | PENDING | — |
| 19 | Shared RL framework (12-algo harness) | PENDING | TR-ML-11/12/13 |
| 20 | Value-based RL (Q-Learning…Dueling DQN) | PENDING | TR-ML-14/15 |
| 21 | Policy-based RL (REINFORCE/A2C/PPO) | PENDING | TR-ML-16 |
| 22 | Continuous showcase (SAC/TD3/DDPG) | PENDING | TR-ML-17 |
| 23 | C++ deployment of headline RL | PENDING | TR-ML-18, O-RL-12 |
| 24 | RL results, ablation & docs | PENDING | TR-ML-19, O-RL-13 |
| 25–36 | 36-algorithm expansion (CV/SC/NLP/RL) | PENDING | Out of current scope |

---

## Backlog for implemented phases (0–11)

### Phase 6 — Real Traffic Demand (OD) + Validation
Implementation finished; the **acceptance checkpoint is failing**:
- `data/chicago/validation_report.json` (2026-08-03): MAPE 21.6% (≤25 OK),
  within-25% **63.6%** (target ≥75%), `passes_checkpoint: false`.
- Action: recalibrate the `--demand-scale` / `speed_factor` sweep in
  `pipeline/src/validate.py` and re-run until `passes_checkpoint: true`.
- Paris/Ahmedabad have `validation_safe: false` proxy OD — validation there is
  intentionally guarded (TR-PIPE-06 circular-MAPE guard).

### Phase 7 — MARL Training Environment + MAPPO
- O-RL-1 env wrapper: docs still "IN PROGRESS".
- **O-RL-5 PENDING**: toy reward curve must rise above the Webster baseline by
  500 episodes. `ml/results/comparison.json` currently shows toy MARL below
  Webster (`improvement_pct ≈ −12.5%`). Needs a long toy run + eval.

### Phase 8 — ONNX Export & C++ Inference
Infrastructure DONE (`ml/export/export_onnx.py`, `validate_onnx.py`,
`engine/src/ai/InferenceEngine.*`, `bench_inference`, `test_inference`,
`docs/AI_STRESS_REPORT.md`).
- Acceptance gate open: PyTorch↔ONNX parity on the 10 test inputs and
  `p95 ≤ 8 ms` verified against a **trained, real** policy (the ONNX engine is
  currently exercised with a random toy policy). Blocked on 9.1.

### Phase 9 — Multi-City Training & Validation
Summary of what remains:
- 9.1 Chicago full training (2000–5000 ep) — the big blocker (CPU-bound).
- 9.2 Chicago validation re-run to pass acceptance (shared with Phase 6).
- 9.5 Re-seed Paris/Ahmedabad transfers from the final Chicago checkpoint
  (current runs used `toy/249.pt`, both at `*-to-*/499.pt`).
- 9.6 Transfer sensitivity sweep (`--chaos`/`--demand-scale`) + doc.
- 9.7 Regenerate `ml/results/comparison.json` with chicago/paris/ahmedabad rows
  (currently stale: toy + piedmont only).

### Phase 10 — Policy Toggles & Dashboard Polish (PARTIAL)
Done so far:
- `CitySelector.tsx` (city switch), `ComparisonPanel.tsx` (MARL-vs-Webster,
  wired to `/comparison.json` via the vite proxy).

Pending (mostly blocked on Phase 12 `policy_switch`):
- Policy toggle panel sending a `policy_switch` control message (TR-DASH-04).
- Before/after metric comparison + tradeoff-curve chart (α/β sweep).
- PDF export of the comparison result.

### Phase 11 — Hardening, Docs & Demo (PARTIAL)
Done: `run.bat` (auto-install prerequisites), CI (pipeline/ml pytest, C++ build,
JS tests), README, stress/bench reports.
Pending:
- `make demo` target working from a clean clone (NFR-8, TRD M-11).
- Benchmark result tables and validation results published (e.g. `docs/results.md`).

---

## Not yet implemented (PENDING) — quick pointers

| Phase | Work item | Where it will land |
|-------|-----------|--------------------|
| 12 | `SignalPolicy` interface, `WebsterPolicy`, live `policy_switch` | `engine/src/agent/`, `engine/src/network/`, `dashboard` |
| 13 | GA calibration (`optimize_calibration.py`), Mamdani `FuzzyPolicy` | `pipeline/src/`, `dashboard CalibrationReportPanel` |
| 14 | CV congestion, classical-vs-CNN | `cv_congestion.py`, `CongestionCVOverlay.tsx` |
| 15 | Virtual camera + detection service | `cv/virtual_camera.py`, `VirtualCameraPanel.tsx` |
| 16 | NLP chat service (rules + optional LLM) | `nlp/chat_service.py`, `ChatPanel.tsx` |
| 17 | Incident parser → simulation mutation | `nlp/incident_parser.py`, `IncidentReportPanel.tsx` |
| 19–24 | RL deep dive (12 algorithms, benchmark.py, C++ deploy, docs) | `ml/algo/`, `ml/eval/`, `ml/env/single_agent.py` |
| 25–36 | 36-algorithm expansion | Out of current scope |

Subject docs already contain target architecture: `CV_DOCUMENTATION.md`
(Ph 14–15, status NOT YET IMPLEMENTED), `NLP_DOCUMENTATION.md` (Ph 16–17),
`SOFT_COMPUTING_DOCUMENTATION.md` (Ph 13), `RL_DOCUMENTATION.md` (Ph 19–24).

---

## Cross-cutting housekeeping

- **TRD statuses stale** — `docs/TRD.md` still shows TR-ML-01…06 as PLANNED
  even though `ml/env` + `train/ppo.py` + MLflow checkpointing exist
  (RL_DOCUMENTATION marks O-RL-2…4 DONE). TR-ML-07 (ONNX export) also has code.
  Recommend a docs pass to align TRD with reality.
- **`ml/results/comparison.json` stale** — holds toy + piedmont rows; regenerate
  in 9.7. It is a tracked deliverable (not gitignored).
- **`docs/TRD.md` TR-ML-06b / `O-RL-7`** — correctly reflect "DONE (infra);
  full Chicago run pending".
- **Interrupted runs** — an MLflow run stuck at `status=1 RUNNING` with no live
  process means the train/transfer was closed; restart with `--resume latest`
  (both `train.py` and `transfer.py` support it now). Never delete checkpoints
  under `ml/checkpoints/`.