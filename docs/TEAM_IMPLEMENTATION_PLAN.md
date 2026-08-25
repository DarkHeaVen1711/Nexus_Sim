# NexusSim — Team-Oriented Implementation Plan

**Version:** 1.0  
**Date:** August 2026  
**Status:** Draft — Pending Approval  
**Maintainers:** Vyom & Vatsal (original), expanding to 4-person team  

---

## 1. Executive Summary

This document transforms the existing linear, single-developer implementation plan into a team-oriented plan that scales across 4 developers while **preserving phases 0–8 exactly as defined**. The foundation phases (0–8) remain sequential and shared — all developers contribute to the common substrate before parallelising. Post-phase-8 work is reorganised into **parallel subject tracks** with defined integration checkpoints, enabling 4 developers to work simultaneously without blocking each other.

**Key design decisions:**
- **Phases 0–8 are untouched.** Every task, branch, and checkpoint artifact stays as-is. Role assignments within phases are additive guidance, not restructuring.
- **Post-8 parallelism** is organised around the 4 academic subjects (CV, NLP, SC, RL) plus cross-cutting integration and dashboard work.
- **Rotating pair assignments** replace rigid ownership — developers pair on tasks within their current track and rotate across tracks at integration checkpoints.
- **Integration checkpoints** are inserted every 2–3 phases to prevent silo drift and ensure the system remains cohesive.
- **GitHub Projects + Issues** provides the project management layer; this plan defines the structure that maps to boards, milestones, and issue templates.

---

## 2. Assumptions and Constraints

### Assumptions

| # | Assumption | Rationale |
|---|------------|-----------|
| A1 | Team starts at 2 developers (Vyom & Vatsal); Dev C and Dev D join after Phase 8 checkpoint. Plan will be re-adjusted at that time. | BR-4 requires 3–4 person parallel execution |
| A2 | All developers are full-stack capable but may have subject-matter strengths | "Flexible / pair on everything" mode |
| A2a | No dedicated training machines; long RL/CV runs execute async on personal dev machines with checkpoint resume | Confirmed by team |
| A3 | Development environment: Windows (MinGW) dev machines; CI on GitHub Actions ubuntu-latest | Current setup confirmed |
| A4 | No hard academic deadline; quality and integration completeness take priority over schedule | Confirmed by team |
| A5 | Phases 0–8 form the shared foundation; no developer works on post-8 phases until Phase 8 checkpoint passes | Phase-gated dependency |
| A6 | Phases 25–36 represent the expanded 36-algorithm scope (sourced from the original MEGA project plan) and will be executed within the post-8 parallel tracks | This document is the authoritative source for all algorithm inventory and phase details |

### Constraints

| # | Constraint | Source | Impact |
|---|------------|--------|--------|
| C1 | Max 100 line insertions per commit; PRs for >100-line changes | TECH_STACK.md | All developers follow same git discipline |
| C2 | Engine is C++17; ML/pipeline is Python 3.11; Dashboard is React+TS | PRD §6 | Developers need C++, Python, and TypeScript proficiency |
| C3 | All external data sources must be ToS-compliant (BR-6) | PRD §3 | No Google Maps scraping; Mapbox/TomTom only |
| C4 | ML/CV/NLP services are independent sidecars (TR-6) | TRD §3 | Parallel development of sidecars is safe; engine stays isolated |
| C5 | New broadcast fields are additive-only (NFR-5) | TRD §4.4 | Dashboard never breaks from engine additions |
| C6 | Windows MinGW dev + Linux CI means cross-platform testing is needed | e2e_checklist | CI catches platform-specific issues late; local testing on Windows first |

---

## 3. Team Structure and Role Definitions

### 3.1 Team Composition (4 developers)

Rather than rigid "role titles," developers operate in **rotating pair configurations** with subject-matter focus areas that shift per phase track.

| Developer | Suggested Strength | Primary Track(s) | Secondary |
|-----------|-------------------|-------------------|-----------|
| Dev A (Vyom) | C++ Engine + Systems | Engine Foundation, RL C++ Integration | SC Engine Integration |
| Dev B (Vatsal) | Python ML + Data | ML Pipeline, RL Training, SC Optimizers | NLP Services |
| Dev C | Python CV + Vision | CV Subject Track | Virtual Camera, Dashboard CV Panels |
| Dev D | React + Full-Stack | Dashboard, Integration, NLP Services | Cross-cutting UI |

> **Note:** These are primary assignments, not rigid boundaries. All developers pair across tracks at integration checkpoints.

### 3.2 Working Mode: Rotating Pairs

```
Phase 0-8 (Foundation):   All 4 developers on shared foundation (sequential)
Phase 9-11 (Extension):   Pair 1 (Dev A+B) | Pair 2 (Dev C+D)
Phase 12-18 (Integration): Pair 1 (Dev A+B) | Pair 2 (Dev C+D) + Integration Lead (Dev D)
Phase 19-24 (RL Deep):    Pair 1 (Dev A+B) | Pair 2 (Dev C+D) on CV/SC/NLP
Phase 25-36 (36-Algo):    4 parallel subject tracks with integration checkpoints
```

### 3.3 Responsibility Matrix (RACI)

| Activity | Dev A | Dev B | Dev C | Dev D |
|----------|-------|-------|-------|-------|
| C++ Engine development | **R/A** | C | I | I |
| Python ML pipeline | C | **R/A** | C | I |
| CV algorithms (CV-1..12) | I | C | **R/A** | C |
| NLP services (NLP-1..12) | I | C | C | **R/A** |
| SC optimizers (SC-1..12) | C | **R/A** | I | C |
| RL training (RL-1..12) | C | **R/A** | I | I |
| Dashboard components | I | I | C | **R/A** |
| Integration testing | **R** | **R** | **R** | **R/A** |
| CI/CD maintenance | C | **R** | I | I |
| Documentation | C | C | C | **R/A** |
| Code review (PRs) | **R** | **R** | **R** | **R** |

*R = Responsible, A = Accountable, C = Consulted, I = Informed*

### 3.4 Integration Lead Rotation

One developer serves as **Integration Lead** per sprint/cycle. The Integration Lead:
- Owns the `main` branch health (all CI green)
- Coordinates merge order for parallel PRs
- Runs the e2e checklist at integration checkpoints
- Resolves cross-track merge conflicts

| Period | Integration Lead |
|--------|-----------------|
| Phases 0–8 | Dev A |
| Phases 9–12 | Dev D |
| Phases 13–18 | Dev D |
| Phases 19–24 | Dev A |
| Phases 25–36 | Rotates per integration checkpoint |

---

## 4. Phased Plan

### 4.1 Phases 0–8: Shared Foundation (PRESERVED)

**All tasks, branches, checkpoints, and sequencing from the original implementation plan are preserved exactly.** What follows is additive guidance for team coordination — not changes to the plan structure.

#### Phase 0 — Repository Skeleton & CI Foundation (3–4 days)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | C++ CMake + GoogleTest setup | 0.1, 0.3 |
| Dev B | Python env + pytest setup | 0.4 |
| Dev C | Directory skeleton + docs | 0.2, 0.8 |
| Dev D | React + Vite scaffold + pre-commit | 0.5, 0.6, 0.7 |

**Additional Phase 0 tasks (governance):**

| # | Task | Branch | Notes |
|---|------|--------|-------|
| 0.9 | Create `docs/adr/` directory with ADR template (`template.md`) | `docs/adr-init` | All future architecture decisions recorded here |
| 0.10 | Create `CONTRIBUTING.md` with team guidelines: onboarding, code review, branch strategy, subject-track rules | `docs/contributing` | Read by all developers before first commit |

**Coordination:** Dev A owns merge to main after all branches pass CI. All developers verify `make test` on clean clone before proceeding.

#### Phase 1 — Graph Loading & Basic City Geometry (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | C++ Graph class + unit tests | 1.6, 1.7 |
| Dev B | Pipeline: download, clean, export | 1.1, 1.2, 1.5 |
| Dev C | Pipeline: lanes, zones | 1.3, 1.4 |
| Dev D | Config: cities.yaml integration | 1.8 |

**Coordination:** Dev B and Dev C work on pipeline in parallel on separate branches. Dev A waits for `graph.json` sample output before starting graph loader. Dev D wires config after pipeline stages are stable.

#### Phase 2 — Agent System & Pathfinding (1.5 weeks)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | Agent struct, A*, IDM, thread pool | 2.1, 2.2, 2.3, 2.8 |
| Dev B | Agent types, spawner, lifecycle | 2.4, 2.5, 2.7 |
| Dev C | Chaos coefficient + config | 2.6 |
| Dev D | Dashboard WS client prep | — (setup `useWebSocket.ts` skeleton) |

**Coordination:** Dev A owns the core agent loop. Dev B adds types and spawner on top. Dev C handles config. Dev D begins dashboard WebSocket foundation (no engine dependency yet).

#### Phase 3 — Quadtree Spatial Index & Collision Avoidance (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | Quadtree core + integration + benchmark | 3.1, 3.2, 3.5 |
| Dev B | Proximity deceleration + lane change | 3.3, 3.4 |
| Dev C | Stress test + memory leak check | 3.6 |
| Dev D | FPS logger + cache alignment | 3.7, 3.8 |

#### Phase 4 — WebSocket Stream & Dashboard Map (1.5 weeks)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | FlatBuffers schema + uWebSockets integration | 4.1, 4.2 |
| Dev B | LOD culling | 4.3 |
| Dev C | React: WS client + map base layer | 4.4, 4.5 |
| Dev D | React: agent markers + reconnect + e2e smoke | 4.6, 4.7, 4.8 |

**Coordination:** Dev A+Dev B work on engine streaming. Dev C+Dev D work on dashboard. Integration point: first live agent rendering.

#### Phase 5 — Fixed-Cycle Signal Baseline (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | Signal controller + agent interaction | 5.1, 5.3 |
| Dev B | Webster's timing + metrics collector | 5.2, 5.4 |
| Dev C | FlatBuffers metrics schema | 5.5 |
| Dev D | Dashboard efficiency + equity views | 5.6, 5.7, 5.8 |

#### Phase 6 — Real Traffic Demand (OD Matrix) (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | Agent spawner OD integration | 6.3 |
| Dev B | Uber Movement pipeline + validation | 6.1, 6.2, 6.5 |
| Dev C | Paris + Ahmedabad pipelines + density proxy | 6.6, 6.7, 6.9 |
| Dev D | cities.yaml config + refactoring | 6.4, 6.8 |

#### Phase 7 — MARL Training Environment (1.5 weeks)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | Gym env wrapper (read-only engine interface) | 7.3, 7.4 |
| Dev B | Observation space, reward function, MAPPO trainer | 7.1, 7.2, 7.5 |
| Dev C | MLflow logging + checkpoints | 7.6, 7.7 |
| Dev D | Training stability verification | 7.8 |

#### Phase 8 — ONNX Export & C++ Inference (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | ONNX Runtime C++ integration + ring buffer | 8.2, 8.3, 8.4 |
| Dev B | ONNX export script + validation | 8.1 |
| Dev C | AI signal controller integration | 8.5 |
| Dev D | Dashboard mode label + stress test | 8.7, 8.8 |

**Phase 8 Checkpoint:** All 4 developers verify `bench_inference.cpp` p95 ≤ 8 ms. Integration Lead (Dev A) runs full e2e checklist. **This is the gate for parallelisation.**

---

### 4.2 Phases 9–11: Extension Layer (Post-8, Preserved Phases)

After Phase 8 checkpoint passes, the team splits into two parallel pairs for the next preserved phases.

#### Phase 9 — Multi-City Training & Validation (1.5 weeks)

| Pair | Focus | Tasks |
|------|-------|-------|
| **Pair 1 (Dev A + Dev B)** | Chicago training + validation | 9.1, 9.2, 9.7, 9.8 |
| **Pair 2 (Dev C + Dev D)** | Paris + Ahmedabad transfer | 9.3, 9.4, 9.5, 9.6 |

**Integration checkpoint:** Both pairs merge comparison table (9.7). Integration Lead (Dev D) verifies side-by-side table renders in dashboard.

#### Phase 10 — Policy Toggles & Dashboard Polish (1 week)

| Pair | Focus | Tasks |
|------|-------|-------|
| **Pair 1 (Dev A + Dev B)** | Engine: runtime policy toggles + EV toggle | 10.1, 10.2 |
| **Pair 2 (Dev C + Dev D)** | Dashboard: toggle panel, comparison, tradeoff, city selector, PDF, accessibility | 10.3, 10.4, 10.5, 10.6, 10.7, 10.8 |

#### Phase 11 — Hardening, Docs & Demo (1 week)

| Pair | Focus | Tasks |
|------|-------|-------|
| **Pair 1 (Dev A + Dev B)** | `make demo` target, dependency pinning, CI audit | 11.2, 11.3, 11.7 |
| **Pair 2 (Dev C + Dev D)** | README, benchmark results, validation results, ablation, demo video | 11.1, 11.4, 11.5, 11.6, 11.8 |

**Phase 11 Checkpoint:** `make demo` works from clean clone. Integration Lead (Dev D) records demo video.

---

### 4.3 Phases 12–18: Cross-Subject Integration (Post-8, Preserved Phases)

These phases introduce the 4-subject architecture. Work splits into two parallel pairs with subject-matter focus.

#### Phase 12 — Signal Policy Abstraction (3–4 days)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | SignalPolicy interface + WebsterPolicy extraction | 12.1, 12.2, 12.3 |
| Dev B | Signal state in broadcast + policy_switch message | 12.4, 12.5 |
| Dev C | — (prepares CV package structure in parallel) | — |
| Dev D | PolicyComparisonPanel.tsx | 12.6 |

**Critical path:** Dev A must finish 12.1–12.3 before Dev B can test 12.5. Dev D can start UI skeleton immediately against the planned message schema.

#### Phase 13 — Soft Computing: GA Calibration & Fuzzy Controller (1.5 weeks)

| Pair | Focus | Tasks |
|------|-------|-------|
| **Pair 1 (Dev A + Dev B)** | GA calibration + fuzzy C++ controller | 13.1, 13.2, 13.3, 13.4, 13.5, 13.6 |
| **Pair 2 (Dev C + Dev D)** | Dashboard: calibration report + ablation docs | 13.7, 13.8 |

#### Phase 14 — CV: Real-World Congestion Classification (1 week)

| Pair | Focus | Tasks |
|------|-------|-------|
| **Pair 1 (Dev A + Dev B)** | CV congestion pipeline (tile fetch + classical + CNN) | 14.1, 14.2, 14.3, 14.4, 14.5, 14.6 |
| **Pair 2 (Dev C + Dev D)** | Dashboard: CongestionCVOverlay | 14.7 |

#### Phase 15 — CV: Synthetic Virtual Camera (1 week)

| Pair | Focus | Tasks |
|------|-------|-------|
| **Pair 1 (Dev A + Dev B)** | Virtual camera renderer + detection + service | 15.1, 15.2, 15.3 |
| **Pair 2 (Dev C + Dev D)** | Dashboard: VirtualCameraPanel + accuracy check | 15.4, 15.5 |

#### Phase 16 — NLP: Live Metrics Chat Interface (1 week)

| Pair | Focus | Tasks |
|------|-------|-------|
| **Pair 1 (Dev A + Dev B)** | Chat service + intent classifier + LLM layer | 16.1, 16.2, 16.3, 16.4 |
| **Pair 2 (Dev C + Dev D)** | Dashboard: ChatPanel + accuracy report | 16.5, 16.6 |

#### Phase 17 — NLP: Incident Reports → Simulation Mutation (1 week)

| Pair | Focus | Tasks |
|------|-------|-------|
| **Pair 1 (Dev A + Dev B)** | Incident parser + engine integration | 17.1, 17.2, 17.3, 17.4 |
| **Pair 2 (Dev C + Dev D)** | Dashboard: IncidentReportPanel + tests | 17.5, 17.6 |

#### Phase 18 — Cross-Subsystem Hardening & Integrated Demo (1 week)

**All 4 developers on integration.**

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | Extended `make demo` + cross-subject event wiring | 18.1 |
| Dev B | Comparison writeup + 4-subject results | 18.2 |
| Dev C | E2E smoke checklist v2 | 18.3 |
| Dev D | Integrated demo video recording | 18.4 |

**Phase 18 Checkpoint (CRITICAL GATE):** Single continuous recording showing all 4 subjects interacting. All developers verify. This gates entry to the deep RL and 36-algorithm expansion.

---

### 4.4 Phases 19–24: RL Deep Dive (Post-8, Preserved Phases)

With the 4-subject integration proven, the team splits for the RL algorithm inventory.

#### Phase 19 — Shared RL Algorithm Framework (3–4 days)

| Pair | Focus | Tasks |
|------|-------|-------|
| **Pair 1 (Dev A + Dev B)** | BaseTrainer interface + configs + single-agent wrapper + eval + benchmark | 19.1, 19.2, 19.3, 19.4, 19.5 |
| **Pair 2 (Dev C + Dev D)** | Begin CV/SC expansion prep (MEGA phases 25–27, 28–30 scoping) | — |

#### Phase 20 — Value-Based RL (1 week)

| Pair | Focus | Tasks |
|------|-------|-------|
| **Pair 1 (Dev A + Dev B)** | Q-Learning, SARSA, DQN, DDQN, Dueling DQN + tests | 20.1–20.6 |
| **Pair 2 (Dev C + Dev D)** | CV foundation track begins (MEGA Phase 25 tasks) | — |

#### Phase 21 — Policy-Based RL (4–5 days)

| Pair | Focus | Tasks |
|------|-------|-------|
| **Pair 1 (Dev A + Dev B)** | REINFORCE, A2C, PPO single-agent | 21.1–21.3 |
| **Pair 2 (Dev C + Dev D)** | CV advanced track (MEGA Phase 26 tasks) | — |

#### Phase 22 — Continuous Showcase (1–2 days)

| Pair | Focus | Tasks |
|------|-------|-------|
| **Pair 1 (Dev A + Dev B)** | SAC, TD3, DDPG via SB3 | 22.1–22.5 |
| **Pair 2 (Dev C + Dev D)** | CV motion + anomaly (MEGA Phase 27 tasks) | — |

#### Phase 23 — C++ Deployment of Headline RL Algorithms (1 week)

| Pair | Focus | Tasks |
|------|-------|-------|
| **Pair 1 (Dev A + Dev B)** | ONNX export generalization + C++ inference dispatch + RLPolicy | 23.1–23.4 |
| **Pair 2 (Dev C + Dev D)** | SC metaheuristics track begins (MEGA Phase 28 tasks) | — |

#### Phase 24 — RL Results, Ablation & Documentation (2 days)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | C++ inference benchmark across all 3 models | — (part of 23.4) |
| Dev B | 12-algorithm comparison table + ablation docs | 24.1, 24.2 |
| Dev C | Update CV documentation | — (MEGA Phase 36.3) |
| Dev D | Update all plan docs + results.md | 24.3 |

**Phase 24 Checkpoint:** 12-algorithm table in `docs/results.md`. All developers review.

---

### 4.5 Phases 25–36: 36-Algorithm Expansion (Post-8)

**This is where maximum parallelism occurs.** After the RL deep dive is complete (Phase 24), all 4 developers can work across 3 parallel subject tracks with integration checkpoints.

#### Track Configuration

```
┌─────────────────────────────────────────────────────────────┐
│                    4 PARALLEL TRACKS                         │
│                                                              │
│  Track 1: Computer Vision (CV-1..CV-12)    [Dev C + Dev D]  │
│  Track 2: Soft Computing (SC-1..SC-12)     [Dev A + Dev B]  │
│  Track 3: NLP (NLP-1..NLP-12)              [Dev B + Dev D]  │
│  Track 4: Integration & Dashboard          [Dev A + Dev C]  │
│                                                              │
│  → Developers rotate between tracks at integration points   │
└─────────────────────────────────────────────────────────────┘
```

> **Note:** Track 4 (Integration) is not a separate work stream — it is the responsibility of whoever is Integration Lead at each checkpoint. All developers contribute to integration testing at checkpoints.

#### Phase 25 — CV Foundation: Virtual Camera + Detection (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev C | CV package init + virtual camera + YOLO detection | 25.1, 25.2, 25.3 |
| Dev D | MOG2 background subtraction + dashboard panels | 25.4, 25.6 |
| Dev A | Wire CV-3 vehicle count into RL reward | 25.5 |
| Dev B | — (prepares SC fitness module in parallel) | — |

#### Phase 26 — CV Advanced: Tracking + Segmentation (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev C | DeepSORT tracking + U-Net segmentation | 26.1, 26.2 |
| Dev D | Mask R-CNN + dashboard panels | 26.3, 26.5 |
| Dev A | Wire CV-7 road condition into SC fuzzy inputs | 26.4 |
| Dev B | — (SC fitness module complete) | — |

#### Phase 27 — CV Motion + Anomaly + Lanes (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev C | Optical flow + anomaly detection + lane detection | 27.1, 27.2, 27.3 |
| Dev D | Crowd density + dashboard optical flow panel | 27.4, 27.6 |
| Dev A | Wire CV-11 anomaly alerts into NLP-9 event extraction | 27.5 |
| Dev B | — (SC track begins) | — |

**CV Track Complete (Phases 25–27):** All 12 CV algorithms implemented. Integration checkpoint: run all CV algorithms on toy graph, collect results.

#### Phase 28 — SC Metaheuristics: GA + PSO + SA + ES (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | GA calibration + fitness module | 28.1, 28.5 |
| Dev B | PSO + SA + ES optimizers | 28.2, 28.3, 28.4 |
| Dev C | — (supporting dashboard prep) | — |
| Dev D | ConvergencePanel.tsx with all optimizer curves | 28.6 |

#### Phase 29 — SC Swarm + Hybrid: ACS + ABC + ANFIS (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | ACS routing + engine integration | 29.1, 29.5 |
| Dev B | ABC + ANFIS + Type-2 fuzzy | 29.2, 29.3, 29.4 |
| Dev C | — (NLP track prep) | — |
| Dev D | FuzzyRulesPanel.tsx | 29.6 |

#### Phase 30 — SC GP + Rough Sets + NSGA-II (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | GP rule evolution + NSGA-II | 30.1, 30.3 |
| Dev B | Rough Sets + engine integration | 30.2, 30.4, 30.5 |
| Dev C | — (NLP track begins) | — |
| Dev D | ParetoFrontPanel.tsx + CalibrationReportPanel update | 30.6 |

**SC Track Complete (Phases 28–30):** All 12 SC algorithms implemented. Integration checkpoint: run all SC algorithms, compare convergence.

#### Phase 31 — NLP Core: Chat + Incidents + Sentiment (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev B | NLP-1 intent classifier + NLP-2 incident parser + NLP-3 sentiment + NLP-5 classifier | 31.1, 31.2, 31.3, 31.4 |
| Dev D | NLP-3 → SC-12 integration + dashboard panels | 31.5, 31.6 |
| Dev A | — (supporting integration) | — |
| Dev C | — (NLP advanced prep) | — |

#### Phase 32 — NLP Extraction: NER + Events + Coref (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev B | NER + event extraction + coreference resolution | 32.1, 32.2, 32.3 |
| Dev D | CV-11 → NLP-9 integration + NERPanel.tsx | 32.4, 32.5 |
| Dev A | — (integration support) | — |
| Dev C | — (NLP advanced continued) | — |

#### Phase 33 — NLP Advanced: Summarization + QA + KG (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev B | Extractive + abstractive summarization + QA + stance + KG | 33.1, 33.2, 33.3, 33.4, 33.5 |
| Dev D | KnowledgeGraphPanel.tsx | 33.6 |
| Dev A | — (integration prep) | — |
| Dev C | — (integration prep) | — |

**NLP Track Complete (Phases 31–33):** All 12 NLP algorithms implemented. Integration checkpoint: run all NLP algorithms, verify cross-subject data flows.

#### Phase 34 — Cross-Subject Integration (1 week)

**All 4 developers on integration.**

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | Cross-subject event bus + CV→NLP→Engine chain | 34.1, 34.2 |
| Dev B | NLP→RL adaptation + SC→RL warm start | 34.3, 34.6 |
| Dev C | SC→RL observation reduction + CV→SC fitness | 34.4, 34.5 |
| Dev D | E2E integration test (36 algorithms) | 34.7 |

#### Phase 35 — Unified Dashboard Algo Explorer (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev D | AlgoExplorer container + subject tabs + AlgorithmCard + ComparisonView | 35.1, 35.6, 35.7 |
| Dev C | CVPanel.tsx + SCPanel.tsx | 35.2, 35.3 |
| Dev B | NLPPanel.tsx + RLPanel.tsx | 35.4, 35.5 |
| Dev A | Algo Explorer API sidecar (port 9006) | 35.8 |

#### Phase 36 — Results, Benchmarks & Documentation (1 week)

| Developer | Focus | Tasks |
|-----------|-------|-------|
| Dev A | Run all 36 algorithms on toy graph | 36.1 |
| Dev B | Cross-subject comparison tables | 36.2 |
| Dev C | Update CV + SC documentation | 36.3, 36.4 |
| Dev D | Update NLP docs + integration doc + demo video | 36.5, 36.6, 36.7 |

**Final Checkpoint:** 36-algorithm integrated demo video. All documentation updated. `make demo` works from clean clone.

---

## 5. Collaboration and Tooling Framework

### 5.1 Communication Practices

| Practice | Frequency | Tool | Owner |
|----------|-----------|------|-------|
| **Daily async standup** | Daily | GitHub Discussions or Slack thread | All devs post by 10am |
| **Weekly sync call** | Weekly (30 min) | Video call | Integration Lead facilitates |
| **Integration checkpoint review** | Per checkpoint | PR review + demo | Integration Lead + all reviewers |
| **Blocker escalation** | As needed | Direct message | Any dev → Integration Lead |
| **Architecture decisions** | As needed | GitHub Issue (ADR template) | Proposer + 2 reviewers required |

### 5.2 Git Workflow

```
main (protected, CI must pass)
├── feature/<name>          # New capability
├── fix/<name>              # Bug fix
├── refactor/<name>         # Internal restructure
├── data/<name>             # Pipeline or data work
├── experiment/<name>       # ML training runs
└── integration/<checkpoint-name>  # Integration checkpoint branches
```

**Branch rules (preserved from original plan):**
- Max 100 line insertions per commit
- PRs required for >100-line changes
- All CI checks must pass before merge
- No force-push to main
- Commit format: `<type>(<scope>): <short summary>`

**Additional team rules:**
- PRs must have at least 1 approval before merge
- Integration checkpoint branches require 2 approvals
- Assign `reviewer` field on PR to the other pair member
- Use `milestone` field on GitHub Issues to track phase progress
- Label PRs with subject area: `cv`, `sc`, `nlp`, `rl`, `engine`, `dashboard`, `integration`

### 5.3 GitHub Projects Board Structure

**Board: NexusSim Team Plan**

| Column | Purpose |
|--------|---------|
| Backlog | Not yet started |
| Sprint (Current) | Active work for current phase track |
| In Review | PR open, awaiting review |
| Integration Checkpoint | Waiting for checkpoint verification |
| Done | Merged + checkpoint verified |

**Milestones (one per phase track):**

| Milestone | Phases | Target |
|-----------|--------|--------|
| Foundation | 0–8 | Phase 8 checkpoint |
| Extension | 9–11 | Phase 11 checkpoint |
| Cross-Subject Integration | 12–18 | Phase 18 checkpoint (critical gate) |
| RL Deep Dive | 19–24 | Phase 24 checkpoint |
| CV Expansion | 25–27 | All 12 CV algorithms |
| SC Expansion | 28–30 | All 12 SC algorithms |
| NLP Expansion | 31–33 | All 12 NLP algorithms |
| Final Integration | 34–36 | 36-algorithm demo |

### 5.4 Code Review Protocol

| Change Type | Reviewer(s) | SLA |
|-------------|-------------|-----|
| Engine (C++) | Any 1 other dev | 24 hours |
| ML/Pipeline (Python) | Any 1 other dev | 24 hours |
| Dashboard (React) | Any 1 other dev | 24 hours |
| Integration changes | 2 other devs | 48 hours |
| Config/doc changes | 1 other dev | 12 hours |

### 5.5 Integration Checkpoint Protocol

At each integration checkpoint (marked in the phase plan):

1. **Freeze:** Integration Lead creates an `integration/<checkpoint>` branch from `main`
2. **Merge:** All completed feature branches for the current phase track are merged into the integration branch
3. **Test:** All developers run `make test` locally; CI must pass on the integration branch
4. **E2E:** Integration Lead runs the full e2e checklist (extended per phase)
5. **Demo:** Integration Lead records a short demo or screenshots showing the checkpoint artifact
6. **Sign-off:** All 4 developers approve the integration branch → merge to `main`
7. **Retrospective:** 15-minute discussion: what worked, what blocked, what to adjust

### 5.6 CI/CD Pipeline

```
Push to any branch
  ├── C++ Build (CMake + Ninja, ubuntu-latest)
  │   ├── clang-format check
  │   ├── clang-tidy check
  │   ├── GoogleTest run
  │   └── Stress test (20k agents)
  ├── Python Pipeline
  │   ├── black + isort format check
  │   ├── pytest (pipeline/tests/)
  │   └── pytest (ml/tests/)
  ├── Dashboard
  │   ├── eslint check
  │   ├── TypeScript type check
  │   └── Vitest run
  └── Integration (on main only)
      └── Full e2e smoke test (headless engine + pipeline + dashboard)
```

**CI triggers:**
- Every push to any branch: full C++ + Python + Dashboard tests
- Pull requests: all checks + code review
- Merge to main: full e2e smoke test added
- Nightly (optional): stress tests + training run on toy graph

**Training runs (no dedicated machines):**
- Long RL/CV training runs (5000+ episodes, CNN fine-tuning) execute **async overnight** on personal dev machines
- MLflow tracks all runs with full hyperparameters and metrics; checkpoint resume is mandatory (Phases 7.7, 19.2)
- Developer commits result JSON and MLflow run ID — not the trained model weights — to the repo
- Large model files (`.pt`, `.onnx`) go to a shared location or `.gitignore`'d local path, documented in `README.md`

---

## 6. Milestones, Metrics, and Risk Controls

### 6.1 Milestones

| # | Milestone | Phase Gate | Artifact | Verification |
|---|-----------|-----------|----------|--------------|
| M1 | Foundation Complete | Phase 8 | `bench_inference.cpp` p95 ≤ 8 ms | All 4 devs verify |
| M2 | Extension Complete | Phase 11 | `make demo` clean clone < 30 min | Integration Lead records demo |
| M3 | Cross-Subject Integration | Phase 18 | Single continuous 4-subject recording | All 4 devs sign off |
| M4 | RL Inventory Complete | Phase 24 | 12-algorithm table in `docs/results.md` | All 4 devs review |
| M5 | CV Expansion Complete | Phase 27 | All 12 CV algorithms with results | Integration checkpoint |
| M6 | SC Expansion Complete | Phase 30 | All 12 SC algorithms with results | Integration checkpoint |
| M7 | NLP Expansion Complete | Phase 33 | All 12 NLP algorithms with results | Integration checkpoint |
| M8 | 36-Algorithm Integration | Phase 36 | Integrated demo video + full docs | Final sign-off |

### 6.2 Team Velocity Metrics

| Metric | How Measured | Target |
|--------|-------------|--------|
| **PR merge rate** | PRs merged per week | 8–12 per week (2–3 per dev) |
| **PR review turnaround** | Time from PR open to merge | < 48 hours average |
| **CI pass rate** | % of CI runs passing on first push | > 85% |
| **Integration checkpoint on-time** | Checkpoint completed within planned window | > 80% |
| **Blocker resolution time** | Time from blocker reported to unblocked | < 24 hours |
| **Cross-track PR reviews** | % of PRs reviewed by someone outside primary track | > 50% |

### 6.3 Technical Quality Metrics

| Metric | Target | Measured At |
|--------|--------|-------------|
| Test coverage (C++) | > 80% line coverage | CI (lcov) |
| Test coverage (Python) | > 85% line coverage | CI (pytest-cov) |
| Dashboard test coverage | > 75% component coverage | CI (Vitest) |
| `make test` total time | < 3 minutes | CI pipeline |
| E2e checklist pass rate | 100% at every checkpoint | Integration Lead |
| No TODO in production code | `grep -r "TODO" engine/src ml/env` returns empty | Phase 11.7, 36 |

### 6.4 Risk Register

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|------|-----------|--------|------------|-------|
| R1 | Parallel tracks produce incompatible interfaces | Medium | High | Integration checkpoints every 2–3 phases; interface contracts in TRD §5 | Integration Lead |
| R2 | C++ engine changes break ML sidecars | Low | High | Sidecar pattern (TR-6); engine is additive-only (NFR-5); integration tests at each checkpoint | Dev A |
| R3 | Developer idle time waiting on blocked dependencies | Medium | Medium | Pair rotation ensures someone is always unblocked; SC and CV tracks are independent after Phase 18 | All devs |
| R4 | Merge conflicts in shared files (e.g., `cities.yaml`, FlatBuffers schema) | Medium | Medium | Assign file ownership; schema changes require integration branch; additive-only rule | Integration Lead |
| R5 | Training runs (RL/CV CNN) consume too much developer wait time | Medium | Low | Async training on dedicated machines; MLflow monitoring; checkpoints allow resume | Dev B |
| R6 | Windows/CI platform divergence causes integration failures | Low | Medium | CI runs on Linux; developers test locally on Windows; cross-platform e2e at checkpoints | Dev A |
| R7 | Scope creep in 36-algorithm expansion | High | High | Phase-gated development; each phase has one checkpoint artifact; "medium depth" rule (BR-2) enforced at reviews | All devs |
| R8 | Onboarding new developers (Dev C, Dev D) slows velocity | Medium | Medium | Foundation phases (0–8) serve as onboarding; all code behind documented interfaces; pair programming mode | Dev A + Dev B |

### 6.5 Risk Response Protocols

| Trigger | Response |
|---------|----------|
| CI broken on `main` for > 2 hours | Integration Lead drops all other work; all PRs frozen until green |
| Integration checkpoint missed by > 2 days | Retrospective triggered; scope cut before extending timeline (per checkpoint rule: every phase ends with one demoable artifact) |
| Developer blocked for > 1 day | Escalate to Integration Lead; pair reassignment within 4 hours |
| Cross-track interface conflict | Architecture Decision Record (ADR) required; all 4 devs discuss; decision recorded in `docs/adr/` |
| Training run diverges / doesn't converge | Reduce scope to toy graph; document failure; proceed with alternative approach per BR-2 |

---

## 7. Appendices

### Appendix A: Phase Map (Visual)

```
Phase 0-8:   [========== ALL 4 DEVELOPERS (Sequential) ==========]
                                                          ↓ CHECKPOINT M1
Phase 9-11:  [== Pair 1 ==] [== Pair 2 ==]  (Parallel Pairs)
                                           ↓ CHECKPOINT M2
Phase 12-18: [== Pair 1 ==] [== Pair 2 ==]  (Parallel Pairs)
                                                ↓ CHECKPOINT M3 (CRITICAL)
Phase 19-24: [== Pair 1 (RL) ==] [== Pair 2 (CV/SC prep) ==]
                                                    ↓ CHECKPOINT M4
Phase 25-27: [Dev C+D (CV)]  [Dev A+B (SC start)]   ← PARALLEL TRACKS
Phase 28-30: [Dev A+B (SC)]  [Dev C+D (NLP start)]   ← PARALLEL TRACKS
Phase 31-33: [Dev B+D (NLP)] [Dev A+C (Integration)]  ← PARALLEL TRACKS
Phase 34-36: [========= ALL 4 DEVELOPERS (Integration) =========]
                                                          ↓ CHECKPOINT M8
```

### Appendix B: Integration Checkpoint Schedule

| Checkpoint | After Phase | Key Artifact | Lead |
|------------|-------------|--------------|------|
| IC-1 | 8 | Inference benchmark p95 ≤ 8 ms | Dev A |
| IC-2 | 11 | `make demo` clean clone | Dev D |
| IC-3 | 18 | 4-subject integrated recording | Dev D |
| IC-4 | 24 | 12-algorithm RL table | Dev A |
| IC-5 | 27 | 12 CV algorithms complete | Dev C |
| IC-6 | 30 | 12 SC algorithms complete | Dev A |
| IC-7 | 33 | 12 NLP algorithms complete | Dev D |
| IC-8 | 36 | 36-algorithm integrated demo | All |

### Appendix C: File Ownership (to reduce merge conflicts)

| File/Area | Primary Owner | Secondary |
|-----------|--------------|-----------|
| `engine/src/` | Dev A | Dev B |
| `pipeline/src/` | Dev B | Dev C |
| `ml/cv/` | Dev C | Dev B |
| `ml/nlp/` | Dev D | Dev B |
| `ml/sc/` | Dev B | Dev A |
| `ml/algo/` | Dev B | Dev A |
| `ml/env/` | Dev A | Dev B |
| `dashboard/src/` | Dev D | Dev C |
| `docs/` | Dev D | All |
| `pipeline/cities.yaml` | Dev B | Dev A |
| FlatBuffers schemas | Dev A | Dev B |
| CI workflows | Dev A | Dev B |
| `Makefile` (root) | Dev A | Dev D |

### Appendix D: CONTRIBUTING.md Outline

The `CONTRIBUTING.md` file (created at Phase 0, task 0.10) should contain:

```
1. Welcome & Project Overview
2. Development Environment Setup
   - C++ (CMake + MinGW on Windows)
   - Python 3.11 + virtual env
   - Node 18+ + npm
   - Pre-commit hooks installation
3. Git Workflow
   - Branch naming conventions (from project git discipline rules)
   - Commit message format
   - PR requirements (100-line rule, review, CI)
4. Code Style
   - C++: clang-format + clang-tidy
   - Python: black + isort
   - TypeScript: eslint + prettier
5. Testing Before Commit
   - `make test` (all subsystems)
   - Running individual test suites
6. Architecture Overview
   - 4 subsystems and their boundaries
   - Sidecar pattern (TR-6)
   - Additive-only broadcast rule (NFR-5)
7. Subject Track Guidelines
   - How to work within CV/NLP/SC/RL tracks
   - Integration checkpoint protocol
   - File ownership and conflict avoidance
8. Onboarding Checklist (link to Appendix E)
9. ADR Process
   - When to write an ADR
   - Template location (docs/adr/template.md)
```

### Appendix E: Onboarding Checklist (for Dev C and Dev D)

- [ ] Read `docs/PRD.md`, `docs/TECH_STACK.md`, `docs/TRD.md`
- [ ] Read `docs/TEAM_IMPLEMENTATION_PLAN.md` (Phases 0–8 for foundation context)
- [ ] Read `docs/TEAM_IMPLEMENTATION_PLAN.md` (Sections relevant to assigned track)
- [ ] Set up dev environment: C++ (CMake + MinGW), Python 3.11, Node 18+
- [ ] Clone repo, run `make test` on clean clone
- [ ] Run `make demo` and verify dashboard loads
- [ ] Complete one small task from current phase (assigned by pair partner)
- [ ] Submit first PR and go through code review
- [ ] Pair with Dev A or Dev B for one full day on engine/ML work

---

## 8. Decisions (Resolved)

| # | Question | Decision | Impact |
|---|----------|----------|--------|
| Q1 | Will Dev C and Dev D join at Phase 0 or later? | **Later.** Dev C and Dev D join after Phase 8 checkpoint. Plan will be adjusted at that time. | Phases 0–8 run with 2 devs; scaling plan activates post-Phase 8 |
| Q2 | Are there dedicated machines for long training runs, or do devs train on personal machines? | **No dedicated machines.** Training runs on personal dev machines. | Long RL/CV training runs scheduled async overnight; MLflow tracks all runs; checkpoint resume critical |
| Q3 | Should we create a `docs/adr/` directory for Architecture Decision Records? | **Yes.** Created at Phase 0. | All architecture decisions documented in ADR format before implementation |
| Q4 | Do you want a `CONTRIBUTING.md` with team-specific guidelines beyond git discipline? | **Yes.** Created at Phase 0. | Includes onboarding steps, code review protocol, branch strategy, and subject-track guidelines |
| Q5 | Any preference on sprint length for the weekly sync cadence? | **1-week sprints** aligned to phase cadence. | Weekly sync call; sprint boundaries align with phase completion | |

---

*This document is ready for review. Once approved, it becomes the operational plan for team execution and the single authoritative source for all phase details, task assignments, and integration checkpoints.*
