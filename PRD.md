# NexusSim — Product Requirements Document

**Version:** 2.0  
**Status:** Active  
**Owner:** Vyom  
**Last Updated:** August 2026

> **Revision notice.** v2.0 supersedes v1.0 (July 2026). It incorporates the scope
> confirmed in the latest documentation — `docs/NexusSim_Explained.md`, `docs/PRD.md`,
> `IMPLEMENTATION_PLAN.md` (Phases 12–18) and `TECH_STACK.md` — which extends the
> product from "engine + pipeline + dashboard" into **one integrated system covering
> four academic subjects: Reinforcement Learning, Computer Vision, NLP, and Soft
> Computing** (BR-1–BR-6). Requirement IDs (FR / NFR / TR / BR) are shared with
> `docs/NexusSim_Explained.md §3` and are traced to implementation phases in
> `IMPLEMENTATION_PLAN.md`.

---

## 1. Problem Statement

Urban traffic management in real cities is governed by static, rule-based signal timings that were calibrated decades ago and rarely updated. City administrators have no safe, cost-free way to test what happens if they add a bus lane, reroute freight, or implement congestion pricing — they make these decisions blind, or after expensive pilot programs that disrupt real commuters.

Additionally, most optimization tools treat "average commute time" as the sole success metric. This systematically benefits already well-connected, high-income zones while underserved neighborhoods — where residents are more dependent on public transit — see no improvement or get worse.

NexusSim solves both problems: it gives planners a high-fidelity, real-city sandbox where policy changes can be stress-tested before any real-world commitment, and it makes equity a first-class metric alongside efficiency. It also exists as a single, demonstrably integrated system in which four AI subject areas — RL, Computer Vision, NLP, and Soft Computing — cooperate on the same live simulation rather than living as four isolated demos (BR-3).

---

## 2. Goals

| Goal | Description | Phase(s) |
|------|-------------|----------|
| G1 | Simulate 20,000+ heterogeneous agents in a real city graph at 60 fps | 0–4 |
| G2 | Train a decentralized MARL policy that outperforms fixed-cycle signal timing | 7–9, 12 |
| G3 | Make equity — not just speed — a measurable, optimized output | 5, 9 |
| G4 | Support 3–4 structurally distinct real cities without code changes | 1, 6, 9 |
| G5 | Produce a policy dashboard that a non-technical administrator can read | 5, 10 |
| G6 | Make signal control pluggable so Webster's, fuzzy, and RL policies hot-swap at runtime | 12 |
| G7 | Replace manual calibration with a genetic algorithm; add a fuzzy-logic controller | 13 |
| G8 | Classify real-world road congestion from traffic imagery (classical + CNN) | 14 |
| G9 | Run a live synthetic "virtual camera" that detects/counts traffic on the sim's own output | 15 |
| G10 | Answer natural-language queries about live simulation state | 16 |
| G11 | Accept free-text incident reports that mutate the running simulation | 17 |
| G12 | Prove all four subjects interoperate in one continuous demo | 18 |

---

## 3. Non-Goals

- NexusSim does **not** connect to or control real traffic signal hardware
- NexusSim does **not** provide real-time live city monitoring
- NexusSim does **not** require proprietary city data to function (all sources are open)
- NexusSim is **not** a navigation or routing app for end users
- NexusSim does **not** script-scrape Google Maps' interactive traffic layer (ToS-violating; substitutes are Mapbox Traffic Tiles / TomTom Traffic Flow API — BR-6, NFR-6)
- Computer Vision / NLP are **not** full research contributions — depth is "medium," a mix of breadth and depth, not stubs and not dissertations (BR-2)
- RL is **not** full cooperative message-passing MARL and **not** a single centralized controller — it is independent per-intersection agents with a shared network-wide reward (BR-5)

---

## 4. Users

### Primary User — Urban Policy Researcher / Student Developer
Builds the system, interprets results, writes academic or policy reports. Needs full technical access. Also the audience for the four academic subjects: reads reward functions, GA convergence reports, CV accuracy tables, and NLP intent accuracy.

### Secondary User — Civil Administrator / Policy Audience
Views the dashboard. Needs plain-language metrics, no jargon. Interacts with policy toggles (add bus lane, increase congestion zone, switch to EV fleet, swap signal policy), live metrics chat, and incident reports.

### Evaluator — Technical Interviewer
Reviews code architecture, model design decisions, and validation methodology across all four subjects. Needs clean interfaces, documented choices, ablation results, and one integrated demo (Phase 18).
