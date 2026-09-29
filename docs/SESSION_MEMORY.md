# NexusSim — Session Memory

Running log for cross-session continuation. **Append a new section per session,
newest first**, with: date, work done, key state (checkpoints / run IDs /
branch / PR), commands that matter, and what to do next. Keep entries short —
point at `docs/BACKLOG.md` for pending work.

Quick orientation:
- Backlog of pending work across all phases: **`docs/BACKLOG.md`**.
- Training/transfer entry points: `ml/train/train.py`, `ml/train/transfer.py`.
- Repo root E2E checklist: `docs/e2e_checklist.md`.

---

## Session 7 — 2026-09-29 | 36-Algorithm Expansion, Master Matrix & Event Bus Integration

**Work done**
- Implemented and audited full 36-algorithm multi-subject portfolio across all 4 subjects:
  - **Computer Vision (12)**: Classical HSV, CNN Traffic Tile Classifier, Top-Down Blob Detector, DeepSORT Tracker, U-Net Segmentation, Mask R-CNN, Hazard Perception (Anomaly Detector), Optical Flow (Lucas-Kanade), Lane Boundary Detector, Crowd Density Estimator, YOLO Detector, MOG2 Background Subtractor.
  - **Soft Computing (12)**: Genetic Algorithm calibration, Mamdani Fuzzy Controller, Interval Type-2 Fuzzy, Particle Swarm Optimization (PSO), Simulated Annealing (SA), CMA-ES, Ant Colony Optimization (ACS), Artificial Bee Colony (ABC), ANFIS Neuro-Fuzzy, Genetic Programming (GP), Rough Sets, NSGA-II Multi-Objective Pareto.
  - **Natural Language Processing (12)**: Regex Intent Classifier, LLM Tool Calling Fallback, RapidFuzz Gazetteer Incident Parser, VADER Sentiment Analyzer, Naive Bayes Classifier, SpaCy/Regex NER Extractor, Coreference Resolver, TextRank Summarizer, QA Engine, RDF Knowledge Graph, Event Extractor, Interactive NLP Command Console.
  - **Reinforcement Learning (12)**: MAPPO (headline multi-agent), Q-Learning, SARSA, DQN, Double DQN, Dueling DQN, REINFORCE, A2C, PPO, DDPG, TD3, SAC.
- **Cross-Subject Event Bus**: Built async pub/sub broker (`pipeline/src/event_bus.py`) on port 9005 connecting CV alerts -> NLP extraction -> SC parameter tuning -> RL action exploration.
- **Evaluation Matrix & Sidecar**: Built `ml/eval/benchmark_36.py` producing `36_algo_matrix.json` (48 total algorithm records) synced to `dashboard/public/data/36_algo_matrix.json`, served via `ml/sidecars/algo_explorer_service.py` on port 9006.
- **Dashboard UI Expansion**: Built `AlgoExplorer` dashboard suite, plus `ParetoFrontPanel`, `ConvergencePanel`, `FuzzyRulesPanel`, `OpticalFlowPanel`, `TrackingOverlay`, `NERPanel`, `SentimentFeedPanel`, `KnowledgeGraphPanel`.
- **Automated Tests**: Added `ml/tests/test_cross_subject_e2e.py` validating full cross-subject data loop; updated requirements with `fastapi`, `uvicorn`, `websockets`.
- **Docs Consolidation**: Unified session progress history into `SESSION_MEMORY.md`, retired superseded progress files (`SESSION_PROGRESS_2026-09-10/11/17.md`), and updated TRD, Backlog, and Subject Documentation.

---

## Session 6 — 2026-09-17 | Chicago 200-Episode Full Training Convergence & Multi-City Sync

**Work done**
- **Full Chicago Training Completed**: 200-episode run converged on the batched PPO path (`batch_size=1024`, CUDA).
- Checkpoints saved to disk: `ml/checkpoints/chicago/{0, 4, 52, 104, 152, 199}.pt`.
- Final performance: Episode reward `-10,298.50` vs Webster baseline `-13,973.97` (**+26.3% reward gain** on 3,709 intersections).
- **Parity & C++ Hot-Path Inference Gate**: Exported production `ml/policy.onnx`. Benchmarked `bench_inference.exe` with batch size 64: p95 latency = 0.0808 ms (well under the 8.0 ms budget).
- **Multi-City Evaluation (Task 9.7)**: Re-evaluated multi-city table (`python -m train.evaluate --cities toy piedmont chicago`). Updated `ml/results/comparison.json` and synced to `dashboard/public/comparison.json`.

---

## Session 5 — 2026-09-11 | Batched/Vectorized PPO Pipeline & Vectorized Sim Integration

**Work done**
- **Batched PPO Refactor**: Eliminated per-agent Python loops in MAPPO. Added `compute_gae_batched` in `ml/train/ppo.py` operating on `[num_agents, horizon]` tensors.
- `collect_episode` refactored to emit agent-major tensors, eliminating 370K per-step CUDA scalar allocations.
- Single batched `ppo_update` across all 370,900 samples per episode-update.
- Increased PPO `batch_size` from 256 to 1024 across `train.py`, `transfer.py`, and `ppo.py`, cutting PPO update bottleneck from ~66 s to ~17 s.
- Verified parity: `compute_gae_batched` matches scalar GAE with `torch.allclose == True`.
- Merged and committed in `a86996d`.

---

## Session 4 — 2026-09-10 | Vectorized Traffic Sim, CUDA Acceleration & MLflow SQLite Migration

**Work done**
- **Vectorized Sim**: Implemented `VectorizedTrafficSim` in `ml/env/vectorized_sim.py` for networks with >100 intersections.
- **Algorithmic Optimizations**: Replaced O(n²) Gini calculation with O(n log n) numpy sort, saving ~0.75 s per env step on Chicago.
- **Robustness**: Fixed `neighbor_pressures` in `ml/env/traffic_sim.py` to gracefully handle asymmetric and one-way road connections.
- **GPU Acceleration**: Upgraded PyTorch to CUDA 12.4/12.6 build (`torch.cuda.is_available() == True` on RTX 2050).
- **MLflow Tracking Fix**: Replaced deprecated file-store URIs with SQLite backend (`sqlite:///ml/mlflow.db`).

---

## Session 3 — 2026-09-02 (later) | TRD alignment + partial 9.7 (PR #29)

**Work done**
- `ml/train/transfer.py`: added `--resume {latest|<path>}` (restores
  policy/value/optimizer state, continues episodes, stores `reward_scale`,
  logs `resumed_from` param).
- `ml/train/train.py` + `transfer.py`: progress bars now meter the **full
  budget** (`total=<goal>, initial=<start>`), so resumed runs show overall
  % complete; both print a completion summary; both early-exit when already
  complete.
- Tests: `ml/tests/test_transfer_evaluate.py` +7 (`_resolve_resume`, resume
  ckpt roundtrip). `ml/tests` suite green (78 passed).
- Resumed Paris + Ahmedabad transfers **199 → 500 episodes** from
  `checkpoints/toy/249.pt` (reward_scale preserved):
  - Paris → `ml/checkpoints/249_to_paris/499.pt` (MLflow run `231163547…`)
  - Ahmedabad → `ml/checkpoints/249_to_ahmedabad/499.pt` (run `097495c1…`)
- Chicago: resume + meter smoke-tested end-to-end (6 tiny episodes); the long
  run was NOT started. Smoke checkpoints cleaned up; dir back to `0.pt`.
- Docs created/updated: `docs/BACKLOG.md` (master backlog, all phases),
  deleted redundant `docs/PHASE9_BACKLOG.md`; `.gitignore` now excludes
  `ml/results/` until 9.7 regenerates it.
- All commits pushed to branch `feature/phase9-wip-pending-training`
  → **PR #29 (OPEN)**: https://github.com/DarkHeaVen1711/Nexus_Sim/pull/29

**Key state / facts**
- Closed/interrupted run marker: MLflow `status=1 RUNNING`, `end_time: null`,
  no live python process. Restart with `--resume latest`; never delete
  `ml/checkpoints/`.
- Chicago graph: 3709 intersections / 77 zones; ~20 s per step on CPU.
- `ml/mlruns/`, `ml/checkpoints/`, `ml/results/` are gitignored.

**Useful commands** (run from repo root; venv is `.venv\Scripts\python.exe`)
- Chicago full training (resume from `0.pt`): `python -m train.train --city
  chicago --episodes 2000 --resume latest --checkpoint-interval 500` (from `ml/`)
- Transfer continue: `python -m train.transfer --source checkpoints/toy/249.pt
  --target <paris|ahmedabad> --episodes <total> --resume latest --experiment
  transfer-toy-to-<city>` (from `ml/`)
- Eval/multi-city table (9.7): `python -m train.evaluate --cities chicago paris
  ahmedabad --checkpoint <ckpt>` (from `ml/`)

**What to do next (see BACKLOG.md)**
1. 9.1 Chicago full training (the long pole; unblocks 9.5/9.6/9.7 and Phase 8
   ONNX parity gate).
2. 9.2/Phase 6: rerun `pipeline/src/validate.py` sweep until
   `data/chicago/validation_report.json` passes (`within_25_pct ≥ 75`).
3. 9.7: regenerate `ml/results/comparison.json` for the 3 cities once Chicago
   model exists; un-ignore `ml/results/` in `.gitignore` when it is final.
4. Align `docs/TRD.md` statuses (TR-ML-01…06 + TR-ML-07 show PLANNED but code
   exists).

---

## Session 3 — 2026-09-02 (later) | TRD alignment + partial 9.7 (PR #29)

**Work done**
- `docs/TRD.md`: TR-ML-01…06 → `DONE`, TR-ML-07 → `DONE`, TR-ENG-12 →
  `DONE (infra)`; parity/p95 gate pending a trained policy. `BACKLOG.md`
  cross-cutting bullets updated to match. Committed `c0dfaf4` + pushed.
- Partial 9.7: evaluated the two trained transfer checkpoints
  (`python -m train.evaluate --cities <city> --checkpoint ...499.pt
  --episodes 20`, from `ml/`). `ml/results/comparison.json` now holds
  Paris + Ahmedabad rows (gitignored, not committed):
  - Paris: MARL −53136 vs Webster −52783 → **−0.7%**
  - Ahmedabad: MARL −61840 vs Webster −56649 → **−9.2%**
  - Both BELOW the fixed-cycle baseline → backs the 9.5 re-seed-from-real-
    Chicago-model concern. Chicago row still pending 9.1.
- Verified the C++ engine runs Paris + Ahmedabad end-to-end
  (from `Engine\Nexus_Sim\engine`: `.\engine.exe --city <city> --agents 2000
  --duration 1 --fast --no-ws`). Paris: 90 nodes/183 edges/8 zones;
  Ahmedabad: 75 nodes/144 edges/6 zones. Dashboard `CITIES` already lists both.
  Gotcha: engine resolves `../data/<city>` relative to `engine/`, not repo root.

**What to do next** (updated)
1. 9.1 Chicago full training (the long pole; unblocks 9.5/9.6/9.7, Phase 8 parity).
2. 9.7: add the Chicago row to `comparison.json` once a trained model exists;
   un-ignore `ml/results/` in `.gitignore` when the 3-city table is final.
3. 9.2/Phase 6: `validate.py` sweep until `data/chicago/validation_report.json`
   passes (`within_25_pct ≥ 75`).
4. Remove the now-stale "TRD statuses aligned" bullet in `BACKLOG.md` on the
   next docs pass.

---

## Session 1 — pre-2026-09-02 | Phase 9 infra (PR #28 / earlier)

- Prior sessions built the multi-city MARL stack: `ml/env/graph_loader.py`,
  `train.py --city`, `train/transfer.py`, `train/evaluate.py`, dashboard
  `ComparisonPanel` (9.8), CI ML-test step, MLflow file-store fix.
- Transfer seed runs from `checkpoints/toy/249.pt` completed 200 episodes for
  Paris/Ahmedabad (pre-continuation); Chicago had a short seed `0.pt`.
- TRD `TR-ML-06b` marked "DONE (train/eval infra); full Chicago run pending".