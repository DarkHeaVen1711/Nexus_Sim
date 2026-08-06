# NexusSim

A real-time, multi-agent traffic simulation platform. NexusSim models urban road networks — extracted from **OpenStreetMap** and driven by real origin–destination (OD) demand — in a high-performance **C++17** engine, and streams the live state to an interactive **React** dashboard over WebSocket.

It is designed to answer macro- and micro-level routing questions: how long does a trip take across a corridor, where do congestion hotspots form, and **who** bears the cost of that congestion (equity analysis). The platform is built for studying and comparing signal-control strategies, testing congestion-mitigation policies, and validating simulation output against observed ground-truth travel times.

## Features

- **Realistic agent model** — five agent types (car, bus, auto-rickshaw, two-wheeler, pedestrian) simulated with the **Intelligent Driver Model (IDM)** car-following logic and per-type parameters.
- **A\* pathfinding** with Euclidean heuristic, plus a **stochastic route-choice** mode (logit-style lognormal cost perturbation) that spreads agents across near-optimal alternatives.
- **Quadtree spatial index** — reduces proximity/collision queries from O(N²) to O(N log N), keeping 10k+ agent simulations interactive.
- **Parallel simulation ticks** — agent updates run across all hardware threads.
- **Signalized intersections** with **Webster's formula** fixed-cycle timing (green/yellow/red phase machine).
- **MARL signal control** — a Phase 7 training environment (`ml/`) where per-intersection MAPPO policies learn to beat the Webster baseline on a toy grid, using pressure + equity rewards, MLflow tracking, and checkpoint save/resume (exported to the engine via ONNX in Phase 8).
- **Multi-city support** — fully config-driven via `pipeline/cities.yaml` (Chicago, Piedmont, Paris, Ahmedabad; adding a city requires config only).
- **Real OD demand** — Chicago rideshare trip data (City of Chicago open portal) drives hourly time-of-day demand; a gravity-model density proxy and uniform fallback cover cities without a public OD feed.
- **Ground-truth validation** — headless engine runs are compared against observed travel times per corridor, with a MAPE checkpoint report (`data/<city>/validation_report.json`).
- **Equity metrics** — Gini coefficient of wait-time inequality and per-zone wait-time distribution, visualized as a live heat overlay.
- **Live WebSocket streaming** with **viewport LOD culling** — the engine only broadcasts agents inside the dashboard's current bounds.
- **Interactive dashboard** — live city switching at runtime, agent markers, efficiency/equity view modes, and a metrics panel.
- **Journey-time export** — per-agent trip logs written to CSV for analysis.
- **CI + pre-commit discipline** — GitHub Actions (build, C++/Python/JS tests) and pre-commit hooks (clang-format, black, isort, eslint).

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Technologies and Dependencies](#technologies-and-dependencies)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Usage](#usage)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Architecture

| Component | Path | Description |
|-----------|------|-------------|
| **Data Pipeline** | `pipeline/` | Python/osmnx scripts that download OSM road networks, clean and simplify them, infer lane counts, tag analysis zones, build OD demand matrices, and export `data/<city>/graph.json`. |
| **Simulation Engine** | `engine/` | C++17 simulator: IDM car-following, A\* pathfinding, quadtree spatial index, signal controllers, parallel ticks, and a uWebSockets server that streams agent state to the dashboard. |
| **Dashboard** | `dashboard/` | React + TypeScript + Leaflet frontend that renders the live simulation over an OpenStreetMap base layer, with a metrics panel and efficiency/equity views. |
| **ML Pipeline** | `ml/` | Phase 7 MARL training environment: a Gym-compatible `NexusSimEnv` over an offline Python micro-simulator, a MAPPO trainer (PPO + GAE, reward scaling, batching, checkpoint save/resume), MLflow logging, and a toy 4-intersection training graph. Trained policies are exported to ONNX for the engine in Phase 8. |
| **Data** | `data/` | Per-city graph and OD files. Raw `.graphml` intermediates are gitignored; small deliverables (e.g. `graph.json`, `od_matrix.json`, validation reports) are committed. |
| **Docs** | `docs/` | PRD, TRD, tech stack, user stories, implementation plan, and schema references. |

The three runtime subsystems communicate over well-defined interfaces: the pipeline produces `graph.json` (+ optional `od_matrix.json`), the engine loads those files and streams JSON state frames over WebSocket (port `9001`), and the dashboard consumes the stream and serves the UI (port `5173`).

The ML subsystem (`ml/`) is **offline** — it reads the same `graph.json` to train signal-control policies against a Python micro-simulator (`ml/env/`). It is not on the live path; in Phase 8 the trained policy is exported to `policy.onnx` and injected into the engine's signal controllers.

```
┌─────────────┐  graph.json/   ┌──────────────┐  WebSocket   ┌─────────────┐
│   PIPELINE  │  od_matrix.json│ C++ ENGINE   │  port 9001   │  DASHBOARD  │
│  Python/    │ ─────────────► │  simulation  │ ───────────► │  React +    │
│  osmnx      │                │  loop        │              │  Leaflet    │
└─────────────┘                └──────────────┘              └─────────────┘
       │  graph.json (read only)      ▲  policy.onnx (Phase 8)
       ▼                              │
┌──────────────────┐                  │
│  ML (Phase 7)    │ ─────────────────┘
│  Gym env + MAPPO │  offline training on Python micro-sim
└──────────────────┘
```

## Technologies and Dependencies

### Simulation engine (`engine/`)

| Dependency | Version | Purpose |
|-----------|---------|---------|
| C++ | C++17 | Implementation language (CMake `project` standard) |
| CMake | >= 3.25 | Build system |
| nlohmann/json | v3.11.2 | `graph.json` / config parsing (fetched via CMake `FetchContent`) |
| FlatBuffers | v23.5.26 | Binary serialization schema for agent deltas (fetched via CMake) |
| uWebSockets | v20.46.0 | WebSocket server (header-only, fetched via CMake) |
| uSockets | v0.8.6 | WebSocket event loop backend (built from source by CMake) |
| libuv | v1.48.0 | Event loop (Windows); `libuv-dev` preferred on Linux if present |
| ZLib | v1.3.1 | Compression support (auto-fetched when not found) |
| GoogleTest | v1.15.2 | Unit tests + benchmarks (only when `ENABLE_TESTING=ON`) |

### Data pipeline (`pipeline/`)

| Dependency | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Implementation language |
| osmnx | >= 1.9.0 | OSM graph download, cleaning, simplification |
| pyyaml | >= 6.0 | `cities.yaml` config parsing |
| pytest | >= 7.0 | Test runner |

### Dashboard (`dashboard/`)

| Dependency | Version | Purpose |
|-----------|---------|---------|
| React / react-dom | ^19.2.7 | UI framework |
| react-leaflet | ^5.0.0 | Map rendering (`Leaflet` ^1.9.4) |
| recharts | ^3.10.1 | Zone wait-time charts |
| Vite | ^8.1.1 | Dev server / bundler (Vite 8 requires Node >= 20.19) |
| TypeScript | ~6.0.2 | Typed JS |
| oxlint | ^1.71.0 | Linting |

### ML training (`ml/`)

| Dependency | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Implementation language |
| numpy | 1.26.4 | Observation vector construction |
| torch | 2.4.1 | MAPPO policy/value networks, PPO + GAE |
| gymnasium | 1.0.0 | `NexusSimEnv` (reset/step/observation_space/action_space) |
| mlflow | 2.16.2 | Run tracking: episode reward, pressure, equity, Gini |
| pytest | >= 7.0 | Test runner (`ml/tests`, 48 tests) |

### Tooling

- **CI**: GitHub Actions (`ubuntu-latest`) — pipeline pytest, engine build + `ctest`, dashboard install + test.
- **pre-commit**: clang-format, black, isort, eslint.
- **Root `Makefile`**: cross-subsystem build/run/test helpers (Unix).

## Prerequisites

### Windows

- [MSYS2](https://www.msys2.org/) with **MinGW-w64 GCC 13+**
- **CMake >= 3.25** and **Ninja** (bundled with MSYS2)
- **Python 3.11+**
- **Node.js 20+** (18+ works for most tasks; Vite 8 builds need >= 20.19)

Install the MSYS2 toolchain:

```bash
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-ninja
```

### Linux / macOS

- GCC 11+ or Clang 14+ with C++17 support
- CMake >= 3.25
- Python 3.11+
- Node.js 20+
- `libuv-dev` / `libuv-devel` (optional — fetched automatically if missing)

```bash
# Ubuntu/Debian
sudo apt install build-essential cmake ninja-build python3-pip nodejs npm

# macOS (Homebrew)
brew install cmake ninja python node
```

## Installation and Setup

```bash
git clone https://github.com/DarkHeaVen1711/Nexus_Sim.git
cd Nexus_Sim
```

There are **no environment variables** to configure. Dependencies are fetched automatically: the C++ engine pulls its libraries via CMake `FetchContent`, and the dashboard uses `npm`.

### Windows (one command)

```batch
run.bat
```

This builds the engine, starts the dashboard at http://localhost:5173, and runs a 5-minute simulation with 500 agents on Piedmont. See [Usage](#usage) for all `run.bat` options.

### Linux / macOS (manual)

**1. Build and run the engine**

```bash
cd engine
mkdir -p build && cd build
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build .
cd ../..

# Run from the repo root so the engine can resolve data/<city>/graph.json
./engine/build/engine --city piedmont --agents 500 --duration 5 --fast
```

**2. Start the dashboard** (in a separate terminal)

```bash
cd dashboard
npm install
npm run dev
```

Open http://localhost:5173 to see the live visualization.

## Usage

### Running the engine

The engine binary is `engine/build/engine` (Unix) or `engine\build\engine.exe` (Windows), built from `engine/`. It has two modes:

- **Interactive (default)** — idles until the dashboard selects a city over WebSocket, then simulates that city continuously (arrived agents respawn so traffic stays live) until another city is chosen.
- **Headless (`--fast`)** — runs a fixed-duration simulation without pacing and writes a journey-times CSV.

```bash
# Headless: 5-minute uniform-random run on Piedmont
./engine/build/engine --city piedmont --agents 500 --duration 5 --fast

# Headless: real OD-driven demand (Chicago) at 8:00 AM, journey log to a custom path
./engine/build/engine --city chicago --od data/chicago/od_matrix.json \
  --duration 60 --start-hour 8 --demand-scale 0.01 --fast \
  --journey data/chicago/journey_times.csv

# Interactive: wait for the dashboard to pick a city
./engine/build/engine
```

**Expected output** (headless mode):

```
NexusSim Engine v3.0
Loading graph for piedmont...
Nodes: 402 Edges: 1043 Lanes: 1132 Zones: 25
Spawning 500 agents (uniform)...
Running 5-min sim (3000 ticks, dt=0.1s) [fast/headless]...
Tick 0/3000 active=500
...
Avg tick: 0.15ms p95: 0.4ms
Saved journey_times.csv
```

### Engine CLI options

| Option | Default | Description |
|--------|---------|-------------|
| `--city NAME` | `piedmont` | City to simulate (must exist in `pipeline/cities.yaml` and have a `graph.json`) |
| `--agents N` | `500` | Number of agents (uniform spawning mode) |
| `--duration N` | `5` | Duration in minutes (headless `--fast` mode only) |
| `--od PATH` | — | OD demand matrix (real-traffic mode; e.g. `data/chicago/od_matrix.json`) |
| `--demand-scale N` | `1.0` | Scale factor applied to hourly OD demand |
| `--start-hour H` | `8.0` | Simulation start hour (0–23, OD mode) |
| `--journey PATH` | `journey_times.csv` | Where to write per-agent journey-time CSV |
| `--speed-factor N` | `1.0` | Network-wide congestion factor on IDM desired speeds (validated setup uses `0.55`) |
| `--route-spread N` | `0.0` | Stochastic route-choice spread (0 = all agents take the shortest path; validated setup uses `0.2`) |
| `--chaos N` | `0.1` | Lane-discipline chaos coefficient 0–1 |
| `--fast` | off | Headless mode: no pacing, exits when the simulation finishes |
| `--no-ws` | off | Disable the WebSocket server (no dashboard) |

### `run.bat` options (Windows)

`run.bat` wraps engine build + run and the dashboard. It accepts the engine options above (`--city`, `--agents`, `--duration`, `--od`, `--demand-scale`, `--start-hour`, `--speed-factor`, `--route-spread`, `--chaos`, `--journey`, `--fast`, `--no-ws`) plus:

| Option | Description |
|--------|-------------|
| `--debug` | Build in Debug mode |
| `--dashboard-only` | Start the dashboard only (skip build/run) |
| `--help`, `-h` | Show usage |

### `Makefile` targets (Unix)

```bash
make help        # List targets
make build       # Configure + build the C++ engine (Release)
make run CITY=piedmont AGENTS=500 DURATION=5
make test        # Run C++ (ctest), Python (pytest), and dashboard tests
make bench       # Build and run the quadtree benchmark
make dashboard   # Start the React dashboard
make clean       # Remove build artifacts
```

### Stress test (Unix)

`stress_test.sh` builds the engine and runs a large-agent run (default: Chicago, 20 000 agents, 10 min), followed by a Valgrind memory check if available:

```bash
./stress_test.sh            # chicago, 20000 agents, 10 min
./stress_test.sh paris 5000 5
```

### Dashboard

1. Start the engine (interactive mode) and the dashboard.
2. The dashboard connects to `ws://localhost:9001` (auto-reconnects with backoff) and the engine to `localhost:9001`.
3. Select a city at the top to start the simulation; switch cities at any time.
4. Toggle **Efficiency** (live agent markers) vs **Equity** (per-zone wait-time heat overlay) in the top-left control.
5. The metrics panel shows average speed, active/completed agents, average wait time, Gini coefficient, and the top congested zones.

### Training the MARL signal-control policy

Phase 7 ships an offline MAPPO trainer that learns to control the intersections of a toy grid (`ml/env/toy_graph.py`) and beat the Webster fixed-cycle baseline:

```bash
cd ml
pip install -r requirements.txt
python -m train.train --city toy --episodes 500 --baseline-episodes 5
```

- **Reward** = `alpha * pressure_i + beta * equity_global` (see `ml/env/reward.py`); defaults `alpha=1.0`, `beta=1.0`. Negative — lower is better.
- **Tracking**: MLflow logs episode reward, pressure, equity, and Gini per episode (stored under `ml/mlruns/`, gitignored); `--experiment` selects the run group.
- **Checkpoints**: saved to `ml/checkpoints/<city>/<episode>.pt` every `--checkpoint-interval` episodes; resume with `--resume <path>.pt`.
- **Validated defaults**: `--lr 5e-4 --gamma 0.95 --entropy-coef 0.003 --episodes-per-update 4`, with rewards auto-scaled from the baseline run.
- **Result on the toy demand**: the trained policy reaches ≈ −7,300 reward within 500 episodes vs the ≈ −11,270 Webster baseline (≈ 35% better), satisfying the Phase 7.8 convergence checkpoint.

### Generating new city data

The pipeline extracts, cleans, and enriches road networks from OpenStreetMap:

```bash
cd pipeline
pip install -r requirements.txt

python src/download.py --city piedmont   # OSM raw.graphml
python src/clean.py --city piedmont      # simplify + largest SCC
python src/lanes.py --city piedmont      # infer lane counts
python src/zones.py --city piedmont      # tag analysis zones
python src/export.py --city piedmont     # write graph.json
```

This produces `data/<city>/graph.json`, which the engine loads. A new city only needs an entry in `pipeline/cities.yaml` (see [Configuration](#configuration)).

### Building OD demand matrices

For OD-driven runs, build the demand matrix first:

```bash
# Chicago: fetch real rideshare trip counts from the City of Chicago portal
python src/download_od.py --city chicago --weekdays 10 --year 2019 --month 10
python src/od_matrix.py --city chicago --weekdays 10 --year 2019 --month 10

# Cities without a public OD feed (paris, ahmedabad): density-proxy matrix
python src/od_proxy.py --city paris --trips-per-node 0.5
```

### Validating the simulation against ground truth

```bash
cd pipeline
python src/validate.py --city chicago --duration 60 --start-hour 8
```

`validate.py` runs the engine headless with OD demand, compares mean simulated journey times per corridor to observed values, and writes `data/chicago/validation_report.json`. The checkpoint passes when `MAPE <= 25%` **and** >= 75% of sampled corridors are within 25% of ground truth. Validation is only meaningful for cities with real observed data (Chicago); the proxy matrices mark themselves `validation_safe: false` and are refused.

## Configuration

### `pipeline/cities.yaml` — city registry (single source of truth)

Every city the engine or pipeline can use is defined here. The pipeline resolves this file relative to its own location, so it works regardless of the working directory.

```yaml
chicago:
  query: "Chicago, Illinois, USA"   # OSM place name for graph download
  chaos: 0.1                        # default lane-discipline chaos coefficient
  od_source:                        # where OD demand comes from
    type: socrata                   # real feed (socrata | density-proxy | uniform)
    dataset: m6dm-c72p              # City of Chicago rideshare trip dataset id
    ...
piedmont:
  query: "Piedmont, California, USA"
  chaos: 0.1
  od_source:
    type: uniform                   # engine uses uniform random spawning
```

Per-city `od_source` variants:
- `socrata` — real rideshare trip data fetched from a Socrata open-data portal (Chicago). Supports validation.
- `density-proxy` — a gravity-model building-density proxy when no public OD feed exists (Paris, Ahmedabad). **Modelled, not measured** — usable for running simulations, not for computing a validation MAPE.
- `uniform` — fallback; the engine spawns agents between random nodes.

The dashboard currently lists `chicago` and `piedmont` in `dashboard/src/constants.ts`; Paris/Ahmedabad are fully configured and runnable via the engine CLI.

### WebSocket protocol (engine ↔ dashboard)

- **Dashboard → engine:** `{"type":"city","city":"chicago"}` (switch city), `{"type":"get_city"}` (late-connect probe), `{"type":"bounds",...}` (viewport for LOD culling), `ping` (keep-alive).
- **Engine → dashboard:** `{"type":"city_loaded","city":...}`, `{"type":"error","message":...}`, and per-tick state frames containing `agents`, `metrics` (avg_speed, active_agents, completed_agents, avg_wait_time, gini_coefficient), and `zone_metrics`.

### Other configuration

- **No environment variables are used** anywhere in the codebase.
- **Engine build flags:** `-DENABLE_TESTING=ON|OFF` controls GoogleTest + benchmarks (`engine/CMakeLists.txt`).
- **Linting rules:** `dashboard/.oxlintrc.json` (React/TypeScript) and `.pre-commit-config.yaml` (root hooks).
- **Data gitignore policy:** raw `.graphml` intermediates, large city dirs, and pipeline cache are ignored; small deliverables (`graph.json`, `od_matrix.json`, validation reports, Chicago OD extracts) are committed.

## Project Structure

```
NexusSim/
├── engine/                     # C++17 simulation engine
│   ├── src/
│   │   ├── agent/              # Agent system, IDM car-following, A* pathfinding,
│   │   │                       #   signal controllers, Simulation loop
│   │   ├── graph/              # Graph model + JSON loader
│   │   ├── network/            # uWebSockets server (port 9001, LOD culling)
│   │   ├── spatial/            # Quadtree spatial index
│   │   ├── main.cpp            # CLI entry point (interactive/headless modes)
│   │   └── nlohmann/           # Vendored nlohmann/json
│   ├── schemas/                # FlatBuffers schema (agent_delta.fbs)
│   ├── bench/                  # Quadtree benchmark
│   ├── tests/                  # GoogleTest suites (agent, graph, quadtree,
│   │                           #   signal, OD spawner, stress)
│   └── CMakeLists.txt          # Build + FetchContent dependencies
├── pipeline/                   # Python data pipeline
│   ├── src/                    # download, clean, lanes, zones, export,
│   │                           #   download_od, od_matrix, od_proxy, validate
│   ├── tests/                  # pytest suites
│   ├── cities.yaml             # City registry (single source of truth)
│   └── requirements.txt
├── dashboard/                  # React + TypeScript + Vite + Leaflet UI
│   ├── src/
│   │   ├── components/         # Map, CitySelector, MetricsPanel, EquityOverlay
│   │   ├── hooks/              # useWebSocket (auto-reconnect, heartbeat)
│   │   └── constants.ts        # City list, Gini thresholds
│   └── package.json
├── ml/                         # Phase 7 MARL training environment
│   ├── env/                    # Gym env, micro-sim, observation, reward, toy graph
│   ├── models/                 # MAPPO policy/value networks
│   ├── train/                  # PPO update, rollout collection, trainer CLI
│   ├── tests/                  # pytest suites (48 tests)
│   ├── mlruns/  checkpoints/   # gitignored MLflow tracking + model checkpoints
│   └── requirements.txt
├── data/                       # City data
│   ├── piedmont/               # graph.json (committed)
│   ├── chicago/                # graph, od_matrix.json, validation_report.json
│   ├── paris/  ahmedabad/      # gitignored until generated locally
│   └── uber-movement-chicago/  # Source OD extracts (committed)
├── docs/                       # PRD, TRD, tech stack, user stories, plans, schemas
├── .github/workflows/ci.yml    # CI: build + test all subsystems
├── .pre-commit-config.yaml     # clang-format, black, isort, eslint hooks
├── Makefile                    # Unix build/run/test helpers
├── run.bat                     # Windows one-click build & run
└── stress_test.sh              # Unix large-scale + valgrind stress run
```

## Testing

### C++ (GoogleTest)

The engine ships unit tests for pathfinding, IDM, the quadtree, signal controllers, Gini computation, OD spawning, and a 20 000-agent stress test. Build with testing enabled and run via `ctest`:

```bash
cd engine
mkdir -p build && cd build
cmake .. -G Ninja -DENABLE_TESTING=ON
cmake --build .
ctest --output-on-failure
```

Benchmarks build alongside tests:

```bash
./bench_quadtree
```

### Python (pytest)

```bash
cd pipeline
pip install -r requirements.txt
python -m pytest tests/ -v
```

Suites cover pipeline module presence, city config, OD matrix geometry/point-in-zone logic, and the density-proxy generator.

### ML (pytest)

```bash
cd ml
pip install -r requirements.txt
python -m pytest tests/ -v
```

Suites cover the observation space, reward terms, env interface, toy graph, and PPO/GAE updates (48 tests).

### Dashboard

```bash
cd dashboard
npm install
npm run lint     # oxlint
npm run test     # NOTE: currently a placeholder ("Dashboard test passed")
```

`[TODO: Dashboard has no real test suite yet — npm run test is a stub echo. Vitest + React Testing Library is planned per docs/TECH_STACK.md.]`

### CI

`.github/workflows/ci.yml` runs the Python tests, the C++ build (`-DENABLE_TESTING=ON`) and `ctest`, and the dashboard install + test on every push/PR (`ubuntu-latest`).

## Deployment

NexusSim is a local-first research/analysis tool rather than a hosted service; there is no production deployment target today. For distribution-style builds:

- **Engine:** build a Release binary (`cmake -DCMAKE_BUILD_TYPE=Release`) and copy it alongside a `data/` directory containing the target city's `graph.json`.
- **Dashboard:** build a static bundle and serve it:

  ```bash
  cd dashboard
  npm run build        # outputs to dashboard/dist
  npm run preview      # serve the built bundle locally
  ```

  `[TODO: No containerization (Dockerfile) or hosting config exists yet — add if a deployment target is required.]`

The engine must be reachable at `ws://localhost:9001` for the dashboard to function.

## Contributing

Contributions are welcome. The repo follows a strict, documented convention (see `docs/TECH_STACK.md` §Developer Tooling & Git Discipline):

- **Commit format:** `<type>(<scope>): <short summary>` — types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`; scopes: `engine`, `pipeline`, `ml`, `dashboard`, `ci`.
  Example: `feat(engine): add quadtree proximity detection for agent collision`
- **Branch naming:** `feature/<desc>`, `fix/<desc>`, `refactor/<desc>`, `data/<desc>`, `experiment/<desc>`.
- **Size discipline:** max ~100 line insertions per commit; splits must stay independently buildable. Changes exceeding 100 insertions total open a pull request.
- **PRs:** describe what changed, why, and what was tested; must pass all CI checks before merge. No force-push to `main`.
- **Hooks:** run `pre-commit install` to enable clang-format (C++), black + isort (Python), and eslint (JS) locally.

Suggestions, bug reports, and pull requests are appreciated. For larger features, open an issue or PR first to discuss scope.

## License

License information not provided.

## Acknowledgements

- **OpenStreetMap** contributors for the road-network data and map tiles.
- **osmnx** (Geoff Boeing) for OSM graph extraction and cleaning.
- The **City of Chicago** open-data portal for the rideshare (TNP) trip dataset used for real OD demand and validation.
- **Uber Movement** for the historical OD journey-time data the Chicago extracts are based on.
- Open-source foundations of the engine and dashboard: uWebSockets/uSockets, libuv, FlatBuffers, GoogleTest, nlohmann/json, ZLib, Leaflet/react-leaflet, Recharts, React, Vite, and TypeScript.
