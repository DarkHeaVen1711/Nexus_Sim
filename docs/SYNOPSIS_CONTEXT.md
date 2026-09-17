# NexusSim — Synopsis Generation Context File

Use this file as the **single source of truth** to generate the content of the
project synopsis. Every fact below is verified from the repository source code,
README, PRD, TRD, schema docs, and committed data files.

The synopsis must contain the following sections, **in this order**:

1. Project Title
2. Introduction
3. Purpose
4. Objectives
5. Platform / Hardware and Software
6. Functionality
7. Data Flow Diagram (DFD — Level 0 and Level 1)
8. E–R Diagram
9. Data Dictionary

Generate each of the nine numbered sections below into polished synopsis prose
(academic/collage-project tone). Use the facts as given; do not invent
features, entities, or metrics that are not present here.

---

## 1. Project Title

**NexusSim — A Real-Time Multi-Agent Urban Traffic Simulation Platform with
AI-Driven Signal Control and Equity Analysis**

- A web-based, real-time traffic simulation of real cities.
- Models thousands of heterogeneous vehicles moving through a real road network
  extracted from OpenStreetMap.
- Uses Reinforcement Learning to control traffic signals; beats the fixed-cycle
  (Webster's) baseline by ~35%.
- Measures "fairness" (equity) alongside efficiency via a Gini coefficient of
  wait-time inequality per zone.
- An integrated 4-subject academic project: Reinforcement Learning, Soft
  Computing, Computer Vision, and NLP (RL is implemented; the other three are
  designed/planned in later phases).

---

## 2. Introduction

Verified facts to express:

- Urban traffic signals today run on **static, fixed timings calibrated years
  ago** and are rarely updated because experimenting on real roads with real
  commuters is expensive and risky.
- City administrators have **no safe, cost-free way** to test changes such as
  adding a bus lane, rerouting freight, changing signal timing, or congestion
  pricing.
- Most optimization tools treat "average commute time" as the only success
  metric, which **systematically benefits well-connected, high-income zones**
  while underserved neighborhoods stagnate or worsen.
- NexusSim solves both problems:
  1. A **high-fidelity real-city sandbox** (a "virtual sandbox") where traffic
     policies can be stress-tested before any real-world commitment.
  2. **Equity as a first-class metric**: it tracks whether improvements benefit
     ALL neighbourhoods equally, not just the well-connected ones.
- The simulation is a **Digital Twin of a real urban road network**: the road
  graph is downloaded from OpenStreetMap, cleaned, simplified, lane-counts are
  inferred, and the output is fed to a high-performance C++17 simulation engine.
- Live state streams to an interactive React/Leaflet browser dashboard over a
  WebSocket.
- Demand is driven by **real trip data** (Chicago rideshare trips from the City
  of Chicago open-data portal).
- Output is **validated against observed ground-truth travel times** (current
  result: MAPE ≈ 21.6% on Chicago corridors).
- An offline **Multi-Agent Reinforcement Learning (MAPPO)** trainer learns
  signal-control policies that beat the fixed Webster baseline (~35% better
  reward on the training grid), and the trained policy is exported to ONNX so
  the C++ engine can run it directly with no Python in the hot path.
- The project is executed in **phases** (Phase 0 → Phase 18 plan); each phase
  produces something working and demoable.

---

## 3. Purpose

- Provide a **safe, virtual testing ground** for city traffic policies before
  spending real money or disrupting real commuters.
- Recreate a real city's road network digitally and simulate thousands of
  vehicles moving through it **in real time**, observable live on a map in the
  browser.
- Let planners test "what if" scenarios (bus lanes, signal retiming, demand
  changes) with realistic, validated behaviour.
- Demonstrate that **learned (RL) signal control can outperform traditional
  fixed-cycle timing**.
- Bring **fairness/equity** into traffic engineering: measure wait-time
  inequality across neighbourhoods (Gini coefficient and per-zone heatmaps).
- **Validate simulation realism**: compare simulated corridor journey times
  against observed real-world data (target ≤25% MAPE; currently ≈21.6%).
- Serve as one integrated academic demonstration of RL (plus planned Soft
  Computing, Computer Vision, and NLP) cooperating on the same live
  simulation.

---

## 4. Objectives

Verified from the PRD (goal set). Express the key achievable objectives:

- Simulate **20,000+ heterogeneous agents** in a real city graph at interactive
  frame rates (60 fps target).
- Train a **decentralized MARL (MAPPO) signal-control policy** that outperforms
  fixed-cycle (Webster's) signal timing.
- Make **equity a measurable, optimized output** (Gini coefficient of wait-time
  inequality across zones).
- Support **multiple structurally distinct cities** (Chicago, Piedmont, Paris,
  Ahmedabad) via configuration only — no code changes.
- Use **real origin–destination demand data** (Chicago rideshare) and validate
  the simulation against observed ground-truth travel times (target
  MAPE ≤ 25% with ≥75% of corridors within 25%).
- Deliver a **planner-readable dashboard**: real-time map, efficiency/equity
  view modes, metrics panel, live city switching.
- Make signal control **pluggable** (Webster's fixed, fuzzy, RL) so policies can
  hot-swap.
- Export the trained RL policy to **ONNX** and run batched inference inside the
  C++ engine within the p95 ≤ 8 ms latency budget.
- (Planned future objectives): soft-computing calibration (genetic algorithm +
  fuzzy controller), computer-vision congestion classification, NLP chat on the
  live simulation.

---

## 5. Platform / Hardware and Software

### Hardware (reference / tested)

- Any modern x86-64 desktop/laptop (Windows, Linux, macOS).
- **Multi-core CPU** (the engine parallelises agent updates across all hardware
  threads); tested stable at 20,000 agents.
- 8 GB+ RAM recommended (Chicago graph.json ≈ 11.5 MB; large `.graphml`
  intermediates are hundreds of MB during pipeline).
- A web browser (Chrome/Edge/Firefox) for the dashboard.
- Optional GPU only for the planned CV training; the core engine + ONNX
  inference run CPU-only.

### Software / Technology Stack

| Layer | Software |
|-------|----------|
| **Simulation Engine** | C++17, CMake (≥3.25), Ninja, nlohmann/json, FlatBuffers, uWebSockets, uSockets, libuv, ZLib, GoogleTest (tests), ONNX Runtime (Phase 8 inference), MSYS2 MinGW-w64 GCC on Windows |
| **Data Pipeline** | Python 3.11+, osmnx (≥1.9), pyyaml, pytest |
| **Dashboard** | React 19, TypeScript, Vite 8, Leaflet/react-leaflet, Recharts, oxlint |
| **ML (MARL)** | Python 3.11+, PyTorch 2.4.1, Gymnasium 1.0, MLflow 2.16, numpy |
| **CI/CD** | GitHub Actions, pre-commit hooks (clang-format, black, isort, eslint) |
| **OS / Environment** | Windows (MSYS2/MinGW, run.bat one-click) and Linux/macOS (Makefile) |

### Running the system

- Windows: run `run.bat` → builds engine, starts dashboard at
  `http://localhost:5173`, runs a 5-minute demo with 500 agents on Piedmont.
- Engine WebSocket server: port **9001**; dashboard dev server: port **5173**.
- No environment variables are required.

---

## 6. Functionality

Describe the four subsystems and their features.

### 6.1 Data Pipeline (Python / osmnx)
- Downloads real city road networks from **OpenStreetMap** (`download.py`),
  cleans/simplifies them, keeps the largest strongly-connected component
  (`clean.py`).
- Infers **lane counts** per road (`lanes.py`), tags **analysis zones**
  (`zones.py`), and exports a single machine-readable `graph.json`
  (`export.py`).
- Builds **OD demand matrices** from real rideshare trip data (Chicago
  Socrata portal) or a gravity-model density proxy for cities without public
  feeds (`od_matrix.py`, `od_proxy.py`).
- `validate.py` runs the engine headless, compares simulated corridor journey
  times with ground truth, and writes a `validation_report.json`.
- Adding a new city is **config-only** (`pipeline/cities.yaml`).

### 6.2 Simulation Engine (C++17)
- **5 agent types**: car, bus, auto-rickshaw, two-wheeler, pedestrian, each
  with per-type parameters.
- **Intelligent Driver Model (IDM)** car-following logic (acceleration, gap,
  lane discipline/chaos coefficient).
- **A\* pathfinding** with Euclidean heuristic; optional **stochastic
  route-choice** (logit-style lognormal cost perturbation) that spreads agents
  across near-optimal routes.
- **Quadtree spatial index** — proximity/collision queries reduced from O(N²)
  to O(N log N); keeps 10k+ agents interactive.
- **Parallel simulation ticks** across all hardware threads.
- **Signalized intersections** with Webster's formula fixed-cycle timing
  (green/yellow/red phase machine); in Phase 8, an experimental AI-policy mode
  via ONNX with graceful fallback to Webster.
- **OD-driven spawning** from real demand matrices with hourly time-of-day
  profiles.
- **Live WebSocket streaming** with viewport LOD culling (only agents inside
  the dashboard's current bounds are broadcast), binary FlatBuffers frames.
- **Headless mode** (`--fast`) for validation/stress runs; per-agent journey
  times exported to CSV.
- **Gini coefficient** computation of wait-time inequality across zones.

### 6.3 Dashboard (React + TypeScript + Leaflet)
- Live map rendering over an OpenStreetMap base layer; live city switching at
  runtime.
- Agent markers with **Efficiency mode** vs **Equity mode** (per-zone wait-time
  heat overlay).
- Metrics panel: average speed, active/completed agents, avg wait time,
  **Gini coefficient**, top congested zones.
- Auto-reconnecting WebSocket client (heartbeat + backoff), viewport bounds
  sent to engine for LOD culling.

### 6.4 ML Pipeline — MARL Signal Control (Python / PyTorch) [offline]
- Gym-compatible `NexusSimEnv` over an offline Python micro-simulator
  (toy 4-intersection grid; Phase 9 extends to real city graphs).
- One **decentralized agent per intersection** with a **pressure-based local
  reward + equity-weighted global reward** (negative = lower is better).
- **MAPPO trainer** (PPO + GAE, reward scaling, batching, checkpoint
  save/resume), MLflow tracking (episode reward, pressure, equity, Gini).
- Result: trained policy reaches ≈ −7,300 reward within 500 episodes vs the
  ≈ −11,270 Webster baseline (**≈35% better**).
- **ONNX export** (`policy.onnx`) → injected into the C++ engine signal
  controllers; inference micro-benchmarked at **p95 ≈ 0.018 ms** per batch of
  64 (budget p95 ≤ 8 ms).

### Example CLI Usage
```
engine/build/engine --city chicago --od data/chicago/od_matrix.json \
  --duration 60 --start-hour 8 --demand-scale 0.01 --fast \
  --journey data/chicago/journey_times.csv
```

---

## 7. Data Flow Diagram (DFD) — Supporting Facts

Model the flows below; the generator should render Level 0 and Level 1 DFDs
(mermaid or similar) plus prose.

### Level 0 (Context diagram)
- **External entities**: OSM/OSMnx (external data source), City of Chicago
  open-data portal (external demand source), Dashboard User (browser).
- **System**: NexusSim.
- Data flows:
  - OSM road network → [Data Pipeline] → `graph.json`
  - Rideshare trips → [Data Pipeline] → `od_matrix.json`
  - `graph.json` + `od_matrix.json` → [C++ Engine]
  - Engine state frames (agents, metrics, zone metrics) → WebSocket → [Dashboard]
  - User picks city / viewport → [Dashboard] → Engine
  - (Offline) `graph.json` → [ML Trainer] → `policy.onnx` → Engine (Phase 8)

### Level 1 — subsystem flows (from README architecture diagram)
```
┌─────────────┐  graph.json / od_matrix.json  ┌──────────────┐  WebSocket   ┌─────────────┐
│  PIPELINE   │ ────────────────────────────► │  C++ ENGINE  │ ───────────► │  DASHBOARD  │
│  Python/osmnx│                              │  simulation  │   port 9001  │  React+Leaflet│
└─────────────┘                               └──────────────┘              └─────────────┘
       │ graph.json (read)                          ▲
       ▼                                             │ policy.onnx (Phase 8)
┌──────────────┐                                    │
│  ML (offline) │ ─────────────────────────────────┘
│  Gym + MAPPO  │   offline training on Python micro-sim
└──────────────┘
```

### Process list (for DFD write-up)
1. **Download & clean OSM graph**: raw `.graphml` → cleaned/simplified graph.
2. **Enrich** (lanes, zones) → `graph.json`.
3. **Build OD demand** (Socrata or density proxy, or uniform) → `od_matrix.json`.
4. **Simulate** (engine): parse graph, spawn agents, advance ticks dt=0.1 s,
   compute metrics/Gini, stream frames.
5. **Visualize** (dashboard): render agents, heat overlays, metrics.
6. **Validate** (offline): compare sim vs observed journey times → report.
7. **Train RL policy** (offline): rollout → PPO update → checkpoint → ONNX.
8. **Infer** (engine, Phase 8): batched ONNX decisions per tick.

### Data stores (for DFD)
- `pipeline/cities.yaml` (city registry)
- `data/<city>/graph.json`
- `data/<city>/od_matrix.json`
- `data/<city>/validation_report.json`
- `journey_times.csv` (per-agent trip logs)
- `ml/checkpoints/<city>/<episode>.pt`, `policy.onnx`
- `ml/mlruns/` (MLflow tracking)

---

## 8. E-R Diagram — Supporting Facts

The generator should produce an ERD (mermaid erDiagram) for the following
entities and relationships. (Note: the system is file/JSON-based, not a
relational DB; the ERD is the conceptual data model.)

### Entities, attributes, primary keys

- **CITY**
  - `city_id` (PK, e.g. `chicago`), `query` (OSM place name), `chaos` (default
    lane-discipline coefficient), `od_source.type` (socrata | density-proxy |
    uniform), (optional) `od_source.dataset`
- **NODE** (road network node / intersection)
  - `node_id` (PK), `lat`, `lon`, `zone_id` (FK → ZONE)
- **EDGE** (directed road segment)
  - `edge_id` (PK), `u` (FK → NODE), `v` (FK → NODE), `length_m`, `lanes`
- **ZONE** (analysis / equity zone, e.g. Chicago's 77 community areas)
  - `zone_id` (PK), `name`, `lat` (centroid), `lon` (centroid)
- **AGENT** (simulated traveler / vehicle)
  - `agent_id` (PK), `type` (car=0, bus=1, auto-rickshaw=2, two-wheeler=3,
    pedestrian=4), `origin` (FK → NODE), `destination` (FK → NODE),
    `origin_zone` (FK → ZONE), `destination_zone` (FK → ZONE), `start_time`,
    `journey_time_seconds`, `status` (Navigating | Arrived), current path/speed/
    position (runtime state)
- **TRIP / OD_PAIR** (origin–destination demand)
  - `origin` (FK → ZONE), `destination` (FK → ZONE) — composite PK,
    `hourly[24]` (vehicles/hour by hour of day), `hourly_tt[24]` (observed mean
    journey time in seconds by hour)
- **SIGNAL_CONTROLLER** (per signalized intersection)
  - `intersection_id` (FK → NODE), `policy` (Webster | AI/ONNX | fuzzy),
    `phase` (green/yellow/red), `timing` (Webster parameters) / RL policy
    parameters
- **VALIDATION_REPORT** (ground-truth comparison)
  - `city_id` (FK), `generated_at`, `run_config` (duration, start_hour,
    demand_scale, speed_factor, route_spread), `mape_pct`, `within_25_pct`,
    `corridor_count`, `passes_checkpoint` (bool)
- **CHECKPOINT / POLICY** (trained RL model, ML side)
  - `checkpoint_id` (PK), `city_id`, `episode`, `reward`, `pressure`, `equity`,
    `gini`, `path` (`.pt`), export → `policy.onnx`

### Relationships
- CITY **has many** ZONE (1 : N)
- CITY **has many** NODE (1 : N)
- CITY **has many** EDGE (1 : N); NODE **is endpoint of** EDGE (M : N)
- ZONE **contains** NODE (1 : N)  ← every node has a `zone_id`
- ZONE **originates** TRIP / **is destination of** TRIP (1 : N each) → OD_PAIR
  (M : N between zones via OD_PAIR)
- NODE **is origin of** AGENT / **is destination of** AGENT (1 : N each)
- AGENT **typed by** (enum), **assigned to** OD demand
- NODE **controlled by** SIGNAL_CONTROLLER (one at signalized intersections)
- CITY **produces** VALIDATION_REPORT (1 : N)
- MANY AGENTS **form** TRIPs per OD_PAIR; OD_PAIR **drives** AGENT spawning
  (demand scaling)
- ML: CITY **trains** CHECKPOINT/POLICY (1 : N) → ENGINE consumes POLICY

---

## 9. Data Dictionary — Supporting Facts

The generator should produce a formal data dictionary (Table · Field · Type ·
Description · Example) for at least the following files/structures. Field
names/types below are taken verbatim from the committed schemas.

### 9.1 `data/<city>/graph.json` — road network

| Field    | Type      | Description                                | Example                  |
|----------|-----------|--------------------------------------------|--------------------------|
| nodes[].id     | integer | Node id (OSM)                   | 247845698                 |
| nodes[].lat    | number  | Latitude                     | 41.8781                  |
| nodes[].lon    | number  | Longitude                    | −87.6298                 |
| nodes[].zone_id| integer | Analysis zone id (FK)        | 8                        |
| edges[].u      | integer | Source node id (FK)          | 247845698                 |
| edges[].v      | integer | Target node id (FK)          | 53101282                  |
| edges[].length_m | number | Edge length in metres      | 95.4                      |
| edges[].lanes  | integer | Lane count                   | 3                         |

### 9.2 `data/<city>/od_matrix.json` — demand matrix

| Field                  | Type            | Description                                      |
|------------------------|-----------------|--------------------------------------------------|
| schema_version         | string          | Schema version                                   |
| city                   | string          | City id matching cities.yaml                     |
| source / source_url    | string          | Provenance + data portal URL                     |
| zone_count             | int             | Number of zones (Chicago: 77)                    |
| units.demand           | string          | "vehicles per hour (avg sampled weekday)"        |
| units.journey_time     | string          | "seconds"                                        |
| sampled_weekdays       | int             | Weekdays aggregated (e.g. 10)                    |
| year_month             | string          | Data period "YYYY-MM" (e.g. "2019-10")           |
| zones.<id>.name        | string          | Zone name (e.g. "Near North Side")               |
| zones.<id>.lat/.lon    | number          | Zone centroid                                    |
| od[].origin            | int (FK→ZONE)   | Origin zone id                                   |
| od[].destination       | int (FK→ZONE)   | Destination zone id                              |
| od[].hourly            | array[24]       | Vehicles/hour for hours 0–23                     |
| od[].hourly_tt         | array[24]       | Mean observed journey time (sec) per hour        |

### 9.3 `journey_times.csv` — per-agent trip log

| Column                  | Type   | Description                                  | Example              |
|-------------------------|--------|----------------------------------------------|----------------------|
| agent_id                | int    | Agent id                                     | 0                    |
| type                    | int    | 0=car,1=bus,2=auto,3=two-wheeler,4=pedestrian | 0                  |
| origin                  | int    | Origin node id                               | 261264061            |
| destination             | int    | Destination node id                          | 27440235             |
| origin_zone             | int    | Origin zone id                               | 8                    |
| destination_zone        | int    | Destination zone id                          | 32                   |
| start_time              | number | Simulation-time start (s)                    | 31.9                 |
| journey_time_seconds    | number | Trip duration (s) (−1 while navigating)      | 1318.7               |
| status                  | string | "Arrived" / "Navigating"                     | Arrived              |

### 9.4 `data/<city>/validation_report.json` — ground-truth validation

| Field                       | Type    | Description                                     |
|-----------------------------|---------|-------------------------------------------------|
| city / generated_at         | string  | City id, timestamp                              |
| checkpoint                  | string  | Pass criterion text                             |
| methodology                 | string  | How comparison was computed                     |
| ground_truth_source         | string  | Data source description                         |
| run_config.{duration_min, start_hour, demand_scale, speed_factor, route_spread} | object | Engine run settings |
| summary.corridor_count      | int     | e.g. 11                                        |
| summary.within_25_pct       | number  | e.g. 63.6 (%)                                  |
| summary.mape_pct            | number  | e.g. 21.6 (%)                                  |
| summary.passes_checkpoint   | bool    | false                                          |
| corridors[]                 | array   | Per-corridor: origin, destination, zone_name_o, zone_name_d, samples, sim_mean_tt_seconds, observed_mean_tt_seconds, error_pct, within_25 |

### 9.5 `pipeline/cities.yaml` — city registry

| Field                | Type   | Description                                   |
|----------------------|--------|-----------------------------------------------|
| <city>.query         | string | OSM place-name query                          |
| <city>.chaos         | number | Default lane-discipline chaos (0–1)           |
| <city>.od_source.type | string | socrata / density-proxy / uniform            |
| <city>.od_source.dataset | string | Socrata dataset id (Chicago: `m6dm-c72p`)  |

### 9.6 Engine metrics streamed to dashboard (per tick)

| Metric               | Type    | Description                                   |
|----------------------|---------|-----------------------------------------------|
| avg_speed            | number  | Network-average speed                         |
| active_agents        | int     | Currently moving agents                       |
| completed_agents     | int     | Finished trips                                |
| avg_wait_time        | number  | Average wait time (s)                         |
| gini_coefficient     | number  | Wait-time inequality across zones (0 = equal) |
| zone_metrics         | array   | Per-zone wait time / congestion               |

### Key reference figures (cite in the synopsis)

- Piedmont graph: **402 nodes, 1043 edges, 1132 lanes, 25 zones**.
- Chicago validation: **11 corridors, 7 within 25%, MAPE 21.6%**, checkpoint
  not yet passed (target ≥75% within 25% and MAPE ≤ 25%).
- RL on toy demand: trained policy **−7,300** vs Webster baseline **−11,270**
  within 500 episodes (~35% better).
- ONNX inference: **p95 ≈ 0.018 ms** (batch 64), **0.027 ms** (batch 256) vs
  p95 ≤ 8 ms budget.
- Stress test: **20,000 agents** without crashes.
- **48 ML pytest tests** passing; C++ GoogleTest + benchmarks; CI on GitHub
  Actions.
- Five agent types; four cities (Chicago, Piedmont, Paris, Ahmedabad);
  WebSocket port 9001; dashboard port 5173.

---

## Generation Instructions for the AI producing the synopsis

1. Write each of the 9 sections in full academic/collage-project English.
2. Where diagrams are needed (Section 7 Data Flow, Section 8 E–R), produce both
   a **mermaid code block** AND a short prose description of what it shows.
3. For Section 9 (Data Dictionary), produce formal tables using the field
   names, types, and descriptions given in Section 9.1–9.6 above.
4. Keep all numbers/capabilities exactly as the repository states them. Mark any
   planned-but-not-implemented features as "planned" / "Phase N".
5. Do NOT invent: real-time traffic monitoring, hardware control, cloud
   deployment, a relational database, or end-user navigation features.