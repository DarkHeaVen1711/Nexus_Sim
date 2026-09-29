# NexusSim Documentation Index

Welcome to the comprehensive documentation suite for **NexusSim** — a high-performance urban traffic simulation and multi-agent AI research platform integrating C++ simulation, Multi-Agent Reinforcement Learning (MARL), Soft Computing, Computer Vision, and Natural Language Processing.

---

## 1. System Architecture & Requirements

- **[PRD — Product Requirements Document](PRD.md)**: Product vision, user goals, feature requirements, and success metrics.
- **[TRD — Technical Requirements Document](TRD.md)**: Technical specifications, interface contracts, performance bounds, and subsystem architecture.
- **[Team Implementation Plan](TEAM_IMPLEMENTATION_PLAN.md)**: Multi-phase engineering roadmap spanning foundation through 36-algorithm multi-subject tracks.
- **[Tech Stack Specification](TECH_STACK.md)**: Detailed breakdown of languages, frameworks, runtime libraries, and sidecar architecture.
- **[User Stories](USER_STORIES.md)**: Stakeholder user stories across city planners, traffic engineers, and academic researchers.
- **[End-to-End Smoke Checklist](e2e_checklist.md)**: Integration test checklist run across pipeline, engine, sidecars, and dashboard.

---

## 2. Four-Subject Academic & Algorithm Documentation

- **[Reinforcement Learning (RL) Documentation](RL_DOCUMENTATION.md)**: Decentralized MAPPO, observation/action formulations, reward engineering (pressure + Gini equity), and 12-algorithm RL inventory benchmarks.
- **[Soft Computing (SC) Documentation](SOFT_COMPUTING_DOCUMENTATION.md)**: GA automated calibration, Mamdani and Interval Type-2 fuzzy signal controllers, metaheuristics (PSO, SA, CMA-ES), swarm intelligence (ACO, ABC), ANFIS, GP, and NSGA-II Pareto optimization.
- **[Computer Vision (CV) Documentation](CV_DOCUMENTATION.md)**: Real-world congestion tile classification, synthetic virtual camera sidecar, DeepSORT tracking, U-Net road segmentation, Mask R-CNN, optical flow, and anomaly detection.
- **[Natural Language Processing (NLP) Documentation](NLP_DOCUMENTATION.md)**: Rule-based & LLM metrics chat service, RapidFuzz gazetteer incident parser, sentiment feed, NER extraction, coreference resolution, and RDF knowledge graph.

---

## 3. Results, Benchmarks & Operational Memory

- **[Master Results & Algorithm Matrix](results.md)**: Consolidated benchmarks, calibration ablations, multi-city MARL gains (+26.3% on Chicago), and the 48-algorithm portfolio matrix.
- **[AI-Mode Stress Test Report](AI_STRESS_REPORT.md)**: Phase 8.8 stress-test report evaluating ONNX inference latency (p95 = 0.0808 ms) and FPS under 20,000 active agents.
- **[Project Backlog & Technical Debt](BACKLOG.md)**: Phase completion statuses (Phases 0–36) and prioritized active backlogs.
- **[Cross-Session Memory Log](SESSION_MEMORY.md)**: Historical session log preserving context, checkpoints, architectural decisions, and run records across sessions.
- **[Academic Synopsis Generation Context](SYNOPSIS_CONTEXT.md)**: Single source of truth containing verified system facts for project reports, DFDs, ER diagrams, and project guides.

---

## 4. Data Schemas

- **[Graph Schema](graph_schema.md)**: JSON structure defining nodes, edges, lanes, and traffic signal controller definitions.
- **[OD Matrix Schema](od_matrix_schema.md)**: Origin-Destination matrix specification for real-world Socrata feeds and gravity-density proxy distributions.
