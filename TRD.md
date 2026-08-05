# NexusSim — Technical Requirements Document (TRD)

**Version:** 1.0  
**Status:** Active  
**Owner:** Vyom  
**Last Updated:** August 2026

> **Source of truth.** This TRD is written against the latest documentation and
> verified codebase state: `docs/NexusSim_Explained.md` (verified, code-cited),
> `PRD.md` v2.0, `TECH_STACK.md`, `IMPLEMENTATION_PLAN.md` (Phases 0–18),
> `docs/graph_schema.md`, `docs/od_matrix_schema.md`, `docs/e2e_checklist.md`, and
> the working tree of the `engine/`, `pipeline/`, `ml/`, and `dashboard/`
> directories. Functional/business requirement IDs (FR, NFR, BR) are shared with
> `docs/NexusSim_Explained.md §3`; `TR-*` in this document extends that set with
> module-level technical requirements and is traceable to implementation-plan tasks.

---

## 1. Purpose and Scope

NexusSim is a real-city traffic simulation used to stress-test urban policy changes
and to train/compare adaptive signal control. It is one integrated system spanning
four academic subjects — Reinforcement Learning, Computer Vision, NLP, and Soft
Computing (BR-1, BR-3).

This document specifies the **technical** requirements: the system's architecture,
module-by-module requirements, interface contracts, data schemas, non-functional
targets, and the verification each requirement maps to. It is the contract between
the product intent (`PRD.md`) and the implementation plan (`IMPLEMENTATION_PLAN.md`).

**Scope:** engine, pipeline, ML, dashboard, and the four-subject extensions
(Phases 12–18). **Out of scope:** real signal hardware control, live city monitoring,
end-user navigation.

---

## 2. Referenced Documents

| Ref | Document | Purpose |
|-----|----------|---------|
| [1] | `PRD.md` (v2.0) | Product goals, features, success metrics |
| [2] | `docs/NexusSim_Explained.md` | Code-verified architecture + FR/NFR/TR/BR requirements |
| [3] | `IMPLEMENTATION_PLAN.md` | Phase-gated build plan (tasks, branches, checkpoints) |
| [4] | `TECH_STACK.md` | Technology decisions and rationale |
| [5] | `docs/graph_schema.md` | `graph.json` schema |
| [6] | `docs/od_matrix_schema.md` | `od_matrix.json` schema |
| [7] | `docs/e2e_checklist.md` | End-to-end smoke checks |
| [8] | `README.md` | Setup, quick start, run flags |

---

## 3. System Architecture

```
pipeline/ (Python)                engine/ (C++17)                 dashboard/ (React+TS)
─────────────────                 ─────────────────               ─────────────────────
download.py → clean.py            Graph.h / GraphLoader.cpp       useWebSocket.ts
  → lanes.py → zones.py             loads graph.json                ws://localhost:9001
  → export.py → graph.json        Simulation.h                    Map.tsx (Leaflet)
download_od.py → od_matrix.py       .tick(dt) every 0.1s          MetricsPanel.tsx
  → od_matrix.json                 IDM.h car-following            EquityOverlay.tsx
od_proxy.py (density proxy)        Pathfinder.h A* + stochastic   PolicyComparisonPanel.tsx
validate.py                        Quadtree.h spatial index       CalibrationReportPanel.tsx
optimize_calibration.py (GA)       SignalPolicy.h (Phase 12)      CongestionCVOverlay.tsx
cv_congestion.py (Phase 14)        InferenceEngine.h (ONNX)       VirtualCameraPanel.tsx
                                   WebSocketServer.h (uWebSockets) ChatPanel.tsx
                                                                    IncidentReportPanel.tsx
ml/ (Python sidecars, Phases 15–17)
  cv/virtual_camera.py → service (port 9003)
  nlp/chat_service.py → REST /chat, /incident (port 9004)
```

**Key architectural rules**
- The engine is the only writer of simulation truth; everything else is a consumer of
  its WebSocket stream (FR-5, verified: `Simulation::tick()`, `broadcast_state()`).
- ML/CV/NLP run as **independent sidecar processes** (TR-6), never in the C++ hot path
  and never in the frontend bundle.
- New broadcast fields are **additive only** (NFR-5): `useWebSocket.ts` ignores unknown
  keys, so additions never break the dashboard.
- Per-city variation is **config, not code** (FR-6, TR-7): `pipeline/cities.yaml` is the
  single source of truth; the root `cities.yaml` is a pointer stub.
