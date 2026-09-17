# NexusSim — Session Progress Context (Sep 17, 2026)

> **Purpose:** Latest handoff document. Earlier files `SESSION_PROGRESS_2026-09-10.md` and
> `SESSION_PROGRESS_2026-09-11.md` are kept for history but superseded by this one.

---

## 0. TL;DR — Where are we

- Vatsal (Dev B, ML) re-launched **full Chicago training today (2026-09-17)** while working in this repo.
  It resumes from `ml/checkpoints/chicago/0.pt` toward a **cumulative 200 episodes** on the batched /
  vectorised path (`batch_size=1024`, one GAE + one PPO update per episode).
- **It is STILL RUNNING.** Last poll 22:09 was at **episode 89/200 (~44%)**, ~38.5 s/ep, ETA ~1 h 10 m
  (≈ 200 episodes ≈ **2.2 h wall**, not the ~40 min the older docs estimated — see §6).
- **Reward already beats the fixed-cycle baseline:** episode ~85 reward `-11,122.6` vs baseline
  `-13,973.97` (≈ **+20%**). Logs: `ml/train_chicago_2026-09-17.{log,err.log}`.
- **Checkpoints on disk today:** `chicago/4.pt` (21:14), `chicago/52.pt` (21:47); `0.pt` is from 01-Sep.
  Next saves: `100.pt`, `150.pt`, `199.pt`.
- **Task 9.7 still PENDING:** `ml/results/comparison.json` has only `toy`, `piedmont`, `chicago_subset`
  rows — **no Chicago row yet**. Transfers (9.5) and validation (9.2) also pending.
- Resume here = §5 (confirm `199.pt`, then run steps 2–5).

---

## 1. Environment & Dependency Changes

Unchanged from 2026-09-11 (`SESSION_PROGRESS_2026-09-11.md` §1):

| Item | Value |
|------|-------|
| `torch` / `torchvision` / `torchaudio` | 2.14.0+cu126 / 0.29.0+cu126 / 2.11.0+cu126 (CUDA build) |
| `mlflow` | 3.16.0, sqlite-only tracking (`sqlite:///ml/mlflow.db`) |
| GPU | NVIDIA GeForce RTX 2050 (4 GB VRAM), `torch.cuda.is_available() == True` |

- No new package installs. Do **NOT** reinstall torch (2.6 GB wheel) — see §6.1.

---

## 2. Code / Git State

- The Sep-11 batched-PPO refactor (`compute_gae_batched`, agent-major rollout tensors, one batched
  `ppo_update`), the PPO `batch_size` 256→1024 change, the vectorized sim, MLflow sqlite migration and
  the chicago subset data are all **COMMITTED and MERGED** (`a86996d` "Merge ... (Vatsal: vectorized sim
  + PPO training)"). `git status` is **clean**.
- Note: the Sep-11 session doc's "changes NOT committed" statements are now stale.

---

## 3. Test Run Record (today's run)

| Item | Value |
|------|-------|
| Launched | 2026-09-17 21:08:59, PID 16536 |
| Command | `.venv\Scripts\python.exe -u -m train.train --city chicago --episodes 200 --resume latest --checkpoint-interval 50 --log-interval 5 --episodes-per-update 4 --device cuda --episode-steps 100 --baseline-episodes 5` |
| Logs | `ml/train_chicago_2026-09-17.log` (stdout), `ml/train_chicago_2026-09-17.err.log` (tqdm progress) |
| Model loaded | `E:\Coding\Nexus_Sim\ml\checkpoints\chicago\0.pt` − resumed as episode 1/200 (cumulative) |
| Baseline (fixed-cycle) | reward `-13,973.97`, pressure `-4.76`, equity `-134.98`, gini `0.286` |
| Progress (22:09) | episode 89/200, ~38.5 s/ep, reward `-11,122.6`, pressure `-3.84`, gini `0.318` |

Reward trend this run: `-17,596` (ep ~5) → `-14,485` (ep ~25) → `-12,476` (ep ~45) → `-11,122` (ep ~85).

### Checkpoints on disk (`ml/checkpoints/`)

```
chicago/       0.pt (01-Sep)  4.pt (today 21:14)  52.pt (today 21:47)   ← TRAINING RUNNING
chicago_subset_to_piedmont/   (none now)
piedmont_to_toy/              (none now)
249_to_paris/     0 … 499.pt
249_to_ahmedabad/ 0 … 499.pt
toy/             0 … 400.pt
piedmont/        3 … 99.pt
249_to_chicago/  (none)
```

- The Sep-11 run's `chicago/3.pt / 7.pt / 11.pt` are **no longer on disk** — that run was abandoned and
  today's run restarted from `0.pt`.

---

## 4. Phase 9 status board

| Task | Status (2026-09-17) |
|------|---------------------|
| 9.1 Chicago full training | **IN PROGRESS** — first 200-ep run live; ~44% through, already ~+20% over baseline |
| 9.2 Chicago validation re-run | Pending — needs finished `chicago/199.pt` |
| 9.5 Re-seed Paris/Ahmedabad transfers | Pending — re-run `transfer` once `199.pt` exists |
| 9.6 Transfer sensitivity sweep | Pending |
| 9.7 Chicago row in `comparison.json` | **PENDING** — file still has only toy / piedmont / chicago_subset |

---

## 5. NEXT STEPS — Resume Point

> Confirm whether the run is done first. **Do NOT relaunch while PID is alive.**
> Poll: `Get-ChildItem ml/checkpoints/chicago` and `Get-Content ml\train_chicago_2026-09-17.err.log -Tail 5`.
> If PID 16536 is gone and logs stopped, treat it as dead → relaunch with §5.0.

### Step 5.0 — Re-launch (only if the job died early)
```bash
cd E:\Coding\Nexus_Sim\ml
python -u -m train.train --city chicago --episodes 200 --resume latest ^
    --checkpoint-interval 50 --log-interval 5 --episodes-per-update 4 ^
    --device cuda --episode-steps 100 --baseline-episodes 5
```
- `--episodes` is cumulative (`--resume latest` picks `52.pt` → target 200; giving a smaller number runs ~0 episodes).

### Step 1 — Confirm `chicago/199.pt` exists, then multi-city evaluation (Task 9.7)
```bash
python -m train.evaluate --cities toy piedmont chicago --checkpoint checkpoints/chicago/199.pt --episodes 20
```
- Writes `ml/results/comparison.json` → adds the **Chicago** row → feeds the dashboard's `ComparisonPanel`.

### Step 2 — Transfer learning (Tasks 9.3–9.5) using the real Chicago checkpoint
```bash
python -m train.transfer --source chicago --target piedmont --episodes 200 --lr 1e-4 --device cuda
python -m train.transfer --source chicago --target toy       --episodes 200 --lr 1e-4 --device cuda
```
- Outputs to `ml/checkpoints/chicago_to_piedmont/` and `ml/checkpoints/chicago_to_toy/`.

### Step 3 — Validate transfers + regenerate comparison table
```bash
python -m train.evaluate --cities toy piedmont chicago --checkpoint checkpoints/chicago_to_toy/199.pt --episodes 20
```

### Step 4 — Dashboard verification
- `cd dashboard && npx vite --port 3000` → `http://localhost:3000` → confirm MARL-vs-Webster table + Chicago row.

---

## 6. Known Issues / Gotchas (updated)

1. **Never rerun `pip install torch ... --index-url .../cu126`** — re-downloads the 2.6 GB wheel.
2. **MLflow file store is dead in 3.16** — always the sqlite URI (already patched).
3. **Chicago = 3,709 intersections.** `VectorizedTrafficSim` auto-activates for >100 intersections; keep the threshold.
4. **`--episodes` is cumulative** in `train.py` — resume with `--episodes <cumulative target>`, not "more episodes".
5. **Real throughput ≠ the old estimate.** Sep-11 doc predicted ~17 s/update / ~40 s per episode by
   raising `batch_size` to 1024; measured reality is **~38.5 s/ep** (PPO got faster, but collect +
   per-step launch overhead dominates). Budget ~2.2 h for 200 episodes, not ~40 min.
6. **Repo path changed.** Older session docs say `E:\Project\NexusSim\Nexus_Sim`; the live repo is
   **`E:\Coding\Nexus_Sim`**.
7. **Dashboard port:** use `--port 3000` (5173 had lingering TIME_WAIT sockets).
8. `ml/mlflow.db` and training logs are untracked / gitignored — keep them out of commits.

---

## 7. Files touched / produced (this session)

| Item | Path |
|------|------|
| Training logs | `ml/train_chicago_2026-09-17.log`, `ml/train_chicago_2026-09-17.err.log` |
| Checkpoints | `ml/checkpoints/chicago/{0,4,52}.pt` |
| Results | `ml/results/comparison.json` (toy / piedmont / chicago_subset only — Chicago pending) |

---

*Generated: 2026-09-17 ~22:10. Full Chicago training RUNNING (PID 16536, ep 89/200, reward ≈ -11.1k vs
baseline -13,974). Resume at §5: wait for `199.pt`, then evaluate (9.7), transfer (9.5), validate, dashboard.*