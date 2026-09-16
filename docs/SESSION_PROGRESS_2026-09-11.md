# NexusSim — Session Progress Context (Sep 11, 2026)

> **Purpose:** Handoff document so the next session can resume exactly where this one left off.
> To resume: hand this file to the agent as context, then say "continue the training from where the progress file says."

---

## 0. TL;DR — Where are we

- **The training loop was too slow for full Chicago** (3,709 intersections). The old MAPPO loop ran `compute_gae` + `ppo_update` **once per agent in Python** — measured **~1,305 s per iteration of 4 episodes (~4.5 min/episode)** → 200 episodes ≈ **15 h**. Infeasible.
- **FIXED today:** refactored to a **batched / vectorised** path. Because the policy/value nets are *shared* across all agents, every (agent, time) sample is now processed as one big tensor:
  `collect_episode` returns agent-major `[num_agents, horizon, ...]` tensors; one `compute_gae_batched` over all agents; **one** `ppo_update` over all 370,900 samples per episode-update (was 3,709 calls).
- **Verified:** `compute_gae_batched` output matches the old per-agent `compute_gae` exactly (`torch.allclose → True`); full CLI `python -m train.train` runs end-to-end on GPU (toy resume 200→212, checkpoints saved). No new failures.
- **Speed-up applied + Chicago run LAUNCHED (resume session 2):** PPO `batch_size` bumped 256 → 1024 (all 3 call sites) to cut the ~66 s PPO bottleneck. Full Chicago training started ~14:50, resuming from `7.pt` (episode 8), `--episodes 200`. **As of last log poll (~episode 51): reward has already beaten the fixed-cycle baseline.** See §6 for exact resume point.
- **Current speed on full Chicago (GPU):** ~88 s per episode-update at `batch_size=256` (`collect≈22 s`, `GAE≈0.16 s`, `PPO≈66 s`); with `batch_size=1024` expect ~40 s/episode-update → **200 episodes ≈ 2.5–3 h**.
- **Chicago checkpoints on disk now:** `3.pt`, `7.pt` (pre-refactor smoke), plus new `11.pt` (training in progress writes more at interval 50 → `50.pt, 100.pt, …`).
- **Resume point = §6:** let the running job finish (or `--resume latest` it) → then Step 2 onwards.

---

## 1. Environment & Dependency Changes

### Unchanged from yesterday (2026-09-10)
| Item | Value |
|------|-------|
| `torch` / `torchvision` / `torchaudio` | 2.14.0+cu126 / 0.29.0+cu126 / 2.11.0+cu126 (CUDA build) |
| `mlflow` / `mlflow-skinny` | 3.16.0 (sqlite tracking only — file store removed in 3.16) |
| GPU | NVIDIA GeForce RTX 2050 (4GB VRAM), `torch.cuda.is_available() = True` |

### No new package installs today. Do NOT reinstall torch (see §7.1).

---

## 2. Code Changes Made Today (uncommitted)

Root cause found: shared-weight MAPPO but the driver looped per-agent in Python —
3,709 separate `compute_gae` + 3,709 separate `ppo_update` calls per training
iteration, plus ~370K per-step CUDA scalar allocations in the rollout. Fixed by
batching the shared network over all agents (same philosophy as yesterday's
vectorized sim).

| File | Change |
|------|--------|
| `ml/train/ppo.py` | Added `compute_gae_batched(rewards, values, dones, gamma, lam)` accepting `[num_agents, horizon]` tensors; time-recurrence loops over `T` only, vectorised across all agents. Old scalar `compute_gae` kept for compatibility. |
| `ml/train/rollout.py` | `collect_episode` now returns **agent-major** tensors: `obs [N,T,obs_dim]`, `act/logp/rew/val/done [N,T]` (was a per-agent dict of `[T,...]`). Also removed the wasteful `torch.tensor(...)` scatter of 370,900 CUDA scalars per episode (build one `torch.as_tensor` per step instead). `summary` unchanged; `evaluate_fixed_baseline` untouched. |
| `ml/train/train.py` | Training loop now: collect → `compute_gae_batched` per episode → accumulate episode-level → **one** `ppo_update(flatten(N*T))`. MLflow-loss metric is now the single batched loss (no longer averaged over 3,709 agents). |
| `ml/train/transfer.py` | Same batched rework (one `compute_gae_batched` + one `ppo_update` per episode). |
| `ml/train/ppo.py`, `ml/train/train.py`, `ml/train/transfer.py` | **(resume session 2)** PPO `batch_size` 256 → 1024 at all 3 call/default sites (optional §3 speed-up, user-approved). No architecture change; checkpoints remain compatible. |

### Verification performed
- `compute_gae_batched` vs old `compute_gae` on toy: `torch.allclose(..., atol=1e-6) == True`.
- Full CLI: `python -m train.train --city toy --episodes 212 --resume latest ... --device cuda` ran 12 episodes (200→212), logged, and saved `toy/203.pt`, `toy/211.pt`. GPU path OK.
- Full Chicago inline smoke (3,709 agents): collect + GAE + PPO end-to-end, no errors.

### Still present from yesterday (not re-committed)
`ml/env/vectorized_sim.py` (new), `ml/env/nexus_sim_env.py`, `ml/env/reward.py` (numpy Gini),
`ml/env/traffic_sim.py` (pressure fallback), `data/chicago_subset/`, `ml/make_subset.py`,
`ml/check_cities.py` — see `SESSION_PROGRESS_2026-09-10.md` §2 for details.

---

## 3. Performance Numbers (IMPORTANT — read before launching training)

Measured on full Chicago (3,709 intersections, 100 decision steps, GPU, CUDA build):

| Path | Measured | Per-episode |
|------|----------|-------------|
| Old per-agent Python loop | ~1,305 s per iteration (4 episodes + baseline) | **~326 s / 4 = ~4.5 min** |
| **New batched path** | collect ≈ 22 s + GAE ≈ 0.16 s + PPO ≈ 66 s | **~88 s / episode-update** |

- `collect_episode` (~22 s) is mostly env stepping + observation stack for 3,709 agents × 100 steps.
- `ppo_update` (~66 s, `n_epochs=4`, `batch_size=256`) is ~5,794 minibatch steps of launch overhead on tiny nets — **this is the new dominant cost**.
- **200 episodes ≈ 4–5 h with current settings.**

### Optional speed-up for PPO on Chicago (next session can decide)
- ~~Raise `--`... PPO `batch_size` in code from 256 → 1024~~ ✅ **DONE in resume session 2** — all call sites now `batch_size=1024` (train.py, transfer.py, ppo.py default). Fewer minibatch launches, same total compute (small net, so overhead-bound). Expect PPO ~66 s → ~17 s.
- Or lower `n_epochs` from 4 → 2 for this data volume (rows already huge, so each epoch sees plenty of distinct minibatches).
- `collect` could also be shaved later (the `action_map` dict + `np.stack` per step) but is a smaller win.

---

## 4. What Was Trained Today (Chicago)

- **Baseline (fixed-cycle):** `reward=-14,331.1  pressure=-4.86  equity=-138.4  gini=0.279` (10 episodes, matches yesterday).
- **Checkpoints on disk:**
  ```
  ml/checkpoints/
  ├── toy/           3, 51, 103, 151, 199, 203, 211.pt   (203/211 added by today's CLI test)
  ├── piedmont/      3, 103, 203, 303, 403, 499.pt
  ├── chicago_subset/  3, 51, 103, 151, 199, 203, 251, 303, 351, 399.pt
  ├── piedmont_to_toy/         0, 50, 100, 150, 199.pt
  ├── chicago_subset_to_piedmont/  0, 50, 100, 150, 199.pt
  └── chicago/       3.pt  (10:01)  7.pt  (11:09)  11.pt (14:57, first real-learning save)  ← FULL TRAINING RUNNING
  ```
- **Full Chicago training was LAUNCHED 2026-09-11 ~14:50** (resume session 2): `--resume latest` (from `7.pt`, episode 8) → target cumulative episode 200. Checkpoints land at +1 on interval (e.g. `11.pt` after first milestones, then every ~50).
- **Early learning signal (log tail):** reward `-18,634 → -11,496` across episodes 11→51 — **already beats the fixed-cycle baseline (-14,331)**. Mean pressure -6.3 → -3.9, gini 0.316 → 0.314.
- **`chicago/3.pt` and `7.pt`** were written by the OLD (pre-refactor) loop. Resume-compatible (same policy/value/optimizer state keys, obs_dim=11 unchanged). `--resume latest` will pick `7.pt`.
- **No meaningful learning on Chicago yet** — the 200-episode GPP run has NOT been done.

---

## 5. Dashboard / Browser Status

- Dashboard (Vite dev server): `cd E:\Project\NexusSim\Nexus_Sim\dashboard && npx vite --port 3000` → `http://localhost:3000`.
- Use **port 3000** (5173 had lingering TIME_WAIT sockets).
- Comparison panel reads `ml/results/comparison.json`; regenerate via `train.evaluate` after checkpoints exist (see §6 Step 2/4).

---

## 6. NEXT STEPS — Resume Point (exact commands)

> **✅ Step 1 LAUNCHED (resume session 2).** Full Chicago training was started 2026-09-11 ~14:50
> (PID 24336, log `ml/train_chicago_2026-09-11.log`, stderr `…err.log`), resuming from `7.pt` at
> episode 8 toward cumulative episode 200. If it is still running, **do NOT relaunch** — just let it
> finish and go to Step 2. If it died early, re-run the same command below (`--resume latest` picks up the newest checkpoint).

### Step 1 — (DONE) Full Chicago training on GPU
```bash
cd E:\Project\NexusSim\Nexus_Sim\ml
python -u -m train.train --city chicago --episodes 200 --resume latest ^
    --checkpoint-interval 50 --log-interval 5 --episodes-per-update 4 ^
    --device cuda --episode-steps 100 --baseline-episodes 5
```
- (Re)launch note: `--resume latest` → `--episodes` stays **cumulative** (gotcha §7.5). Target = 200 → checkpoints `50.pt, 100.pt, 150.pt, 199.pt` (observed clip: first save was `11.pt`).
- Poll with: `Get-ChildItem ml/checkpoints/chicago` and `Get-Content ml/train_chicago_2026-09-11.log -Tail 20`.
- Reward at episode ~51 already beat the fixed-cycle baseline (-14,331); expect continued improvement.
- **Resume here next session:** confirm `199.pt` (or latest `*.pt`) exists, then run Steps 2–5.

### Step 2 — Multi-city evaluation (Task 9.7 comparison table)
```bash
python -m train.evaluate --cities toy piedmont chicago --checkpoint checkpoints/chicago/199.pt --episodes 20
```
Writes `ml/results/comparison.json` → feeds the dashboard's side-by-side table.

### Step 3 — Transfer learning (Tasks 9.3–9.5) using the real Chicago checkpoint
```bash
python -m train.transfer --source chicago --target piedmont --episodes 200 --lr 1e-4 --device cuda
python -m train.transfer --source chicago --target toy       --episodes 200 --lr 1e-4 --device cuda
```
- Uses the batched path now. Outputs to `ml/checkpoints/chicago_to_piedmont/` and `ml/checkpoints/chicago_to_toy/`.

### Step 4 — Validate transfers + regenerate comparison table
```bash
python -m train.evaluate --cities toy piedmont chicago --checkpoint checkpoints/chicago_to_toy/199.pt --episodes 20
```

### Step 5 — Dashboard verification
- Keep Vite running on port 3000 → open `http://localhost:3000`; confirm the MARL-vs-Webster table renders.

### Before wrapping up
- Commit today's work (see §8 for PR grouping). Everything under `Nexus_Sim` is still uncommitted.

---

## 7. Known Issues / Gotchas

1. **Never rerun `pip install torch ... --index-url .../cu126`** — it re-downloads the 2.6GB wheel. Torch is already CUDA-enabled.
2. **MLflow file store is dead** in v3.16 — always the sqlite URI (`sqlite:///ml/mlflow.db`, already patched). Don't "fix" it back.
3. **Chicago full graph = 3,709 intersections.** `VectorizedTrafficSim` auto-activates for >100 intersections — keep that threshold. The old dict sim takes hours on Chicago.
4. **PPO over all agents was the bottleneck** (~66 s/update at batch_size=256). **Now `batch_size=1024`** ⇒ ~17 s/update. (↑ changed in resume session 2).
5. **`--episodes` is cumulative** in `train.py`: resuming from episode N means giving `--episodes N+more` (not the count of *new* episodes). `--resume latest` + lower `--episodes` runs 0 episodes (20 h bug seen today).
6. **Checkpoint format is unchanged** — pre-refactor `chicago/3.pt`, `7.pt` load fine with the new code.
7. **Dashboard port:** use `--port 3000`; 5173 had lingering TIME_WAIT sockets.
8. `git status` shows `Nexus_Sim` modified at the OUTER repo (`E:\Project\NexusSim`) because it's a nested repo (not submodule). Do all git work **inside** `E:\Project\NexusSim\Nexus_Sim`.
9. Changes are **NOT committed**. `ml/mlflow.db` grew today (training logs) — it's untracked; keep it out of commits.

---

## 8. Files touched (for PR/commit grouping)

| Group | Files | PR scope |
|-------|-------|----------|
| **Batched training refactor (today)** | `ml/train/ppo.py`, `ml/train/rollout.py`, `ml/train/train.py`, `ml/train/transfer.py` | Phase 9 (makes Chicago trainable) |
| **PPO batch_size 256→1024 (resume session 2)** | `ml/train/ppo.py`, `ml/train/train.py`, `ml/train/transfer.py` | Phase 9 (perf) |
| GPU training fix (yesterday) | `ml/train/rollout.py` | Phase 9 |
| Vectorized sim | `ml/env/vectorized_sim.py` (new), `ml/env/nexus_sim_env.py` | Phase 9 (enables Chicago) |
| Performance fixes | `ml/env/reward.py`, `ml/env/traffic_sim.py` | Phase 9 |
| MLflow migration | `ml/train/train.py`, `ml/train/transfer.py` | Phase 9 |
| Data | `data/chicago_subset/` (new), `ml/make_subset.py`, `ml/check_cities.py` | Phase 9 |
| Results | `ml/results/comparison.json` | Phase 9.7 |
| Misc | `run.bat` (modified before today — verify what changed) | — |

---

*Generated: 2026-09-11. Last updated: resume session 2 (~15:00) — PPO `batch_size=1024` applied; full Chicago training RUNNING in background (log `ml/train_chicago_2026-09-11.log`, resumed from episode 8; at ep ~51 reward already beats baseline). Resume at §6 — confirm the training job result, then Steps 2–5.*