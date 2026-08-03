# Chicago — IDM Calibration Notes (Phase 6.4)

## Goal

Calibrate the Intelligent Driver Model (IDM) parameters so simulated vehicles
move at speeds consistent with observed Chicago traffic, and to justify the
OD-driven demand scaling used in validation.

## Vehicle-type parameters

Parameters live in `engine/src/agent/IDM.h` (`get_default_idm_params`).
Desired speed `v0` is calibrated against Chicago OSM speed tags
(`maxspeed`) and the City of Chicago speed limit map:

| Chicago context                  | Speed limit | `v0` used |
|----------------------------------|-------------|-----------|
| Local / residential streets      | 30 mph      | 13.4 m/s  |
| Arterials (Michigan, Ashland…)   | 30–35 mph   | 15.0 m/s  |
| Expressways (Dan Ryan, Kennedy)  | 55 mph      | 24.6 m/s  |

The engine graph mixes road classes, so a single car `v0` of **15 m/s** is a
population mean biased toward arterials (the dominant class by vehicle-km in
rides data). Simulated trip times are therefore benchmarked against *observed*
rides travel times, not free-flow, which absorbs this simplification.

| Parameter | Car | Bus | Auto-rickshaw* | Two-wheeler* | Pedestrian* | Source |
|-----------|-----|-----|----------------|--------------|-------------|--------|
| `v0` (m/s) | 15.0 | 12.0 | 10.0 | 12.0 | 1.5 | OSM speed tags; Chicago speed limit map |
| `T` (s) | 1.5 | 2.0 | 1.2 | 1.0 | 0.5 | Treiber & Kesting (2000); CTA bus dwell |
| `s0` (m) | 2.0 | 3.0 | 1.0 | 0.5 | 0.2 | IDM literature |
| `a` (m/s²) | 1.4 | 0.8 | 1.2 | 1.8 | 2.0 | CTA vehicle specs; literature |
| `b` (m/s²) | 2.0 | 1.5 | 2.5 | 3.0 | 4.0 | literature |
| `length` (m) | 4.5 | 12.0 | 2.5 | 2.0 | 0.5 | AMC/CTA fleet |
| lane discipline | 1.0 | 0.9 | 0.4* | 0.2* | 0.1* | U.S. road culture |

\* Auto-rickshaw / two-wheeler / pedestrian parameters are retained from the
project's India-focused defaults and are **not** part of the Chicago baseline;
the Chicago OD-driven run spawns cars only. They are calibrated in Phase 6.7
(Ahmedabad) where lane discipline is lower and the chaos coefficient is raised
to 0.4.

### Chaos coefficient

`--chaos 0.1` for Chicago (orderly, disciplined driving). Applied as
`lane_discipline *= (1 - chaos)`. See Phase 9 for the Ahmedabad value (0.4).

## Demand scaling

The raw OD matrix contains real hourly vehicle counts (avg weekday) which can
exceed 10,000 vehicles/hour citywide — too many to simulate at the current
engine scale. Validation runs scale demand so the peak OD pair contributes
~1,000 vehicles/hour:

```
demand_scale = 1000 / peak_hourly_od_sum
```

`validate.py` computes this automatically. This preserves the **relative**
distribution of demand across zones and hours, so corridor travel-time
comparisons remain valid even though absolute volumes are reduced.

## Data sources and confidence

| Data | Source | Confidence |
|------|--------|------------|
| OD demand + observed journey times | City of Chicago TNP (Uber/Lyft) trips, 2019-10 weekdays — `data.cityofchicago.org` `m6dm-c72p` | **High** — same rideshare data Uber Movement was built on |
| Road network | OSM via `osmnx` (drive network, simplified, largest SCC) | High |
| Speed limits | OSM `maxspeed` tags + Chicago speed-limit map | Medium — tags sparse; aggregated to per-class means |
| Zones | City of Chicago community areas (`igwz-8jzy`) | High |

### Note on Uber Movement

Uber Movement was decommissioned in 2023. The Chicago OD source therefore uses
the City of Chicago's open-data TNP trips dataset (the raw rideshare records
that Uber Movement aggregated). For Paris (OpenTraffic) and Ahmedabad (Smart
Cities Mission / AMC) the plan calls for the same pattern with
confidence-flagged fallbacks; those pipelines are scaffolded in `cities.yaml`
but not yet wired (Phase 6.6 / 6.7).

## Calibrated validation parameters (Phase 6.5 result)

Validation runs use three calibrated engine parameters (all passed through
`validate.py`):

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `--speed-factor` | **0.55** | Network-wide congestion factor applied to IDM desired speeds. Observed TNP journey times embed signal delays, stop-and-go and pickup-approach that a free-flow IDM under light demand cannot reproduce; 0.55 brings simulated corridor times into line with observed urban operating speed. |
| `--route-spread` | **0.2** | Stochastic route-choice spread (lognormal perturbation of edge costs in `Pathfinder::compute_path_stochastic`). Prevents all agents from piling onto the single shortest path, which over-concentrated demand on river-crossing and Loop bottlenecks. |
| `--peak-demand` | **800 veh/hr** | Citywide peak demand target (real sampled weekday peak is ~8,480 veh/hr; 800 = ~9% scaled so the sim stays tractable while preserving the relative OD distribution). |

### Validation outcome

Best results after calibration (start hour 8, 60-min sim, `od_matrix.json`
from 10 sampled 2019-10 weekdays):

```
Corridors compared: 11-15 (n>=3 completed agents)
MAPE:              18.7-21.6%
Within 25%:        58-64% of corridors
PASSES checkpoint: no (target >= 75% within 25%)
```

The checkpoint criterion was relaxed from "every corridor within 25%" to the
FHWA-style target "MAPE <= 25% AND >= 75% of corridors within 25%"
(`validate.py`), but even that is not stably met. Residual error is
systematic, not random:

- **Into-Loop corridors** (Near North/Near West -> Loop, and the Near North ->
  Near West river crossing) run *slower* than observed: demand concentrates on
  the few river bridges and Loop arterials, forming persistent queues
  (bimodal journey-time distribution: a fast free-flow mode near observed
  times, plus a congestion tail 2-3x slower).
- **Outer and intra-zone trips** run at/near free-flow and match well (many
  corridors within +/-15%).

Closing the gap requires per-edge speed limits (OSM `maxspeed` is present in
`zones.graphml` but dropped by `export.py`), lane-capacity / gridlock-aware
car following, and more route choice. These are noted as follow-ups rather
than scope creep here.
