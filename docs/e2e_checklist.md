# End-to-End Smoke Checklist

**Plan reference:** Phase 4.8 — *"Checklist committed; run before every phase-end."*

Run this top to bottom before closing any phase. It walks the full chain —
pipeline → engine → dashboard — and is designed to catch integration breakage
that unit tests miss, because every layer here is exercised against the layer
it actually talks to.

Tick every box. If a step fails, stop and fix it before continuing: later steps
assume earlier ones passed.

---

## 0. Preconditions

- [ ] Working tree builds clean: `cd engine/build && cmake --build .`
- [ ] C++ unit tests pass: `ctest --output-on-failure` (from `engine/build`)
- [ ] Python tests pass: `cd pipeline && python -m pytest tests/ -q`
- [ ] Dashboard tests pass: `cd dashboard && npm run test`

> On Windows/MinGW the test binary needs the compiler's runtime DLLs on `PATH`.
> If `engine_test.exe` exits immediately with no output, that is the cause —
> run it through `ctest`, which sets the environment up correctly.

---

## 1. Pipeline — data preparation

Only needed when the city's data is missing or its config changed.

- [ ] `pipeline/cities.yaml` contains the city (this is the **only** config file
      the pipeline reads; the root `cities.yaml` is a pointer stub)
- [ ] `python src/download.py --city <city>` → `data/<city>/raw.graphml`
- [ ] `python src/clean.py --city <city>` → `cleaned.graphml`, node count drops
      (disconnected fragments removed)
- [ ] `python src/lanes.py --city <city>` → `lanes.graphml`
- [ ] `python src/zones.py --city <city>` → `zones.graphml`
- [ ] `python src/export.py --city <city>` → `data/<city>/graph.json`
- [ ] `graph.json` sanity: non-zero `nodes` and `edges`, and more than one
      distinct `zone_id`

### 1a. OD demand — pick the branch matching the city's `od_source.type`

**`socrata`** (real measured feed — currently Chicago only):

- [ ] `python src/download_od.py --city <city>` → `od_counts.csv`
- [ ] `python src/od_matrix.py --city <city>` → `data/<city>/od_matrix.json`
- [ ] Matrix has **no** `validation_safe: false` flag (it is real data)

**`density-proxy`** (no real feed — Paris, Ahmedabad):

- [ ] `python src/od_proxy.py --city <city>` → `data/<city>/od_matrix.json`
- [ ] Output reports `confidence: low` and prints the "NOT valid input for
      validate.py" warning
- [ ] Matrix carries `method: gravity-density-proxy` and
      `validation_safe: false`

**`uniform`** (no OD at all — Piedmont): skip this step; the engine spawns
agents randomly.

---

## 2. Engine — headless run

- [ ] Runs to completion without crashing:
      `run.bat --fast --no-ws --city <city> --od data\<city>\od_matrix.json --duration 10 --journey data\<city>\journey_times.csv`
- [ ] Startup log prints a plausible node / edge / lane / zone count
- [ ] `Initialized N signal controllers` appears with `N > 0`
- [ ] `Loaded N OD pairs` appears (OD mode) with `N > 0`
- [ ] `[FPS]` lines appear and `avg` tick time stays well under 100 ms
- [ ] `journey_times.csv` is written and contains rows with status `Arrived`
- [ ] Some agents actually complete — an all-`Navigating` file means agents are
      stuck (usually a broken graph or an over-restrictive signal phase)

---

## 3. Validation — real-data cities only

Skip for `density-proxy` and `uniform` cities: their journey times are modelled,
so a MAPE against them would be circular. `validate.py` refuses them by design —
confirming that refusal is itself a check.

- [ ] `python src/validate.py --city chicago` completes
- [ ] `data/chicago/validation_report.json` is written
- [ ] `summary.mape_pct` is reported and `passes_checkpoint` is `true`
      (checkpoint: MAPE ≤ 25% **and** ≥ 75% of corridors within 25%)
- [ ] Negative check: run `validate.py` against a city whose `od_matrix.json`
      was produced by `od_proxy.py`. It must **exit with an error** naming the
      matrix as a proxy, never silently produce a MAPE.
      (Covered automatically by
      `pipeline/tests/test_od_proxy.py::test_validate_py_refuses_a_proxy_matrix`;
      re-check by hand only if that guard changes.)

---

## 4. Engine + dashboard — live run

- [ ] Start the engine with WebSocket enabled: `run.bat --city <city> --od data\<city>\od_matrix.json --duration 30`
- [ ] Engine logs `WebSocket server listening on port 9001`
- [ ] `cd dashboard && npm run dev`, open <http://localhost:5173>
- [ ] Engine logs `Client connected`
- [ ] Agents render on the map and visibly move
- [ ] Road geometry renders under the agents
- [ ] Metrics panel populates: avg speed, active agents, completed agents,
      avg wait time, Gini coefficient
- [ ] Active-agent count rises after start, then completed count climbs
- [ ] Toggle **Efficiency** ↔ **Equity** view; the equity overlay renders
      per-zone bubbles
- [ ] Top-5 congested zones chart populates

### 4a. Level-of-detail culling (Phase 4.3)

- [ ] Pan/zoom the map; the engine keeps streaming without stalling
- [ ] Zooming into a small area reduces the number of rendered agents
      (off-viewport agents are culled server-side)
- [ ] Global metrics stay stable while zooming — culling must affect only the
      rendered agent list, never the metric totals

### 4b. Reconnection (Phase 4.7)

- [ ] Stop the engine (Ctrl+C) → dashboard shows a reconnecting state rather
      than crashing
- [ ] Restart the engine → dashboard reconnects on its own, no page refresh

---

## 5. Performance spot-check

- [ ] `make bench` (or run `engine/build/bench_quadtree`) — quadtree beats naive
      search by ≥ 10× at 10,000 agents
- [ ] Stress test passes: the 20,000-agent case in `engine/tests/test_stress.cpp`
- [ ] No unbounded memory growth over a long run

---

## 5a. Multi-city + MARL comparison (Phase 9)

- [ ] `ml/tests` pass (from repo root: `.venv\Scripts\python.exe -m pytest ml\tests`)
- [ ] Engine trains a city: `.venv\Scripts\python.exe -m train.train --city chicago
      --episodes N --checkpoint-interval N` logs "Loaded chicago: 3709 intersections,
      77 zones" and writes `ml/checkpoints/chicago/<ep>.pt`
- [ ] Transfer: `.venv\Scripts\python.exe -m train.transfer` fine-tunes the source
      checkpoint to Paris and Ahmedabad (`ml/checkpoints/*_to_paris/`, `*_to_ahmedabad/`)
- [ ] Evaluate: `.venv\Scripts\python.exe -m train.evaluate --cities <cities>
      --checkpoint <ckpt>` writes `ml/results/comparison.json` with a
      Webster + MARL row per city
- [ ] Dashboard dev server serves `/comparison.json` (vite dev proxy); the
      ComparisonPanel renders the MARL-vs-Webster table bottom-right

---

## 6. Repo hygiene

- [ ] No stray generated files staged (`journey_times.csv`, `build/`, `*.graphml`)
- [ ] `git status` reviewed before committing — confirm nothing unintended, and
      no credentials or API keys, are included
- [ ] Docs updated if any interface, CLI flag, or config key changed

---

## Recording a run

Note the date, commit SHA, city, and any box that failed with its reason. A
failed box left unexplained is the thing most likely to resurface as a
"mysterious" bug two phases later.
