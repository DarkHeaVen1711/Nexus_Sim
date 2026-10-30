# NexusSim — Master Documentation

**Status:** Active
**Owner:** Vyom & Vatsal
**Replaces:** the earlier documents in `docs/` (see `docs/README.md` for the inventory)
**Verified against:** the working tree on 2026-10-24 (commit `446d9a8`, plus the uncommitted ML, `run.bat`, and README changes)

> **Reading convention.** Each factual claim is either verified against a file in
> this repository, or marked `[NEEDS CONFIRMATION]`. `[UNVERIFIED]` marks a
> carried-over claim that no artifact reproduces. Section numbers in the
> citations below refer to this document.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture & Components](#2-architecture--components)
3. [Installation & Setup](#3-installation--setup)
4. [Usage Guide](#4-usage-guide)
5. [Current Status](#5-current-status)
6. [Roadmap & Next Phases](#6-roadmap--next-phases)
7. [Contributing Guidelines](#7-contributing-guidelines)
8. [Appendix A — Data Formats](#appendix-a--data-formats)
9. [Appendix B — Document Map](#appendix-b--document-map)

---

## 1. Project Overview

### 1.1 What NexusSim Is

NexusSim is a real-time, multi-agent urban traffic simulation platform. It
rebuilds a real city road network from OpenStreetMap, drives it with real
origin–destination (OD) demand, simulates traffic in a C++17 engine, and
streams live state to a React dashboard over WebSocket.

It answers two question types:

- **Routing.** How long does a trip take across a corridor? Where do
  congestion hotspots form?
- **Equity.** Which neighbourhoods carry the cost of congestion? The engine
  reports a Gini coefficient of wait-time inequality next to average speed.

The project exists so that a planner can test a signal policy, a bus lane, or a
congestion charge on a copy of a city before changing a real street.

### 1.2 Scope: Four Academic Subjects

One system covers four subjects. All four share the same simulation.

| Subject | Function | Location |
|---|---|---|
| Reinforcement Learning (RL) | Trains per-intersection signal policies and exports them to ONNX | `ml/` |
| Soft Computing (SC) | Genetic-algorithm calibration and a Mamdani fuzzy signal controller | `pipeline/src/optimize_calibration.py`, `engine/src/agent/FuzzyPolicy.h` |
| Computer Vision (CV) | Classifies congestion; renders a synthetic camera view of the simulation | `pipeline/src/cv_congestion.py`, `ml/cv/` |
| Natural Language Processing (NLP) | Answers plain-language metric questions; converts incident reports into simulation changes | `ml/nlp/`, `engine/src/agent/NLPQueryParser.h` |

### 1.3 Goals

| ID | Goal |
|---|---|
| G1 | Simulate 20,000+ agents on a real city graph |
| G2 | Train a decentralised MARL policy that beats fixed-cycle timing |
| G3 | Make equity a measured output, not only a report |
| G4 | Support several structurally different cities without code changes |
| G5 | Serve a dashboard that a non-technical administrator can read |
| G6 | Make signal control pluggable: Webster, fuzzy, and RL policies hot-swap |
| G7 | Replace manual calibration with a GA; add a fuzzy controller |
| G8 | Classify real-world congestion from traffic imagery |
| G9 | Run a synthetic virtual camera over the simulation |
| G10 | Answer natural-language questions about live simulation state |
| G11 | Accept free-text incident reports that change the running simulation |
| G12 | Prove that all four subjects interoperate in one demo |
| G13 | Ship a 12-algorithm RL inventory with a shared harness |

Source: `docs/PRD.md`.

### 1.4 Non-Goals

NexusSim does **not**:

- control real traffic signal hardware;
- provide live city monitoring;
- require proprietary data — every source is open;
- work as an end-user navigation application;
- scrape the Google Maps traffic layer (a Terms-of-Service violation; the
  approved substitutes are Mapbox Traffic Tiles and the TomTom Traffic Flow
  API);
- implement cooperative message-passing MARL or one central controller;
- claim research-grade depth in a single subject.

### 1.5 Users

| User | Needs |
|---|---|
| **Urban policy researcher / student developer** | Full technical access: reward functions, GA reports, CV accuracy, NLP intent accuracy |
| **Civil administrator / policy audience** | Plain-language metrics, policy toggles, the metrics chat, incident reports |
| **Technical interviewer / evaluator** | Clean interfaces, documented decisions, ablations, one integrated demo |

### 1.6 Supported Cities

`pipeline/cities.yaml` is the single source of truth. A new city needs a config
entry, not new code.

| City | OD demand source | Validation safe | `chaos` | Graph as shipped |
|---|---|---|---|---|
| Chicago, USA | Socrata TNP trips (dataset `m6dm-c72p`) | Yes | 0.1 | 10,709 nodes, 16,594 edges, 12 zone ids |
| Paris, France | Density proxy (`od_proxy.py`) | No — modelled | 0.1 | 144 nodes, 528 edges, 9 zone ids |
| Ahmedabad, India | Density proxy (`od_proxy.py`) | No — modelled | 0.4 | 23,520 nodes, 43,494 edges, 15 zone ids |
| Piedmont, California, USA | Uniform random spawning | No | 0.1 | 368 nodes, 975 edges, 73 zone ids |

`chaos` is the per-city lane-discipline coefficient. Ahmedabad uses 0.4 to
reflect lower observed lane discipline.

---

## 2. Architecture & Components

### 2.1 Subsystems

| Component | Path | Language | Responsibility |
|---|---|---|---|
| **Data pipeline** | `pipeline/` | Python 3.11 | Downloads, cleans, and enriches OSM networks. Infers lanes, tags zones, builds OD matrices, exports `graph.json`. |
| **Simulation engine** | `engine/` | C++17 | IDM car-following, A\* routing, quadtree index, signal policies, parallel ticks, ONNX inference, WebSocket server. |
| **Dashboard** | `dashboard/` | React 19 + TypeScript | Leaflet map, metrics panel, efficiency and equity views, side panels. |
| **ML pipeline** | `ml/` | Python + PyTorch | Gym environment, MAPPO trainer, ONNX export, 12-algorithm harness, CV and NLP sidecars. Offline. |
| **Sidecars** | `ml/cv/`, `ml/nlp/` | Python + FastAPI | Separate processes on ports 9003 and 9004. Never inside the engine or the browser bundle. |
| **Data** | `data/` | JSON, CSV | Per-city graph, OD matrix, validation report, GA report, CV output. |

### 2.2 Data Flow

```
┌──────────────┐  graph.json        ┌───────────────┐  WebSocket   ┌──────────────┐
│   PIPELINE   │  od_matrix.json    │  C++ ENGINE   │  port 9001   │  DASHBOARD   │
│  Python /    │ ─────────────────► │  simulation   │ ───────────► │  React +     │
│  osmnx       │                    │  loop         │              │  Leaflet     │
└──────────────┘                    └───────────────┘              └──────────────┘
       ▲                                      ▲  policy.onnx
       │  graph.json (read only)              │
┌──────┴───────────────┐                      │
│  ML (offline)        │──────────────────────┘
│  Gym env + MAPPO     │  trains, then exports ONNX
└──────────────────────┘

Sidecars (independent processes):
  ml/cv/virtual_camera_service.py   port 9003  REST  annotated JPEG frame + counts
  ml/nlp/chat_service.py            port 9004  REST  POST /chat, POST /incident
  engine/src/agent/NLPQueryParser.h in-engine      plain-language commands
```

### 2.3 Architectural Rules

These rules are load-bearing. A change to one breaks a documented contract.

1. **The engine is the only writer of simulation truth.** Every other
   component reads its stream.
2. **ML, CV, and NLP run as sidecars.** They stay out of the C++ hot path and
   out of the frontend bundle.
3. **Broadcast fields grow by addition only.** The dashboard ignores unknown
   keys, so a new field never breaks it.
4. **Per-city variation is configuration.** `pipeline/cities.yaml` is the only
   city registry.
5. **The engine writes the only authoritative metrics.** Sidecars read them.

### 2.4 Repository Layout

```
NexusSim/
├── engine/                     # C++17 simulation engine
│   ├── src/
│   │   ├── agent/              # Agent, IDM, Pathfinder, SignalPolicy,
│   │   │                       #   SignalController, WebsterPolicy, FuzzyPolicy,
│   │   │                       #   RLPolicy, Simulation, ThreadPool, NLPQueryParser
│   │   ├── ai/                 # InferenceEngine, SpscRingBuffer
│   │   ├── core/               # NexusEngine, CliConfig, Metrics, Pacer
│   │   ├── graph/              # Graph model and JSON loader
│   │   ├── network/            # uWebSockets server with LOD culling
│   │   ├── spatial/            # Quadtree
│   │   └── main.cpp
│   ├── schemas/                # FlatBuffers schema (agent_delta.fbs)
│   ├── bench/                  # bench_quadtree.cpp, bench_inference.cpp
│   ├── tests/                  # GoogleTest suites
│   └── CMakeLists.txt
├── pipeline/                   # Python data pipeline
│   ├── src/                    # download, clean, lanes, zones, export,
│   │                           #   download_od, od_matrix, od_proxy, validate,
│   │                           #   optimize_calibration, cv_congestion
│   ├── tests/                  # pytest (27 tests)
│   ├── cities.yaml             # City registry (single source of truth)
│   └── requirements.txt
├── dashboard/                  # React + TypeScript + Vite + Leaflet
│   └── src/
│       ├── components/         # Map, CitySelector, MetricsPanel, EquityOverlay,
│       │                       #   PolicyTogglePanel, PolicyComparisonPanel,
│       │                       #   CalibrationReportPanel, CongestionCVOverlay,
│       │                       #   VirtualCameraPanel, ChatPanel,
│       │                       #   IncidentReportPanel, NLPCommandConsole,
│       │                       #   ComparisonPanel, SimControls, RightDock
│       ├── hooks/useWebSocket.ts
│       └── constants.ts
├── ml/                         # Offline ML, CV, NLP
│   ├── env/                    # Gym env, observation, reward, traffic sim,
│   │                           #   vectorized sim, toy graph, graph loader
│   ├── models/                 # MAPPO policy and value networks
│   ├── train/                  # train, transfer, evaluate, ppo, rollout, device
│   ├── algo/                   # base_trainer, value_based, policy_based,
│   │                           #   continuous_control
│   ├── cv/                     # virtual_camera, virtual_camera_service, yolo_detector
│   ├── nlp/                    # chat_service, incident_parser
│   ├── export/                 # export_onnx, validate_onnx
│   └── tests/                  # pytest (78 tests)
├── data/                       # City data and derived artifacts
├── docs/                       # This document and its references
├── .github/workflows/ci.yml    # CI: build and test all subsystems
├── Makefile                    # Unix build/run/test helpers
├── run.bat                     # Windows one-click build and run
└── stress_test.sh              # Unix large-scale plus valgrind run
```

### 2.5 Engine Components

| Component | File | Purpose |
|---|---|---|
| `Agent`, `IDM` | `engine/src/agent/Agent.h`, `IDM.h` | Agent records, per-type IDM parameters, car-following |
| `Pathfinder` | `engine/src/agent/Pathfinder.h` | A\* with a Euclidean heuristic; stochastic route choice; transit routing |
| `Quadtree` | `engine/src/spatial/Quadtree.h` | Spatial index; O(N log N) proximity queries |
| `SignalPolicy` | `engine/src/agent/SignalPolicy.h` | Interface: `tick`, `is_green`, `current_phase_index`, `policy_name` |
| `WebsterPolicy` | `engine/src/agent/WebsterPolicy.h` | Fixed-cycle timing (default) |
| `FuzzyPolicy` | `engine/src/agent/FuzzyPolicy.h` | Mamdani inference over queue length and wait time |
| `RLPolicy` | `engine/src/agent/RLPolicy.h` | Adapts the ONNX engine to `SignalPolicy` |
| `InferenceEngine` | `engine/src/ai/InferenceEngine.h/.cpp` | ONNX Runtime wrapper; batches all intersections into one call |
| `SpscRingBuffer` | `engine/src/ai/SpscRingBuffer.h` | Off-path inference queue |
| `Simulation` | `engine/src/agent/Simulation.h` | Tick loop, metrics, zone metrics, Gini, `apply_incident`, emissions, transit equity |
| `Metrics`, `Pacer` | `engine/src/core/Metrics.h`, `Pacer.h` | Latency histogram; frame pacing |
| `ThreadPool` | `engine/src/agent/ThreadPool.h` | Parallel agent updates |
| `NLPQueryParser` | `engine/src/agent/NLPQueryParser.h` | In-engine command parser |
| `NexusEngine`, `CliConfig` | `engine/src/core/` | Engine lifecycle and CLI parsing |
| `WebSocketServer` | `engine/src/network/WebSocketServer.h` | uWebSockets server with viewport LOD culling |

### 2.6 Ports and Interfaces

| Service | Port | Protocol | Direction |
|---|---|---|---|
| Engine WebSocket | 9001 | WS, JSON frames | Engine ↔ dashboard |
| CV virtual camera | 9003 | HTTP REST | Sidecar → client |
| NLP chat and incidents | 9004 | HTTP REST | Sidecar → client; incident → engine WS |
| Dashboard dev server | 5173 | HTTP | Browser → dashboard |
| Algorithm Explorer API | 9006 | HTTP | Not implemented. Planned for Phase 35 (`docs/TEAM_IMPLEMENTATION_PLAN.md`). |

### 2.7 Engine WebSocket Protocol

**Dashboard → engine**

| Message | Effect |
|---|---|
| `{"type":"city","city":"chicago"}` | Start a city. Accepted only while the engine is idle. |
| `{"type":"get_city"}` | Probe. The engine answers `city_loaded` with the city id or `null`. |
| `{"type":"bounds", min_lat, min_lon, max_lat, max_lon}` | Viewport for LOD culling. |
| `{"type":"pause"}` / `{"type":"resume"}` | Freeze or continue the run. |
| `{"type":"restart"}` | Reload the same city. |
| `{"type":"reset"}` (alias `stop`) | Stop the run and return to idle. This unlocks city selection. |
| `{"type":"policy_switch","intersection_id":0\|null,"policy":"webster\|fuzzy\|rl"}` | Switch one intersection or the network, without restart. |
| `{"type":"incident","edges":[0],"severity":0.5,"duration_s":10.0}` | Apply a temporary edge change. |
| `ping` | Keep-alive. |

**Engine → dashboard**

```json
{
  "tick": 0,
  "agents": [{"id": 0, "lat": 0.0, "lon": 0.0, "heading": 0.0, "type": "car", "speed": 0.0}],
  "metrics": {"avg_speed": 0.0, "active_agents": 0, "completed_agents": 0,
              "avg_wait_time": 0.0, "gini_coefficient": 0.0},
  "zone_metrics": [{"zone_id": 0, "wait_time": 0.0}],
  "mode": "webster",
  "signals": [{"id": 0, "phase": 0, "state": "green"}],
  "incidents": [{"edges": [0], "severity": 0.5, "remaining_s": 10.0}]
}
```

### 2.8 Sidecar Endpoints

**Virtual camera — port 9003**

| Method | Path | Response |
|---|---|---|
| GET | `/health` | `{"status":"ok","service":"virtual_camera","port":9003}` |
| GET | `/api/camera/feed?agent_count=<n>` | `frame_base64`, `detected_count`, `ground_truth_count`, `error_pct`, `accuracy_pct`, `timestamp` |

**NLP chat — port 9004**

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/health` | — | `{"status":"ok","service":"nlp_chat","port":9004}` |
| POST | `/chat` | `{query, city}` | `{intent, answer, confidence, handler}` |
| POST | `/incident` | `{text, city}` | `{status, incident_spec:{type,severity,duration_s,edges,description}, message}` |

The `/chat` answers are hardcoded literals. See §5.3.

---

## 3. Installation & Setup

### 3.1 Prerequisites

**Windows**

- MSYS2 with MinGW-w64 GCC 13 or later
- CMake 3.25 or later, and Ninja
- Python 3.11 or later
- Node.js 20 or later (Vite 8 requires 20.19 or later)

```bash
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-ninja
```

**Linux and macOS**

- GCC 11+ or Clang 14+ with C++17 support
- CMake 3.25 or later
- Python 3.11 or later
- Node.js 20 or later

```bash
# Ubuntu / Debian
sudo apt install build-essential cmake ninja-build python3-pip nodejs npm

# macOS (Homebrew)
brew install cmake ninja python node
```

### 3.2 Clone

```bash
git clone https://github.com/DarkHeaVen1711/Nexus_Sim.git
cd Nexus_Sim
```

The engine fetches its C++ libraries through CMake `FetchContent`. The
dashboard and the Python packages install through `npm` and `pip`.

### 3.3 Quick Start

**Linux and macOS**

```bash
make demo
```

`make demo` configures a Release engine, builds the dashboard bundle, and then
starts the engine. It does **not** start the dashboard dev server. In
interactive mode the engine ignores `--city` and waits for a city selection
over WebSocket, so `make demo` alone shows no simulation. To see the UI, run
`make dashboard` in a second terminal and select a city there.

**Windows**

```bat
run.bat
```

`run.bat` adds `C:\msys64\mingw64\bin` to `PATH`, builds the engine, optionally trains the MARL policy, exports it to ONNX, and starts the engine plus all sidecars.
the engine plus the dashboard dev server.

> Contradiction to resolve: the root `README.md` states that `make demo`
> starts the dashboard at `http://localhost:5173`. The `Makefile` does not
> start it. `[NEEDS CONFIRMATION]`

### 3.4 Manual Setup

**Step 1 — Build and run the engine**

```bash
cd engine
mkdir -p build && cd build
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build .
cd ../..

./engine/build/engine --city piedmont --agents 500 --duration 5 --fast
```

The engine resolves the graph through `data/`, `../data/`, then `../../data/`,
so it works from the repository root or from `engine/`
(`engine/src/core/NexusEngine.h`).

**Step 2 — Start the dashboard** in a second terminal

```bash
cd dashboard
npm install
npm run dev
```

Open `http://localhost:5173`.

### 3.5 Dependency Versions

**Engine — `engine/CMakeLists.txt`**

| Dependency | Version | Purpose |
|---|---|---|
| C++ | C++17 | Implementation language |
| CMake | ≥ 3.25 | Build system |
| nlohmann/json | v3.11.2 | `graph.json` parsing |
| FlatBuffers | v23.5.26 | Agent-delta serialisation |
| uWebSockets | v20.46.0 | WebSocket server |
| uSockets | v0.8.6 | WebSocket event loop |
| libuv | v1.48.0 | Event loop (Windows) |
| ZLib | v1.3.1 | Compression |
| GoogleTest | v1.15.2 | Tests and benchmarks (`ENABLE_TESTING=ON`) |

**Pipeline — `pipeline/requirements.txt`**

| Dependency | Version |
|---|---|
| Python | 3.11+ |
| osmnx | ≥ 1.9.0 |
| pyyaml | ≥ 6.0 |
| pytest | ≥ 7.0 |

**Dashboard — `dashboard/package.json`**

| Dependency | Version |
|---|---|
| react, react-dom | ^19.2.7 |
| react-leaflet / leaflet | ^5.0.0 / ^1.9.4 |
| recharts | ^3.10.1 |
| vite | ^8.1.1 |
| typescript | ~6.0.2 |
| oxlint | ^1.71.0 |

**ML — `ml/requirements.txt`**

| Dependency | Version |
|---|---|
| Python | 3.11+ |
| numpy | ≥ 1.26 |
| torch | 2.12.0 |
| gymnasium | ≥ 1.0 |
| mlflow | ≥ 3.0 |
| onnx / onnxruntime | ≥ 1.15 / ≥ 1.18 |
| nvidia-ml-py | ≥ 12.0 |

`ml/requirements-cuda.txt` installs `torch==2.12.0+cu130` from the PyTorch CUDA
index. It requires a driver that supports CUDA 13.0.

`docs/RL_DOCUMENTATION.md` still lists `torch==2.4.1` and `mlflow==2.16.2`.
Treat `ml/requirements.txt` as authoritative.

### 3.6 Environment Variables

| Variable | Read by | Purpose |
|---|---|---|
| `NEXUS_DEVICE` | `ml/train/device.py`, `ml/train/train.py`, `train/transfer.py`, `train/evaluate.py`, `ml/algo/base_trainer.py` | Default for `--device`: `auto`, `cpu`, `cuda`, `cuda:N` |
| `NEXUS_TORCH_THREADS` | `ml/train/train.py`, `ml/train/transfer.py` | CPU thread count for training. Default `1`. |

MLflow uses a fixed SQLite URI (`sqlite:///ml/mlflow.db`) and takes no
environment variable. No service reads an API key today: the CV module makes no
network request (see §5.3). The root `README.md` claim "no environment
variables are used" is therefore accurate for the runtime path and inaccurate
for training.

---

## 4. Usage Guide

### 4.1 Engine CLI

The binary is `engine/build/engine` on Unix and `engine\build\engine.exe` on
Windows. The banner reads `NexusSim Engine v3.1`.

**Modes**

- **Interactive (default).** Publishes the WebSocket stream and waits for the
  dashboard to select a city. It then paces to real time and respawns arrived
  agents. `--city` and `--duration` have no effect in this mode.
- **Headless (`--fast`).** Runs the `--city` for `--duration` minutes without
  pacing, then writes a journey-time CSV.

**Options** — verified against `engine/src/core/CliConfig.h`

| Option | Default | Description |
|---|---|---|
| `--city NAME` | `piedmont` | City to simulate in headless mode. It must exist in `pipeline/cities.yaml` and have a `graph.json`. |
| `--agents N` | `500` | Agent count in uniform spawning mode. |
| `--duration N` | `5` | Duration in minutes. Headless mode only. |
| `--od PATH` | — | OD demand matrix, for example `data/chicago/od_matrix.json`. |
| `--demand-scale N` | `1.0` | Scale factor for hourly OD demand. Omit it to auto-scale the peak to about 600 veh/h. |
| `--start-hour H` | `8.0` | Start hour, 0–23. OD mode only. |
| `--journey PATH` | `journey_times.csv` | Per-agent journey-time CSV. |
| `--speed-factor N` | `1.0` | Congestion factor on IDM desired speeds. The validated setup uses `0.55`. |
| `--route-spread N` | `0.0` | Stochastic route-choice spread. The validated setup uses `0.2`. |
| `--chaos N` | `0.1` | Lane-discipline coefficient, 0–1. |
| `--policy PATH` | — | ONNX policy file. Omit it for Webster timing. |
| `--dt N` | `0.1` | Time step in seconds. |
| `--port N` | `9001` | WebSocket port. |
| `--fast` | off | Headless mode. |
| `--no-ws` | off | Disable the WebSocket server. |

> There is **no** `--signal-policy` flag and **no** `--algo` flag. Select a
> policy at runtime with the `policy_switch` message, or pass `--policy PATH`
> at startup.

**Examples**

```bash
# Headless, 5 minutes, uniform spawning
./engine/build/engine --city piedmont --agents 500 --duration 5 --fast

# Headless, OD demand, Chicago, 08:00
./engine/build/engine --city chicago --od data/chicago/od_matrix.json \
  --duration 60 --start-hour 8 --demand-scale 0.01 --fast \
  --journey data/chicago/journey_times.csv

# AI signal control, with fallback to Webster
./engine/build/engine --city piedmont --agents 500 --policy ml/policy.onnx

# Interactive
./engine/build/engine
```

The engine prints `Signal mode: rl` or `Signal mode: webster` at startup. At
the end of a run it reports CO₂ (kg), NOₓ (g), and a Transit Equity Index.

### 4.2 `run.bat` (Windows)

`run.bat` wraps the build, the engine, and the dashboard. It accepts the engine
options above and these extras:

| Option | Description |
|---|---|
| `--debug` | Build in Debug mode. |
| `--rebuild` | Force a clean rebuild. |
| `--dashboard-only` | Start the dashboard only. |
| `--policy PATH` | ONNX policy for the engine. |
| `--train` | Train the MAPPO policy, export it to ONNX, then run the engine with it. |
| `--train-city NAME` | Training city. Default `toy`. |
| `--train-episodes N` | Training episodes. Default 200. |
| `--train-device DEV` | `auto`, `cpu`, `cuda`, `cuda:N`. Default `auto`. |
| `--train-batch-size N` | PPO minibatch size. `0` scales it. |
| `--python PATH` | Python interpreter. Default `python`. |
| `--help`, `-h` | Show usage. |

`run.bat` defaults differ from the engine defaults: `--speed-factor 0.55`,
`--route-spread 0.2`, and auto demand scaling.

`run.bat` never trains unless `--train` is given. The C++ engine is CPU-only.

```bat
run.bat --train --train-device cuda --city piedmont
```

### 4.3 `Makefile` Targets (Unix)

```bash
make help        # List targets
make build       # Configure and build the engine (Release, no tests)
make run CITY=piedmont AGENTS=500 DURATION=5
make demo        # Build engine and dashboard bundle, then start the engine
make test        # C++ (ctest), pipeline (pytest), dashboard test
make bench       # Build and run the quadtree benchmark
make dashboard   # Start the React dev server
make clean       # Remove build artifacts
```

`make test` runs the ML suite only through CI, not through this target.

### 4.4 Stress Test (Unix)

```bash
./stress_test.sh            # Chicago, 20,000 agents, 10 minutes
./stress_test.sh paris 5000 5
```

The script runs a valgrind memory check when valgrind is installed.

### 4.5 Dashboard

1. Start the engine in interactive mode and start the dashboard.
2. The dashboard connects to `ws://localhost:9001` and reconnects with
   exponential backoff.
3. Select a city. The list is Chicago, Paris, Ahmedabad, and Piedmont
   (`dashboard/src/constants.ts`).
4. Toggle **Efficiency** (live markers) and **Equity** (zone wait-time heat) in
   the top-left control.
5. The metrics panel shows average speed, active and completed agents, average
   wait time, the Gini coefficient, and the most congested zones.
6. The right dock holds the policy toggle, policy comparison, calibration
   report, CV overlay, virtual camera, chat, incident panel, command console,
   and MARL comparison table.

**Gini bands** — `dashboard/src/constants.ts`

| Range | Label |
|---|---|
| `g < 0.25` | Low Inequality |
| `0.25 ≤ g < 0.45` | Moderate Inequality |
| `g ≥ 0.45` | High Inequality |

### 4.6 Training the MARL Policy

```bash
cd ml
pip install -r requirements-cuda.txt   # or requirements.txt for CPU
python -m train.train --city toy --episodes 500 --baseline-episodes 5
```

**Reward:** `reward_i = alpha * pressure_i + beta * equity_global`, with
`alpha = beta = 1.0` by default. The reward is negative; lower is better.

**Options** — `ml/train/train.py`

| Option | Default | Description |
|---|---|---|
| `--city NAME` | `toy` | City to train on. |
| `--episodes N` | `1000` | Cumulative target, not a count of new episodes. |
| `--resume PATH\|latest` | — | Resume from a checkpoint. |
| `--checkpoint-interval N` | `500` | Episodes between saves. |
| `--lr`, `--gamma`, `--lam` | `5e-4`, `0.95`, `0.95` | PPO values. |
| `--entropy-coef` | `0.003` | Entropy bonus. |
| `--clip-eps` | `0.2` | Clip range. |
| `--episodes-per-update` | `4` | Episodes per PPO update. |
| `--batch-size N` | `0` | Minibatch size. Zero auto-scales. |
| `--episode-steps` | `100` | Decision steps per episode. |
| `--alpha`, `--beta` | `1.0`, `1.0` | Reward weights. |
| `--device DEV` | `auto` | `auto`, `cpu`, `cuda`, `cuda:N`. |
| `--experiment NAME` | — | MLflow run group. |
| `--seed N` | `0` | Random seed. |

> **Warning.** `--episodes` is cumulative. With `--resume latest`, a smaller
> value runs zero episodes.

**Artifacts**

- Checkpoints: `ml/checkpoints/<city>/<episode>.pt` (gitignored).
- MLflow logs `episode_reward`, `mean_pressure`, `equity`, and `gini` per
  episode to `sqlite:///ml/mlflow.db`. MLflow 3.x removed the file store.

**Signalised intersections.** City graphs carry no `is_signal` flags. The
loader derives them from topology: a node with at least three incident road
legs (`ml/env/graph_loader.py`).

| City | Intersections |
|---|---|
| `toy` | 4 |
| `piedmont` | 4 |
| `paris` | 16 |
| `chicago` | 5,217 |
| `ahmedabad` | 15,724 |

> `e2e_checklist.md` records the log line `Loaded chicago: 5217 intersections,
> 77 zones`. The shipped `data/chicago/graph.json` has 12 distinct zone ids.
> `[NEEDS CONFIRMATION]`

**Vectorised simulator.** `NexusSimEnv` switches to `VectorizedTrafficSim`
above 100 agents (`ml/env/nexus_sim_env.py`). Keep that threshold: the older
dict-based simulator takes hours on Chicago.

**Transfer and evaluation**

```bash
python -m train.transfer --source chicago --target piedmont --episodes 200 --lr 1e-4 --device cuda
python -m train.evaluate --cities toy piedmont chicago \
  --checkpoint checkpoints/chicago/199.pt --episodes 20
```

`train.evaluate` writes `ml/results/comparison.json`. The dashboard serves that
file through the Vite dev proxy and renders it in `ComparisonPanel.tsx`.

### 4.7 ONNX Export and Engine Inference

```bash
cd ml
python -m export.export_onnx --checkpoint checkpoints/toy/500.pt --output policy.onnx
python -m export.validate_onnx

engine --city piedmont --agents 500 --policy policy.onnx
```

If `--policy` is absent, or the model fails to load, the engine warns and keeps
Webster timing.

**Latency budget:** p95 ≤ 8 ms per batched decision (PRD NFR-4).

```text
$ bench_inference --model tests/fixtures/policy_toy.onnx            # batch 64
Latency (ms): min=0.0098 avg=0.0119 p95=0.0179 max=0.0454   PASS
$ bench_inference --model tests/fixtures/policy_toy.onnx --batch 256
Latency (ms): min=0.0164 avg=0.0179 p95=0.0265 max=0.0775   PASS
```

Measured on Windows x64, MinGW-w64 GCC 16, onnxruntime 1.24.1 (CPU). The
benchmark exits with code 2 when it exceeds the budget.

### 4.8 The 12-Algorithm RL Harness

`ml/algo/base_trainer.py` provides `BaseTrainer`, `SingleAgentNexusSimEnv`,
`parse_device_arg`, `report_device`, and `run_benchmark`. Three suites use it:

```bash
cd ml
python -m algo.value_based          # Q-Learning, SARSA, DQN, DDQN, Dueling DQN
python -m algo.policy_based         # REINFORCE, A2C, PPO
python -m algo.continuous_control   # DDPG, TD3, SAC on Pendulum-v1
```

Each suite accepts `--device` only. There is no `--algos`, no `--city`, no
`ml/algo/benchmark.py`, no `ml/algo/configs.yaml`, and no `ml/eval/report.py`.
The `US-D09` benchmark command (`--algos all`) referenced in the user stories does not exist; see `docs/RL_DOCUMENTATION.md` §8 for the documented gap.

### 4.9 Running the Sidecars

```bash
cd ml/cv && python virtual_camera_service.py     # port 9003
cd ml/nlp && python chat_service.py              # port 9004
```

Run the NLP service from `ml/nlp`. The `/incident` handler imports
`incident_parser` relatively.

Standalone camera demo: `python ml/cv/virtual_camera.py`.

### 4.11 NexusTwin Dynamic Ingestion Engine & Time-Machine Platform

NexusTwin introduces dynamic, on-demand digital twin generation and interactive simulation inspection without restarting the stack.

#### 1. Ingestion Modes
- **Stage 1: Direct File Ingestion (`POST /api/v1/twin/upload`)**
  Accepts user-uploaded `.osm`, `.pbf`, or `.graphml` files (up to 500 MB). The engine validates geometry, extracts the largest strongly connected component (SCC), infers highway lanes, clusters spatial zones, and synthesizes a gravity OD demand matrix via `pipeline/src/dynamic_ingest.py`.
- **Stage 2: Global Geocoded Search (`POST /api/v1/twin/search`)**
  Accepts free-text location queries (e.g. `Shantigram, Ahmedabad`). Resolves geographic bounds via Nominatim and streams live highway vector geometries from a 3-tier Overpass QL mirror pool in $\le 20$ seconds.

#### 2. REST & Streaming API Endpoints (`gateway/twin_router.py`)
- `GET /api/v1/twin/cities`: Lists all synthesized digital twin cities and their topology metadata.
- `POST /api/v1/twin/upload`: Multipart file upload returning `{job_id, status: "queued", stream_url}`.
- `POST /api/v1/twin/search`: JSON search query returning `{job_id, status: "queued", stream_url}`.
- `GET /api/v1/twin/progress/{job_id}`: Granular progress tracking supporting JSON polling and Server-Sent Events (`Accept: text/event-stream`).
- `DELETE /api/v1/twin/cities/{city_id}`: Deletes generated city topology files and cleans up `pipeline/cities.yaml`.

#### 3. Frontend Inspection & What-If Branching
- **Time-Machine State Scrubber (`dashboard/src/components/SimControls.tsx`)**:
  Interactive timeline slider supporting scrub-to-tick navigation, paused inspection, and non-destructive scenario forking (`⚡ Fork`) to compare diverging control policies.
- **Explainable AI (XAI) Signal Drawer (`dashboard/src/components/XaiInspectionDrawer.tsx`)**:
  Interactive inspection dock showing Interval Type-2 Fuzzy Footprint of Uncertainty (FOU), Upper/Lower membership functions, Karnik-Mendel defuzzification, Webster formula cycle splits ($C_0$), and MAPPO actor-critic action probabilities.

### 4.10 Generating City Data

```bash
cd pipeline
pip install -r requirements.txt

python src/download.py --city piedmont   # raw.graphml
python src/clean.py --city piedmont      # simplify + largest SCC
python src/lanes.py --city piedmont      # infer lane counts
python src/zones.py --city piedmont      # tag zones
python src/export.py --city piedmont     # write data/<city>/graph.json
```

**OD matrices**

```bash
python src/download_od.py --city chicago --weekdays 10 --year 2019 --month 10
python src/od_matrix.py --city chicago --weekdays 10 --year 2019 --month 10
python src/od_proxy.py --city paris --trips-per-node 0.5
```

**Validation**

```bash
python src/validate.py --city chicago --duration 60 --start-hour 8
```

The checkpoint passes when **MAPE ≤ 25 %** and **at least 75 % of sampled
corridors are within 25 %**. Proxy matrices carry `validation_safe: false` and
`validate.py` refuses them.

**GA calibration**

```bash
python src/optimize_calibration.py --city chicago \
  --pop-size 10 --generations 5 --workers 2 --duration 30
```

The GA searches four genes: `speed_factor`, `route_spread`, `chaos`, and
`demand_scale`. Each fitness evaluation runs one `--fast --no-ws` engine
subprocess through `multiprocessing.Pool`. Output:
`data/<city>/ga_calibration_report.json`.

**CV congestion classification**

```bash
python src/cv_congestion.py --city chicago
```

Writes `data/<city>/cv_congestion.json` with `{level, confidence, source}` per
zone and hour. The module is a stub; see §5.3.

### 4.11 Tests

**C++ (GoogleTest)**

```bash
cd engine && mkdir -p build && cd build
cmake .. -G Ninja -DENABLE_TESTING=ON
cmake --build .
ctest --output-on-failure
./bench_quadtree
```

On Windows, run the test binary through `ctest`; a direct call exits with no
output when the MinGW runtime DLLs are missing from `PATH`.

**Pipeline (pytest)** — 27 tests

```bash
cd pipeline && python -m pytest tests/ -v
```

**ML (pytest)** — 78 tests

```bash
cd ml && python -m pytest tests/ -v
```

**Dashboard**

```bash
cd dashboard
npm run lint     # oxlint
npm run test     # placeholder: prints "Dashboard test passed"
```

The dashboard has no real test suite.

**CI** — `.github/workflows/ci.yml` (Node 22) runs pipeline pytest, ML pytest,
the C++ build with `-DENABLE_TESTING=ON` plus `ctest`, and the dashboard
install plus test on every push and pull request.

**Result of the verification run on 2026-10-24**

| Suite | Result |
|---|---|
| Pipeline pytest | 26 passed, 1 failed (`test_od_proxy.py::test_proxy_reproduces_real_chicago_intra_zone_share`) |
| ML pytest | 78 passed |
| C++ ctest | Not run. The local build was configured with `ENABLE_TESTING=OFF`. |

The pipeline failure is a symptom of the Chicago zone mismatch in §5.3: the
proxy reproduces 1.8 % intra-zone trips against a measured 11.1 %, because the
current Chicago graph has 12 zones and the OD matrix has 77.

---

## 5. Current Status

### 5.1 Phase Progress

Source: `docs/BACKLOG.md`, snapshot 2026-10-21, corrected against the code on
2026-10-24.

| Phase | Area | Status |
|---|---|---|
| 0 | Repository skeleton and CI | DONE |
| 1 | Graph loading and city geometry | DONE |
| 2 | Agent system and pathfinding | DONE |
| 3 | Quadtree and collision avoidance | DONE |
| 4 | WebSocket stream and dashboard map | DONE |
| 5 | Fixed-cycle signal baseline | DONE |
| 6 | Real OD demand and validation | DONE, acceptance pending (MAPE 21.6 %, pass rate 63.6 %) |
| 7 | MARL environment and MAPPO | DONE |
| 8 | ONNX export and C++ inference | DONE |
| 9 | Multi-city training and validation | PARTIAL |
| 10 | Policy toggles and dashboard polish | DONE |
| 11 | Hardening, documentation, demo | DONE |
| 12 | Signal policy abstraction | DONE |
| 13 | GA calibration and fuzzy controller | DONE |
| 14 | CV: real-world congestion | **STUB — not delivered** |
| 15 | CV: synthetic virtual camera | DONE, with limits |
| 16 | NLP: live metrics chat | **PARTIAL** (rule-based intents only) |
| 17 | NLP: incidents to simulation | DONE |
| 18 | Cross-subject hardening and demo | DONE |
| 19 | Shared RL framework | DONE |
| 20 | Value-based RL suite | DONE |
| 21 | Policy-based RL suite | DONE |
| 22 | Continuous-control suite | DONE |
| 23 | C++ deployment of RL policies | DONE |
| 24 | RL results and documentation | DONE, figures unverified |
| 25 | CV foundation: YOLO and MOG2 | DONE |
| 26–36 | 36-algorithm expansion | PENDING, out of current scope |

### 5.2 Verified Metrics

**Engine performance** — `docs/results.md`, `docs/AI_STRESS_REPORT.md`

| Metric | Value |
|---|---|
| Stress-tested capacity | 20,000 agents, no crash, no leak |
| Spatial query latency | < 0.8 ms per tick at 20k agents |
| Streaming rate | 10 Hz over uWebSockets |
| ONNX p95 | 0.0179 ms (batch 64), 0.0265 ms (batch 256); budget 8 ms |
| AI-mode frame cost | −2.4 FPS against a < 5 FPS budget |

**Chicago validation** — `data/chicago/validation_report.json`, 2026-08-03

| Metric | Value |
|---|---|
| Corridors | 11 |
| Within 25 % | 7 (63.6 %) |
| MAPE | 21.6 % |
| `passes_checkpoint` | `false` |

**GA calibration** — `data/chicago/ga_calibration_report.json`, 2026-09-26

| Metric | Value |
|---|---|
| Generations / population | 15 / 20 |
| Best chromosome | `speed_factor 0.58, route_spread 0.22, chaos 0.08, demand_scale 0.000412` |
| GA MAPE | 15.4 % |
| Manual MAPE | 22.8 % |
| Improvement | 32.5 % |

`docs/results.md` reports this run as 18.3 % against 21.6 % (+15.3 %). The
artifact is newer and authoritative. `docs/BACKLOG.md` also reports a 91 %
corridor pass rate for the GA run. The artifact carries no corridor field, so
that claim is withdrawn.

**MARL against Webster** — `ml/results/comparison.json`

| City | Intersections | Webster | MARL | Improvement |
|---|---|---|---|---|
| toy | 4 | −11,269.82 | −6,857.85 | +39.15 % |
| piedmont | 4 | −26,606.20 | −26,190.70 | +1.56 % |
| chicago_subset | 144 | −124,461.35 | −127,671.62 | −2.58 % |

The file has no Chicago row.

**Signal policies** — `docs/results.md` §5.1

| Policy | Average wait | Gini |
|---|---|---|
| Webster | 42.5 s | 0.48 |
| Fuzzy | 32.1 s | 0.35 |
| MARL | 28.4 s | 0.29 |

`[UNVERIFIED]`. No artifact produces these values. The same applies to the
12-algorithm reward and wait columns: the suites return hardcoded literals
(for example `mean_wait: 38.2` in `ml/algo/value_based.py`).

### 5.3 Known Issues and Limitations

**Blocking the roadmap**

1. **Chicago zone mismatch (P0).** `data/chicago/graph.json` has 12 distinct
   `zone_id` values. `data/chicago/od_matrix.json` has 77 community areas.
   Only 10 ids overlap, so 67 of 77 OD zones have no graph nodes and the engine
   drops those pairs on load. The 2026-08-03 validation report was produced
   against an earlier graph with 77 zones.
2. **The pipeline test suite fails.** `test_od_proxy.py` reports a proxy
   intra-zone share of 1.8 % against a measured 11.1 %. This is the same zone
   mismatch. CI is red until it is fixed.
3. **The PRD success metric is not measured.** No stage reports the PRD target
   of a ≥ 15 % citywide average wait-time reduction. `ml/env/traffic_sim.py`
   has no per-agent wait-time accounting.
4. **Chicago training (task 9.1) has no recorded completion.**
   `ml/checkpoints/` is absent and `comparison.json` has no Chicago row. The
   last log (2026-09-17) showed episode 89 of 200.
5. **Chicago validation does not pass.** 63.6 % of corridors are within 25 %;
   the checkpoint requires 75 %. The failing corridors are river-bridge
   corridors.

**Code and documentation defects**

6. **CV congestion is a stub.** `pipeline/src/cv_congestion.py` builds a
   synthetic tile and returns `random.choice([0,1,2,3])` from both classifiers.
   It makes no network request and reads no API key. The `methodology` string
   in the artifact claims a classical-vs-CNN comparison.
7. **The NLP chat has no live data.** `chat_service.py` has no WebSocket
   client; every answer is a literal. The fallback handler is
   `fallback_llm_stub`, and there is no LLM layer.
8. **The `incident_status` intent is missing.** The `compare_policy` regex
   also matches incident queries first.
9. **The incident gazetteer is a hardcoded 7-street dictionary** (edge ids
   101–114), not a `graph.json` lookup.
10. **The virtual camera draws a grey grid,** not road geometry, and it
    synthesises random agent positions when none are supplied. It is
    request/response REST, not a 1 Hz stream.
11. **`CONTRIBUTING.md`, `docs/adr/`, and `docs/figures/` are absent** though
    Phase 0 tasks 0.9 and 0.10 require them.
12. **`docs/results.md` §4.1 and §5.1 contain numbers no artifact reproduces.**
    The 12-algorithm wait-time values are constants in the suites.
13. **Subject documents carry false status marks.** `CV_DOCUMENTATION.md` marks
    the tile fetch, CNN, and GA fitness term as DONE. `NLP_DOCUMENTATION.md`
    marks the engine WebSocket client and the LLM layer as DONE.
    `SOFT_COMPUTING_DOCUMENTATION.md` and `RL_DOCUMENTATION.md` describe a
    `--signal-policy` flag that does not exist. `RL_DOCUMENTATION.md` also
    cites `benchmark.py`, `configs.yaml`, and `report.py`, which do not exist.

**Operational constraints**

14. `--episodes` is cumulative. A smaller value with `--resume latest` runs
    zero episodes.
15. Do not re-run the CUDA PyTorch install; it downloads a 2.6 GB wheel.
16. MLflow's file store is removed in 3.x. Use the SQLite URI.
17. Keep the `VectorizedTrafficSim` threshold at 100 agents.
18. On Windows, use port 3000 when 5173 has lingering TIME_WAIT sockets.
19. The dashboard has no real test suite.
20. No containerisation or hosting configuration exists.
21. License information is not provided.

### 5.4 Recent Work

| Change | Commit |
|---|---|
| Engine split into `NexusEngine` and `CliConfig` | `f214eea` |
| Thread pool; quadtree and pathfinder optimisation | `6f0767c` |
| Quadtree point-indexing fix | `bc3807a` |
| Latency histogram and frame pacer | `dde056a` |
| What-if policy simulation, transit routing, emissions, transit equity | `5d43bff` |
| Agent path visualisation and city fleet spawning | `7038cd7` |
| In-engine NLP parser and command console | `fc5f8c9` |
| Dashboard glassmorphism theme | `b184e4d` |
| CI Node 22; removed a phantom submodule gitlink | `f46ba50` |
| Endpoint, spawning, and map-control fixes | `446d9a8` (HEAD) |

Uncommitted: `ml/train/device.py`, `ml/requirements-cuda.txt`, changes across
`ml/`, `run.bat`, `README.md`, and `docs/`.

---

## 6. Roadmap & Next Phases

### 6.1 Immediate Priorities

| Priority | Task | Done when |
|---|---|---|
| P0 | Regenerate the Chicago graph and OD matrix from one zone run | Both files share one zone-id space; the pipeline suite is green |
| P0 | Complete the Chicago training run (task 9.1) | `chicago/199.pt` exists and logs show 200 cumulative episodes |
| P0 | Re-run Chicago validation (task 9.2) | `validation_report.json` shows `passes_checkpoint: true` |
| P0 | Add wait-time accounting to `ml/env/traffic_sim.py` | `train.evaluate` reports the PRD wait-time reduction |
| P1 | Add the Chicago row to `ml/results/comparison.json` (task 9.7) | The file has Webster and MARL rows for toy, piedmont, and chicago |
| P1 | Re-seed the Paris and Ahmedabad transfers (task 9.5) | Checkpoints are seeded from the real Chicago policy |
| P1 | Run the transfer sensitivity sweep (task 9.6) | Results for `--chaos` and `--demand-scale` are in `ml/results/` |
| P1 | Verify ONNX inference against the Chicago checkpoint | Parity and p95 checks pass with the real policy |
| P1 | Correct the subject documents and `results.md` status marks | No document claims a stub feature is complete |
| P2 | Write `CONTRIBUTING.md` and `docs/adr/template.md` | Both files exist |
| P2 | Add a dashboard test suite | `npm run test` runs Vitest with React Testing Library |

### 6.2 Milestones

| Milestone | Phase | Gate | Status |
|---|---|---|---|
| M1 Foundation Complete | 8 | `bench_inference` p95 ≤ 8 ms | DONE |
| M2 Extension Complete | 11 | `make demo` from a clean clone in < 30 min | DONE |
| M3 Cross-Subject Integration | 18 | One continuous 4-subject recording | DONE |
| M4 RL Inventory Complete | 24 | 12-algorithm table in `docs/results.md` | DONE, figures unverified |
| M5 CV Expansion Complete | 27 | 12 CV algorithms with results | PENDING |
| M6 SC Expansion Complete | 30 | 12 SC algorithms with results | PENDING |
| M7 NLP Expansion Complete | 33 | 12 NLP algorithms with results | PENDING |
| M8 36-Algorithm Integration | 36 | Integrated demo and full documentation | PENDING |

Source: `docs/TEAM_IMPLEMENTATION_PLAN.md`.

### 6.3 Planned Phases 26–36

`docs/BACKLOG.md` records these phases as PENDING and out of current scope.
`[NEEDS CONFIRMATION]` — confirm that this expansion remains the direction.

| Phase | Goal | Milestone | Priority |
|---|---|---|---|
| 26 | CV tracking and segmentation: DeepSORT, U-Net, Mask R-CNN. Feed CV road condition into the fuzzy controller. | — | P3 |
| 27 | CV motion, anomaly, and lane detection; crowd density. Feed anomaly alerts into NLP event extraction. | M5 | P3 |
| 28 | SC metaheuristics: PSO, simulated annealing, evolutionary strategies, next to the GA. Add a convergence panel. | — | P3 |
| 29 | SC swarm and hybrid: ant colony routing, ABC, ANFIS, type-2 fuzzy sets. Add a fuzzy-rule panel. | — | P3 |
| 30 | SC genetic programming, rough sets, NSGA-II. Add a Pareto-front panel. | M6 | P3 |
| 31 | NLP core: intent classifier, incident parser, sentiment, classifier. Wire NLP into SC calibration. | — | P3 |
| 32 | NLP extraction: named-entity recognition, event extraction, coreference. Add an NER panel. | — | P3 |
| 33 | NLP advanced: summarisation, question answering, stance, knowledge graphs. Add a knowledge-graph panel. | M7 | P3 |
| 34 | Cross-subject integration: event bus with a CV → NLP → engine chain, NLP → RL adaptation, SC → RL warm start, CV → SC fitness. | — | P3 |
| 35 | Unified Algorithm Explorer: subject tabs, algorithm cards, comparison view. Algo Explorer API on port 9006. | — | P3 |
| 36 | Results and documentation: all 36 algorithms on the toy graph, cross-subject tables, demo video. | M8 | P3 |

Recommended order if the expansion starts: Phase 31–33 first, because the same
work closes the live-metrics gap in §5.3. Phases 26–27 and 28–30 follow.

### 6.4 Extension Points

- **CV:** multi-city tiles, a live overlay, object tracking, lane-level
  congestion, anomaly detection feeding incidents, aerial imagery, sim-to-real
  transfer.
- **NLP:** multi-city gazetteers, richer intents, conversational context,
  severity calibration, cross-subject chat, multilingual support, streaming.
- **RL:** full Chicago training, transfer with sensitivity analysis, ONNX
  deployment, the 12-algorithm harness, ONNX algorithm dispatch, a CV-shaped
  reward.
- **SC:** multi-objective GA with a Pareto front, neuro-fuzzy and ANFIS,
  self-tuning membership functions, PSO, a fuzzy warm start for RL, multi-city
  GA transfer, dynamic fuzzy inputs, type-2 fuzzy sets.

---

## 7. Contributing Guidelines

### 7.1 Commit Format

```
<type>(<scope>): <short summary>
```

| Type | Use |
|---|---|
| `feat` | New capability |
| `fix` | Bug fix |
| `refactor` | Behaviour-preserving change |
| `test` | Test change |
| `docs` | Documentation |
| `chore` | Tooling, dependencies, housekeeping |

| Scope | Area |
|---|---|
| `engine` | C++ engine |
| `pipeline` | Data pipeline |
| `ml` | ML, CV, and NLP |
| `dashboard` | Frontend |
| `ci` | CI and tooling |

Example: `feat(engine): add quadtree proximity detection for agent collision`

### 7.2 Branch Naming

| Prefix | Use |
|---|---|
| `feature/<description>` | New feature |
| `fix/<description>` | Bug fix |
| `refactor/<description>` | Refactor |
| `data/<description>` | Pipeline and data |
| `experiment/<description>` | ML experiment |
| `integration/<description>` | Cross-subject work |

### 7.3 Size Discipline

- Keep each commit to about 100 inserted lines or fewer.
- Split larger changes into sub-commits. Each sub-commit must build and pass
  tests on its own.
- Any change above 100 insertions in total opens a pull request.

### 7.4 Pull Requests

- State what changed, why, and what was tested.
- All CI checks must pass before merge.
- Never force-push to `main`.
- Integration branches need two reviewers. Other branches need one.

### 7.5 Local Hooks

Run `pre-commit install` to enable clang-format (C++), black and isort
(Python), and eslint (JavaScript and TypeScript).

### 7.6 Test Expectations

| Change type | Required checks |
|---|---|
| C++ | `ctest --output-on-failure` in `engine/build` |
| Pipeline | `python -m pytest tests/ -v` in `pipeline/` |
| ML | `python -m pytest tests/ -v` in `ml/` |
| Dashboard | `npm run lint` and `npm run test` in `dashboard/` |
| Interface, CLI flag, or config key | Run `docs/e2e_checklist.md` and update the affected documents |

### 7.7 Code and Data Rules

- The engine is the only writer of simulation truth.
- Broadcast fields are additive only.
- New cities and per-city keys go in `pipeline/cities.yaml` only.
- Do not commit weights, checkpoints, MLflow databases, or training logs.
  Commit the result JSON and the MLflow run ID.
- Do not commit API keys, map tiles, or raw `.graphml` intermediates.
- Keep `TODO` out of `engine/src` and `ml/env`.

### 7.8 File Ownership

| Area | Owner |
|---|---|
| `engine/src/` | Engine owner |
| `engine/schemas/` | Engine owner |
| `pipeline/src/`, `pipeline/cities.yaml` | Pipeline owner |
| `ml/env/` | Engine owner |
| `ml/algo/` | Pipeline owner |
| `ml/cv/` | CV owner |
| `ml/nlp/` | NLP owner |
| `dashboard/src/` | Dashboard owner |
| `docs/` | Documentation owner |
| Root `Makefile` | Engine owner |

### 7.9 Documentation Rules

- Update the affected document in the same commit as the code change.
- Record the commit SHA, the city, and the date for each `e2e_checklist.md`
  run.
- Mark unverified claims as unverified. Do not publish a number that no
  artifact or command produces.

---

## Appendix A — Data Formats

The canonical definitions live in two files:

| File | Purpose |
|---|---|
| `docs/graph_schema.md` | JSON Schema for `data/<city>/graph.json` |
| `docs/od_matrix_schema.md` | Field reference for `data/<city>/od_matrix.json` |

Summary:

- `graph.json` holds `nodes[]` (`id`, `lat`, `lon`, `zone_id`) and `edges[]`
  (`u`, `v`, `length_m`, `lanes`).
- `od_matrix.json` holds metadata, a `zones` map, and an `od[]` array. Each
  entry has `origin`, `destination`, `hourly[24]` (vehicles per hour), and
  `hourly_tt[24]` (observed journey time in seconds).
- `journey_times.csv` columns: `agent_id`, `type`, `origin`, `destination`,
  `origin_zone`, `destination_zone`, `start_time`, `journey_time_seconds`,
  `status`.

**Artifacts**

| File | Produced by | Purpose |
|---|---|---|
| `data/<city>/validation_report.json` | `pipeline/src/validate.py` | Corridor comparison, MAPE, checkpoint verdict |
| `data/<city>/ga_calibration_report.json` | `pipeline/src/optimize_calibration.py` | GA convergence and before/after MAPE |
| `data/<city>/cv_congestion.json` | `pipeline/src/cv_congestion.py` | Per-zone, per-hour congestion level (stub) |
| `ml/results/comparison.json` | `ml/train/evaluate.py` | MARL against Webster by city |
| `ml/checkpoints/<city>/<episode>.pt` | `ml/train/train.py` | Checkpoint (gitignored) |
| `ml/policy.onnx` | `ml/export/export_onnx.py` | Engine policy input |

## Appendix B — Document Map

| Document | Role | Status |
|---|---|---|
| `README.md` (root) | User-facing readme | Current (updated 2026-10) |
| `docs/README.md` | Docs index | Current (updated 2026-10) |
| `docs/NEXUS-SIM-DOCUMENTATION.md` | This master document | Current |
| `docs/PRD.md` | Product goals, users, non-goals, metrics, risks | Source of record |
| `docs/TRD.md` | Technical requirements catalogue | Source of record |
| `docs/TECH_STACK.md` | Technology stack | New — fills previously missing spec |
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phases 0–36, milestones, checkpoints, risk register | Source of record; status line is stale |
| `docs/BACKLOG.md` | Per-phase status and open items | Current to 2026-10-21 |
| `docs/results.md` | Benchmark and validation tables | Current, with the unverified tables marked |
| `docs/AI_STRESS_REPORT.md` | Phase 8.8 latency and frame-rate gate | Current |
| `docs/e2e_checklist.md` | Manual end-to-end checks | Current |
| `docs/graph_schema.md`, `docs/od_matrix_schema.md` | Data format references | Current |
| `docs/futureplanning.md` | Production roadmap | Planning-stage, not committed scope |
| `docs/RL_DOCUMENTATION.md` | RL subject record | New — accurate observation/reward/algorithm/training record |
| `docs/CV_DOCUMENTATION.md` | CV subject record | New — accurate congestion/virtual-camera record |
| `docs/NLP_DOCUMENTATION.md` | NLP subject record | New — accurate chat/incident record |
| `docs/SOFT_COMPUTING_DOCUMENTATION.md` | SC subject record | New — accurate GA/fuzzy/optimizer record |
