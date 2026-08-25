# Soft Computing — NexusSim Documentation

---

## Subject Overview

The Soft Computing subsystem provides two gradient-free optimization techniques for NexusSim: a genetic algorithm (GA) that replaces manual parameter calibration with an automated evolutionary search, and a fuzzy-logic signal controller that provides a third non-learned signal strategy alongside Webster's formula and RL. Together, these demonstrate optimization without gradients (GA) and approximate reasoning under uncertainty (fuzzy logic)—the two core pillars of soft computing—integrated with the simulation engine through the same pluggable signal-policy interface and calibration pipeline.

**Key references:** `docs/TEAM_IMPLEMENTATION_PLAN.md` (Phases 13, 28–30), `docs/PRD.md` G7, `docs/TRD.md` §4.1 (TR-ENG-09/11), §4.2 (TR-PIPE-07).

---

## Role in Project

The Soft Computing subsystem serves three critical roles in NexusSim:

1. **Automated calibration:** Replaces the manual parameter-sweep loop in `validate.py` (currently `speed_factor`, `route_spread`, `chaos`, `demand_scale` searched by hand) with a genetic algorithm that evolves optimal calibration parameters, targeting GA-tuned MAPE ≤ manually-tuned MAPE from Phase 6.
2. **Alternative signal strategy:** The fuzzy-logic controller provides a human-readable, rule-based signal strategy that is neither fixed-cycle (Webster's) nor learned (RL)—demonstrating approximate reasoning with triangular membership functions, Mamdani inference, and centroid defuzzification as a distinct soft-computing approach.
3. **Cross-subject integration:** CV-derived real-world congestion data feeds the GA as an additional fitness term (Phase 14.6), and the fuzzy controller slots into the same FR-7 pluggable `SignalPolicy` interface as Webster's and RL for live dashboard comparison.

**TRD traceability:** TR-PIPE-07 (GA calibration), TR-ENG-09/11 (SignalPolicy interface, FuzzyPolicy), TR-DASH-06 (CalibrationReportPanel).

---

## Objectives

| ID | Objective | Phase(s) | Status | Acceptance Criteria |
|----|-----------|----------|--------|---------------------|
| O-SC-1 | Refactor `validate.py` so `build_report()` is directly importable as a pure fitness function | 13.1 | PLANNED | No CLI behaviour change; unlocks reuse from GA (TR-PIPE-07) |
| O-SC-2 | Implement `pipeline/src/optimize_calibration.py`: real-valued chromosome `[speed_factor, route_spread, chaos, demand_scale]`, tournament selection, blend crossover, Gaussian mutation | 13.2 | PLANNED | Population ~20, ~20–30 generations; bounds in module docstring (TR-PIPE-07) |
| O-SC-3 | Parallelize fitness evaluation via `multiprocessing.Pool` — each eval is one independent `--fast --no-ws` engine subprocess | 13.3 | PLANNED | No engine changes needed (TR-PIPE-07) |
| O-SC-4 | Write `data/<city>/ga_calibration_report.json`: best chromosome, per-generation best/mean fitness, final `validation_report.json` | 13.4 | PLANNED | Feeds `CalibrationReportPanel.tsx` |
| O-SC-5 | Implement `engine/src/agent/FuzzyPolicy.h`: Mamdani inference over queue length + wait time (triangular membership), rule base, centroid defuzzification → green-time extension | 13.5 | PLANNED | Implements `SignalPolicy` interface from Phase 12 (TR-ENG-11) |
| O-SC-6 | Unit test `FuzzyPolicy`: membership function boundaries, rule firing, defuzzified output range | 13.6 | PLANNED | GoogleTest; mirrors `test_signal.cpp` structure |
| O-SC-7 | Dashboard: `CalibrationReportPanel.tsx` — GA convergence chart (Recharts) | 13.7 | PLANNED | Reads static JSON report; no live WS data needed (TR-DASH-06) |
| O-SC-8 | Ablation note: GA-tuned vs. manually-tuned MAPE; Webster vs. Fuzzy avg-wait/Gini | 13.8 | PLANNED | Markdown table in `docs/results.md` |
| O-SC-9 | Wire `cv_congestion.json` into GA as additional fitness term (sim zone wait/speed vs. CV-observed level, blended with MAPE) | 14.6 | PLANNED | Both terms weighted; weight documented |

---

## Current Implementation

### Status: NOT YET IMPLEMENTED

The Soft Computing subsystem is entirely **PLANNED** (Phase 13). No GA or fuzzy-logic source files exist. The following describes the designed architecture.

### Component A: Genetic Algorithm Calibration (Phase 13.1–13.4)

**Existing baseline being replaced:**

The current `pipeline/src/validate.py` contains a manual parameter sweep in its `main()` function (`validate.py:161–236`) that iterates over hand-selected parameter combinations and reports the best MAPE. The GA replaces this with an evolutionary search.

**Chromosome design:**

```python
# Real-valued chromosome — 4 genes
chromosome = {
    "speed_factor": float,    # Multiplier on agent desired speed
    "route_spread": float,    # Stochastic route diversity factor
    "chaos": float,           # Lane discipline chaos coefficient
    "demand_scale": float,    # OD demand scaling factor
}
```

**GA parameters (designed):**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Population size | ~20 | Balances diversity with evaluation cost (each eval = one engine subprocess) |
| Generations | ~20–30 | Sufficient for convergence on 4-dimensional space |
| Selection | Tournament (k=3) | Standard; preserves diversity better than roulette |
| Crossover | Blend (BLX-α) | Natural for real-valued genes; α=0.5 typical |
| Mutation | Gaussian (σ per gene) | Smooth perturbation; σ anneals over generations |
| Fitness | `build_report()` accuracy score | Same function used by `validate.py` Phase 6 |
| Parallelism | `multiprocessing.Pool` | Each fitness eval = independent `--fast --no-ws` engine subprocess |

**Fitness function (`build_report()` from `validate.py`):**

```python
def build_report(
    graph_path: str,
    od_matrix_path: str,
    speed_factor: float,
    route_spread: float,
    chaos: float,
    demand_scale: float,
) -> dict:
    """
    Run engine headlessly and compare simulated corridor journey times
    against ground truth. Returns:
    - mape: float (mean absolute percentage error)
    - corridors_within_25: float (fraction of corridors within 25% error)
    - passes_checkpoint: bool (MAPE <= 25% AND >= 75% corridors within 25%)
    """
```

**Output (`ga_calibration_report.json`):**

```json
{
  "city": "chicago",
  "generations": 25,
  "best_chromosome": {
    "speed_factor": 1.12,
    "route_spread": 0.35,
    "chaos": 0.15,
    "demand_scale": 0.95
  },
  "best_fitness": 0.87,
  "convergence": [
    {"gen": 0, "best_fitness": 0.62, "mean_fitness": 0.45},
    {"gen": 1, "best_fitness": 0.68, "mean_fitness": 0.51},
    ...
  ],
  "final_validation": { /* standard validate.py report */ },
  "ga_tuned_mape": 18.3,
  "manual_tuned_mape": 21.6,
  "improvement_pct": 15.3
}
```

**Dashboard panel (`CalibrationReportPanel.tsx`):**

| Element | Type | Data Source |
|---------|------|-------------|
| Convergence chart | Recharts LineChart | `convergence[].best_fitness`, `convergence[].mean_fitness` |
| Best parameters | Key-value display | `best_chromosome` |
| MAPE comparison | Before/after bar chart | `ga_tuned_mape` vs. `manual_tuned_mape` |
| Final validation | Status badge | `final_validation.passes_checkpoint` |

### Component B: Fuzzy-Logic Signal Controller (Phase 13.5–13.6)

**Interface implemented:** `SignalPolicy` from Phase 12:

```cpp
// PLANNED — engine/src/agent/SignalPolicy.h (Phase 12)
class SignalPolicy {
public:
    virtual ~SignalPolicy() = default;
    virtual void tick(float dt) = 0;
    virtual bool is_green(int64_t edge_id) const = 0;
    virtual int current_phase_index() const = 0;
    virtual std::string policy_name() const = 0;
};
```

**FuzzyPolicy design (`engine/src/agent/FuzzyPolicy.h`):**

| Component | Design |
|-----------|--------|
| Inputs | Queue length (vehicles), wait time (seconds) — per approach |
| Membership functions | Triangular: `short`, `medium`, `long` for queue; `short`, `medium`, `long` for wait |
| Rule base | Mamdani-style IF-THEN rules (e.g., "IF queue IS long AND wait IS long → extend green significantly") |
| Inference | Mamdani min-max composition |
| Defuzzification | Centroid method → concrete green-time extension in seconds |
| Output | Green-time extension added to current phase duration |
| Activation | Runs via `--signal-policy fuzzy` CLI flag |

**Membership functions (triangular):**

```
Queue length:
  short:  (0, 0, 10)      — 0 to 10 vehicles
  medium: (5, 15, 25)     — 5 to 25 vehicles
  long:   (20, 35, 50)    — 20 to 50 vehicles

Wait time:
  short:  (0, 0, 30)      — 0 to 30 seconds
  medium: (20, 60, 100)   — 20 to 100 seconds
  long:   (80, 150, 300)  — 80 to 300 seconds
```

**Rule base (9 rules, 3×3):**

| Queue \ Wait | Short | Medium | Long |
|-------------|-------|--------|------|
| **Short** | Extend 0s | Extend 2s | Extend 5s |
| **Medium** | Extend 2s | Extend 5s | Extend 10s |
| **Long** | Extend 5s | Extend 10s | Extend 15s |

*(Actual rule outputs are continuous via centroid defuzzification, not discrete.)*

**Unit tests (`engine/tests/test_fuzzy.cpp`):**

| Test | Validates |
|------|-----------|
| `MembershipShortBoundary` | `short` membership = 1.0 at center, 0.0 at boundaries |
| `MembershipMediumOverlap` | `medium` overlaps with `short` and `long` correctly |
| `RuleFiring` | At known input, correct rules fire with expected activation strength |
| `DefuzzifiedRange` | Output always in [0, 15] seconds (bounded extension) |
| `ZeroInputZeroOutput` | Empty queue + zero wait → no extension |
| `MaxInputMaxOutput` | Max queue + max wait → maximum extension |
| `PolicyName` | `policy_name()` returns `"fuzzy"` |

---

## Dependencies/Interfaces

### Upstream (what Soft Computing depends on)

| Dependency | Source | Interface | Status |
|------------|--------|-----------|--------|
| `validate.py` `build_report()` | Pipeline (`pipeline/src/validate.py:85–150`) | Pure fitness function returning `{mape, corridors_within_25, passes_checkpoint}` | DONE (needs refactoring in Phase 13.1) |
| `graph.json` | Pipeline | Road network for engine subprocess evaluations | DONE (Phase 1) |
| `od_matrix.json` | Pipeline | OD demand for engine subprocess evaluations | DONE (Phase 6) |
| `SignalPolicy` interface | C++ engine (Phase 12) | `tick()`, `is_green()`, `current_phase_index()`, `policy_name()` | PLANNED (Phase 12) |
| CV congestion data | `cv_congestion.json` (Phase 14) | Per-zone per-hour congestion levels for blended fitness | PLANNED (Phase 14.5–14.6) |

### Downstream (what depends on Soft Computing)

| Consumer | Interface | Status |
|----------|-----------|--------|
| C++ engine (`--signal-policy fuzzy`) | `FuzzyPolicy` implements `SignalPolicy`; loaded at startup | PLANNED (Phase 13.5) |
| Dashboard `CalibrationReportPanel.tsx` | Reads `ga_calibration_report.json` for convergence chart | PLANNED (Phase 13.7) |
| Dashboard `PolicyComparisonPanel.tsx` | Fuzzy appears alongside Webster's and RL for comparison | PLANNED (Phase 12.6) |
| `docs/results.md` | GA-tuned vs. manual MAPE; Webster vs. Fuzzy avg-wait/Gini ablation | PLANNED (Phase 13.8) |
| RL training (optional future) | GA-optimized parameters could initialize RL training for faster convergence | NOT PLANNED (potential extension) |

### External dependencies

| Package | Purpose | Required? |
|---------|---------|-----------|
| Python `multiprocessing` | Parallel fitness evaluation | Yes (stdlib) |
| GoogleTest | FuzzyPolicy unit tests | Yes (already in CMakeLists.txt) |

---

## Future Extension Points

1. **Multi-objective GA:** Extend fitness to simultaneously optimize MAPE and Gini coefficient (Pareto front).
2. **Adaptive fuzzy rules:** Learn rule weights from data rather than hand-specifying them (neuro-fuzzy / ANFIS).
3. **Self-tuning membership functions:** Adjust triangular MF boundaries based on observed data distributions.
4. **Particle Swarm Optimization (PSO):** Alternative metaheuristic for comparison against GA on the same calibration task.
5. **Fuzzy + RL hybrid:** Fuzzy controller provides warm-start policy for RL training; RL fine-tunes from fuzzy baseline.
6. **Multi-city GA transfer:** Train GA on Chicago, transfer best parameters to Paris/Ahmedabad with city-specific mutation.
7. **Dynamic fuzzy inputs:** Add more inputs (neighbor pressure, time of day, weather) to the fuzzy rule base.
8. **Type-2 fuzzy sets:** Handle greater uncertainty in queue/wait measurements with interval type-2 membership functions.

---

## References

| Document | Section | Content |
|----------|---------|---------|
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phase 13 | Full phase: GA calibration (13.1–13.4), fuzzy controller (13.5–13.6), dashboard (13.7), ablation (13.8) |
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phase 14.6 | CV congestion wired into GA as additional fitness term |
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phases 28–30 | Expanded SC: PSO, SA, ES, ACS, ABC, ANFIS, Type-2, GP, Rough Sets, NSGA-II |
| `docs/PRD.md` | G7, G6, F7 | Soft computing goals, pluggable signal policies |
| `docs/TRD.md` | §4.2 (TR-PIPE-07) | GA calibration technical requirement |
| `docs/TRD.md` | §4.1 (TR-ENG-09, TR-ENG-11) | SignalPolicy interface, FuzzyPolicy technical requirements |
| `docs/TRD.md` | §4.4 (TR-DASH-06) | CalibrationReportPanel technical requirement |
| `docs/TRD.md` | §7 | Data requirements: GA search space, calibration report schema |
| `pipeline/src/validate.py` | `build_report()` (lines 85–150), `main()` (lines 161–236) | Existing fitness function and manual sweep to be refactored |
| `docs/TECH_STACK.md` | §Directory Structure | `pipeline/src/optimize_calibration.py` location |

---

*This document is self-contained and independently updatable. Changes to other subject documentation files do not require changes here, and vice versa. Last updated: August 2026.*
