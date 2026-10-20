# NexusSim — Future Planning: Production Roadmap

> **Status:** Planning / Design  
> **Owner:** Product + Engineering  
> **Date:** 2026-10-20  
> **Scope:** Dynamic city onboarding, multi-tenant workspaces, simulation-as-a-service, what-if scenarios, real-time ingestion, algorithm marketplace, federated learning, multi-modal simulation, disaster response, emissions accounting, collaborative planning.

---

## 1. Executive Summary

NexusSim is currently a single-city, single-tenant traffic simulation stack: a C++17 engine (`:9001`), Python sidecars (`:9003–:9006`), a unified FastAPI gateway (`:8000`), and a React dashboard (`:3000`). Cities are hardcoded in `pipeline/cities.yaml` (Chicago, Paris, Ahmedabad, Piedmont) and downloaded via OSMnx at build time.

This document defines a production-grade evolution: **a multi-city, multi-tenant traffic simulation platform** where any user can upload OSM data for a new city (e.g., Mumbai), have the pipeline process it, and immediately run the full stack of 48 algorithms, ML models, and signal policies on that city through the dashboard.

The plan is organized into 10 capability modules, 5 implementation phases, and a production architecture covering API contracts, data models, security, observability, and deployment.

---

## 2. Vision & Product Principles

| Principle | Meaning |
|-----------|---------|
| **City-agnostic core** | Engine, sidecars, and algorithms must not assume Chicago schemas. Any valid OSM/PBF graph should load and simulate. |
| **Multi-tenant by default** | Workspaces isolate city data, simulation runs, and scenarios between users/organizations. |
| **API-first** | Every capability is reachable via REST/WebSocket on the gateway; the dashboard is one client among many. |
| **Observable & auditable** | Every simulation run produces lineage: input OSM hash, pipeline version, model checkpoint, random seed, KPI snapshot. |
| **Graceful degradation** | If real OD data is unavailable for a user city, fall back to gravity/density proxy and flag results as "modelled, not measured" (existing convention). |

---

## 3. Capability Modules

### 3.1 Dynamic City Upload (OSM Onboarding)
**User story:** A traffic engineer uploads `mumbai.osm.pbf` (or `.osm` / `.graphml`) through the dashboard. The system ingests it, runs the cleaning + export pipeline, registers the city, and makes it selectable in the dashboard alongside Chicago.

**Production requirements:**
- Accept `.osm`, `.osm.pbf`, `.graphml` uploads (max 500 MB, virus-scanned).
- Extract bounding box, project to WGS84, simplify, keep largest connected component.
- Generate `data/{city_id}/graph.json` (nodes/edges) for the C++ engine.
- Auto-register in city registry with `od_source: uniform` fallback; allow user to supply GTFS/OD CSV later.
- Assign a `city_id` (slug: `mumbai`, `delhi-central`, etc.) and workspace scope.

### 3.2 Multi-Tenant City Workspaces
**User story:** A consulting firm manages Mumbai and Delhi projects simultaneously. Workspace A sees only Mumbai runs; Workspace B sees only Delhi. No cross-workspace data leakage.

**Production requirements:**
- Workspace entity with members, roles (admin, viewer, editor).
- Gateway routes `/{workspace_id}/ws` and `/{workspace_id}/api/*` to isolated engine/sidecar instances (or process pools).
- City registry scoped to workspace; public cities (Chicago, Paris) shared read-only.
- JWT-based auth with workspace claims; row-level isolation in any persisted metadata DB.

### 3.3 Simulation-as-a-Service (SaaS)
**User story:** An external planning tool calls `POST /api/simulations` with `{city_id: "mumbai", agents: 20000, duration_min: 60, signal_mode: "fuzzy"}` and receives a `simulation_id`. It polls state via WebSocket and tears down on completion.

**Production requirements:**
- Ephemeral engine process pool (Docker containers or lightweight VMs) per simulation run.
- Port allocation from a dynamic range; health checks before accepting connections.
- Run lifecycle: queued → running → completed → failed → archived → garbage-collected (TTL 24h).
- Usage metering per workspace (agent-ticks, compute minutes).

### 3.4 What-If Scenario Engine
**User story:** Fork a live Mumbai simulation at tick 5000, switch signal policy from Webster to Type-2 Fuzzy, inject a road closure incident, and compare KPIs (wait time, Gini, emissions) against the baseline timeline.

**Production requirements:**
- Deterministic engine snapshots (agent state, signal phases, queues, RNG seed) at arbitrary tick.
- Fork creates `scenario_id` sharing the base city graph but diverging in state.
- Side-by-side KPI comparison dashboard (baseline vs scenario).
- Scenario templates: incident, road closure, signal retiming, demand surge (+chaos), evacuation.

### 3.5 Real-Time Data Ingestion (Live Digital Twin)
**User story:** Connect GTFS-Realtime (transit), CV2X messages, CCTV, or weather APIs to the event bus. The engine reacts to live incidents and demand spikes within the same sim tick.

**Production requirements:**
- Adapters: GTFS-RT protobuf, CV2X (ETSI/SAE J2735/DSRC), MQTT for CCTV, OpenWeatherMap.
- Normalize into NexusSim event bus topics: `cv.anomaly`, `nlp.incident`, `sc.adaptation`, `scenario.demand_spike`.
- Temporal alignment: map real-world timestamps to sim clock via configurable warp factor.
- Circuit breakers: if live feed stalls > N ticks, fall back to last-known demand model.

### 3.6 Algorithm Marketplace / Plugin Registry
**User story:** A researcher contributes a new RL signal policy as an ONNX model + Python sidecar. It appears in Algo Explorer, is selectable in `--signal-mode`, and can be A/B tested against MAPPO on Mumbai.

**Production requirements:**
- Registry: `algo_id`, name, version, discipline (CV/SC/NLP/RL), ONNX path, sidecar URL, author, validation status.
- Gateway routes `/api/algo/{algo_id}/*` to registered sidecars.
- Sandboxed sidecar execution (container resource limits, read-only rootfs).
- Versioned algorithms; rollback to previous version if KPIs regress.

### 3.7 Federated Multi-City Learning
**User story:** Train MAPPO on Chicago, export ONNX weights, initialize Ahmedabad and Mumbai from those weights, fine-tune locally. Only model deltas cross city boundaries — raw trip data never leaves the city workspace.

**Production requirements:**
- ONNX export/import pipeline (existing `ml/export/export_onnx.py`).
- Federated averaging coordinator (optional central server) or direct checkpoint transfer.
- Privacy audit log: what left the workspace, when, and under what policy.
- Transfer sensitivity sweep (existing `ml/train/sensitivity_sweep.py`) per city pair.

### 3.8 Multi-Modal Simulation Layer
**User story:** Simulate buses, trains, bicycles, pedestrians, and EVs with charging dwell time. Optimize for person-throughput and transit signal priority, not just vehicle throughput.

**Production requirements:**
- Agent taxonomy: `car`, `bus`, `train`, `bike`, `pedestrian`, `ev` in `Agent.h` SoA layout.
- New pathfinder modes (rail graph, bike lanes, pedestrian network).
- Signal phases with transit priority (bus preempts red).
- EV charging stations as destinations with occupancy/dwell.

### 3.9 Disaster & Incident Response Mode
**User story:** Simulate a bridge collapse on a major arterial. NLP parses incident text, CV detects anomalies from cameras, signals reroute traffic, emergency vehicles get green waves.

**Production requirements:**
- Incident injection API (`POST /api/incident` already exists; extend with geometry/polygon).
- Road closure = edge weight → ∞ or removed from pathfinder.
- Emergency vehicle preemption policy in `SignalPolicy.h`.
- Evacuation demand surge model (chaos multiplier per zone).
- After-action report: KPI degradation vs baseline, recovery time.

### 3.10 Emissions & Carbon Accounting
**User story:** Per policy scenario, report CO₂, NOx, PM2.5 per zone. Identify pollution inequity (peripheral neighborhoods bearing burden for central throughput).

**Production requirements:**
- Energy model: ICE fuel consumption vs speed/acceleration; EV kWh per km.
- Idling emissions at intersections (signal phase × queue length).
- Emissions KPI added to `Metrics.h` and `EquityOverlay`.
- Export to CSV/PDF for climate-action planning.

### 3.11 Collaborative Planning Dashboard
**User story:** Two planners in different cities open the same scenario. Shared cursors, comments on intersections, voting on scenario proposals, export to PDF/GeoJSON.

**Production requirements:**
- Presence & awareness over Event Bus WS (`/ws/events`).
- Comment/annotation entities attached to edge/node IDs.
- Scenario proposal lifecycle: draft → review → approved → archived.
- Export: PDF report, GeoJSON network, CSV KPI table.

---

## 4. Production Architecture

### 4.1 High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Clients (Dashboard, API, CLI)                   │
└──────────────────┬──────────────────────────────────────────────────────┘
                   │ HTTPS / WSS
┌──────────────────▼──────────────────────────────────────────────────────┐
│                    Unified API Gateway (:8000 / :443)                   │
│  • AuthN/AuthZ (JWT + workspace claims)                                 │
│  • Rate limiting per workspace                                          │
│  • REST + WS proxy to sidecars & engine pools                           │
│  • City registry & simulation orchestrator                              │
└──────────────────┬──────────────────────────────────────────────────────┘
                   │
   ┌───────────────┼───────────────┬───────────────┬───────────────┐
   ▼               ▼               ▼               ▼               ▼
 Engine Pool   Sidecar Pool    City Import    Metadata DB   Object Storage
 (:9001 N)     (:9003-:9006)   Pipeline     (workspaces,  (OSM uploads,
 Docker/K8s    Docker/K8s      Workers      runs, scenarios)  checkpoints,
                                        Redis cache           ONNX models)
```

### 4.2 Data Flow: User Uploads Mumbai OSM

```
1. User uploads mumbai.osm.pbf → POST /api/cities/upload (multipart)
2. Gateway validates JWT, workspace, file type, size, virus scan
3. Object Storage: raw/{workspace_id}/{city_id}/mumbai.osm.pbf
4. City Import Worker (Celery/RQ or K8s Job):
   a. osmnx.graph_from_xml / PBF parser → raw.graphml
   b. clean.py → cleaned.graphml (simplify, largest CC)
   c. export.py → data/{city_id}/graph.json
   d. Compute bounding box, centroid, node/edge counts
5. Gateway writes city entry to Metadata DB + cities.yaml append
6. Dashboard GET /api/cities → Mumbai appears in CitySelector
7. User selects Mumbai → engine starts with --city mumbai
8. Simulation frames stream via /{workspace_id}/ws
```

### 4.3 Data Flow: What-If Scenario Fork

```
1. Baseline run: simulation_id = S1, city = mumbai, tick = 5000
2. POST /api/scenarios {base_simulation: S1, tick: 5000,
   mutations: [{op: "signal_mode", value: "type2_fuzzy"},
               {op: "incident", text: "road closed", edge_id: E42}]}
3. Orchestrator snapshots engine state at tick 5000 (deterministic export)
4. New engine process starts from snapshot, applies mutations
5. Divergent stream: S1-baseline vs S2-scenario via separate WS channels
6. ComparisonPanel computes KPI delta: wait_time, gini, co2, throughput
```

---

## 5. Data Models

### City
```json
{
  "city_id": "mumbai",
  "workspace_id": "ws_acme",
  "label": "Mumbai, India",
  "source": "user_upload",
  "source_file": "mumbai.osm.pbf",
  "source_hash": "sha256:...",
  "bbox": [19.0, 72.8, 19.2, 72.9],
  "center": [19.076, 72.877],
  "node_count": 45230,
  "edge_count": 89410,
  "od_source": "uniform",
  "status": "ready", // ingesting | ready | failed
  "created_at": "2026-10-20T10:00:00Z",
  "created_by": "user_123"
}
```

### Workspace
```json
{
  "workspace_id": "ws_acme",
  "name": "Acme Consulting",
  "members": [{"user_id": "u1", "role": "admin"}],
  "cities": ["mumbai", "chicago(read_only)"],
  "plan": "team",
  "quota": {"agent_ticks_per_month": 500000000}
}
```

### Simulation Run
```json
{
  "simulation_id": "sim_7f3a",
  "workspace_id": "ws_acme",
  "city_id": "mumbai",
  "signal_mode": "fuzzy",
  "policy_id": "mappo_v3",
  "agent_count": 20000,
  "duration_min": 60,
  "chaos": 0.1,
  "seed": 42,
  "status": "running", // queued | running | completed | failed | archived
  "started_at": "...",
  "completed_at": null,
  "kpi_snapshot": null,
  "ttl_seconds": 86400
}
```

### Scenario
```json
{
  "scenario_id": "sc_9b2c",
  "workspace_id": "ws_acme",
  "base_simulation_id": "sim_7f3a",
  "fork_tick": 5000,
  "mutations": [...],
  "status": "completed",
  "comparison": {"wait_time_delta_pct": -12.4, "gini_delta": -0.03}
}
```

### Algorithm Registration
```json
{
  "algo_id": "rl_custom_v1",
  "name": "Custom PPO Mumbai",
  "discipline": "rl",
  "version": "1.0.0",
  "onnx_path": "s3://models/ws_acme/rl_custom_v1.onnx",
  "sidecar_url": "https://sidecars.ws_acme.internal:9006",
  "author": "researcher_456",
  "validation_status": "validated",
  "created_at": "..."
}
```

---

## 6. API Contracts (Gateway)

### City Management
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/cities` | List cities visible to workspace |
| `POST` | `/api/cities/upload` | Multipart OSM upload → triggers import job |
| `GET` | `/api/cities/{city_id}` | City metadata, bbox, status |
| `DELETE` | `/api/cities/{city_id}` | De-register city (soft delete) |

### Simulation Lifecycle
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/simulations` | Create run (city, agents, duration, signal_mode, policy) |
| `GET` | `/api/simulations/{id}` | Run status, KPI snapshot, logs |
| `DELETE` | `/api/simulations/{id}` | Cancel / tear down |
| `WS` | `/{workspace_id}/ws` | Live engine frames for a simulation |
| `WS` | `/{workspace_id}/ws/events` | Event bus stream |

### Scenario Engine
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scenarios` | Fork simulation with mutations |
| `GET` | `/api/scenarios/{id}` | Scenario result + comparison vs baseline |
| `GET` | `/api/simulations/{id}/compare/{scenario_id}` | Side-by-side KPI diff |

### Algorithm Registry
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/algo` | Catalog (48 default + registered) |
| `POST` | `/api/algo/register` | Register new algorithm version |
| `GET` | `/api/algo/{algo_id}` | Algorithm metadata + ONNX info |

### Workspace & Auth
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/login` | JWT issuance |
| `GET` | `/api/workspaces` | List user workspaces |
| `GET` | `/api/workspaces/{id}/members` | Membership management |

---

## 7. End-to-End Implementation Plan

### Phase 0 — Foundation (Weeks 0–2)
**Goal:** Make the codebase ready for multi-city, multi-tenant work.

- [ ] Add auth middleware to gateway (JWT, workspace claims).
- [ ] Add `GET /api/cities` and `POST /api/cities/upload` stubs.
- [ ] Add `postman/results/` to `.gitignore` (done).
- [ ] Add API verification tests for new endpoints in `postman/api_check.py`.
- [ ] Dockerize pipeline import workers (Dockerfile.pipeline).
- [ ] Add `docker-compose.workspaces.yml` for local multi-workspace dev.
- [ ] CI gate: run `api_check.py` + all pytest suites on every PR.

### Phase 1 — Dynamic City Upload (Weeks 2–6)
**Goal:** A user can upload OSM for any city and simulate it.

- [ ] `pipeline/src/import_osm.py`: parse `.osm`/`.osm.pbf`/`.graphml` → `raw.graphml`.
  - Use `osmnx.graph_from_xml` for `.osm`; `osmnx` + `pyosmium` or `osmium-tool` for `.pbf`.
- [ ] Extend `clean.py` and `export.py` to accept arbitrary `city_id` paths.
- [ ] Gateway `POST /api/cities/upload`:
  - Validate file, store to object storage (`data/uploads/{workspace_id}/{city_id}/`).
  - Enqueue import job; return `job_id`.
  - On success, append to `cities.yaml` and register in metadata DB.
- [ ] Dashboard:
  - `CitySelector` fetches `GET /api/cities` instead of hardcoded `CITIES`.
  - Add "Upload City" button → file picker → progress poller.
- [ ] `api_check.py`: add tests for upload endpoint and city listing.
- [ ] Validation: upload Mumbai (or sample OSM), run engine `--city mumbai`, confirm 200 health + WS frames.

### Phase 2 — Multi-Tenant Workspaces (Weeks 6–10)
**Goal:** Isolated workspaces with auth.

- [ ] Metadata DB (PostgreSQL) schema: workspaces, members, cities, runs, scenarios.
- [ ] Gateway workspace routing: `/{workspace_id}/ws`, `/{workspace_id}/api/*`.
- [ ] Auth service: login, JWT, workspace-scoped API keys.
- [ ] Row-level isolation: city queries filtered by workspace.
- [ ] Dashboard: workspace switcher, workspace-scoped city list.
- [ ] Rate limiting per workspace (agent-ticks/month).

### Phase 3 — Simulation-as-a-Service + Scenario Engine (Weeks 10–16)
**Goal:** Ephemeral simulation runs and what-if forking.

- [ ] Orchestrator service: Docker/K8s job scheduler for engine processes.
- [ ] Dynamic port allocation + health checks.
- [ ] `POST /api/simulations`, `GET /api/simulations/{id}`, WS frame stream.
- [ ] Deterministic snapshot export/import in C++ engine (`Simulation.h` state serialization).
- [ ] `POST /api/scenarios` with mutations (signal_mode, incident, demand_scale).
- [ ] ComparisonPanel: baseline vs scenario KPI diff.
- [ ] Garbage collection: TTL-based cleanup of ephemeral engines.

### Phase 4 — Real-Time, Marketplace, Federated (Weeks 16–24)
**Goal:** Live data, plugin algorithms, cross-city learning.

- [ ] Real-time adapters: GTFS-RT, CV2X, MQTT, weather → event bus topics.
- [ ] Algorithm Registry: `/api/algo/register`, versioned ONNX + sidecars.
- [ ] Sandboxed sidecar execution (resource limits, read-only FS).
- [ ] Federated checkpoint transfer: Chicago ONNX → Mumbai init → fine-tune.
- [ ] Privacy audit log for cross-workspace model movement.

### Phase 5 — Multi-Modal, Disaster, Emissions, Collaboration (Weeks 24–36)
**Goal:** Full digital twin capabilities.

- [ ] Agent taxonomy (bus, train, bike, pedestrian, EV) in `Agent.h`.
- [ ] Transit signal priority, EV charging dwell, rail pathfinder.
- [ ] Disaster mode: incident injection, edge closure, evacuation chaos.
- [ ] Emissions model: ICE/EV per-agent energy + idling emissions KPI.
- + Collaborative annotations, presence, PDF/GeoJSON export.

---

## 8. Production Considerations

### 8.1 Infrastructure
| Concern | Recommendation |
|---------|---------------|
| Compute | Engine processes are CPU-heavy; run on dedicated worker nodes with CPU pinning. ONNX inference benefits from CUDA where available. |
| Storage | Object storage (S3/minio) for OSM uploads, ONNX models, checkpoints, scenario snapshots. |
| Metadata | PostgreSQL with row-level security for workspace isolation. |
| Caching | Redis for city registry, job queues, session state. |
| Orchestration | Kubernetes with custom operator or Celery/RQ workers for import jobs. |
| DNS/TLS | Wildcard certs for `*.nexussim.internal`; mTLS between gateway and sidecars. |

### 8.2 Security
- **Auth:** OIDC/OAuth2 (Keycloak, Auth0, or Azure AD) + short-lived JWTs.
- **Authorization:** Workspace-scoped RBAC (admin/editor/viewer).
- **File upload:** ClamAV virus scan, file type validation, max size 500 MB, quarantine suspicious uploads.
- **Network:** Sidecars bound to `127.0.0.1` internally; gateway terminates TLS; no direct client access to `:9001–:9006`.
- **Secrets:** HashiCorp Vault or cloud KMS for JWT signing keys, DB credentials.

### 8.3 Observability
- **Metrics:** Prometheus + Grafana (agent-ticks/s, engine tick latency, simulation run duration, workspace quota usage).
- **Tracing:** OpenTelemetry trace IDs propagated from gateway → sidecar → engine for distributed debugging.
- **Logging:** Structured JSON logs; simulation run ID in every log line.
- **Alerting:** PagerDuty on engine crash, import failure, workspace quota breach.

### 8.4 CI/CD & Testing
- **Unit:** Engine CTest, pipeline pytest, ML pytest, dashboard vitest (existing).
- **Integration:** `api_check.py` extended for upload/sim/scenario endpoints.
- **Contract tests:** Pact or OpenAPI validation between gateway and sidecars.
- **Chaos:** Kill ephemeral engine mid-run; verify graceful failure + KPI partial results.
- **Performance:** 20k-agent stress test per new city before marking `status: ready`.

---

## 9. Risk & Mitigation

| Risk | Mitigation |
|------|------------|
| OSM data quality varies by city | Validation step: check graph connectivity, signal node density; flag low-confidence cities. |
| Large PBF files slow imports | Stream parsing, background jobs, progress polling, size limits. |
| Engine non-determinism across forks | Pin RNG seed, export full state snapshot, version engine binary per run. |
| Multi-tenant data leakage | Namespace all resources by `workspace_id`; penetration test quarterly. |
| No real OD data for user cities | Fallback to gravity/density proxy (existing convention); flag as modelled. |
| GPU contention in ONNX inference | Per-workspace GPU quota; CPU fallback. |

---

## 10. Success Metrics

| KPI | Target |
|-----|--------|
| Cities onboardable via upload | Any valid OSM/PBF < 500 MB |
| Time from upload to first sim frame | < 10 minutes (small city), < 60 minutes (metro) |
| Multi-tenant isolation | Zero cross-workspace data leaks (audit quarterly) |
| Scenario fork latency | < 30 seconds from request to divergent stream |
| Test coverage | ≥ 90% on gateway + pipeline import modules |
| Regression rate | Zero KPI regressions on algorithm marketplace rollouts |

---

## 11. Appendix: Current State vs Future State

| Area | Today | Future (Production) |
|------|-------|---------------------|
| Cities | 4 hardcoded in `cities.yaml` | Unlimited, user-uploaded, workspace-scoped |
| Tenancy | Single-tenant | Multi-tenant with RBAC |
| Simulation | Long-running local process | Ephemeral API runs with TTL |
| Scenarios | None | Fork, mutate, compare |
| Data | Static OSM downloads | Live GTFS/CV2X/weather ingestion |
| Algorithms | 48 hardcoded | Plugin registry + ONNX marketplace |
| Learning | Single-city training | Federated multi-city transfer |
| Modes | Cars only | Multi-modal (bus, rail, bike, EV, pedestrian) |
| Output | WS frames + dashboard | API + WS + PDF/GeoJSON/CSV reports |

---

*End of document. To begin implementation, start with Phase 0 and Phase 1: add `GET /api/cities`, `POST /api/cities/upload`, `pipeline/src/import_osm.py`, and extend `postman/api_check.py` with upload tests.*
