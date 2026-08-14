# NexusSim — User Stories

**Version:** 1.0

User stories are grouped by the three user types defined in the PRD. Each story has an ID, a priority (P1 = must-have, P2 = should-have, P3 = nice-to-have), and acceptance criteria.

---

## Actor 1 — Developer / Researcher (you)

These stories define what the system must let you do during development, training, and analysis.

---

### US-D01 · Load a real city into the engine
**Priority:** P1

As a developer, I want to run a single command that downloads, cleans, and converts OpenStreetMap data for any supported city into a `graph.json` that the C++ engine loads without manual edits, so that adding a new city is a config change, not a code change.

**Acceptance Criteria:**
- `python pipeline/src/export.py --city chicago` produces a valid `graph.json` in under 5 minutes
- The C++ engine loads `graph.json` and logs node count, edge count, and zone count on startup
- If OSM lane data is missing, the fallback chain runs and each inferred edge has a `confidence` field
- Running the same command for Paris and Ahmedabad produces valid graphs without code modification

---

### US-D02 · Watch the simulation run live
**Priority:** P1

As a developer, I want to open a browser tab and see all agents moving on the real city map in real time, so I can visually verify that pathfinding, collision avoidance, and agent spawning are working correctly before I start training.

**Acceptance Criteria:**
- Dashboard connects to the engine WebSocket and renders agent positions within 2 seconds of engine start
- Frame rate stays above 55 fps with 5,000 agents on a dev machine
- Each agent type is visually distinguishable (different colour or shape)
- If the WebSocket drops, the dashboard shows a reconnecting indicator and reconnects automatically

---

### US-D03 · Run a training session and track reward progress
**Priority:** P1

As a developer, I want to launch a MAPPO training run and watch the reward curve in real time via MLflow, so I can catch divergence or instability early and stop the run rather than waiting hours for a broken result.

**Acceptance Criteria:**
- `python ml/train/train.py --city chicago --episodes 5000` starts a training run
- MLflow UI at `localhost:5000` shows episode reward, pressure term, equity term, and Gini coefficient per checkpoint
- Training can be interrupted and resumed from the last checkpoint
- At end of training, a `policy.onnx` file is written to `ml/export/`

---

### US-D04 · Load a trained policy into the engine
**Priority:** P1

As a developer, I want the C++ engine to load a `policy.onnx` file at startup and use it for signal control during the simulation, so I can compare AI-controlled runs against the fixed-cycle baseline in the same visual dashboard.

**Acceptance Criteria:**
- Engine accepts `--policy path/to/policy.onnx` flag at startup
- Without the flag, engine uses Webster's fixed-cycle baseline
- Inference batch completes within 8 ms per tick (logged to stdout every 100 ticks)
- Dashboard shows an "AI mode" / "Baseline mode" label in the corner

---

### US-D05 · Run validation against real data
**Priority:** P1

As a developer, I want to compare simulated corridor journey times against Uber Movement ground truth data for Chicago, so I can quantify how close the simulation is to reality and report this in my write-up.

**Acceptance Criteria:**
- A validation script outputs a table: corridor name, simulated time, Uber Movement time, % error
- Average % error across corridors is logged and compared against the 20% target from the PRD
- Results are saved to `data/chicago/validation_report.json`

---

### US-D06 · Generate the efficiency vs. equity tradeoff curve
**Priority:** P1

As a developer, I want to run the trained policy with different values of β (the equity weight) and plot the resulting efficiency vs. equity tradeoff curve, so I have a concrete chart showing the deliberate design tradeoff.

**Acceptance Criteria:**
- Script accepts a list of β values and runs the simulation for each, recording citywide avg wait time and Gini coefficient
- Output is a CSV and a rendered chart image saved to `docs/figures/`
- Dashboard tradeoff chart panel renders this curve interactively

---

### US-D07 · Add a new city with only config changes
**Priority:** P2

As a developer, I want to add a fourth city (e.g. Jakarta) by adding a config entry and running the pipeline, without touching C++ or Python ML code, so the system is genuinely generalisable.

**Acceptance Criteria:**
- A new entry in `pipeline/config/cities.yaml` with city name, OSM region key, and equity-zone source is all that's needed
- Pipeline, engine, and dashboard all handle the new city without code edits
- City selector in the dashboard populates automatically from config

---

### US-D08 · Run the full test suite in under 3 minutes
**Priority:** P2

As a developer, I want `make test` to run all unit tests across C++, Python pipeline, and ML env in under 3 minutes, so I can run it before every commit without it becoming friction.

**Acceptance Criteria:**
- `make test` runs GoogleTest (engine), pytest (pipeline + ml) and Vitest (dashboard)
- All passing on a clean clone with dependencies installed
- CI runs the same target and fails the build if any test fails

---

### US-D09 · Run the multi-algorithm RL comparison benchmark
**Priority:** P2

As a developer, I want to run all RL algorithms through one benchmark command and see a comparison table against the Webster baseline, so I can identify which algorithm family performs best on the signal-control task and report the full inventory in my write-up.

**Acceptance Criteria:**
- `python ml/train/benchmark.py --algos all --city toy` trains/evaluates every registered algorithm
- Comparison table shows per algorithm: family, avg wait, Gini, pressure, equity, % change vs. Webster
- Each run logs full hyperparameters and metrics to MLflow
- The 9 signal-control algorithms each produce `ml/results/<algo>/eval_report.json`
- SAC/TD3/DDPG showcase runs on `Pendulum-v1` and are reported separately from the signal-control results

---

## Actor 2 — Civil Administrator / Policy Audience

These stories define what a non-technical user must be able to do on the dashboard.

---

### US-P01 · See the live city traffic map without setup
**Priority:** P1

As an administrator, I want to open a URL and immediately see the simulated city's traffic moving on a familiar map, with no login, no configuration, and no technical knowledge required.

**Acceptance Criteria:**
- Dashboard is accessible at a single URL with no authentication
- Map loads with agent animation within 3 seconds
- City name and current mode (AI / Baseline) are visible without scrolling

---

### US-P02 · Switch between efficiency view and equity view
**Priority:** P1

As an administrator, I want to toggle between a speed-focused view and a fairness-focused view, so I can show stakeholders both dimensions of the simulation's performance in the same meeting.

**Acceptance Criteria:**
- Efficiency view shows: citywide average wait time, top 5 congested corridors
- Equity view shows: per-zone average wait time heatmap, Gini coefficient gauge, worst-served zones ranked list
- Toggle is a single button click; view switches in under 1 second

---

### US-P03 · Apply a policy change and see the result
**Priority:** P1

As an administrator, I want to toggle a "dedicated bus lane" switch for a specific corridor and see how average wait time and equity metrics change in the simulation, so I can make a data-backed case for or against the policy to my superiors.

**Acceptance Criteria:**
- Dashboard has policy toggles: dedicated bus lane, congestion pricing zone, EV fleet ratio slider, chaos coefficient slider
- Toggling any policy restarts the simulation with the new parameter and shows updated metrics within 30 seconds
- Metrics from before and after the policy change are shown side by side

---

### US-P04 · Read the equity metrics in plain language
**Priority:** P1

As an administrator with no data science background, I want the equity panel to explain what the Gini coefficient means in plain language next to the number, so I don't need to look it up.

**Acceptance Criteria:**
- Gini gauge shows a value between 0 and 1
- A plain-language label accompanies it: 0.0–0.2 "Very equal", 0.2–0.4 "Moderate inequality", 0.4+ "High inequality — review signal plan"
- Worst-served zones are listed by ward name, not by technical ID

---

### US-P05 · Export a summary report
**Priority:** P2

As an administrator, I want to export a one-page PDF summary of the current simulation run — showing the key efficiency and equity metrics, the policy toggles applied, and the city name — so I can share it in a presentation without taking a screenshot.

**Acceptance Criteria:**
- "Export Report" button generates a PDF with: city, mode, policy toggles active, efficiency metrics, equity metrics, Gini gauge, and timestamp
- PDF is generated client-side and downloaded immediately
- No personally identifiable data is included

---

## Actor 3 — Technical Interviewer / Evaluator

These stories represent what the system must be able to demonstrate in a technical review.

---

### US-E01 · Show spatial index performance benchmark
**Priority:** P1

As an evaluator, I want to see a benchmark comparing Quadtree vs. naive O(N²) proximity detection at different agent counts, so I can verify that C++ was justified and that the spatial index delivers meaningful gains.

**Acceptance Criteria:**
- `engine/tests/bench_quadtree.cpp` runs both approaches at 1k, 5k, 10k, 20k agents and prints a table
- Quadtree shows at least 10× speedup at 10k agents
- Results are included in the README

---

### US-E02 · Show MARL vs. baseline comparison
**Priority:** P1

As an evaluator, I want to see a clear side-by-side comparison of MARL signal control vs. Webster's fixed-cycle baseline on the same city and traffic demand, so I can assess whether the ML component actually works.

**Acceptance Criteria:**
- Comparison table shows: avg wait time (MARL), avg wait time (baseline), % improvement, Gini coefficient (MARL), Gini coefficient (baseline)
- MARL achieves ≥ 15% wait time reduction and ≥ 10% Gini improvement vs. baseline
- Chart is embedded in the dashboard and exportable

---

### US-E03 · Inspect the reward function implementation
**Priority:** P1

As an evaluator, I want to read the reward function code and see that pressure-based local rewards and equity-weighted global rewards are implemented exactly as described, with no hidden heuristics or hardcoded shortcuts.

**Acceptance Criteria:**
- `ml/env/reward.py` is a standalone, well-commented module
- Pressure term and equity term are computed in separate functions with docstrings
- Unit tests in `ml/tests/test_reward.py` verify both terms independently with toy inputs

---

### US-E04 · Verify ONNX inference latency
**Priority:** P1

As an evaluator, I want to see that the C++ ONNX inference batch consistently completes within the 8 ms budget, so I know the ML integration doesn't break the real-time simulation loop.

**Acceptance Criteria:**
- Engine logs inference latency (min, max, p95) every 100 ticks to stdout
- A latency benchmark test in `engine/tests/bench_inference.cpp` runs 1000 batched inference calls and prints statistics
- p95 latency is ≤ 8 ms on the dev machine used for development

---

### US-E05 · Validate against real city data
**Priority:** P1

As an evaluator, I want to see a validation report showing how closely the simulation matches real Uber Movement journey times for at least one city, so I can assess whether the simulation is grounded in reality.

**Acceptance Criteria:**
- `data/chicago/validation_report.json` exists and contains per-corridor simulated vs. real times
- Average error is reported and compared to the 20% target
- Methodology for calibration (OD matrix source, IDM parameter choices) is documented in the README

---

### US-E06 · Run the project from a clean clone
**Priority:** P2

As an evaluator, I want to clone the repo, follow the README setup steps, and have a working simulation running in the browser within 30 minutes, so I can assess it without needing to contact the developer.

**Acceptance Criteria:**
- README has a "Quick Start" section: install deps → run pipeline → build engine → start dashboard
- All dependencies are pinned (CMake version, Python packages in `requirements.txt`, npm packages in `package.json`)
- `make demo` runs a pre-packaged Chicago demo with a small pre-processed graph.json included in the repo

---

### US-E07 · Evaluate the 12-algorithm RL inventory
**Priority:** P2

As an evaluator, I want to see the full RL algorithm inventory compared and ablated in one place, so I can assess breadth (how many algorithm families are covered) and depth (whether they actually work on the task).

**Acceptance Criteria:**
- `docs/results.md` has a 12-algorithm table: family, on/off-policy, value/policy, env, result vs. Webster where applicable
- Ablation section compares value vs. policy, on-policy vs. off-policy, tabular vs. neural on the same signal-control task
- MAPPO, PPO, and DQN each run live in the engine via ONNX, with p95 inference ≤ 8 ms logged (NFR-4)
- SAC/TD3/DDPG each show a learning curve on `Pendulum-v1` (Phase 22)
