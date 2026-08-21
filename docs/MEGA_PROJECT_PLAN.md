# NexusSim Mega Project Plan - 36 Algorithms Across 4 Subjects

**Version:** 1.0
**Date:** August 2026
**Goal:** Expand NexusSim to 36 total algorithms (12 RL + 12 CV + 12 SC + 12 NLP), all deeply integrated with the traffic simulation engine, visualized through a unified Algo Explorer dashboard, and suitable for university project submission per subject.

---

## Table of Contents

1. Architecture Overview
2. Proposed Project Structure
3. Computer Vision (CV) - 12 Algorithms
4. Soft Computing (SC) - 12 Algorithms
5. Natural Language Processing (NLP) - 12 Algorithms
6. Reinforcement Learning (RL) - 12 Algorithms (Existing Plan)
7. Cross-Subject Integration Architecture
8. Unified Dashboard: Algo Explorer
9. Experiment Tracking Strategy
10. Implementation Phases (Extended)
11. Real-World Data Sources
12. Dependencies Summary

---

## 1. Architecture Overview

### Current State

```
Engine (C++) <--WS--> Dashboard (React)
      ^
  ML/RL (Python) -- 1 algorithm (MAPPO) implemented
```

### Target State

```
                    +-------------------------------------------+
                    |       UNIFIED ALGO EXPLORER               |
                    |    Dashboard (React + Recharts)           |
                    |  +-----+-----+-----+-----+              |
                    |  | CV  | SC  | NLP | RL  | <-- tabs     |
                    |  +--+--+--+--+--+--+--+--+              |
                    +----+-----+-----+-----+-------------------+
                         |     |     |     |
       +-----------------+-----+-----+-----+-------------------+
       |           SERVICE LAYER (Python Sidecars)              |
       |                                                         |
       |  +--------+ +--------+ +--------+ +------+            |
       |  | ml/cv/ | | ml/sc/ | | ml/nlp/ | |ml/   |            |
       |  |12 algos| |12 algos| |12 algos| |algo  |            |
       |  +---+----+ +---+----+ +---+----+ +--+---+            |
       |      |          |          |          |                |
       |      v          v          v          v                |
       |  +----------------------------------------------+     |
       |  |     SHARED STATE BUS (WebSocket)             |     |
       |  |  Engine state + cross-subject events         |     |
       |  +---------------------+------------------------+     |
       +------------------------+------------------------------+
                                |
                    +-----------v-----------+
                    |   C++ ENGINE          |
                    |   (Simulation)        |
                    |   Port 9001           |
                    +-----------------------+
```

### Key Design Principles

1. **Every algorithm integrates with the simulation** - no standalone demos; each reads from or writes to the engine state
2. **Cross-subject data flows** - CV congestion feeds SC fuzzy controller; NLP incidents trigger RL re-routing; SC-optimized params seed RL training
3. **Unified experiment tracking** - MLflow for training-heavy algorithms (RL, CNN), flat JSON for lighter ones (fuzzy, rule-based NLP)
4. **Single dashboard entry point** - Algo Explorer panel with subject tabs and algorithm dropdowns

---

## 2. Proposed Project Structure

```
Nexus_Sim/
├── engine/                          # C++ (unchanged structure)
│   └── src/agent/
│       ├── SignalPolicy.h           # Phase 12: interface (PLANNED)
│       ├── WebsterPolicy.h          # Phase 12: extract from SignalController
│       ├── FuzzyPolicy.h            # SC-2: Mamdani fuzzy controller
│       └── NeuroFuzzyPolicy.h       # SC-7: ANFIS-based controller
│
├── pipeline/
│   └── src/
│       ├── optimize_calibration.py  # SC-1: GA calibration
│       ├── pso_optimizer.py         # SC-4: Particle Swarm Optimization
│       ├── acs_router.py            # SC-5: Ant Colony System routing
│       ├── sa_optimizer.py          # SC-6: Simulated Annealing
│       ├── moea_optimizer.py        # SC-12: NSGA-II multi-objective
│       └── cv_congestion.py         # CV-1: tile-based congestion
│
├── ml/
│   ├── cv/                          # NEW: Computer Vision package
│   │   ├── __init__.py
│   │   ├── configs.yaml
│   │   ├── virtual_camera.py        # CV-6: base renderer
│   │   ├── virtual_camera_service.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── resnet_congestion.py # CV-2: CNN congestion classifier
│   │   │   ├── yolo_detector.py     # CV-3: YOLOv8 vehicle detection
│   │   │   ├── deepsort_tracker.py  # CV-4: SORT/DeepSORT tracking
│   │   │   ├── unet_segmentation.py # CV-7: semantic segmentation
│   │   │   ├── mask_rcnn.py         # CV-8: instance segmentation
│   │   │   ├── optical_flow.py      # CV-9: dense optical flow
│   │   │   ├── background_sub.py    # CV-10: background subtraction
│   │   │   ├── anomaly_detector.py  # CV-11: autoencoder anomaly
│   │   │   ├── lane_detector.py     # CV-12: lane detection
│   │   │   └── crowd_density.py     # CV-5: density estimation
│   │   ├── eval/
│   │   │   ├── __init__.py
│   │   │   ├── benchmark.py
│   │   │   └── metrics.py
│   │   └── data/
│   │       ├── synthetic/
│   │       └── real_world/
│   │
│   ├── sc/                          # NEW: Soft Computing package
│   │   ├── __init__.py
│   │   ├── configs.yaml
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── ga_calibration.py    # SC-1: Genetic Algorithm
│   │   │   ├── pso_optimizer.py     # SC-4: Particle Swarm
│   │   │   ├── ant_colony.py        # SC-5: Ant Colony System
│   │   │   ├── simulated_annealing.py # SC-6: Simulated Annealing
│   │   │   ├── neuro_fuzzy.py       # SC-7: ANFIS
│   │   │   ├── type2_fuzzy.py       # SC-8: Type-2 Fuzzy Logic
│   │   │   ├── evo_strategy.py      # SC-9: Evolution Strategies
│   │   │   ├── bee_colony.py        # SC-10: Artificial Bee Colony
│   │   │   ├── rough_sets.py        # SC-11: Rough Set Theory
│   │   │   └── nsga2.py             # SC-12: NSGA-II
│   │   ├── eval/
│   │   │   ├── __init__.py
│   │   │   ├── benchmark.py
│   │   │   └── convergence.py
│   │   └── engine/
│   │       ├── genetic_programming.py # SC-3: GP rule evolution
│   │       └── fitness.py
│   │
│   ├── nlp/                         # NEW: NLP package
│   │   ├── __init__.py
│   │   ├── configs.yaml
│   │   ├── chat_service.py          # NLP-1: live metrics chat
│   │   ├── incident_parser.py       # NLP-2: incident report parser
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── sentiment_analyzer.py # NLP-3: traffic sentiment
│   │   │   ├── ner_extractor.py     # NLP-4: named entity recognition
│   │   │   ├── text_classifier.py   # NLP-5: incident classification
│   │   │   ├── extractive_summary.py # NLP-6: extractive summarization
│   │   │   ├── abstractive_summary.py # NLP-7: abstractive summarization
│   │   │   ├── qa_system.py         # NLP-8: question answering
│   │   │   ├── event_extractor.py   # NLP-9: event extraction
│   │   │   ├── coref_resolver.py    # NLP-10: coreference resolution
│   │   │   ├── stance_detector.py   # NLP-11: stance detection
│   │   │   └── knowledge_graph.py   # NLP-12: knowledge graph builder
│   │   ├── eval/
│   │   │   ├── __init__.py
│   │   │   ├── benchmark.py
│   │   │   └── test_sets/
│   │   └── data/
│   │       ├── synthetic/
│   │       ├── real_world/
│   │       └── gazetteers/
│   │
│   ├── algo/                        # RL algorithms (existing plan)
│   │   ├── __init__.py
│   │   ├── configs.yaml
│   │   ├── base_trainer.py
│   │   ├── value_based/
│   │   │   ├── q_learning.py
│   │   │   ├── sarsa.py
│   │   │   ├── dqn.py
│   │   │   ├── ddqn.py
│   │   │   └── dueling_dqn.py
│   │   ├── policy_based/
│   │   │   ├── reinforce.py
│   │   │   ├── a2c.py
│   │   │   └── ppo_single.py
│   │   └── continuous/
│   │       ├── sac.py
│   │       ├── td3.py
│   │       └── ddpg.py
│   │
│   ├── env/                         # Existing (unchanged)
│   ├── models/                      # Existing (unchanged)
│   ├── train/                       # Existing + benchmark.py
│   ├── eval/
│   │   ├── __init__.py
│   │   ├── cross_subject_benchmark.py
│   │   └── report_generator.py
│   └── export/
│       └── export_onnx.py
│
├── dashboard/
│   └── src/components/
│       ├── AlgoExplorer/            # NEW: unified algorithm explorer
│       │   ├── AlgoExplorer.tsx
│       │   ├── CVPanel.tsx
│       │   ├── SCPanel.tsx
│       │   ├── NLPPanel.tsx
│       │   ├── RLPanel.tsx
│       │   ├── AlgorithmCard.tsx
│       │   └── ComparisonView.tsx
│       ├── CV/
│       │   ├── VirtualCameraPanel.tsx
│       │   ├── CongestionCVOverlay.tsx
│       │   ├── SegmentationPanel.tsx
│       │   ├── OpticalFlowPanel.tsx
│       │   └── DetectionPanel.tsx
│       ├── SC/
│       │   ├── CalibrationReportPanel.tsx
│       │   ├── ConvergencePanel.tsx
│       │   ├── FuzzyRulesPanel.tsx
│       │   └── ParetoFrontPanel.tsx
│       ├── NLP/
│       │   ├── ChatPanel.tsx
│       │   ├── IncidentReportPanel.tsx
│       │   ├── SentimentPanel.tsx
│       │   ├── NERPanel.tsx
│       │   └── KnowledgeGraphPanel.tsx
│       └── (existing panels unchanged)
│
├── data/<city>/
│   ├── cv_congestion.json
│   ├── cv_detection_results.json
│   ├── cv_tracking_results.json
│   ├── cv_segmentation_results.json
│   ├── ga_calibration_report.json
│   ├── pso_report.json
│   ├── acs_report.json
│   ├── sa_report.json
│   ├── moga_report.json
│   ├── nlp_incidents.json
│   ├── nlp_sentiment.json
│   ├── nlp_knowledge_graph.json
│   └── ...
│
└── docs/
    ├── MEGA_PROJECT_PLAN.md          # This document
    ├── RL_DOCUMENTATION.md           # Existing
    ├── CV_DOCUMENTATION.md           # Existing (to be expanded)
    ├── NLP_DOCUMENTATION.md          # Existing (to be expanded)
    └── SOFT_COMPUTING_DOCUMENTATION.md # Existing (to be expanded)
```

---

## 3. Computer Vision (CV) - 12 Algorithms

### Overview

All 12 CV algorithms process visual data from two sources:
- **Source A: Real-world imagery** - Mapbox/TomTom traffic tiles, real dashcam datasets
- **Source B: Synthetic imagery** - Virtual camera rendering from engine stream

Every algorithm's output feeds back into the simulation (congestion data for SC calibration, detection counts for RL reward shaping, anomaly alerts for NLP incident generation).

### Algorithm Inventory

| # | Algorithm | Category | Data Source | Integration Target | Dashboard Viz |
|---|-----------|----------|-------------|-------------------|---------------|
| CV-1 | HSV Color-Threshold Congestion | Classical | Mapbox tiles | SC GA fitness term | CongestionCVOverlay |
| CV-2 | ResNet-18 Congestion CNN | Deep Learning | Mapbox tiles | SC GA fitness term (comparison) | CongestionCVOverlay |
| CV-3 | YOLOv8 Vehicle Detection | Object Detection | Virtual camera | RL reward (vehicle count) | DetectionPanel |
| CV-4 | SORT/DeepSORT Tracking | Object Tracking | Virtual camera | RL reward (flow patterns) | DetectionPanel |
| CV-5 | CSRNet Crowd Density | Density Estimation | Virtual camera + real | NLP pedestrian alerts | DetectionPanel |
| CV-6 | Virtual Camera Renderer | Rendering | Engine WS stream | All CV algorithms (data source) | VirtualCameraPanel |
| CV-7 | U-Net Semantic Segmentation | Segmentation | Virtual camera + real | SC road condition input | SegmentationPanel |
| CV-8 | Mask R-CNN Instance Seg | Instance Segmentation | Virtual camera | CV-4 tracking init | SegmentationPanel |
| CV-9 | Farneback Optical Flow | Motion Analysis | Virtual camera | RL reward (congestion signal) | OpticalFlowPanel |
| CV-10 | MOG2 Background Subtraction | Foreground Detection | Virtual camera | CV-3 detection refinement | OpticalFlowPanel |
| CV-11 | Autoencoder Anomaly Detection | Anomaly Detection | Virtual camera + real | NLP incident auto-generation | DetectionPanel |
| CV-12 | Hough Transform Lane Detection | Lane Analysis | Virtual camera + real | SC lane-level signal tuning | SegmentationPanel |

### Detailed Algorithm Designs

#### CV-1: HSV Color-Threshold Congestion Classification (EXISTING)

- **What it does:** Classifies road congestion level (0-3) from Mapbox/TomTom traffic tile imagery using HSV color space thresholding
- **How it integrates:** Output `cv_congestion.json` feeds into SC GA calibration as additional fitness term
- **Files:** `pipeline/src/cv_congestion.py`
- **Status:** Documented in Phase 14, PLANNED

#### CV-2: ResNet-18 Congestion CNN (EXISTING)

- **What it does:** Fine-tuned ResNet-18 (4-class) on hand-labeled tile crops for congestion classification
- **How it integrates:** Comparison baseline against CV-1; same output format
- **Files:** `ml/cv/models/resnet_congestion.py`
- **Status:** Documented in Phase 14.4, PLANNED

#### CV-3: YOLOv8 Vehicle Detection

- **What it does:** Real-time vehicle detection and counting on virtual camera frames using YOLOv8-nano
- **How it integrates:**
  - Vehicle count per zone feeds into RL reward function as congestion density signal
  - Detection confidence feeds into CV-4 (DeepSORT) initialization
  - Anomalous detection patterns (sudden count spike/drop) trigger NLP-9 event extraction
- **Files:** `ml/cv/models/yolo_detector.py`
- **Input:** Virtual camera frames (from CV-6)
- **Output:** `data/<city>/cv_detection_results.json` - `{frame_id: [{bbox, class, confidence, zone_id}]}`
- **Training:** Pre-trained YOLOv8-nano on COCO, fine-tuned on UA-DETRAC traffic dataset
- **Dashboard:** `DetectionPanel.tsx` - bounding boxes overlaid on virtual camera feed, live count per zone

#### CV-4: SORT/DeepSORT Multi-Object Tracking

- **What it does:** Tracks individual vehicles across consecutive virtual camera frames using Kalman filtering + appearance features
- **How it integrates:**
  - Trajectory data feeds into RL reward (smooth flow = good, stop-and-go = bad)
  - Vehicle re-identification across non-overlapping camera views
  - Flow velocity estimation feeds into CV-9 optical flow validation
- **Files:** `ml/cv/models/deepsort_tracker.py`
- **Input:** CV-3 detection results + virtual camera frames
- **Output:** `data/<city>/cv_tracking_results.json` - `{track_id: [{frame, bbox, velocity, zone_id}]}`
- **Dependencies:** Requires CV-3 (YOLO) detections as input
- **Dashboard:** DetectionPanel.tsx - trajectories drawn as colored trails

#### CV-5: CSRNet Crowd Density Estimation

- **What it does:** Estimates pedestrian/vehicle density maps from overhead imagery using dilated CNN (CSRNet architecture)
- **How it integrates:**
  - Pedestrian-heavy zones flagged for NLP pedestrian incident reports
  - Density map feeds into SC fuzzy controller as additional input (high density = extend green)
  - Calibrates simulation pedestrian spawn rates
- **Files:** `ml/cv/models/crowd_density.py`
- **Input:** Virtual camera frames (focused on pedestrian zones) + real crowd imagery (ShanghaiTech dataset)
- **Output:** Density heatmaps per zone, count estimates
- **Training:** CSRNet on ShanghaiTech Crowd dataset, fine-tuned on synthetic virtual camera data
- **Dashboard:** Density heatmap overlay on map

#### CV-6: Virtual Camera Renderer (EXISTING)

- **What it does:** Renders top-down frames from engine WebSocket stream; roads from graph.json, agents as colored shapes
- **How it integrates:** Foundation for CV-3 through CV-12 (data source)
- **Files:** `ml/cv/virtual_camera.py`, `ml/cv/virtual_camera_service.py`
- **Status:** Documented in Phase 15, PLANNED

#### CV-7: U-Net Semantic Segmentation

- **What it does:** Pixel-level classification of road scenes into classes: road, vehicle, sidewalk, building, vegetation, sky
- **How it integrates:**
  - Road surface condition assessment (wet/dry/blocked) feeds into SC fuzzy controller
  - Segmented road area ratio validates simulation graph.json road coverage
  - Vehicle-to-road ratio per zone feeds into RL reward
- **Files:** `ml/cv/models/unet_segmentation.py`
- **Input:** Virtual camera frames + Cityscapes/Mapillary Vistas real-world images
- **Output:** Segmentation masks, per-class area ratios per zone
- **Training:** U-Net on Cityscapes dataset, domain-adapted to synthetic virtual camera style
- **Dashboard:** `SegmentationPanel.tsx` - color-coded segmentation overlay

#### CV-8: Mask R-CNN Instance Segmentation

- **What it does:** Per-vehicle instance masks for precise counting and size estimation
- **How it integrates:**
  - Instance masks improve CV-4 tracking (better appearance features than bbox alone)
  - Vehicle size classification (car/bus/truck) feeds into RL agent type distribution
  - Validates simulation vehicle type ratios against real-world distributions
- **Files:** `ml/cv/models/mask_rcnn.py`
- **Input:** Virtual camera frames
- **Output:** Instance masks, per-vehicle class + size
- **Dependencies:** Complements CV-3 (YOLO) with finer-grained segmentation
- **Dashboard:** SegmentationPanel.tsx - instance-colored overlays

#### CV-9: Farneback Optical Flow

- **What it does:** Computes dense optical flow field between consecutive frames, estimating per-pixel motion direction and magnitude
- **How it integrates:**
  - Mean flow magnitude per zone = real-time congestion velocity signal
  - Flow divergence patterns detect merging/splitting traffic (intersection analysis)
  - Feeds into RL reward as smoothness term (consistent flow = positive reward)
  - Validates against simulation agent velocities
- **Files:** `ml/cv/models/optical_flow.py`
- **Input:** Consecutive virtual camera frames
- **Output:** Flow field visualization, mean flow per zone, congestion velocity metric
- **Dashboard:** `OpticalFlowPanel.tsx` - flow field arrows overlaid on camera feed

#### CV-10: MOG2 Background Subtraction

- **What it does:** Gaussian mixture model background subtraction to isolate moving vehicles from static road background
- **How it integrates:**
  - Foreground mask improves CV-3 YOLO detection in low-contrast scenes
  - Static vs. moving vehicle ratio detects traffic jams (high static = jam)
  - Motion mask feeds into CV-9 optical flow as pre-processing
- **Files:** `ml/cv/models/background_sub.py`
- **Input:** Consecutive virtual camera frames
- **Output:** Foreground masks, moving/static vehicle counts per zone
- **Dependencies:** Pre-processing step for CV-3 and CV-9
- **Dashboard:** OpticalFlowPanel.tsx - foreground mask overlay

#### CV-11: Autoencoder Anomaly Detection

- **What it does:** Trains a convolutional autoencoder on normal traffic patterns; high reconstruction error = anomalous scene (accident, road closure, unusual congestion)
- **How it integrates:**
  - Anomaly score above threshold triggers NLP-9 event extraction (auto-incident generation)
  - Anomaly alerts feed into NLP-2 incident parser as structured events
  - Anomaly timeline visible in dashboard for cross-subject correlation analysis
- **Files:** `ml/cv/models/anomaly_detector.py`
- **Input:** Virtual camera frames (trained on normal traffic, tested on all)
- **Output:** Per-frame anomaly score, anomaly regions, triggered incidents
- **Training:** Convolutional autoencoder on "normal" virtual camera footage (no incidents)
- **Dashboard:** DetectionPanel.tsx - anomaly heatmap overlay, alert timeline

#### CV-12: Hough Transform Lane Detection

- **What it does:** Detects lane markings and road boundaries using edge detection + Hough line transform
- **How it integrates:**
  - Lane count validation against graph.json edge lane counts
  - Detected lane usage patterns feed into SC fuzzy controller (lane occupancy)
  - Lane-level congestion analysis (which lanes are most used)
  - Road geometry validation for simulation accuracy
- **Files:** `ml/cv/models/lane_detector.py`
- **Input:** Virtual camera frames (focused on road surface)
- **Output:** Detected lane lines, lane count per edge, lane usage statistics
- **Dashboard:** SegmentationPanel.tsx - lane overlay on road surface

### CV Data Flow Diagram

```
Mapbox/TomTom API -----> CV-1 (HSV Congestion) --+
                                                  +--> cv_congestion.json --> SC GA fitness
Mapbox/TomTom API -----> CV-2 (ResNet CNN) ------+

Engine WS Stream ------> CV-6 (Virtual Camera) --+
       |                                          |
       |    +-----> CV-3 (YOLO) -------> CV-4 (DeepSORT) --> tracking.json --> RL reward
       |    |
       |    +-----> CV-5 (Crowd Density) --------> density.json --> SC fuzzy input
       |    |
       |    +-----> CV-7 (U-Net Seg) ------------> seg.json --> SC road condition
       |    |
       |    +-----> CV-8 (Mask R-CNN) -----------> masks.json --> CV-4 appearance
       |    |
       |    +-----> CV-9 (Optical Flow) ----------> flow.json --> RL reward smoothness
       |    |
       |    +-----> CV-10 (BG Sub) -------> foreground --> CV-3 refinement
       |    |
       |    +-----> CV-11 (Anomaly AE) ---> anomaly.json --> NLP incident auto-gen
       |    |
       |    +-----> CV-12 (Lane Detect) --> lane.json --> SC lane-level tuning
```

---

## 4. Soft Computing (SC) - 12 Algorithms

### Overview

All 12 SC algorithms operate on the shared simulation calibration/signal-control problem. They share a common fitness evaluation function and produce outputs that directly configure the simulation engine.

### Algorithm Inventory

| # | Algorithm | Category | Problem | Integration Target | Dashboard Viz |
|---|-----------|----------|---------|-------------------|---------------|
| SC-1 | Genetic Algorithm (GA) | Evolutionary | Parameter calibration | Engine config | CalibrationReportPanel |
| SC-2 | Fuzzy Logic Controller (Mamdani) | Fuzzy Logic | Signal timing | SignalPolicy interface | FuzzyRulesPanel |
| SC-3 | Genetic Programming (GP) | Evolutionary | Rule evolution | SignalPolicy rules | FuzzyRulesPanel |
| SC-4 | Particle Swarm Optimization (PSO) | Swarm Intelligence | Parameter calibration | Engine config | ConvergencePanel |
| SC-5 | Ant Colony System (ACS) | Swarm Intelligence | Route optimization | Pathfinder edge costs | ConvergencePanel |
| SC-6 | Simulated Annealing (SA) | Probabilistic | Parameter calibration | Engine config | ConvergencePanel |
| SC-7 | Adaptive Neuro-Fuzzy (ANFIS) | Hybrid | Signal timing | SignalPolicy interface | FuzzyRulesPanel |
| SC-8 | Type-2 Fuzzy Logic | Fuzzy Logic | Signal timing (uncertainty) | SignalPolicy interface | FuzzyRulesPanel |
| SC-9 | Evolution Strategies (ES) | Evolutionary | Parameter calibration | Engine config | ConvergencePanel |
| SC-10 | Artificial Bee Colony (ABC) | Swarm Intelligence | Signal timing | SignalPolicy interface | ConvergencePanel |
| SC-11 | Rough Set Theory | Approximation | Feature reduction | Observation space pruning | N/A (embedded) |
| SC-12 | NSGA-II Multi-Objective | Evolutionary | Multi-objective calibration | Engine config (Pareto) | ParetoFrontPanel |

### Detailed Algorithm Designs

#### SC-1: Genetic Algorithm Calibration (EXISTING)

- **What it does:** Evolves optimal calibration parameters [speed_factor, route_spread, chaos, demand_scale] using tournament selection, blend crossover, Gaussian mutation
- **How it integrates:** Replaces manual parameter sweep in validate.py; output configures engine
- **Files:** `pipeline/src/optimize_calibration.py`, `ml/sc/models/ga_calibration.py`
- **Status:** Documented in Phase 13, PLANNED
- **Fitness function:** `build_report()` MAPE from validate.py

#### SC-2: Fuzzy Logic Signal Controller (EXISTING)

- **What it does:** Mamdani inference over queue length + wait time with triangular MFs, centroid defuzzification -> green-time extension
- **How it integrates:** Implements SignalPolicy interface; hot-swappable with Webster and RL
- **Files:** `engine/src/agent/FuzzyPolicy.h`
- **Status:** Documented in Phase 13.5, PLANNED

#### SC-3: Genetic Programming for Rule Evolution

- **What it does:** Evolves fuzzy IF-THEN rules automatically using GP (tree-based program evolution) instead of hand-specifying them
- **How it integrates:**
  - Evolved rules replace hand-crafted rules in SC-2 FuzzyPolicy
  - GP-evolved rules compared against hand-designed rules for performance
  - Rules are human-readable (a key advantage of GP over neural approaches)
- **Files:** `ml/sc/engine/genetic_programming.py`
- **Input:** Same fitness function as SC-1 (MAPE from engine subprocess)
- **Output:** Evolved rule set as JSON, deployed to FuzzyPolicy.h at runtime
- **GP Design:**
  - Terminals: input variables (queue_length, wait_time, neighbor_pressure, time_of_day)
  - Functions: IF-THEN-ELSE, AND, OR, NOT, comparison operators
  - Fitness: negative MAPE (lower MAPE = better)
  - Tree depth limit: 6 levels (prevents overfitting)
  - Population: 100, Generations: 50
- **Dashboard:** `FuzzyRulesPanel.tsx` - tree visualization of evolved rules vs. hand-crafted rules

#### SC-4: Particle Swarm Optimization (PSO)

- **What it does:** Optimizes the same 4 calibration parameters using swarm intelligence (velocity-position updates with inertia weight)
- **How it integrates:**
  - Same problem as SC-1 (GA) but different metaheuristic; comparison shows GA vs. PSO convergence
  - Output replaces engine calibration parameters
  - Best position -> engine config
- **Files:** `ml/sc/models/pso_optimizer.py`
- **Input:** Same fitness function as SC-1
- **Output:** `data/<city>/pso_report.json` - convergence curve + best parameters
- **PSO Design:**
  - Swarm size: 20 particles
  - Inertia weight: 0.7 -> 0.4 (linear anneal)
  - Cognitive coefficient c1 = 1.5, Social coefficient c2 = 1.5
  - Same bounds as SC-1 chromosome
  - Iterations: 30
- **Dashboard:** `ConvergencePanel.tsx` - PSO convergence curve alongside GA for comparison

#### SC-5: Ant Colony System (ACS) for Route Optimization

- **What it does:** Optimizes vehicle routing in the simulation by pheromone-based path selection; ants (virtual vehicles) explore routes, successful routes accumulate pheromone
- **How it integrates:**
  - Pheromone trails modify edge costs in Pathfinder -> changes agent routing
  - ACS-optimized routes compared against A* shortest path
  - Reduces average journey time by finding congestion-aware routes
- **Files:** `ml/sc/models/ant_colony.py`
- **Input:** Simulation graph + live congestion data (from CV-1 or engine metrics)
- **Output:** `data/<city>/acs_report.json` - pheromone heatmap, route quality metrics
- **ACS Design:**
  - Number of ants: 50 per iteration
  - Pheromone evaporation rate: 0.1
  - Alpha (pheromone weight): 1.0, Beta (heuristic weight): 2.0
  - Local pheromone update: reduce trail to encourage exploration
  - 20 iterations; evaluated on toy graph first, then Chicago
- **Engine integration:** New `--routing-policy acs` flag in Simulation that modifies edge costs based on pheromone matrix
- **Dashboard:** ConvergencePanel.tsx - pheromone heatmap overlay on map

#### SC-6: Simulated Annealing (SA)

- **What it does:** Optimizes calibration parameters using temperature-annealed probabilistic search; accepts worse solutions early (exploration) then narrows (exploitation)
- **How it integrates:**
  - Same problem as SC-1/SC-4 but with single-solution approach (not population-based)
  - Comparison shows population-based (GA/PSO) vs. single-solution (SA)
  - Output replaces engine calibration parameters
- **Files:** `ml/sc/models/simulated_annealing.py`
- **Input:** Same fitness function as SC-1
- **Output:** `data/<city>/sa_report.json` - temperature schedule, accepted solutions, final parameters
- **SA Design:**
  - Initial temperature: T0 = 100.0
  - Cooling schedule: exponential (alpha = 0.95)
  - Min temperature: 0.01
  - Perturbation: Gaussian step per parameter
  - Acceptance probability: exp(-delta/T)
  - Max iterations per temperature: 10
- **Dashboard:** ConvergencePanel.tsx - temperature schedule + fitness over time

#### SC-7: Adaptive Neuro-Fuzzy Inference System (ANFIS)

- **What it does:** Combines neural network learning with fuzzy logic; learns membership function parameters and rule consequents from data rather than hand-specifying
- **How it integrates:**
  - Trained on simulation data (queue lengths, wait times -> optimal green extension)
  - Replaces hand-crafted fuzzy rules in SC-2 with learned rules
  - Implements SignalPolicy interface for live deployment
  - Compares against SC-2 (hand-crafted) and SC-3 (GP-evolved)
- **Files:** `ml/sc/models/neuro_fuzzy.py`, `engine/src/agent/NeuroFuzzyPolicy.h`
- **Input:** Simulation training data: (queue_length, wait_time, neighbor_pressure) -> optimal_green_extension
- **Output:** Learned ANFIS model (parameters exported to C++ for real-time inference)
- **ANFIS Design:**
  - 5 layers: fuzzification -> rule firing -> normalization -> consequent -> defuzzification
  - Same 2 inputs as SC-2 (queue, wait) + 1 additional (neighbor pressure)
  - 3 MFs per input -> 27 rules (3^3)
  - Training: hybrid learning (gradient descent + least squares)
  - 1000 training samples from simulation runs
- **Engine integration:** Exported ANFIS parameters to JSON; loaded by NeuroFuzzyPolicy.h at startup
- **Dashboard:** FuzzyRulesPanel.tsx - learned MF shapes + rule strengths vs. hand-crafted

#### SC-8: Type-2 Fuzzy Logic Controller

- **What it does:** Extends SC-2's type-1 fuzzy logic with type-2 membership functions to handle greater uncertainty in queue/wait measurements
- **How it integrates:**
  - Higher uncertainty handling for noisy sensor data scenarios
  - Comparison: type-1 (SC-2) vs. type-2 (SC-8) performance under measurement noise
  - Implements SignalPolicy interface
- **Files:** `ml/sc/models/type2_fuzzy.py`
- **Input:** Same as SC-2 + noise injection for robustness testing
- **Output:** Green-time extension with uncertainty bounds
- **Type-2 Design:**
  - Interval type-2 fuzzy sets (IT2 FS)
  - Foot of uncertainty (FOU) = +/- 20% around type-1 MF centers
  - Same rule base as SC-2 but with type-2 inference
  - Type reduction: Karnik-Mendel algorithm
  - Defuzzification: centroid of type-reduced set
- **Engine integration:** Same SignalPolicy interface as SC-2; activated via `--signal-policy type2-fuzzy`
- **Dashboard:** FuzzyRulesPanel.tsx - FOU visualization alongside type-1 MFs

#### SC-9: Evolution Strategies (ES)

- **What it does:** Population-based parameter optimization using self-adaptive mutation rates; each individual carries its own strategy parameters (step sizes)
- **How it integrates:**
  - Same calibration problem as SC-1/SC-4/SC-6
  - Self-adaptive mutation vs. fixed mutation rate (GA) vs. velocity-based (PSO)
  - Output replaces engine calibration parameters
- **Files:** `ml/sc/models/evo_strategy.py`
- **Input:** Same fitness function as SC-1
- **Output:** `data/<city>/es_report.json` - convergence + self-adaptive parameter evolution
- **ES Design:**
  - (mu, lambda) = (10, 50) strategy
  - Self-adaptive step sizes (sigma per dimension)
  - Recombination: intermediate (average of parents)
  - Mutation: Gaussian with self-adaptive step sizes
  - 30 generations
- **Dashboard:** ConvergencePanel.tsx - alongside GA/PSO/SA

#### SC-10: Artificial Bee Colony (ABC)

- **What it does:** Signal timing optimization using bee colony foraging behavior; employed bees exploit known solutions, onlookers select profitable ones, scouts explore new regions
- **How it integrates:**
  - Optimizes fuzzy controller parameters (MF widths, rule weights) rather than raw calibration
  - Comparison: GA-tuned fuzzy (SC-1 -> SC-2) vs. ABC-tuned fuzzy
  - Implements SignalPolicy interface with ABC-optimized parameters
- **Files:** `ml/sc/models/bee_colony.py`
- **Input:** Same fitness function; optimization target = fuzzy controller parameters
- **Output:** Optimized fuzzy parameters, convergence data
- **ABC Design:**
  - Colony size: 30 (10 employed, 10 onlookers, 10 scouts)
  - Limit for abandonment: 5 trials
  - Fitness: negative MAPE
  - 30 cycles
- **Engine integration:** Optimized parameters loaded into FuzzyPolicy at startup
- **Dashboard:** ConvergencePanel.tsx + FuzzyRulesPanel.tsx (shows tuned MFs)

#### SC-11: Rough Set Theory for Feature Reduction

- **What it does:** Reduces the observation space dimensionality using rough set approximation; identifies minimal reduct (subset of features that preserves classification accuracy)
- **How it integrates:**
  - Applied to RL observation space: current 11-dim vector may have redundant features
  - Reduct set feeds into RL environment (fewer observations = faster training)
  - Discovers which simulation features are most informative for signal control decisions
  - Cross-subject: output affects RL observation space design
- **Files:** `ml/sc/models/rough_sets.py`
- **Input:** Simulation state data: (queue_lengths, pressures, time, phase) -> action (extend/switch)
- **Output:** Reduct set (minimal feature subset), decision rules, accuracy comparison
- **Rough Set Design:**
  - Discretization: equal-frequency binning for continuous attributes
  - Lower/upper approximation computation
  - Positive region maximization
  - Reduct computation via greedy heuristic
  - Compare accuracy: full 11 features vs. reduct features
- **Dashboard:** Embedded in AlgoExplorer SC tab - feature importance chart

#### SC-12: NSGA-II Multi-Objective Optimization

- **What it does:** Simultaneously optimizes conflicting objectives: minimize MAPE (accuracy) AND minimize Gini coefficient (equity) using Pareto-based selection
- **How it integrates:**
  - Produces Pareto front of calibration parameter sets
  - Each Pareto-optimal point represents a different accuracy-equity tradeoff
  - User selects operating point from Pareto front -> configures engine
  - Extends SC-1 (single-objective GA) to multi-objective
- **Files:** `ml/sc/models/nsga2.py`, `pipeline/src/moea_optimizer.py`
- **Input:** Two fitness functions: MAPE (from validate.py) + Gini coefficient (from simulation metrics)
- **Output:** `data/<city>/moga_report.json` - Pareto front, best compromise solution
- **NSGA-II Design:**
  - Population: 50
  - Generations: 40
  - Same chromosome as SC-1 [speed_factor, route_spread, chaos, demand_scale]
  - Non-dominated sorting + crowding distance
  - SBX crossover (eta=20) + polynomial mutation (eta=20)
- **Engine integration:** Selected Pareto point -> engine config; tradeoff curve visible in dashboard
- **Dashboard:** `ParetoFrontPanel.tsx` - interactive Pareto front plot (Recharts scatter), click to deploy

### SC Data Flow Diagram

```
Fitness Function (validate.py MAPE) --+---> SC-1 (GA) ------> best_params.json
                                      |                        |
CV congestion (cv_congestion.json) ---+---> SC-4 (PSO) ------> best_params.json
                                      |                        |
Simulation graph + live metrics ------+---> SC-5 (ACS) -------> pheromone.json
                                      |                        |
Fitness Function ---------------------+---> SC-6 (SA) -------> best_params.json
                                      |
Sim training data --------------------+---> SC-7 (ANFIS) -----> learned_params.json
                                      |
Same as SC-2 + noise injection -------+---> SC-8 (Type-2) ----> type2_params.json
                                      |
Fitness Function ---------------------+---> SC-9 (ES) -------> best_params.json
                                      |
Fuzzy parameters ---------------------+---> SC-10 (ABC) -----> tuned_fuzzy.json
                                      |
Sim state-action data ----------------+---> SC-11 (Rough) ----> reduct_set.json
                                      |
MAPE + Gini (two objectives) ---------+---> SC-12 (NSGA-II) --> pareto_front.json

SC-2 (Fuzzy) <--- SC-3 (GP evolved rules)
SC-2 (Fuzzy) <--- SC-7 (ANFIS learned params)
SC-2 (Fuzzy) <--- SC-8 (Type-2 variant)
SC-2 (Fuzzy) <--- SC-10 (ABC-tuned params)

All SC outputs ---> Engine SignalPolicy interface or engine config
```

---

## 5. Natural Language Processing (NLP) - 12 Algorithms

### Overview

All 12 NLP algorithms process text data related to the traffic simulation. They operate on three text sources:
- **Live metrics queries** from dashboard users
- **Generated incident reports** (synthetic + real)
- **Simulation event logs** converted to text

### Algorithm Inventory

| # | Algorithm | Category | Task | Integration Target | Dashboard Viz |
|---|-----------|----------|------|-------------------|---------------|
| NLP-1 | Rule-Based Intent Classifier | Classical | Query understanding | Live chat responses | ChatPanel |
| NLP-2 | Gazetteer + Fuzzy Incident Parser | Classical | Incident extraction | Engine apply_incident | IncidentReportPanel |
| NLP-3 | Sentiment Analyzer | ML | Traffic report sentiment | SC feedback loop | SentimentPanel |
| NLP-4 | Named Entity Recognizer (NER) | ML | Entity extraction | NLP-2 enhancement | NERPanel |
| NLP-5 | Text Classifier (Incident Type) | ML | Text classification | NLP-2 type detection | IncidentReportPanel |
| NLP-6 | Extractive Summarizer | Classical | Report summarization | Dashboard digest | ChatPanel |
| NLP-7 | Abstractive Summarizer | Deep Learning | Briefing generation | Dashboard briefing | ChatPanel |
| NLP-8 | Question Answering System | Deep Learning | QA over metrics | Enhanced chat | ChatPanel |
| NLP-9 | Event Extraction | ML | Structured event parsing | Auto incident generation | IncidentReportPanel |
| NLP-10 | Coreference Resolution | ML | Entity tracking across reports | Incident deduplication | NERPanel |
| NLP-11 | Stance Detection | ML | Feedback classification | SC parameter adjustment | SentimentPanel |
| NLP-12 | Knowledge Graph Builder | ML | Relationship extraction | Cross-subject query | KnowledgeGraphPanel |

### Detailed Algorithm Designs

#### NLP-1: Rule-Based Intent Classifier (EXISTING)

- **What it does:** Regex-based intent classification for live metric queries (worst_zone, avg_speed, active_agents, gini_explain, compare_policy, incident_status)
- **How it integrates:** Answers user queries from live engine state via WebSocket cache
- **Files:** `ml/nlp/chat_service.py`
- **Status:** Documented in Phase 16, PLANNED

#### NLP-2: Gazetteer + Fuzzy Incident Parser (EXISTING)

- **What it does:** Parses free-text incident reports into structured specs using street-name gazetteer + rapidfuzz matching
- **How it integrates:** Parsed incidents mutate the live simulation via apply_incident()
- **Files:** `ml/nlp/incident_parser.py`
- **Status:** Documented in Phase 17, PLANNED

#### NLP-3: Sentiment Analyzer for Traffic Reports

- **What it does:** Classifies sentiment (positive/negative/neutral) of traffic-related text: news reports, social media posts about traffic conditions
- **How it integrates:**
  - Aggregated sentiment per zone -> public perception metric
  - Negative sentiment spike -> potential incident -> triggers NLP-9 event extraction
  - Sentiment trend feeds into SC-12 as third objective (public satisfaction)
  - RL reward shaped by public sentiment (negative = something is wrong)
- **Files:** `ml/nlp/models/sentiment_analyzer.py`
- **Input:** Synthetic traffic reports + real datasets (SemEval traffic, Twitter traffic corpus)
- **Output:** `data/<city>/nlp_sentiment.json` - `{zone_id: {timestamp, sentiment_score, confidence, source_text}}`
- **Model approach:**
  - Baseline: TF-IDF + Logistic Regression
  - Comparison: Fine-tuned DistilBERT (6 layers, 66M params)
  - Training data: 5000 synthetic traffic reports with sentiment labels + real traffic tweet dataset
- **Dashboard:** `SentimentPanel.tsx` - sentiment timeline per zone, word cloud of positive/negative terms

#### NLP-4: Named Entity Recognizer (NER)

- **What it does:** Extracts structured entities from traffic text: LOCATION (streets, zones, landmarks), TIME (when), VEHICLE_TYPE (car, truck, bus), SEVERITY (minor, major), ACTION (blocked, slowed, diverted)
- **How it integrates:**
  - Enhances NLP-2 incident parser with richer entity extraction
  - Location entities validate against graph.json gazetteer
  - Extracted entities feed into NLP-12 knowledge graph
  - Time entities enable temporal reasoning in NLP-9 event extraction
- **Files:** `ml/nlp/models/ner_extractor.py`
- **Input:** Free-text traffic reports
- **Output:** Entity-tagged text + entity list per report
- **Model approach:**
  - Baseline: Rule-based + regex patterns for known entity types
  - Advanced: Fine-tuned BERT-NER on CoNLL-2003 + custom traffic entity annotations
  - Custom entity types: LOCATION, TIME, VEHICLE, SEVERITY, ROAD_FEATURE
- **Dashboard:** `NERPanel.tsx` - highlighted entities in text, entity type distribution chart

#### NLP-5: Text Classifier for Incident Type Classification

- **What it does:** Classifies traffic reports into incident categories: accident, construction, closure, weather, event, breakdown, congestion, other
- **How it integrates:**
  - Enhanced incident type detection for NLP-2 (replaces simple keyword matching)
  - Classification confidence feeds into NLP-2 severity estimation
  - Category distribution per zone feeds into SC calibration (construction zone patterns)
  - Enables smarter incident routing (construction vs. accident -> different engine responses)
- **Files:** `ml/nlp/models/text_classifier.py`
- **Input:** Free-text traffic reports
- **Output:** Incident type + confidence score
- **Model approach:**
  - Baseline: Keyword + TF-IDF + Naive Bayes
  - Comparison: Fine-tuned DistilBERT multi-class classifier
  - 8-class classification
  - Training: 3000 synthetic reports across 8 categories
- **Dashboard:** IncidentReportPanel.tsx - classification confidence per incident

#### NLP-6: Extractive Summarizer

- **What it does:** Extracts key sentences from multiple traffic reports to create a concise zone-level summary using TextRank algorithm
- **How it integrates:**
  - Summarizes all incidents in a zone into a brief status update
  - Summary feeds into ChatPanel responses (NLP-1) for richer answers
  - Daily summaries stored for historical analysis
  - Comparison baseline for NLP-7 (abstractive)
- **Files:** `ml/nlp/models/extractive_summary.py`
- **Input:** Collection of traffic reports per zone per time window
- **Output:** 2-3 sentence extractive summary per zone
- **Model approach:**
  - TextRank (graph-based sentence ranking)
  - BM25 scoring for sentence importance
  - Rouge-1/Rouge-L evaluation against human summaries
- **Dashboard:** ChatPanel.tsx - summary shown when user asks "what's happening in zone X?"

#### NLP-7: Abstractive Summarizer

- **What it does:** Generates natural-language traffic briefings from multiple incident reports using a fine-tuned language model
- **How it integrates:**
  - Generates human-readable briefings for dashboard display
  - Comparison: extractive (NLP-6) vs. abstractive quality
  - Briefings include cross-subject data: "Zone 5 has heavy congestion (CV detected), signal on fuzzy mode (SC), RL policy adapting (RL)"
  - Feeds into NLP-1 chat responses for natural language answers
- **Files:** `ml/nlp/models/abstractive_summary.py`
- **Input:** Multiple incident reports + live metrics + CV congestion data
- **Output:** Natural-language briefing paragraph per zone
- **Model approach:**
  - Fine-tuned T5-small (60M params) on synthetic traffic briefings
  - Input format: "summarize traffic: [incident1] [incident2] [metrics]"
  - Comparison against extractive (NLP-6) using human evaluation
- **Dashboard:** ChatPanel.tsx - briefing mode response

#### NLP-8: Question Answering System

- **What it does:** Answers specific questions about traffic conditions by combining retrieval (from metrics cache) with language understanding
- **How it integrates:**
  - Enhanced version of NLP-1 that handles complex questions
  - "Why is zone 5 congested?" -> retrieves incidents + CV data + generates explanation
  - "What happened between 2pm and 4pm?" -> temporal reasoning over event logs
  - Supports follow-up questions via conversation context
- **Files:** `ml/nlp/models/qa_system.py`
- **Input:** User questions + simulation state cache + incident history
- **Output:** Answer text + evidence sources
- **Model approach:**
  - Retrieval-augmented: BM25 retrieval from cached metrics/incidents + extractive QA
  - Comparison: rule-based (NLP-1) vs. retrieval QA vs. optional LLM
  - Handles 5 question types: factual, causal, temporal, comparative, advisory
- **Dashboard:** ChatPanel.tsx - enhanced responses with evidence links

#### NLP-9: Event Extraction

- **What it does:** Extracts structured events from unstructured text: (trigger, location, time, impact, duration) tuples
- **How it integrates:**
  - Auto-generates incident reports from CV-11 anomaly detection alerts
  - Converts simulation log messages into structured events
  - Event timeline feeds into dashboard event feed
  - Events trigger NLP-10 coreference resolution for deduplication
  - Feeds into NLP-12 knowledge graph as nodes
- **Files:** `ml/nlp/models/event_extractor.py`
- **Input:** Anomaly alerts (from CV-11), free-text reports, simulation logs
- **Output:** Structured event tuples
- **Model approach:**
  - Pattern-based extraction using dependency parsing
  - Comparison: rule-based vs. fine-tuned sequence-to-sequence model
  - Event schema: {type, location, time_start, time_end, impact_level, affected_edges[], description}
- **Dashboard:** IncidentReportPanel.tsx - event timeline visualization

#### NLP-10: Coreference Resolution

- **What it does:** Resolves entity references across multiple reports: "the accident on Michigan Ave" and "the crash near downtown" refer to the same incident
- **How it integrates:**
  - Deduplicates incident reports (same incident reported multiple times)
  - Maintains incident identity across temporal updates ("the accident is still there")
  - Feeds into NLP-12 knowledge graph with resolved entity links
  - Prevents duplicate apply_incident() calls to the engine
- **Files:** `ml/nlp/models/coref_resolver.py`
- **Input:** Multiple incident reports with unresolved references
- **Output:** Reports with resolved coreferences, cluster IDs for same-entity mentions
- **Model approach:**
  - Rule-based: string similarity + gazetteer matching (baseline)
  - Neural: Fine-tuned SpanBERT for span-level coreference
  - Evaluation: MUC, B-cubed, CEAFE metrics on annotated traffic report set
- **Dashboard:** NERPanel.tsx - coreference chains visualization

#### NLP-11: Stance Detection

- **What it does:** Classifies user feedback/opinions about traffic policies into stance categories: support, oppose, neutral, suggestion
- **How it integrates:**
  - Public stance on policies (bus lanes, congestion zones) feeds into SC-12 as soft constraint
  - Suggestion detection: "they should add a left turn lane" -> structured suggestion -> engine modification
  - Stance aggregation per zone: majority oppose -> consider policy rollback
  - Enables human-in-the-loop simulation adjustment
- **Files:** `ml/nlp/models/stance_detector.py`
- **Input:** User feedback text (synthetic + real forum/社交媒体 posts about traffic)
- **Output:** Stance label + confidence + aspect (what policy they're referring to)
- **Model approach:**
  - Baseline: TF-IDF + SVM
  - Advanced: Fine-tuned BERT for stance classification
  - 4-class: support, oppose, neutral, suggestion
  - Training: 2000 synthetic feedback comments
- **Dashboard:** SentimentPanel.tsx - stance distribution per policy

#### NLP-12: Knowledge Graph Builder

- **What it does:** Constructs a traffic knowledge graph from all NLP outputs: entities, relationships, events, and their temporal/spatial connections
- **How it integrates:**
  - Central hub connecting all NLP algorithms: NER entities + events + coreferences + sentiments
  - Queryable via NLP-8 QA system ("what incidents happened near zone 5 this week?")
  - Feeds into SC-11 rough set analysis (KG relationships as features)
  - KG statistics visible in dashboard (entity count, relationship density, temporal coverage)
  - Enables graph-based reasoning: "accident at X causes congestion at Y which affects Z"
- **Files:** `ml/nlp/models/knowledge_graph.py`
- **Input:** All NLP outputs (NER, events, coreferences, sentiments)
- **Output:** `data/<city>/nlp_knowledge_graph.json` - nodes (entities) + edges (relationships)
- **KG Design:**
  - Nodes: Locations, Incidents, Vehicles, TimePeriods, Zones, Policies
  - Edges: LOCATED_AT, CAUSES, AFFECTS, TEMPORAL_BEFORE, REPORTED_BY, SIMILAR_TO
  - Storage: NetworkX graph in Python, exported as JSON for dashboard
  - Query API: SPARQL-like pattern matching over the graph
- **Dashboard:** `KnowledgeGraphPanel.tsx` - interactive force-directed graph visualization

### NLP Data Flow Diagram

```
User queries ---------> NLP-1 (Rule Intent) -----> Chat responses
                       |                            |
                       +---> NLP-8 (QA System) ----+

Free-text reports ----> NLP-2 (Fuzzy Parser) ----> apply_incident() -> Engine
                       |
                       +---> NLP-4 (NER) ----------> entities
                       |
                       +---> NLP-5 (Classifier) ---> incident_type
                       |
                       +---> NLP-9 (Event Extract) -> structured events
                       |         |
                       |    CV-11 anomaly alerts ---+
                       |                             |
                       +---> NLP-10 (Coref) --------> deduplicated events
                       |
                       +---> NLP-3 (Sentiment) -----> sentiment.json -> SC-12
                       |
                       +---> NLP-6 (Extractive) ----> summaries
                       |
                       +---> NLP-7 (Abstractive) ---> briefings

All NLP outputs -----> NLP-12 (Knowledge Graph) ---> kg.json
                                |
                           NLP-8 (QA) queries the KG

User feedback -------> NLP-11 (Stance) ----------> stance.json -> SC-12
```

---

## 6. Reinforcement Learning (RL) - 12 Algorithms (Existing Plan)

*No changes to the existing RL plan. See docs/IMPLEMENTATION_PLAN.md Phases 19-24.*

| # | Algorithm | Family | Status |
|---|-----------|--------|--------|
| RL-1 | MAPPO | Actor-Critic (MARL) | IMPLEMENTED |
| RL-2 | Q-Learning | Tabular Value | PLANNED (Phase 20.1) |
| RL-3 | SARSA | Tabular Value | PLANNED (Phase 20.2) |
| RL-4 | DQN | Deep Value | PLANNED (Phase 20.3) |
| RL-5 | DDQN | Deep Value | PLANNED (Phase 20.4) |
| RL-6 | Dueling DQN | Deep Value | PLANNED (Phase 20.5) |
| RL-7 | REINFORCE | Policy Gradient | PLANNED (Phase 21.1) |
| RL-8 | A2C | Actor-Critic | PLANNED (Phase 21.2) |
| RL-9 | PPO (Single) | Actor-Critic | PLANNED (Phase 21.3) |
| RL-10 | SAC | Actor-Critic (continuous) | PLANNED (Phase 22.2) |
| RL-11 | TD3 | Actor-Critic (continuous) | PLANNED (Phase 22.3) |
| RL-12 | DDPG | Actor-Critic (continuous) | PLANNED (Phase 22.4) |

---

## 7. Cross-Subject Integration Architecture

### Integration Flow Diagram

```
+------------------+     +------------------+     +------------------+
|   CV-1/2         |     |   CV-3/4         |     |   CV-11          |
|   Congestion     |     |   Vehicle Count  |     |   Anomaly        |
|   Classification |     |   + Tracking     |     |   Detection      |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         v                        v                        v
+------------------+     +------------------+     +------------------+
| SC-1 GA Fitness  |     | RL Reward Shape  |     | NLP-9 Auto       |
| (accuracy term)  |     | (density signal) |     | Incident Gen     |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         v                        v                        v
+------------------+     +------------------+     +------------------+
| SC-4/6/9/12      |     | RL-1..12         |     | NLP-2 Incident   |
| Calibration      |     | Signal Control   |     | Parser           |
| Optimization     |     | Policies         |     | apply_incident() |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         +------------------------+------------------------+
                                  |
                                  v
                    +---------------------------+
                    |    C++ ENGINE             |
                    |    SignalPolicy interface |
                    |    live simulation        |
                    +---------------------------+
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
          +------------------+     +------------------+
          | SC-2/7/8/10      |     | NLP-1/8          |
          | Fuzzy/NeuroFuzzy |     | Live Chat        |
          | Signal Control   |     | Query Interface  |
          +------------------+     +------------------+
```

### Detailed Cross-Subject Data Flows

#### Flow 1: CV -> SC (Congestion-Calibration Feedback)

```
CV-1/2 (congestion from tiles) --> cv_congestion.json
  --> SC-1 GA: additional fitness term (sim accuracy vs. CV-observed)
  --> SC-12 NSGA-II: second objective (CV validation accuracy)
  --> SC-7 ANFIS: training data (congestion patterns)
```

#### Flow 2: CV -> RL (Visual Congestion Signal)

```
CV-3/4 (vehicle count + tracking) --> detection_results.json
  --> RL reward function: vehicle density per zone
  --> RL reward function: flow smoothness (from tracking trajectories)
  --> CV-9 (optical flow) --> flow.json --> RL reward: velocity signal
```

#### Flow 3: CV -> NLP (Anomaly-Triggered Incidents)

```
CV-11 (autoencoder anomaly) --> anomaly_score > threshold
  --> NLP-9 (event extraction): structured event from anomaly
  --> NLP-2 (incident parser): formatted incident report
  --> Engine apply_incident() --> simulation mutation
```

#### Flow 4: NLP -> Engine -> RL (Incident-Driven Adaptation)

```
NLP-2 (parsed incident) --> apply_incident(edges, severity, duration)
  --> Engine: temporary speed/capacity reduction
  --> RL agents observe changed queue patterns --> policy adapts
  --> CV virtual camera detects altered traffic flow
  --> Dashboard shows cross-subject reaction chain
```

#### Flow 5: SC -> Engine (Optimized Parameters)

```
SC-1/4/6/9 (GA/PSO/SA/ES) --> best calibration parameters
  --> Engine config: speed_factor, route_spread, chaos, demand_scale
  --> SC-5 (ACS): pheromone-modified edge costs --> routing
  --> SC-2/7/8/10 (Fuzzy/ANFIS/Type2/ABC): signal timing
  --> SC-11 (Rough Sets): reduced observation space for RL
```

#### Flow 6: NLP -> SC (Sentiment-Stance Feedback)

```
NLP-3 (sentiment) --> sentiment.json per zone
NLP-11 (stance) --> stance.json per policy
  --> SC-12 NSGA-II: third objective (public satisfaction)
  --> Pareto front now considers: accuracy + equity + sentiment
```

#### Flow 7: NLP -> NLP (Pipeline)

```
NLP-4 (NER) --> entities
NLP-5 (Classifier) --> incident type
  --> NLP-2 (enhanced parser): richer extraction
  --> NLP-10 (Coref): deduplication
  --> NLP-12 (Knowledge Graph): relationship storage
  --> NLP-8 (QA): queries the KG for complex answers
  --> NLP-6/7 (Summary): summarizes events for dashboard
```

#### Flow 8: SC -> RL (Warm Start)

```
SC-11 (Rough Sets) --> reduct set (minimal features)
  --> RL environment: reduced observation space (faster training)
SC-1 (GA) --> optimal parameters
  --> RL training: initialize with GA-optimized params
SC-7 (ANFIS) --> learned fuzzy policy
  --> RL: fuzzy policy as initial policy (warm start)
```

---

## 8. Unified Dashboard: Algo Explorer

### Component Architecture

```
AlgoExplorer.tsx
├── Subject Tabs: [CV] [SC] [NLP] [RL] [Compare]
│
├── CVPanel.tsx
│   ├── Algorithm Dropdown: [CV-1..CV-12]
│   ├── AlgorithmCard.tsx (description, status, metrics)
│   ├── Visualization area (switches based on selected algo):
│   │   ├── VirtualCameraPanel.tsx (CV-3,4,6,10)
│   │   ├── CongestionCVOverlay.tsx (CV-1,2)
│   │   ├── SegmentationPanel.tsx (CV-7,8,12)
│   │   ├── OpticalFlowPanel.tsx (CV-9,10)
│   │   └── DetectionPanel.tsx (CV-3,4,5,11)
│   └── Benchmark results table
│
├── SCPanel.tsx
│   ├── Algorithm Dropdown: [SC-1..SC-12]
│   ├── AlgorithmCard.tsx
│   ├── Visualization area:
│   │   ├── CalibrationReportPanel.tsx (SC-1,4,6,9)
│   │   ├── ConvergencePanel.tsx (SC-1,4,5,6,9,10)
│   │   ├── FuzzyRulesPanel.tsx (SC-2,3,7,8)
│   │   └── ParetoFrontPanel.tsx (SC-12)
│   └── Comparison: all optimizer convergence curves
│
├── NLPPanel.tsx
│   ├── Algorithm Dropdown: [NLP-1..NLP-12]
│   ├── AlgorithmCard.tsx
│   ├── Visualization area:
│   │   ├── ChatPanel.tsx (NLP-1,6,7,8)
│   │   ├── IncidentReportPanel.tsx (NLP-2,5,9,10)
│   │   ├── SentimentPanel.tsx (NLP-3,11)
│   │   ├── NERPanel.tsx (NLP-4,10)
│   │   └── KnowledgeGraphPanel.tsx (NLP-12)
│   └── NLP benchmark results
│
├── RLPanel.tsx
│   ├── Algorithm Dropdown: [RL-1..RL-12]
│   ├── AlgorithmCard.tsx
│   ├── Visualization area:
│   │   ├── Training curves (MLflow data)
│   │   ├── PolicyComparisonPanel.tsx (Phase 12.6)
│   │   └── MetricsPanel.tsx (live simulation metrics)
│   └── 12-algorithm comparison table
│
└── ComparisonView.tsx
    ├── Cross-subject correlation charts
    │   ├── CV congestion vs SC signal timing
    │   ├── NLP incidents vs RL policy adaptation
    │   └── SC parameters vs simulation accuracy
    └── Unified benchmark: all 36 algorithms summary
```

### API Endpoints (New Sidecar Services)

```
Port 9001: C++ Engine (existing)
Port 9003: CV Service (virtual camera + detection) [existing plan]
Port 9004: NLP Service (chat + incidents) [existing plan]
Port 9005: SC Service (optimizer status + convergence) [NEW]
Port 9006: Algo Explorer API (unified benchmark data) [NEW]
```

### Algo Explorer API Design

```python
# GET /api/algorithms - list all 36 algorithms with metadata
# GET /api/algorithms/{subject} - list algorithms for a subject
# GET /api/algorithms/{subject}/{id}/status - training status + metrics
# GET /api/benchmark/{subject} - comparison data for all algorithms in subject
# GET /api/benchmark/cross-subject - cross-subject integration metrics
# WS   /ws/live-metrics - real-time simulation metrics for dashboard
```

---

## 9. Experiment Tracking Strategy

### Hybrid Approach

| Algorithm Category | Tracking Method | Rationale |
|-------------------|----------------|-----------|
| RL (all 12) | MLflow | Training runs with hyperparams, checkpoints, metrics curves |
| CV deep learning (CV-2,3,4,7,8,11) | MLflow | Model training with epochs, loss curves, accuracy |
| CV classical (CV-1,5,6,9,10,12) | Flat JSON | Lightweight; no training loop |
| SC population-based (SC-1,3,4,9,10,12) | MLflow | Generation-by-generation tracking |
| SC other (SC-2,5,6,7,8,11) | Flat JSON | Configuration results, no training loop |
| NLP deep learning (NLP-7,8) | MLflow | Fine-tuning runs with epochs |
| NLP ML (NLP-3,4,5,9,10,11) | MLflow | Training with train/val metrics |
| NLP classical (NLP-1,2,6,12) | Flat JSON | Rule-based, no training |

### Output Schema Convention

All algorithms produce a result file at `data/<city>/<algorithm>_results.json`:

```json
{
  "algorithm": "cv_yolo_detection",
  "subject": "cv",
  "version": "1.0",
  "timestamp": "2026-08-19T12:00:00Z",
  "city": "chicago",
  "metrics": {
    "primary": {"name": "mAP@0.5", "value": 0.87},
    "secondary": [{"name": "inference_time_ms", "value": 12.3}]
  },
  "config": { "model": "yolov8n", "img_size": 640 },
  "mlflow_run_id": "abc123"  // or null for flat-file algorithms
}
```

---

## 10. Implementation Phases (Extended)

### Existing Phases (0-24): Unchanged

See docs/IMPLEMENTATION_PLAN.md

### New Phases (25-36): CV, SC, NLP Expansion

#### Phase 25 - CV Foundation: Virtual Camera + Detection (1 week)

| # | Task | Branch |
|---|------|--------|
| 25.1 | Implement `ml/cv/` package structure with `__init__.py`, `configs.yaml` | `feature/cv-package-init` |
| 25.2 | Implement CV-6 virtual camera renderer (from Phase 15 design) | `feature/cv6-virtual-camera` |
| 25.3 | Implement CV-3 YOLOv8 vehicle detection on virtual camera frames | `feature/cv3-yolo-detection` |
| 25.4 | Implement CV-10 MOG2 background subtraction | `feature/cv10-bg-subtraction` |
| 25.5 | Wire CV-3 vehicle count into RL reward function | `feature/cv3-rl-integration` |
| 25.6 | `DetectionPanel.tsx` + `VirtualCameraPanel.tsx` | `feature/cv-dashboard-panels` |

#### Phase 26 - CV Advanced: Tracking + Segmentation (1 week)

| # | Task | Branch |
|---|------|--------|
| 26.1 | Implement CV-4 DeepSORT multi-object tracking | `feature/cv4-deepsort` |
| 26.2 | Implement CV-7 U-Net semantic segmentation | `feature/cv7-unet-segmentation` |
| 26.3 | Implement CV-8 Mask R-CNN instance segmentation | `feature/cv8-mask-rcnn` |
| 26.4 | Wire CV-7 road condition into SC fuzzy controller inputs | `feature/cv7-sc-integration` |
| 26.5 | `SegmentationPanel.tsx` + update `DetectionPanel.tsx` | `feature/cv2-dashboard` |

#### Phase 27 - CV Motion + Anomaly + Lanes (1 week)

| # | Task | Branch |
|---|------|--------|
| 27.1 | Implement CV-9 Farneback optical flow | `feature/cv9-optical-flow` |
| 27.2 | Implement CV-11 autoencoder anomaly detection | `feature/cv11-anomaly-detection` |
| 27.3 | Implement CV-12 Hough lane detection | `feature/cv12-lane-detection` |
| 27.4 | Implement CV-5 CSRNet crowd density estimation | `feature/cv5-crowd-density` |
| 27.5 | Wire CV-11 anomaly alerts into NLP-9 event extraction | `feature/cv11-nlp-integration` |
| 27.6 | `OpticalFlowPanel.tsx` | `feature/cv3-dashboard` |

#### Phase 28 - SC Metaheuristics: GA + PSO + SA + ES (1 week)

| # | Task | Branch |
|---|------|--------|
| 28.1 | Implement SC-1 GA calibration (from Phase 13 design) | `feature/sc1-ga-calibration` |
| 28.2 | Implement SC-4 PSO optimizer | `feature/sc4-pso` |
| 28.3 | Implement SC-6 Simulated Annealing | `feature/sc6-sa` |
| 28.4 | Implement SC-9 Evolution Strategies | `feature/sc9-es` |
| 28.5 | Common fitness evaluation module `ml/sc/engine/fitness.py` | `feature/sc-fitness` |
| 28.6 | `ConvergencePanel.tsx` with all optimizer curves | `feature/sc-convergence-panel` |

#### Phase 29 - SC Swarm + Hybrid: ACS + ABC + ANFIS (1 week)

| # | Task | Branch |
|---|------|--------|
| 29.1 | Implement SC-5 Ant Colony System routing | `feature/sc5-acs` |
| 29.2 | Implement SC-10 Artificial Bee Colony | `feature/sc10-abc` |
| 29.3 | Implement SC-7 ANFIS neuro-fuzzy controller | `feature/sc7-anfis` |
| 29.4 | Implement SC-8 Type-2 fuzzy controller | `feature/sc8-type2-fuzzy` |
| 29.5 | Wire SC-5 pheromone routing into Pathfinder | `feature/sc5-engine-integration` |
| 29.6 | `FuzzyRulesPanel.tsx` with MF visualization | `feature/sc-fuzzy-panel` |

#### Phase 30 - SC GP + Rough Sets + NSGA-II (1 week)

| # | Task | Branch |
|---|------|--------|
| 30.1 | Implement SC-3 Genetic Programming rule evolution | `feature/sc3-gp` |
| 30.2 | Implement SC-11 Rough Set feature reduction | `feature/sc11-rough-sets` |
| 30.3 | Implement SC-12 NSGA-II multi-objective optimization | `feature/sc12-nsga2` |
| 30.4 | Wire SC-11 reduct set into RL observation space | `feature/sc11-rl-integration` |
| 30.5 | Wire SC-12 Pareto front into engine config selection | `feature/sc12-pareto-deploy` |
| 30.6 | `ParetoFrontPanel.tsx` + update `CalibrationReportPanel.tsx` | `feature/sc2-dashboard` |

#### Phase 31 - NLP Core: Chat + Incidents + Sentiment (1 week)

| # | Task | Branch |
|---|------|--------|
| 31.1 | Implement NLP-1 rule-based intent classifier (from Phase 16) | `feature/nlp1-intent-classifier` |
| 31.2 | Implement NLP-2 gazetteer incident parser (from Phase 17) | `feature/nlp2-incident-parser` |
| 31.3 | Implement NLP-3 sentiment analyzer | `feature/nlp3-sentiment` |
| 31.4 | Implement NLP-5 text classifier | `feature/nlp5-text-classifier` |
| 31.5 | Wire NLP-3 sentiment into SC-12 multi-objective | `feature/nlp3-sc-integration` |
| 31.6 | `ChatPanel.tsx` + `IncidentReportPanel.tsx` + `SentimentPanel.tsx` | `feature/nlp1-dashboard` |

#### Phase 32 - NLP Extraction: NER + Events + Coref (1 week)

| # | Task | Branch |
|---|------|--------|
| 32.1 | Implement NLP-4 NER extractor | `feature/nlp4-ner` |
| 32.2 | Implement NLP-9 event extraction | `feature/nlp9-event-extraction` |
| 32.3 | Implement NLP-10 coreference resolution | `feature/nlp10-coref` |
| 32.4 | Wire NLP-9 with CV-11 anomaly alerts | `feature/nlp9-cv-integration` |
| 32.5 | `NERPanel.tsx` | `feature/nlp2-dashboard` |

#### Phase 33 - NLP Advanced: Summarization + QA + KG (1 week)

| # | Task | Branch |
|---|------|--------|
| 33.1 | Implement NLP-6 extractive summarizer | `feature/nlp6-extractive` |
| 33.2 | Implement NLP-7 abstractive summarizer | `feature/nlp7-abstractive` |
| 33.3 | Implement NLP-8 QA system | `feature/nlp8-qa-system` |
| 33.4 | Implement NLP-11 stance detection | `feature/nlp11-stance` |
| 33.5 | Implement NLP-12 knowledge graph builder | `feature/nlp12-knowledge-graph` |
| 33.6 | `KnowledgeGraphPanel.tsx` | `feature/nlp3-dashboard` |

#### Phase 34 - Cross-Subject Integration (1 week)

| # | Task | Branch |
|---|------|--------|
| 34.1 | Implement cross-subject event bus (WebSocket message routing) | `feature/cross-subject-bus` |
| 34.2 | Wire CV-11 -> NLP-9 -> Engine incident chain | `feature/cv-nlp-engine-chain` |
| 34.3 | Wire NLP incidents -> RL policy adaptation feedback | `feature/nlp-rl-adaptation` |
| 34.4 | Wire SC-11 -> RL observation space reduction | `feature/sc-rl-obs-reduction` |
| 34.5 | Wire CV congestion -> SC GA fitness term | `feature/cv-sc-fitness` |
| 34.6 | Wire SC params -> RL warm start initialization | `feature/sc-rl-warmstart` |
| 34.7 | End-to-end integration test: all 4 subjects reacting | `feature/e2e-36-algo-test` |

#### Phase 35 - Unified Dashboard Algo Explorer (1 week)

| # | Task | Branch |
|---|------|--------|
| 35.1 | Implement `AlgoExplorer.tsx` container with subject tabs | `feature/algo-explorer-base` |
| 35.2 | Implement `CVPanel.tsx` with algorithm dropdown + dynamic viz | `feature/algo-explorer-cv` |
| 35.3 | Implement `SCPanel.tsx` with algorithm dropdown + dynamic viz | `feature/algo-explorer-sc` |
| 35.4 | Implement `NLPPanel.tsx` with algorithm dropdown + dynamic viz | `feature/algo-explorer-nlp` |
| 35.5 | Implement `RLPanel.tsx` with algorithm dropdown + dynamic viz | `feature/algo-explorer-rl` |
| 35.6 | Implement `ComparisonView.tsx` cross-subject correlation charts | `feature/algo-explorer-compare` |
| 35.7 | Implement `AlgorithmCard.tsx` reusable component | `feature/algo-card-component` |
| 35.8 | Implement Algo Explorer API sidecar (port 9006) | `feature/algo-explorer-api` |

#### Phase 36 - Results, Benchmarks & Documentation (1 week)

| # | Task | Branch |
|---|------|--------|
| 36.1 | Run all 36 algorithms on toy graph, collect results | `experiment/36-algo-benchmark` |
| 36.2 | Generate cross-subject comparison tables | `docs/36-algo-results` |
| 36.3 | Update CV_DOCUMENTATION.md with all 12 CV algorithms | `docs/cv-12-algorithms` |
| 36.4 | Update SOFT_COMPUTING_DOCUMENTATION.md with all 12 SC algorithms | `docs/sc-12-algorithms` |
| 36.5 | Update NLP_DOCUMENTATION.md with all 12 NLP algorithms | `docs/nlp-12-algorithms` |
| 36.6 | Write mega project integration document | `docs/mega-integration-doc` |
| 36.7 | Record integrated demo video showing all 36 algorithms | `docs/demo-36-algo` |

---

## 11. Real-World Data Sources

### CV Datasets

| Dataset | Purpose | Size | Source |
|---------|---------|------|--------|
| UA-DETRAC | Vehicle detection + tracking training | 10 hours, 100K frames | detrac.compking.cn |
| BDD100K | Diverse driving scenes (seg, det) | 100K video clips | bdd.berkeley.edu |
| Cityscapes | Semantic segmentation | 5K fine + 20K coarse | cityscapes-dataset.com |
| Mapillary Vistas | Street-level semantic seg | 25K images | mapillary.com |
| KITTI | Detection, tracking, depth | 15K frames | cvlibs.net/datasets/kitti |
| ShanghaiTech Crowd | Crowd density estimation | 1198 images |  |
| Synthetic (virtual camera) | Generated from simulation | Unlimited | CV-6 renderer |

### NLP Datasets

| Dataset | Purpose | Size | Source |
|---------|---------|------|--------|
| SemEval Traffic | Traffic sentiment analysis | 5K sentences | SemEval shared tasks |
| CoNLL-2003 | NER pre-training | 22K sentences | HuggingFace datasets |
| SQuAD 2.0 | QA pre-training | 150K questions |rajpurkar.github.io |
| MATRES | Temporal relation extraction | 18K pairs |  |
| SynthIA (synthetic) | Traffic incident reports | 10K generated | Template + LLM |
| Custom annotated | Traffic NER, sentiment, stance | 5K labeled | Generated + annotated |

### SC Benchmark Functions

| Function | Purpose | Dimensions |
|----------|---------|------------|
| Rosenbrock | SC-1/4/6/9 benchmark | 4 |
| Rastrigin | Multi-modal optimization test | 4 |
| Simulation MAPE | Actual fitness function | 4 |
| Simulation Gini | Equity objective | 4 |

---

## 12. Dependencies Summary

### New Python Packages

| Package | Subject | Algorithms | Purpose |
|---------|---------|------------|---------|
| `ultralytics` | CV | CV-3 | YOLOv8 vehicle detection |
| `deep-sort-realtime` | CV | CV-4 | SORT/DeepSORT tracking |
| `torchvision` | CV | CV-2,7,8,11 | CNN, U-Net, Mask R-CNN, Autoencoder |
| `opencv-python` | CV | CV-1,6,9,10,12 | Image processing |
| `scikit-image` | CV | CV-9,12 | Hough transform, flow |
| `scikit-fuzzy` | SC | SC-2,8 | Fuzzy logic |
| `anfis` or custom | SC | SC-7 | Neuro-fuzzy |
| `pyswarm` | SC | SC-4 | PSO (or implement from scratch) |
| `networkx` | NLP | NLP-12 | Knowledge graph |
| `transformers` | NLP | NLP-3,4,5,7,8,10,11 | BERT, T5, DistilBERT |
| `spacy` | NLP | NLP-4,6,9,10 | NER, parsing, coref |
| `rapidfuzz` | NLP | NLP-2 | Fuzzy string matching |
| `rouge-score` | NLP | NLP-6,7 | Summarization evaluation |

### No Changes to Existing

- C++ engine dependencies: unchanged
- Dashboard dependencies: React + Leaflet + Recharts (extended, not replaced)
- MLflow: already in stack
- Python ML: PyTorch, gymnasium, numpy (already in stack)

---

*This document is the master plan for expanding NexusSim to a 36-algorithm mega project. Each subject's documentation file (CV_DOCUMENTATION.md, SOFT_COMPUTING_DOCUMENTATION.md, NLP_DOCUMENTATION.md) should be updated to match the detailed designs in sections 3, 4, and 5 respectively.*

*Last updated: August 2026.*
