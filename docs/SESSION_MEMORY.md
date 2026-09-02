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

## Session 2 — 2026-09-02 | Phase 9 continuation plumbing (PR #29)

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

## Session 1 — pre-2026-09-02 | Phase 9 infra (PR #28 / earlier)

- Prior sessions built the multi-city MARL stack: `ml/env/graph_loader.py`,
  `train.py --city`, `train/transfer.py`, `train/evaluate.py`, dashboard
  `ComparisonPanel` (9.8), CI ML-test step, MLflow file-store fix.
- Transfer seed runs from `checkpoints/toy/249.pt` completed 200 episodes for
  Paris/Ahmedabad (pre-continuation); Chicago had a short seed `0.pt`.
- TRD `TR-ML-06b` marked "DONE (train/eval infra); full Chicago run pending".