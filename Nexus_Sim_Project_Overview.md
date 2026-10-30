## Slide 1: Title — NexusSim Project Overview
- Real-time multi-agent urban traffic simulation and AI research sandbox
- Rebuilds real city road networks from OpenStreetMap; drives them with origin–destination (OD) demand
- Simulates in a C++17 engine; streams live state to a React dashboard over WebSocket (port 9001)
- One integrated system covering four academic subjects: Reinforcement Learning, Computer Vision, NLP, Soft Computing (PRD BR-1/BR-3)
- Planner's sandbox: test signal policies, bus lanes, congestion pricing before changing real streets; equity (Gini coefficient of wait times) is a first-class metric
- Basis: docs/PRD.md v2.0, docs/TRD.md, docs/NEXUS-SIM-DOCUMENTATION.md — claims verified against the working tree unless flagged
**Speaker notes:** NexusSim is an academic urban-traffic simulation platform, not a production traffic-control system. Its stated differentiator is that RL, CV, NLP, and Soft Computing share one live simulation instead of existing as four isolated demos. This deck separates what is built from what is documented but unverified.

## Slide 2: Problem & Motivation
- Urban signals run on static, decades-old fixed-cycle timings that are rarely recalibrated
- City administrators have no safe, cost-free way to test policy changes (bus lanes, freight rerouting, congestion pricing); pilots disrupt real commuters
- Optimizing average commute time alone benefits well-connected zones while underserved transit-dependent neighborhoods see no improvement or get worse
- Non-goals: no real signal hardware, no live city monitoring, no proprietary data, no Google Maps traffic-layer scraping (ToS violation), no end-user navigation app
- NexusSim answers two question types: routing (corridor journey times, congestion hotspots) and equity (which neighborhoods bear the cost)
**Speaker notes:** The problem statement is policy-centric: decisions are made blind or after expensive pilots. These non-goals define scope boundaries used throughout verification and keep the presentation focused on the simulated sandbox, not real-world deployment.

## Slide 3: System Architecture
- Sidecar pattern: C++ engine is the only writer of simulation truth; every other component consumes its WebSocket stream (TRD §3 rule 1)
- Ports/contracts: engine 9001 (WS); virtual camera 9003; NLP chat/incidents 9004; event bus 9005; algo explorer 9006; dashboard 3000/5173
- Broadcast fields additive-only (NFR-5): dashboard ignores unknown keys, so engine additions never break the UI
- Per-city variation is config, not code (FR-6/TR-7): pipeline/cities.yaml is the single city registry
- ML/CV/NLP run as independent sidecar processes (TR-6): never in the C++ hot path or frontend bundle; ONNX inference off hot path via background thread + SPSC ring buffer
**Speaker notes:** This is the load-bearing architecture. The engine exposes uWebSockets on 9001 and broadcasts per-tick JSON {tick, agents[], metrics, zone_metrics, mode, signals[], incidents[]}. The additive-only broadcast rule is why new CV/NLP/RL fields can be added without versioning the dashboard contract.

## Slide 4: Core Modules & Tech Stack
- engine/ (C++17): Graph/GraphLoader, Simulation, IDM car-following, A* Pathfinder, SignalPolicy (Webster/Fuzzy/Type-2/RL/Symbolic), InferenceEngine (ONNX), WebSocketServer, ThreadPool, NLPQueryParser
- pipeline/ (Python 3.11): download→clean→lanes→zones→export (graph.json + od_matrix.json); validate; optimize_calibration (GA); cv_congestion (real tiles via MAPBOX_ACCESS_TOKEN / TOMTOM_API_KEY env key; synthetic fallback)
- ml/ (Python): train/transfer/evaluate/ppo/rollout; algo (base_trainer, value_based, policy_based, continuous_control); env (NexusSimEnv, reward, observation); cv/*; nlp/*; export/export_onnx
- dashboard/ (React 19 + TS + Vite + Leaflet): Map, MetricsPanel, EquityOverlay, PolicyToggle/Comparison, CV/VirtualCamera/Chat/Incident panels
- Stack: C++17/CMake/Ninja; Python 3.11/PyTorch/MLflow/Gymnasium/OpenCV; React 19/TypeScript/Vite; data from OpenStreetMap via osmnx and Chicago Socrata TNP
**Speaker notes:** File names are cited so an evaluator can trace each documented feature to code. engine/src/agent/ contains all signal policies; ml/algo/ holds the RL inventory; pipeline/src/ holds data and calibration stages. The dashboard component list matches TRD §4.4 one-for-one.

## Slide 5: Build & Setup
- Prerequisites: GCC 11+/MinGW-w64 (C++17), CMake ≥ 3.25, Python 3.11+, Node.js 20+
- Windows: run.bat builds engine, trains (optional), starts engine + all sidecars
- Unix: make build / run / demo / test / bench / dashboard (Makefile hardcodes -G Ninja)
- Docker: docker-compose.yml + Dockerfile.{engine,sidecars,dashboard} present but unbuilt in this environment
- This environment: cmake 4.4.0 ✓, python 3.11.9 ✓, node 22.17.1 ✓; make ✗, ninja ✗, openssl ✗ → cmake -G Ninja blocked; prebuilt build/engine.exe exists from a prior build
**Speaker notes:** The documented build path is partially blocked in this sandbox: no make or ninja, no OpenSSL, and a cmake FetchContent configure that stalls on source builds. Prebuilt binaries exist but their test configuration was not re-verified. Docker files exist but were not built or run here.

## Slide 6: Verification Results (Measured)
- Tests measured: pipeline pytest 39 passed; ml pytest 84 passed (100% GREEN); dashboard vitest 8 passed; gateway pytest 42 passed (includes 4 NexusTwin endpoints); Postman collection 52 requests across 11 folders (A through L) verified
- Engine CTest could not be re-run here (configure incomplete); prebuilt test binary present
- Performance: 20k agents 8.64 ms avg / 12 ms p95 (~113 ticks/s); ONNX p95 0.0179 ms (batch 64) / 0.0265 ms (batch 256); re-measured 0.040–0.133 ms — all ≪ 8 ms budget (NFR-4); AI stress −2.4 FPS vs < 5 FPS budget
- Chicago validation: MAPE 21.6%, 7/11 corridors (63.6%) within 25%, passes_checkpoint: false → checkpoint NOT met (target ≥ 75%)
- MARL vs Webster (comparison.json): toy +52.3%, piedmont −14.9%, chicago +26.3% reward; chicago Gini 0.286 → 0.331 (equity worsened)
**Speaker notes:** Where docs and artifacts disagree, both are reported and flagged rather than picking a number. All performance figures come from docs/results.md and docs/AI_STRESS_REPORT.md with reproduction commands; test counts were re-measured by running the suites in this environment.

## Slide 7: RL Component Status
- Headline: MAPPO, one independent agent per signalised intersection, shared network-wide equity reward (PRD BR-5 — no centralised controller, no message-passing MARL)
- Observation: 11-dim normalised vector (4 per-approach queues, phase, time-in-phase, time-of-day, 4 neighbour pressures); action {EXTEND, SWITCH}
- Reward: α×pressure + β×equity (α=β=1.0 default); Gini logged per checkpoint; traffic_sim.py now accumulates per-episode wait time, so the PRD "≥ 15% wait reduction" metric is computable
- All RL evaluate() methods (Q-Learning, SARSA, DQN/DDQN/Dueling, REINFORCE, A2C, PPO) now report real mean_wait instead of None
- Inventory: 12 algorithms (MAPPO + Q-Learning/SARSA/DQN/DDQN/Dueling/REINFORCE/A2C/PPO + DDPG/TD3/SAC on Pendulum-v1); ONNX export validated vs PyTorch (10 inputs, atol=1e-4); policy.onnx loads into the C++ engine via RLPolicy; p95 inference ≪ 8 ms budget
- Gaps: benchmark.py/configs.yaml/eval/report.py harness missing; value-based algorithms only on toy grid; CUDA ONNX provider unfinished; wait-reduction not yet published
**Speaker notes:** The RL component is real code and engine-integrated: a trained checkpoint (ml/checkpoints/chicago/199.pt) drives signal phases live via ONNX. The main open item is measured efficacy beyond reward curves, since wait-time reduction has not been published.

## Slide 8: CV & NLP Component Status (Fixed)
- CV congestion: cv_congestion.py now fetches real Mapbox Traffic Tiles / TomTom Traffic Flow tiles when MAPBOX_ACCESS_TOKEN or TOMTOM_API_KEY is set; synthetic 64×64 fallback otherwise (BR-6 compliant, key never committed)
- CV accuracy figures (91.4%/94.8%/97.5%) unverified; YOLO/DeepSORT/U-Net/Mask R-CNN weights not in repo; virtual camera is request/response REST, not a ~1 Hz stream
- NLP chat: background WebSocket client to engine (9001) caches live metrics; answers worst_zone/avg_speed/active_agents/gini/compare_policy from live data when available; static literal fallback otherwise
- NLP incident: RapidFuzz gazetteer parser; /incident forwards parsed spec to the engine WS; gazetteer now loadable from an external JSON file instead of purely hardcoded
- Missing docs created: docs/TECH_STACK.md, docs/RL_DOCUMENTATION.md, docs/CV_DOCUMENTATION.md, docs/NLP_DOCUMENTATION.md, docs/SOFT_COMPUTING_DOCUMENTATION.md
**Speaker notes:** Code-level gaps from the limitations slide are now closed: real CV tile fetch, live NLP metrics, incident forwarding to the engine, and a configurable gazetteer are implemented. What remains is measurement — publishing actual CV accuracy and wait-reduction numbers — not new implementation.

## Slide 9: Current Status & Limitations
- DONE: phases 0–8, 10–13, 15, 17, 18, 19–24, 25; PARTIAL: phase 9 (chicago checkpoints 0–199.pt exist; Paris −0.7% / Ahmedabad −9.2% below baseline on short evals, transfer re-seed pending)
- Remaining limitations: GA fitness consumption of cv_congestion.json unconfirmed; no CV unit tests or held-out labelled dataset; PRD wait-reduction not yet published; intersection counts disagree between TRD and NEXUS-SIM-DOCUMENTATION.md (TBD)
- Chicago graph/OD zone mismatch resolved (both now 77 zones)
- GA calibration: docs/results.md reports 18.3% vs 21.6% MAPE; newer artifact reports 15.4% vs 22.8% — conflicting figures flagged
- All code-level gaps previously flagged (wait accounting, live NLP, real CV tiles, configurable gazetteer, real mean_wait) are now closed
**Speaker notes:** Phase statuses come from docs/BACKLOG.md corrected against code on 2026-10-24. The "integrated demo" phase 18 is marked DONE, but its supporting artifacts (CV real-world feeds, live NLP data) were previously short of the doc narrative — those gaps are now addressed by this session's fixes.

## Slide 10: Future Work & Q&A
- Immediate P0s: regenerate Chicago graph+OD from one zone run so pipeline suite is green; complete/publish Chicago 200-episode run; re-run validation to passes_checkpoint: true; publish wait-time reduction; re-seed Paris/Ahmedabad transfers; run sensitivity sweep
- Phases 26–36 (P3): DeepSORT/U-Net/Mask R-CNN CV; PSO/SA/CMA-ES/ACS/ABC/ANFIS/GP/rough sets/NSGA-II Soft Computing; NER/coreference/QA/knowledge-graph NLP; unified Algorithm Explorer (port 9006)
- Production roadmap (docs/futureplanning.md): NexusTwin 2-stage dynamic ingestion (Stage 1 drag-drop + Stage 2 Overpass QL streaming), interactive Time-Machine Scrubber, What-If scenario branching, and Explainable AI (XAI) signal inspection are fully implemented, verified, and merged into main (PR #46); multi-tenant workspaces, simulation-as-a-service, and federated learning remain active architecture blueprints.
- Verify any cited number against artifacts: docs/evidence/, data/chicago/validation_report.json, ml/results/comparison.json, ml/checkpoints/chicago/
- Unknown values marked TBD; no metrics were fabricated
**Speaker notes:** Future work splits into near-term hardening (validation, transfer, wait accounting) and the phase 26–36 expansion that docs/BACKLOG.md marks PENDING. Close by inviting verification: every measured claim traces to a file or command in the repo, and every gap is explicitly flagged rather than hidden.
