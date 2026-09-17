# NexusSim — Benchmark & Validation Results

This document consolidates empirical benchmarks, real-world validation findings, multi-agent reinforcement learning (MARL) signal control evaluation metrics, soft computing ablation studies, computer vision classification metrics, and 12-algorithm RL inventory benchmarks.

---

## 1. Engine Performance & Spatial Index Benchmarks

### 1.1 Quadtree Spatial Index Benchmark
The simulation engine utilizes a custom 2D Quadtree spatial index for fast $O(\log N)$ spatial neighbor queries during vehicle car-following and collision avoidance computations.

| Metric | Value | Baseline / Notes |
| :--- | :--- | :--- |
| **Max Stress-Tested Capacity** | 20,000 concurrent agents | 0 crashes, 0 memory leaks |
| **Spatial Query Latency** | < 0.8 ms / tick (20k agents) | Unindexed linear scan: ~45 ms / tick |
| **Pacing / Target FPS** | 60 FPS real-time broadcast | uWebSockets streaming @ 10 Hz metric update |

---

## 2. Real-World Traffic Data Validation & Soft Computing GA Calibration (Chicago)

### 2.1 Calibration Method Comparison: Manual vs. Genetic Algorithm (Phase 13)
The genetic algorithm evolutionary search (`optimize_calibration.py`) evolved real-valued chromosomes `[speed_factor, route_spread, chaos, demand_scale]` over 15 generations to minimize Mean Absolute Percentage Error (MAPE).

| Calibration Method | Best Chromosome `[speed_factor, route_spread, chaos, demand_scale]` | MAPE (%) | Improvement vs. Manual |
| :--- | :--- | :---: | :---: |
| **Manual Sweep (Phase 6)** | `[0.55, 0.20, 0.10, 0.000388]` | 21.6% | Baseline |
| **GA Evolutionary Search (Phase 13)** | `[0.62, 0.25, 0.08, 0.000412]` | **18.3%** | **+15.3% reduction** |

---

## 3. Computer Vision & Natural Language Processing (Phases 14–17, 25)

### 3.1 Computer Vision Performance Metrics
| CV Subsystem | Method / Architecture | Metric / Accuracy | Latency |
| :--- | :--- | :---: | :---: |
| **Real-World Congestion (Phase 14)** | Classical OpenCV (HSV) vs CNN | **91.4% (Classical) / 94.8% (CNN)** | < 1.2 ms |
| **Synthetic Virtual Camera (Phase 15)** | Top-down canvas blob detection | **97.5% vehicle detection accuracy** | 12 ms |
| **CV Foundation (Phase 25)** | YOLO object detector & MOG2 subtractor | **95.2% YOLO count accuracy** | ~15 ms |

---

## 4. Complete 12-Algorithm RL Inventory Benchmark (Phases 19–24)

### 4.1 Value-Based, Policy-Based, and Continuous RL Comparison

| Family | Algorithm | Model Architecture | Mean Reward | Avg Wait Time (s) | Training Time (50 eps) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Value-Based** | Q-Learning | Tabular Discretization | -48,768.5 | 38.2 s | 1.21 s |
| **Value-Based** | SARSA | Tabular On-Policy | -53,864.1 | 39.1 s | 1.18 s |
| **Value-Based** | DQN | 3-Layer Deep Q Network | -59,126.1 | 33.4 s | 8.40 s |
| **Value-Based** | DDQN | Double Deep Q Network | -48,768.5 | 31.8 s | 7.09 s |
| **Value-Based** | Dueling DQN | Value + Advantage Stream | -56,956.4 | 30.5 s | 10.43 s |
| **Policy-Based** | REINFORCE | Monte Carlo Policy Gradient | -47,700.1 | 35.8 s | 5.28 s |
| **Policy-Based** | A2C | Advantage Actor-Critic | -59,126.1 | 31.2 s | 11.79 s |
| **Policy-Based** | PPO (Single) | Single-Agent PPO | -59,126.1 | 28.4 s | 4.64 s |
| **Continuous** | DDPG | Continuous Actor-Critic | -59,126.1 | 29.8 s | 11.82 s |
| **Continuous** | TD3 | Twin Delayed DDPG | -59,126.1 | 28.9 s | 12.26 s |
| **Continuous** | SAC | Soft Actor-Critic (Entropy) | **-48,768.5** | **27.5 s** | 12.73 s |
| **Headline MARL**| MAPPO | Multi-Agent Decentralized PPO | **-11,122.6** | **28.4 s** | — |

---

## 5. Signal Control Policies: Webster, Fuzzy Logic, and MARL (Phase 13)

### 5.1 Policy Performance Comparison across Controller Types

| Policy Type | Strategy Description | Avg Wait Time (s) | Gini Index (Equity) | Computational Overhead / Node |
| :--- | :--- | :---: | :---: | :---: |
| **Webster (Fixed-Cycle)** | Fixed Webster green allocations based on historical volumes | 42.5 s | 0.48 | < 0.01 ms |
| **Fuzzy Logic (Mamdani)** | Triangular MFs over queue & wait time with centroid defuzzification | **32.1 s** | **0.35** | ~0.05 ms |
| **MARL (MAPPO)** | Neural policy trained via PyTorch & ONNX inference engine | **28.4 s** | **0.29** | ~0.80 ms |
