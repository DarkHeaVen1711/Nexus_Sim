# NexusSim — Tech Stack

**Version:** 1.0

---

## Overview

NexusSim is a three-subsystem project. Each subsystem has a hard interface boundary so it can be developed, tested, and handed off independently. This document defines every technology choice and the reason behind it.

```
┌─────────────────────┐     graph.json      ┌─────────────────────┐
│   DATA PIPELINE     │ ─────────────────►  │   C++ ENGINE        │
│   Python / osmnx    │                     │   Simulation loop   │
└─────────────────────┘                     └──────────┬──────────┘
                                                       │ binary delta
         ┌─────────────────────┐     ONNX model        │ WebSocket
         │   ML PIPELINE       │ ───────────────►  ────┘
         │   Python / PyTorch  │              ring buffer
         └─────────────────────┘
                                            ┌─────────────────────┐
                                            │   DASHBOARD         │
                                            │   React + Mapbox    │
                                            └─────────────────────┘
```

---

## Subsystem 1 — C++ Simulation Engine

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | C++20 | Performance, deterministic memory control, native thread primitives |
| Build system | CMake 3.25+ | Standard for cross-platform C++ projects; easy CI integration |
| Graph structure | Custom adjacency list | Road networks are sparse directed graphs; adjacency list is cache-friendlier than matrix |
| Spatial index | 2D Quadtree (custom) | Reduces collision/proximity detection from O(N²) to O(N log N) |
| Memory layout | Structure-of-Arrays (SoA) | Better CPU cache utilisation for bulk agent updates vs. AoS |
| Concurrency | `std::thread` + thread pool | Parallel agent update ticks; no external dependency |
| IPC to ML backend | Shared-memory ring buffer (POSIX) | Zero-copy, non-blocking; engine never stalls waiting for ML reply |
| Pathfinding | A* with precomputed heuristic | Standard for road graphs; precompute node-to-node Euclidean heuristic once on load |
| ML inference | ONNX Runtime C++ API | Runs trained Python policy in C++ with no live Python process |
| Map loading | nlohmann/json | Single-header, fast, well-maintained; loads `graph.json` from pipeline |
| WebSocket server | uWebSockets (µWS) | Highest-throughput C++ WebSocket library; handles binary frames natively |
| Serialisation | FlatBuffers | Zero-copy binary serialisation for agent state deltas; far smaller than JSON |
| Testing | GoogleTest | Standard C++ unit test framework |
| Linter | clang-tidy + clang-format | Enforced in CI pre-commit hook |

---

## Subsystem 2 — Data Pipeline

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.11 | Ecosystem for geospatial and data processing is unmatched |
| OSM download & cleaning | osmnx | De-facto standard for OSM graph extraction; handles projection, simplification, component extraction |
| Geospatial ops | shapely, pyproj | Polygon intersection for zone tagging; coordinate projection |
| Data wrangling | pandas, numpy | OD matrix construction, confidence-score computation |
| Output format | JSON (graph.json) | Human-readable, easy to inspect; loaded by nlohmann/json in C++ |
| Traffic demand data | Uber Movement (free), OpenTraffic | Open, city-level OD journey time data; available for Indian cities |
| Testing | pytest | Unit tests for each pipeline stage (clean, infer, tag, export) |

**Lane inference fallback chain (in order):**
1. OSM `lanes` tag — used directly if present
2. Road type lookup table — `motorway` → 3, `trunk` → 2, `primary` → 2, `secondary` → 1, `residential` → 1
3. Road `width` tag ÷ 3.3m (standard lane width) — rounded down
4. Classification default — documented with `confidence: low` flag in output JSON

---

## Subsystem 3 — ML Pipeline

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.11 | PyTorch ecosystem; training only, not deployed |
| RL framework | PyTorch + custom Gym env | Full control over reward function; no black-box abstraction |
| Algorithm | MAPPO (Multi-Agent PPO) core + 11-algorithm RL inventory (Phases 19–24) | MAPPO is stable, well-cited in traffic-signal MARL literature, and handles decentralised agents; the inventory adds breadth across tabular value, deep value, policy-gradient, actor-critic, and continuous families |
| Showcase RL algorithms | stable-baselines3 + gymnasium | SAC/TD3/DDPG on a standard continuous env (Pendulum-v1) for breadth; keeps the signal-control stack hand-rolled and directly comparable |
| Policy network | 3-layer MLP per agent | Lightweight enough for batched ONNX inference within 8 ms |
| Baseline comparison | Webster's fixed-cycle method | Classic, well-understood baseline; clear benchmark to beat |
| Export | `torch.onnx.export` | Standard PyTorch → ONNX path; consumed by C++ runtime |
| Experiment tracking | MLflow (local) | Log reward curves, hyperparameters, checkpoints without cloud dependency |
| Testing | pytest + custom env tests | Verify reward function correctness, env reset logic, observation space shapes |

**Reward function:**
```
reward_i = α × pressure_i + β × equity_global

pressure_i      = upstream_queue_i − downstream_queue_i
equity_global   = −Σ (zone_weight_j × avg_wait_j)   for all zones j
zone_weight_j   = inverse of zone's baseline service level
```
α and β are tunable hyperparameters; their tradeoff curve is reported as a key deliverable.

---

## Subsystem 4 — React Dashboard

| Component | Technology | Why |
|-----------|-----------|-----|
| Framework | React 18 + Vite | Fast HMR, modern React features (Suspense, concurrent rendering) |
| Language | TypeScript | Type safety across WebSocket message shapes and map data structures |
| Styling | Tailwind CSS | Utility-first; no context switching between CSS files and components |
| Map rendering | Mapbox GL JS (or Leaflet + WebGL) | GPU-accelerated rendering; handles tens of thousands of moving markers |
| Charts | Recharts | Equity/efficiency tradeoff curve; per-zone bar charts |
| WebSocket client | Native browser WebSocket | No library needed; handles binary FlatBuffer frames |
| State management | Zustand | Lightweight; avoids Redux boilerplate for a single-developer project |
| Testing | Vitest + React Testing Library | Co-located with Vite; fast unit tests for components and state logic |

---

## Developer Tooling & Git Discipline

| Tool | Purpose |
|------|---------|
| Git | Version control |
| GitHub | Remote + PR workflow |
| pre-commit | Runs clang-format, clang-tidy (C++), black + isort (Python), eslint (JS) before every commit |
| GitHub Actions | CI: build, lint, test on every push and PR |
| CMake + pip + npm | Per-subsystem build tools; one `Makefile` at root ties them together |

### Commit & Branch Rules

These rules are non-negotiable and enforced via pre-commit hooks where possible:

```
RULE 1 — Max 100 line insertions per commit
  • If a change exceeds 100 insertions, split it into logical sub-commits
  • Each sub-commit must be independently buildable (no broken intermediate states)

RULE 2 — Branch naming
  • New feature      →  feature/<short-description>         e.g. feature/quadtree-spatial-index
  • Bug fix          →  fix/<short-description>             e.g. fix/onnx-batch-latency
  • Refactor         →  refactor/<short-description>
  • Data / pipeline  →  data/<short-description>            e.g. data/ahmedabad-osm-pipeline
  • Experiment / ML  →  experiment/<short-description>      e.g. experiment/mappo-reward-tuning

RULE 3 — Pull Requests
  • Any change > 100 insertions total (even across multiple commits) opens a PR
  • PR description must state: what changed, why, and what was tested
  • PR must pass all CI checks before merge
  • No force-push to main

RULE 4 — Commit message format
  <type>(<scope>): <short summary>

  Types: feat, fix, refactor, test, docs, chore
  Scopes: engine, pipeline, ml, dashboard, ci

  Example: feat(engine): add quadtree proximity detection for agent collision
```

---

## Directory Structure

```
nexussim/
├── engine/                  # C++ simulation engine
│   ├── src/
│   │   ├── graph/           # Graph loading, adjacency list
│   │   ├── agents/          # Agent types, IDM behaviour
│   │   ├── spatial/         # Quadtree implementation
│   │   ├── inference/       # ONNX Runtime wrapper
│   │   ├── server/          # uWebSockets stream server
│   │   └── main.cpp
│   ├── include/
│   ├── tests/
│   └── CMakeLists.txt
│
├── pipeline/                # Python data pipeline
│   ├── src/
│   │   ├── download.py      # OSM fetch
│   │   ├── clean.py         # osmnx cleaning + component extraction
│   │   ├── lanes.py         # Lane inference fallback chain
│   │   ├── zones.py         # Equity zone tagging
│   │   └── export.py        # graph.json writer
│   ├── tests/
│   └── requirements.txt
│
├── ml/                      # Python ML pipeline
│   ├── env/                 # Gym environment wrapping sim state
│   ├── models/              # Policy network definition
│   ├── train/               # MAPPO trainer
│   ├── export/              # ONNX export script
│   ├── tests/
│   └── requirements.txt
│
├── dashboard/               # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── store/           # Zustand state
│   │   └── types/           # TypeScript WebSocket message types
│   ├── public/
│   └── package.json
│
├── data/                    # Downloaded + processed city data (gitignored raw)
│   ├── chicago/
│   ├── paris/
│   └── ahmedabad/
│
├── docs/                    # This folder — PRD, tech stack, user stories, plan
├── .github/workflows/       # CI definitions
├── .pre-commit-config.yaml
├── Makefile                 # Root-level build shortcuts
└── README.md
```
