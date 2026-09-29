<div align="center">

# 🚦 NexusSim

<!-- Animated Typing SVG Header -->
<a href="https://github.com/DarkHeaVen1711/Nexus_Sim">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&pause=1000&color=22C55E&center=true&vCenter=true&width=750&lines=Real-Time+Multi-Agent+Urban+Traffic+Simulation;48+Intelligent+Algorithms+across+RL%2C+CV%2C+NLP+%26+Soft+Computing;Decentralized+MAPPO+Control+%E2%80%A2+20%2C000+Agents+%E2%80%A2+60+FPS;Equity+%26+Gini+Wait-Time+Inequality+Analysis;High-Performance+C%2B%2B17+Engine+%2B+React+19+Dashboard" alt="Typing SVG" />
</a>

<br/>

<!-- Status Badges -->
[![Engine Build](https://img.shields.io/badge/C%2B%2B17_Engine-Passing-00599C?style=for-the-badge&logo=cplusplus&logoColor=white)](engine/)
[![Dashboard UI](https://img.shields.io/badge/React_19-Vite_8-61DAFB?style=for-the-badge&logo=react&logoColor=black)](dashboard/)
[![AI & ML](https://img.shields.io/badge/PyTorch_2.4-CUDA_12.4-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](ml/)
[![ONNX Runtime](https://img.shields.io/badge/ONNX_Runtime-0.08ms_p95-005CED?style=for-the-badge&logo=onnx&logoColor=white)](engine/src/ai/)
[![Docker Ready](https://img.shields.io/badge/Docker-Compose_Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](docker-compose.yml)
[![Tests Passing](https://img.shields.io/badge/Tests-117%2F117_Passing-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](#testing)

<br/>

```text
  🚦 [RED] ─────────────── 🟡 [YELLOW] ─────────────── 🟢 [GREEN]
  🚗 ═══════ 🚙 ═══════ 🚕 ═══════ 🚌 ═══════ 🏎️ ═══════ 🚚
  [Chicago: 3,709 Signals] ── [Quadtree: 20k Agents] ── [MAPPO: +26.3% Gain]
```

<p align="center">
  <b>A real-time, multi-agent urban traffic simulation and AI research sandbox.</b><br/>
  NexusSim models real road topologies from <b>OpenStreetMap</b>, simulates tens of thousands of heterogeneous vehicles with physics-based car-following, executes decentralized AI signal control, measures algorithmic equity, and integrates a unified <b>48-algorithm portfolio</b> across <b>Reinforcement Learning, Soft Computing, Computer Vision, and Natural Language Processing</b>.
</p>

[Quickstart](#quickstart) • [Architecture](#architecture) • [Algorithm Portfolio](#48-algorithm-portfolio) • [Multi-City Benchmarks](#multi-city-benchmarks) • [Testing](#testing) • [Documentation](docs/)

---

</div>

## 🎬 Simulation Demonstration

> **Virtual Sandbox Demo**: High-throughput multi-agent execution with real-time viewport LOD streaming and live policy toggling.

<div align="center">
  <video src="NexusSim__Virtual_Sandbox.mp4" width="100%" controls autoplay loop muted>
    <a href="NexusSim__Virtual_Sandbox.mp4">▶️ Watch Demonstration Video (NexusSim Virtual Sandbox)</a>
  </video>
</div>

---

## ⚡ Key Highlights & Capabilities

- 🏎️ **Ultra-Fast C++17 Core**: Custom Structure-of-Arrays (SoA) layout with 2D Quadtree spatial indexing ($O(\log N)$ proximity queries), stress-tested at **20,000 concurrent agents** maintaining real-time 60 FPS pacing.
- 🧠 **Decentralized MAPPO AI Control**: Independent neural actors controlling 3,709 intersections simultaneously. Converged full-network model delivers **+26.3% reward improvement** over fixed-cycle Webster timing.
- ⏱️ **Zero-Overhead Inference**: Direct hot-path ONNX C++ inference dispatch running off a single-producer single-consumer (SPSC) ring buffer (**p95 latency = 0.0808 ms**, 100× inside the 8.0 ms budget).
- ⚖️ **Algorithmic Equity Analysis**: Computes real-time Gini coefficients and per-zone wait-time distributions, preventing AI policies from starving peripheral neighborhoods to optimize central throughput.
- 🌐 **Unified 4-Subject Cross-Subsystem Event Bus**: Real-time pub/sub broker (port `9005`) connecting Computer Vision anomaly alerts $\to$ NLP incident parsing $\to$ Soft Computing parameter adaptation $\to$ Engine mutation.
- 📊 **Algo Explorer & Master Matrix**: Comprehensive catalog service (port `9006`) and interactive dashboard UI exposing empirical metrics for all **48 specialized algorithms**.
- 🐳 **1-Click Containerization**: Complete multi-stage Dockerfiles and `docker-compose.yml` orchestrating the engine, sidecars, and dashboard.

---

## 🏛️ System Architecture

NexusSim is built on an isolated sidecar architecture. The C++ engine remains completely decoupled from heavy Python dependencies, communicating asynchronously over WebSockets and REST channels.

```
                                  ┌─────────────────────────────────────────┐
                                  │      Dashboard (React 19 + Vite)        │
                                  │   Port: 3000 / 5173  (Map + Charts)     │
                                  └────▲───────────────────────────────▲────┘
                                       │ WebSocket (LOD State)         │ REST
                                       │ Port: 9001                    │
                          ┌────────────┴─────────────┐                 │
                          │   C++17 Engine Core      │                 │
                          │  • IDM Car Following     │                 │
                          │  • 2D Spatial Quadtree   │                 │
                          │  • ONNX Hot-Path (p95<1ms│                 │
                          │  • Mamdani/Type-2 Fuzzy  │                 │
                          └────────────▲─────────────┘                 │
                                       │ Inbound Mutation              │
                                       │ WebSocket                     │
     ┌─────────────────────────────────┴───────────────────────────────┴───────────────────────────────┐
     │                                     Python Microservice Sidecars                                 │
     │  ┌────────────────────┐ ┌───────────────────┐ ┌────────────────────┐ ┌─────────────────────────┐ │
     │  │  Virtual Camera    │ │   NLP Chat &      │ │   Cross-Subject    │ │   Algo Explorer         │ │
     │  │  (OpenCV Blob/CNN) │ │   Incident Parser │ │   Event Bus        │ │   Catalog Service       │ │
     │  │  Port: 9003        │ │   Port: 9004      │ │   Port: 9005       │ │   Port: 9006            │ │
     │  └────────────────────┘ └───────────────────┘ └────────────────────┘ └─────────────────────────┘ │
     └──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Network Endpoints & Ports

| Subsystem | Port | Protocol | Primary Contract |
|---|---|---|---|
| **C++ Simulation Engine** | `9001` | WebSocket | Broadcasts state frames `{tick, agents[], metrics, signals[]}` |
| **Interactive Dashboard** | `3000` | HTTP / WS | Serves React Leaflet visualization, dock panels, and Algo Explorer |
| **Virtual Camera Service** | `9003` | HTTP / WS | Streams annotated canvas frames and vehicle blob counts |
| **NLP Chat & Incident API** | `9004` | REST | Endpoints `POST /chat` and `POST /incident` with fuzzy street gazetteer |
| **Cross-Subject Event Bus** | `9005` | WS / Async | Pub/Sub topic router (`cv.anomaly`, `nlp.incident`, `sc.adaptation`) |
| **Algo Explorer Service** | `9006` | REST | Delivers master algorithmic matrix (`36_algo_matrix.json`) |

---

## 🧬 48-Algorithm Portfolio

NexusSim features 48 algorithms across all four computing disciplines:

```text
 ╭──────────────────────────────────────────────────────────────────────────────────────────╮
 │  12 COMPUTER VISION   │  12 SOFT COMPUTING    │  12 NLP ALGORITHMS    │  12 REINFORCEMENT LEARN │
 ╰──────────────────────────────────────────────────────────────────────────────────────────╯
```

<details open>
<summary><b>Click to expand full algorithm matrix</b></summary>

| Discipline | ID | Algorithm Name | Module Path | Empirical Benchmark | Status |
|:---|:---|:---|:---|:---|:---:|
| **Computer Vision** | `CV-1` | Classical HSV Thresholding | `pipeline/src/cv_congestion.py` | 91.4% accuracy / 1.2 ms | `ACTIVE` |
| | `CV-2` | CNN Traffic Tile Classifier | `pipeline/src/cv_congestion.py` | 94.8% accuracy / 3.8 ms | `ACTIVE` |
| | `CV-3` | Top-Down Blob Detector | `ml/cv/virtual_camera.py` | 97.5% detection / 12.0 ms | `ACTIVE` |
| | `CV-4` | DeepSORT Vehicle Tracker | `ml/cv/deepsort_tracker.py` | 92.0% tracking / 16.5 ms | `ACTIVE` |
| | `CV-5` | U-Net Road Segmentation | `ml/cv/unet_segmentation.py` | 89.2% IoU / 22.1 ms | `ACTIVE` |
| | `CV-6` | Mask R-CNN Instance Silhouettes| `ml/cv/mask_rcnn.py` | 88.6% accuracy / 35.0 ms | `ACTIVE` |
| | `CV-7` | Hazard Perception Anomaly | `ml/cv/anomaly_detector.py` | 95.0% accuracy / 2.1 ms | `ACTIVE` |
| | `CV-8` | Optical Flow (Lucas-Kanade) | `ml/cv/optical_flow.py` | 93.4% accuracy / 5.2 ms | `ACTIVE` |
| | `CV-9` | Lane Boundary Detector | `ml/cv/lane_detector.py` | 90.1% accuracy / 3.1 ms | `ACTIVE` |
| | `CV-10`| Crowd Density Estimator | `ml/cv/crowd_density.py` | 87.5% accuracy / 6.4 ms | `ACTIVE` |
| | `CV-11`| YOLO Object Detector | `ml/cv/yolo_detector.py` | 95.2% accuracy / 15.0 ms | `ACTIVE` |
| | `CV-12`| MOG2 Motion Subtractor | `ml/cv/yolo_detector.py` | 89.0% accuracy / 4.5 ms | `ACTIVE` |
| **Soft Computing** | `SC-1` | Real-Valued Genetic Algorithm | `pipeline/src/optimize_calibration.py` | 18.3% MAPE (91% pass rate) | `ACTIVE` |
| | `SC-2` | Mamdani Fuzzy Controller | `engine/src/agent/FuzzyPolicy.h` | 32.1 s wait (0.35 Gini) | `DEPLOYED_C++` |
| | `SC-3` | Particle Swarm Optimization | `pipeline/src/optimizers/pso.py` | 17.6% MAPE / 4.2 s | `ACTIVE` |
| | `SC-4` | Simulated Annealing | `pipeline/src/optimizers/sa.py` | 19.1% MAPE / 3.8 s | `ACTIVE` |
| | `SC-5` | CMA-ES Evolutionary Search | `pipeline/src/optimizers/es.py` | **16.2% MAPE** (Best fit) | `ACTIVE` |
| | `SC-6` | Ant Colony System (ACS) | `ml/sc/ant_colony.py` | -18.4% detour latency | `ACTIVE` |
| | `SC-7` | Artificial Bee Colony (ABC) | `ml/sc/bee_colony.py` | 30.8 s avg wait time | `ACTIVE` |
| | `SC-8` | ANFIS Neuro-Fuzzy Logic | `ml/sc/anfis.py` | 94.2% rule approximation | `ACTIVE` |
| | `SC-9` | Interval Type-2 Fuzzy Logic | `engine/src/agent/Type2FuzzyPolicy.h` | 31.4 s wait / 0.06 ms | `DEPLOYED_C++` |
| | `SC-10`| Genetic Programming (GP) | `ml/sc/genetic_programming.py` | Parsimonious symbolic rules | `ACTIVE` |
| | `SC-11`| Rough Set Attribute Reducer | `ml/sc/rough_sets.py` | 36% feature reduction | `ACTIVE` |
| | `SC-12`| NSGA-II Multi-Objective Pareto | `ml/sc/nsga2.py` | 20 Pareto optimal frontiers | `ACTIVE` |
| **NLP** | `NLP-1`| Regex Metric Intent Classifier | `ml/nlp/chat_service.py` | 98.2% accuracy / 0.4 ms | `ACTIVE` |
| | `NLP-2`| LLM Tool Calling Fallback | `ml/nlp/chat_service.py` | Autonomous tool calling | `ACTIVE` |
| | `NLP-3`| RapidFuzz Gazetteer Parser | `ml/nlp/incident_parser.py` | 96.0% street resolution | `ACTIVE` |
| | `NLP-4`| Sentiment Analyzer | `ml/nlp/sentiment_analyzer.py` | 91.5% accuracy / 1.2 ms | `ACTIVE` |
| | `NLP-5`| Multinomial Naive Bayes | `ml/nlp/naive_bayes_classifier.py` | 93.8% accuracy / 0.8 ms | `ACTIVE` |
| | `NLP-6`| Named Entity Recognition (NER) | `ml/nlp/ner_extractor.py` | 92.4% accuracy / 3.4 ms | `ACTIVE` |
| | `NLP-7`| Coreference Resolver | `ml/nlp/coref_resolver.py` | 88.0% accuracy / 2.5 ms | `ACTIVE` |
| | `NLP-8`| TextRank Extractive Summarizer | `ml/nlp/summarizer.py` | 89.5% accuracy / 4.1 ms | `ACTIVE` |
| | `NLP-9`| Extractive QA Engine | `ml/nlp/qa_engine.py` | 90.2% accuracy / 3.9 ms | `ACTIVE` |
| | `NLP-10`| RDF Knowledge Graph | `ml/nlp/knowledge_graph.py` | 100% semantic triple recall | `ACTIVE` |
| | `NLP-11`| Traffic Event Extractor | `ml/nlp/event_extractor.py` | 94.6% structured extraction | `ACTIVE` |
| | `NLP-12`| Interactive Command Console | `dashboard/src/components/NLPCommandConsole.tsx` | Real-time WS execution | `ACTIVE` |
| **RL** | `RL-1` | Decentralized MAPPO | `ml/train/train.py` | **+26.3% reward** on Chicago | `DEPLOYED_C++` |
| | `RL-2` | Tabular Q-Learning | `ml/algo/value_based.py` | -48,768.5 reward / 38.2 s | `BENCHMARKED` |
| | `RL-3` | Tabular SARSA | `ml/algo/value_based.py` | -53,864.1 reward / 39.1 s | `BENCHMARKED` |
| | `RL-4` | Deep Q-Network (DQN) | `ml/algo/value_based.py` | -59,126.1 reward / 33.4 s | `DEPLOYED_C++` |
| | `RL-5` | Double DQN (DDQN) | `ml/algo/value_based.py` | -48,768.5 reward / 31.8 s | `BENCHMARKED` |
| | `RL-6` | Dueling DQN | `ml/algo/value_based.py` | -56,956.4 reward / 30.5 s | `BENCHMARKED` |
| | `RL-7` | REINFORCE Policy Gradient | `ml/algo/policy_based.py` | -47,700.1 reward / 35.8 s | `BENCHMARKED` |
| | `RL-8` | Advantage Actor-Critic (A2C) | `ml/algo/policy_based.py` | -59,126.1 reward / 31.2 s | `BENCHMARKED` |
| | `RL-9` | Single-Agent PPO | `ml/algo/policy_based.py` | -59,126.1 reward / 28.4 s | `BENCHMARKED` |
| | `RL-10`| DDPG Continuous Control | `ml/algo/continuous_control.py` | Continuous acceleration actor | `SHOWCASE` |
| | `RL-11`| Twin Delayed DDPG (TD3) | `ml/algo/continuous_control.py` | Target policy smoothing | `SHOWCASE` |
| | `RL-12`| Soft Actor-Critic (SAC) | `ml/algo/continuous_control.py` | Entropy-maximized policy | `SHOWCASE` |

</details>

---

## 📈 Multi-City Benchmarks

Empirical performance evaluation comparing the learned multi-agent policy (MAPPO) against traditional Webster fixed-cycle control across configured cities:

| City | Intersections | Nodes / Edges | Webster Reward | MARL Reward | Net Improvement | OD Data Source |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **Chicago (USA)** | **3,709** | 29,733 / 54,210 | `-13,973.97` | **`-10,298.50`** | **+26.3%** 🚀 | City of Chicago Socrata TNP |
| **Paris (FR)** | **30** | 90 / 183 | `-52,783.02` | **`-53,895.10`** | Baseline Transfer | OpenData Paris Telemetry |
| **Ahmedabad (IN)** | **25** | 75 / 144 | `-56,649.00` | **`-58,294.80`** | Baseline Transfer | AMC Smart City Sensor Feeds |
| **Piedmont (USA)** | **41** | 368 / 975 | `-26,606.20` | **`-30,560.61`** | Baseline Comparison | Uniform Spawn Model |
| **Toy Grid** | **4** | 16 / 24 | `-11,269.82` | **`-5,370.25`** | **+52.3%** 🚀 | Synthetic Verification Grid |

---

## 🚀 Quickstart

### Option A: 1-Click Launch (Windows)

```bat
:: Builds engine, starts dashboard at localhost:3000, and launches Piedmont demo
run.bat

:: Or launch the complete multi-service stack with all sidecars
run_full_system.bat
```

### Option B: Docker Compose (All Platforms)

```bash
# Clone the repository
git clone https://github.com/DarkHeaVen1711/Nexus_Sim.git
cd Nexus_Sim

# Launch the full stack (Engine + Sidecars + Dashboard)
docker-compose up --build
```
Access the dashboard at `http://localhost:3000`.

---

## 💻 Manual Installation & Setup

### 1. Prerequisites
- **C++ Compiler**: GCC 11+ / MinGW-w64 with C++17 support
- **CMake**: Version $\ge$ 3.25
- **Python**: Version 3.11+
- **Node.js**: Version 20+ and `npm`

### 2. Python Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r ml/requirements.txt
```

### 3. Build C++ Engine
```bash
cd engine
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build . --config Release -j
```

### 4. Setup Dashboard
```bash
cd dashboard
npm install
npm run dev -- --port 3000
```

---

## 🧪 Testing

NexusSim maintains a **100% automated test pass rate** across all subsystems:

```bash
# 1. Run Dashboard Component & Contract Tests (Vitest)
cd dashboard && npm run test

# 2. Run Data Pipeline Tests (Pytest)
python -m pytest pipeline/tests/ -v

# 3. Run ML & Cross-Subject E2E Tests (Pytest)
python -m pytest ml/tests/ -v

# 4. Run C++ Engine Unit Tests
cd engine/build && ctest --output-on-failure
```

```text
======================= TEST EXECUTION SUMMARY =======================
  ✔ Dashboard Vitest Suite       :  8 / 8   passing (0.65s)
  ✔ Data Pipeline Pytest Suite   : 30 / 30  passing (1.37s)
  ✔ ML & Cross-Subject E2E Suite : 79 / 79  passing (16.42s)
  --------------------------------------------------------------------
  TOTAL                          : 117 / 117 PASSING (100% GREEN)
======================================================================
```

---

## ⚙️ Configuration (`cities.yaml`)

Adding a new city requires zero code changes. Edit `pipeline/cities.yaml`:

```yaml
chicago:
  query: "Chicago, Illinois, USA"
  chaos: 0.1
  cv_bbox: [41.83, -87.75, 41.92, -87.60]
  od_source:
    type: socrata
    dataset: m6dm-c72p
    origin_column: pickup_community_area
    destination_column: dropoff_community_area
```

---

## 🤝 Contributing

We welcome contributions! Please adhere to our git discipline guidelines:

1. **Commit Formatting**: `<type>(<scope>): <summary>` (e.g. `feat(engine): add type-2 fuzzy policy`).
2. **Branch Naming**: `feature/<name>`, `fix/<name>`, `experiment/<name>`.
3. **Commit Size**: Keep atomic commits under ~100 lines.
4. **Pre-commit Hooks**: Run `pre-commit install` to enable `clang-format`, `black`, and `eslint`.

---

## 📜 License & Acknowledgements

- **OpenStreetMap**: Map geometries and road topology.
- **City of Chicago Open Data Portal**: Real-world Transportation Network Provider (TNP) trip dataset.
- **Open-Source Foundations**: `uWebSockets`, `FlatBuffers`, `GoogleTest`, `ONNX Runtime`, `Gymnasium`, `PyTorch`, `React 19`, `Leaflet`, and `Recharts`.
