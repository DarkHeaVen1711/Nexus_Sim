# NexusSim — Session Progress Context (Sep 10, 2026) — SUPERSEDED

> **Sep 17, 2026 update:** superseded by `SESSION_PROGRESS_2026-09-11.md` and then
> `SESSION_PROGRESS_2026-09-17.md` (keep only for history). The Sep-17 file has the live state of the
> full Chicago training run (via `E:\Coding\Nexus_Sim`, not the old `E:\Project\NexusSim\Nexus_Sim` path).

> **Purpose:** Handoff document so the next session can resume exactly where this one left off.
> To resume: hand this file to the agent as context, then say "continue the training from where the progress file says."

---

## 1. Environment & Dependency Changes

### Installed today
| Package | Version | Command | Why |
|---------|---------|---------|-----|
| `mlflow` / `mlflow-skinny` | 3.16.0 | `pip install --quiet mlflow-skinny` | Training logging; was missing |
| `torch` | **2.14.0+cu126** | `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126` | Upgraded from CPU-only 2.10.0 to CUDA build (2.6GB download) |
| `torchvision` | 0.29.0+cu126 | (same command) | CUDA build |
| `torchaudio` | 2.11.0+cu126 | (same command) | CUDA build |

### GPU verified working
```
GPU: NVIDIA GeForce RTX 2050 (4GB VRAM)
torch.cuda.is_available() = True
torch.__version__ = 2.14.0+cu126
Device name: NVIDIA GeForce RTX 2050
```

### MLflow caveat (IMPORTANT)
- MLflow 3.16 **removed** file-store support (`file:///` tracking URIs now raise `MlflowException`).
- The env var `MLFLOW_ALLOW_FILE_STORE=1`/`true` **does NOT work** in v3.16 (throws `ValueError: value must be one of ['true','false','1','0']`).
- **Fix applied:** `ml/train/train.py` and `ml/train/transfer.py` now use:
  ```python
  mlflow_uri = "sqlite:///" + os.path.join(ML_DIR, "mlflow.db").replace("\\", "/")
  ```
- The SQLite db was created at `ml/mlflow.db` (committed-ignored, see git status).

---

## 2. Code Changes Made Today

All changes are in `E:\Project\NexusSim\Nexus_Sim` (this dir is its own git repo, nested inside the parent repo).

### Modified files (uncommitted)
| File | Change | Why |
|------|--------|-----|
| `ml/env/traffic_sim.py` | `neighbor_pressures()`: replaced `next(...)` generator with safe loop + fallback to 0.0 pressure | Real-city graphs have asymmetric/one-way connections where no approach points back → `StopIteration` crash on Chicago |
| `ml/env/reward.py` | `gini_coefficient()`: replaced O(n²) double Python loop with O(n log n) numpy sort-based Gini | With 3,709 zone waits, O(n²) = 13.7M Python pair ops per step → made each env step take ~0.75s (the #1 bottleneck) |
| `ml/env/nexus_sim_env.py` | Added auto-selection of `VectorizedTrafficSim` when `num_agents > 100`; added `_step_vectorized()` fast path for vectorized sim; `_observe()` now uses vectorized obs building for large graphs | Python-dict sim can't do 3,709 intersections in reasonable time |
| `ml/train/rollout.py` | `act` tensors now created with `device=device` | GPU training crash: `RuntimeError: Expected all tensors to be on the same device... index is on cpu, different from other tensors on cuda:0` |
| `ml/train/train.py` | MLflow URI → sqlite (see §1); (also supports `--device cuda` already) | File store removed in MLflow 3.16 |
| `ml/train/transfer.py` | MLflow URI → sqlite (see §1) | Same as above |
| `run.bat` | (modified — verify what changed; possibly MLflow/env related) | — |

### New files (uncommitted)
| File | Purpose |
|------|---------|
| `ml/env/vectorized_sim.py` | **`VectorizedTrafficSim`** — numpy-vectorized simulator (queues as `(N,4)` arrays, batched controller state machine, `np.add.at` travel routing, `neighbor_pressures_vec()`, `build_observations_vec()`). Auto-used when graph has >100 intersections. This is what makes full Chicago (3,709 intersections) trainable: **20s → 5.2s per episode** |
| `data/chicago_subset/graph.json` | Subset of Chicago graph (zones 1–5 → 144 intersections, 5 zones) used before vectorized sim existed |
| `ml/make_subset.py` | Helper that generated `chicago_subset` (executed with `python make_subset.py`) |
| `ml/check_cities.py` | Helper to print intersection/zone counts per city |
| `ml/results/` | Output of `evaluate.py` — `comparison.json` |

---

## 3. What Was Trained Today (Results)

**Legend:** reward is NEGATIVE (lower magnitude = better). `improvement%` = (MARL − Webster)/|Webster| × 100; positive = MARL beats Webster.

### 3.1 CPU runs (pre-vectorization, toy + piedmont + chicago_subset)
| Seed/model | Episodes | Best reward | Checkpoint |
|-----------|----------|-------------|------------|
| toy | 200 | -10,997 | `ml/checkpoints/toy/199.pt` |
| piedmont | 500 | -25,655 | `ml/checkpoints/piedmont/499.pt` |
| chicago_subset | 400 (199 + 201 resume) | -124,219 | `ml/checkpoints/chicago_subset/399.pt` |

### 3.2 Transfer learning (CPU)
| Transfer | Episodes | Result |
|----------|----------|--------|
| piedmont → toy | 200 | `ml/checkpoints/piedmont_to_toy/199.pt` (weights transferred, obs_dim=11 matched) |
| chicago_subset → piedmont | 200 | `ml/checkpoints/chicago_subset_to_piedmont/199.pt` (weights transferred) |

### 3.3 Multi-city evaluation (Task 9.7) — chicago_subset/399.pt
| City | Webster | MARL | Improvement |
|------|---------|------|-------------|
| toy | -11,269.8 | -6,857.8 | **+39.1%** |
| piedmont | -26,606.2 | -26,190.7 | **+1.6%** |
| chicago_subset | -124,461.4 | -127,671.6 | -2.6% |

### 3.4 Full Chicago GPU run — INCOMPLETE (ready to resume)
- **Started:** 200 episodes, 100 steps, `--device cuda`
- **Crash at 1st PPO update** — device mismatch (`act` on CPU, obs on GPU). **FIXED** in `rollout.py` (see §2).
- **Verified working after fix:** a smoke test ran `collect_episode` + `compute_gae` + `ppo_update` end-to-end on GPU with a 3,709-intersection trajectory — **no error, passed silently**.
- **Chicago baseline computed:** `Fixed-cycle baseline: reward=-14,331.1 pressure=-4.86 equity=-138.4 gini=0.279`
- **NO checkpoints in `ml/checkpoints/chicago/` yet** (crash happened before first checkpoint save).

### Checkpoints on disk (all dirs)
```
ml/checkpoints/
├── toy/           3, 51, 103, 151, 199.pt
├── piedmont/      3, 103, 203, 303, 403, 499.pt
├── chicago_subset/  3, 51, 103, 151, 199, 203, 251, 303, 351, 399.pt
├── piedmont_to_toy/         0, 50, 100, 150, 199.pt
├── chicago_subset_to_piedmont/  0, 50, 100, 150, 199.pt
└── chicago/       (EMPTY — training did not save any yet)
```

---

## 4. Dashboard / Browser Status

- Dashboard (Vite dev server) runs with: `cd E:\Project\NexusSim\Nexus_Sim\dashboard && npx vite --port 3000`
- Was started at `http://localhost:3000` (port 5173 may be in TIME_WAIT from earlier attempts; port 3000 works).
- The dashboard reads `/results/comparison.json`-style data for the MARL comparison panel (Phase 9.8). After training + running `train.evaluate`, the comparison table refreshes.

---

## 5. NEXT STEPS — Resume Point (exact commands)

> Start here tomorrow. The GPU fix is already applied.

### Step 1 — Launch full Chicago training on GPU (the task that was in progress)
```bash
cd E:\Project\NexusSim\Nexus_Sim\ml
python -m train.train --city chicago --episodes 200 --checkpoint-interval 50 ^
    --log-interval 5 --episodes-per-update 4 --device cuda --episode-steps 100
```
- Expected: ~5.2s/episode sim + PPO → ~200 episodes ≈ 20–40 min.
- Saves checkpoints to `ml/checkpoints/chicago/{3,51,103,151,199}.pt`.
- If you want to extend beyond 200: resume with `--resume latest` and a higher `--episodes`.

### Step 2 — Multi-city evaluation (Task 9.7 comparison table)
```bash
python -m train.evaluate --cities toy piedmont chicago --checkpoint checkpoints/chicago/199.pt --episodes 20
```
This writes `ml/results/comparison.json` → feeds the dashboard's side-by-side table (9.7/9.8).

### Step 3 — Transfer learning (Tasks 9.3–9.5) using the real Chicago checkpoint
```bash
# Chicago → piedmont (source is now the real trained Chicago policy)
python -m train.transfer --source chicago --target piedmont --episodes 200 --lr 1e-4

# Chicago → toy
python -m train.transfer --source chicago --target toy --episodes 200 --lr 1e-4
```
- Weights transfer directly when `obs_dim` matches (all cities are 11 — they will match).
- Outputs go to `ml/checkpoints/chicago_to_piedmont/` and `ml/checkpoints/chicago_to_toy/`.

### Step 4 — Validate transfers + regenerate comparison table
```bash
python -m train.evaluate --cities toy piedmont chicago --checkpoint checkpoints/chicago_to_toy/199.pt --episodes 20
```

### Step 5 — Dashboard verification (9.7 checkpoint, Integration Lead = Dev D)
- Keep Vite running on port 3000 → open `http://localhost:3000`.
- Verify the MARL-vs-Webster comparison table renders side-by-side.

---

## 6. Known Issues / Gotchas

1. **Never rerun `pip install torch ... --index-url .../cu126`** — it re-downloads the 2.6GB wheel. Torch is already CUDA-enabled.
2. **MLflow file store is dead** in v3.16 — always use the sqlite URI (already patched). Don't "fix" it back.
3. **Chicago full graph = 3,709 intersections** — do NOT train it with the old dict-based `TrafficSim`; it takes hours. The `VectorizedTrafficSim` auto-activates for >100 intersections. Keep that threshold.
4. **Dashboard port:** use `--port 3000`; 5173 had lingering TIME_WAIT sockets.
5. `git status` shows `Nexus_Sim` modified at the OUTER repo (`E:\Project\NexusSim`) because it's a nested repo (not submodule). Do all git work **inside** `E:\Project\NexusSim\Nexus_Sim`.
6. Changes are **NOT committed** — remember to commit today's work (train.py, transfer.py, rollout.py, reward.py, traffic_sim.py, nexus_sim_env.py, vectorized_sim.py, data/chicago_subset/, make_subset.py, check_cities.py) when the team is ready.

---

## 7. Files touched today (for PR/commit grouping)

| Group | Files | PR scope |
|-------|-------|----------|
| GPU training fix | `ml/train/rollout.py` | Phase 9 |
| Vectorized sim | `ml/env/vectorized_sim.py` (new), `ml/env/nexus_sim_env.py` | Phase 9 (enables Chicago) |
| Performance fixes | `ml/env/reward.py`, `ml/env/traffic_sim.py` | Phase 9 |
| MLflow migration | `ml/train/train.py`, `ml/train/transfer.py` | Phase 9 |
| Data | `data/chicago_subset/` (new), `ml/make_subset.py`, `ml/check_cities.py` | Phase 9 (subset now optional) |
| Results | `ml/results/comparison.json` | Phase 9.7 |

---

*Generated: 2026-09-10. Ready to resume at §5 Step 1.*