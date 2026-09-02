# Phase 9 Backlog — Multi-City Training & Validation

Status snapshot: **2026-09-02** (after resuming Paris/Ahmedabad transfers and
landing resume + completion-meter support).

Scope per `TEAM_IMPLEMENTATION_PLAN.md` §4.2 (Phase 9, 1.5 weeks), split across
two parallel pairs:

| Pair | Focus | Tasks |
|------|-------|-------|
| Pair 1 (Dev A + B) | Chicago training + validation | 9.1, 9.2, 9.7, 9.8 |
| Pair 2 (Dev C + D) | Paris + Ahmedabad transfer | 9.3, 9.4, 9.5, 9.6 |

**Acceptance (TRD §9 milestone M9):** MARL-vs-Webster table across 3 cities in
`ml/results/comparison.json` rendered by dashboard `ComparisonPanel`;
`ml/tests` green in CI. (G4, FR-8, TR-ML-06b)

---

## Status summary

| Task | Status | Evidence / notes |
|------|--------|------------------|
| 9.1 Full Chicago training (2000–5000 ep) | **PENDING** | Only `ml/checkpoints/chicago/0.pt`; ~20 s/step on this machine so it is an overnight/multi-day run. Infra finished (see below). |
| 9.2 Chicago validation | **PARTIAL** | `data/chicago/validation_report.json` (2026-08-03) `passes_checkpoint: false` — MAPE 21.6% (≤25 OK), within-25% **63.6%** (< 75% target). Needs recalibration/demand sweep. |
| 9.3 Paris transfer | DONE | `ml/checkpoints/249_to_paris/499.pt`; run `231163547…` FINISHED (200→500 ep). |
| 9.4 Ahmedabad transfer | DONE | `ml/checkpoints/249_to_ahmedabad/499.pt`; run `097495c1…` FINISHED (200→500 ep). |
| 9.5 Transfer from **final Chicago** model | **PENDING** | Plan seeds transfers from the completed Chicago checkpoint; current runs used `toy/249.pt`. Blocked on 9.1. |
| 9.6 Transfer sensitivity sweep (`--chaos` / `--demand-scale`) + doc | **PENDING** | No Paris/Ahmedabad `validation_report.json`; no sensitivity write-up. |
| 9.7 MARL-vs-Webster across 3 cities → `ml/results/comparison.json` | **PENDING** | Current file only has toy + piedmont rows; target cities missing (needs a trained Chicago ckpt to be meaningful). |
| 9.8 Dashboard `ComparisonPanel` + `/comparison.json` proxy | DONE | `dashboard/src/components/ComparisonPanel.tsx`, `dashboard/vite.config.ts`; PR #29 `c8c28ea`. |
| `ml/tests` green | DONE | 78 passed locally; ML pytest step present in `ci.yml`. |

---

## Completed this cycle (2026-09-02)

- **Resume support for transfers** — `ml/train/transfer.py` gained
  `--resume {latest|<path>}`: restores policy/value/optimizer state, continues
  from the last checkpoint, stores `reward_scale` in checkpoints for scale
  continuity, and logs a `resumed_from` param.
- **Completion meter** — `train.py` and `transfer.py` progress bars now key off
  the full episode budget (`total=…, initial=start_ep`), so a resumed run shows
  overall % complete (e.g. `40%|████| 200/500 … complete=40.0%`) instead of
  only the remaining episodes. Both print a completion summary on finish.
- **Transfers advanced 200 → 500 episodes** — Paris resumed from `199.pt`
  (`250…499.pt` written; final reward −51964.7 vs baseline −52783), Ahmedabad
  resumed from `199.pt` (`250…499.pt` written; final reward −60088.2).
- **Chicago resume smoke-test** — `train.py --city chicago --resume latest`
  verified; temporary ckpts cleaned up (dir back to `0.pt` only).
- **Tests extended** — `ml/tests/test_transfer_evaluate.py` +7 tests
  (`_resolve_resume`, resume ckpt roundtrip); full `ml/tests` suite green.

---

## Pending backlog

### 9.1 — Full Chicago graph training
Train MAPPO on the real Chicago graph (3709 intersections, 77 zones) to the
planned 2000–5000 episode budget, resuming from the existing seed:

```
cd ml
..\.venv\Scripts\python.exe -m train.train --city chicago ^
    --episodes 2000 --resume latest ^
    --checkpoint-interval 500 --log-interval 10 --baseline-episodes 10
```

Unblocks 9.5, 9.6, 9.7. **Blocker:** no dedicated GPU; ~20 s/step CPU.

### 9.2 — Chicago validation
`data/chicago/validation_report.json` fails acceptance (within-25% 63.6% < 75%).
Recalibrate `--demand-scale` / `speed_factor` sweep; re-run and get
`passes_checkpoint: true`.

### 9.5 — Retrain transfers from the finished Chicago model
Re-run `ml/train/transfer.py` seeding Paris/Ahmedabad from
`ml/checkpoints/chicago/<final>.pt` (obs_dim permitting) so the pipelines match
the plan. Blocked on 9.1.

### 9.6 — Transfer sensitivity sweep + documentation
`validate.py` sweep over the engine's `--chaos` lane-discipline coefficient
(TR-ENG-03) and `--demand-scale` (TR-PIPE-06) for the transferred models; write
up sensitivity in `docs/RL_DOCUMENTATION.md`.

### 9.7 — Comparison table across the 3 target cities
Regenerate `ml/results/comparison.json` once trained checkpoints exist:

```
cd ml
..\.venv\Scripts\python.exe -m train.evaluate ^
    --cities chicago paris ahmedabad ^
    --checkpoint ../ml/checkpoints/<city>/<final>.pt
```

Dashboard `ComparisonPanel` already renders whatever this file contains.

---

## Rollback / restart notes

- Dead/interrupted runs look like `mappo-chicago` run `2eb4b368…`:
  MLflow `status=1 RUNNING` with `end_time: null` and no live process. Restart
  with `--resume latest` (never delete checkpoints).
- `ml/checkpoints/` and `ml/mlruns/` are gitignored; `ml/results/comparison.json`
  is a tracked deliverable but currently stale (toy/piedmont only).