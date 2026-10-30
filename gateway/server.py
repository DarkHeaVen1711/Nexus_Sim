"""Unified Backend API Gateway for NexusSim (Port 8000).

Consolidates all internal backend microservices under a single entry point:
- C++ Simulation Engine (Port 9001)        -> /ws
- Virtual Camera Service (Port 9003)      -> /api/camera/*
- NLP Chat & Incident Service (Port 9004) -> /api/chat, /api/incident
- Cross-Subject Event Bus (Port 9005)     -> /ws/events, /api/events/*
- Algo Explorer Catalog (Port 9006)       -> /api/algo/*

Additional platform services:
- Authentication & JWT tokens               -> /api/auth/*
- Multi-tenant workspaces                   -> /api/workspaces/*
- Dynamic city onboarding                   -> /api/cities/*
- Simulation-as-a-Service                   -> /api/simulations/*
- What-if scenario engine                   -> /api/scenarios/*
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import uvicorn
import yaml
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
import ssl
import websockets

# Ensure the repo root is on sys.path so uvicorn can import "gateway.server"
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Add pipeline/src to path for import_osm module
_PIPELINE_SRC = os.path.join(_REPO_ROOT, "pipeline", "src")
if _PIPELINE_SRC not in sys.path:
    sys.path.insert(0, _PIPELINE_SRC)

# Import auth module
from gateway.auth import (  # type: ignore
    authenticate_user,
    create_access_token,
    get_current_user,
    require_workspace_access,
    require_role,
    list_user_workspaces,
    create_workspace,
    WORKSPACES,
    USERS,
)

# Import OSM import module (pipeline/src is already on sys.path above)
from import_osm import import_osm  # type: ignore

# Import platform services (algorithm registry, rate limiting, emissions, ingestion)
from gateway.twin_router import router as twin_router
from gateway.platform_services import (  # type: ignore
    RegisteredAlgorithm,
    algorithm_registry,
    rate_limiter,
    compute_emissions,
    aggregate_emissions,
    realtime_ingestion,
    compare_kpis,
)

# Trust the local self-signed cert for ALL upstream connections (the
# sidecars and engine serve TLS with certs/server.{crt,key}).
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

app = FastAPI(
    title="NexusSim Unified Backend Gateway",
    description="Single-port API Gateway routing to Engine, NLP, CV, Event Bus, and Algo Explorer services.",
    version="2.0.0",
)

# Enable CORS for frontend dashboard (port 3000)
app.include_router(twin_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Target service URLs (configurable via environment variables for Docker)
ENGINE_WS_URL = os.environ.get("ENGINE_WS_URL", "wss://127.0.0.1:9001")
CAMERA_HTTP_URL = os.environ.get("CAMERA_HTTP_URL", "https://127.0.0.1:9003")
NLP_HTTP_URL = os.environ.get("NLP_HTTP_URL", "https://127.0.0.1:9004")
EVENT_BUS_HTTP_URL = os.environ.get("EVENT_BUS_HTTP_URL", "https://127.0.0.1:9005")
EVENT_BUS_WS_URL = os.environ.get("EVENT_BUS_WS_URL", "wss://127.0.0.1:9005/ws")
ALGO_HTTP_URL = os.environ.get("ALGO_HTTP_URL", "https://127.0.0.1:9006")

GATEWAY_PORT = int(os.environ.get("GATEWAY_PORT", "8000"))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
CITIES_YAML = os.path.join(REPO_ROOT, "pipeline", "cities.yaml")
ENGINE_EXE = os.path.join(REPO_ROOT, "engine", "build", "engine.exe")

os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# In-memory simulation & scenario registry (replace with DB in production)
# ---------------------------------------------------------------------------

SIMULATIONS: Dict[str, Dict[str, Any]] = {}
SCENARIOS: Dict[str, Dict[str, Any]] = {}
ENGINE_PROCESSES: Dict[str, subprocess.Popen] = {}


# ---------------------------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/auth/login")
async def login(username: str = Form(...), password: str = Form(...)) -> Dict[str, Any]:
    """Authenticate user and return JWT access token."""
    user = authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=401, detail="Incorrect username or password"
        )
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
        "workspaces": list_user_workspaces(user),
    }


@app.get("/api/auth/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Return current user info."""
    return current_user


# ---------------------------------------------------------------------------
# Workspace Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/workspaces")
async def list_workspaces(current_user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    """List workspaces accessible to the current user."""
    return list_user_workspaces(current_user)


@app.post("/api/workspaces")
async def create_workspace_endpoint(
    workspace_id: str = Form(...),
    name: str = Form(...),
    current_user: Dict[str, Any] = Depends(require_role(["admin"])),
) -> Dict[str, Any]:
    """Create a new workspace (admin only)."""
    return create_workspace(workspace_id, name, current_user["username"])


# ---------------------------------------------------------------------------
# City Registry
# ---------------------------------------------------------------------------

def _load_cities_yaml() -> Dict[str, Any]:
    if os.path.exists(CITIES_YAML):
        with open(CITIES_YAML, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_cities_yaml(config: Dict[str, Any]) -> None:
    with open(CITIES_YAML, "w") as f:
        yaml.safe_dump(config, f, sort_keys=False)


def _city_entry_from_yaml(city_id: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "city_id": city_id,
        "city_name": city_id.replace("-", " ").title(),
        "source": "config",
        "chaos": cfg.get("chaos", 0.1),
        "cv_bbox": cfg.get("cv_bbox"),
        "od_source": (cfg.get("od_source") or {}).get("type", "unknown"),
        "status": "ready",
    }


def _city_entry_from_data_dir(city_id: str) -> Optional[Dict[str, Any]]:
    city_dir = os.path.join(DATA_DIR, city_id)
    graph_json = os.path.join(city_dir, "graph.json")
    if not os.path.isdir(city_dir) or not os.path.exists(graph_json):
        return None

    node_count = 0
    edge_count = 0
    try:
        with open(graph_json, "r") as f:
            graph = json.load(f)
        node_count = len(graph.get("nodes", []))
        edge_count = len(graph.get("edges", []))
    except Exception:
        pass

    yaml_config = _load_cities_yaml()
    yaml_entry = yaml_config.get(city_id, {})

    return {
        "city_id": city_id,
        "city_name": city_id.replace("-", " ").title(),
        "source": "upload",
        "chaos": yaml_entry.get("chaos", 0.1),
        "cv_bbox": yaml_entry.get("cv_bbox"),
        "od_source": (yaml_entry.get("od_source") or {}).get("type", "uniform"),
        "status": "ready",
        "node_count": node_count,
        "edge_count": edge_count,
    }


def list_cities() -> List[Dict[str, Any]]:
    cities: Dict[str, Dict[str, Any]] = {}
    yaml_config = _load_cities_yaml()
    for city_id, cfg in yaml_config.items():
        cities[city_id] = _city_entry_from_yaml(city_id, cfg)
    if os.path.isdir(DATA_DIR):
        for entry in os.listdir(DATA_DIR):
            city_dir = os.path.join(DATA_DIR, entry)
            if not os.path.isdir(city_dir):
                continue
            entry_data = _city_entry_from_data_dir(entry)
            if entry_data:
                cities[entry] = entry_data
    return sorted(cities.values(), key=lambda c: c["city_id"])


def get_city(city_id: str) -> Optional[Dict[str, Any]]:
    for c in list_cities():
        if c["city_id"] == city_id:
            return c
    return None


@app.get("/api/cities", response_model=List[Dict[str, Any]])
async def list_cities_endpoint() -> List[Dict[str, Any]]:
    return list_cities()


@app.get("/api/cities/{city_id}", response_model=Dict[str, Any])
async def get_city_endpoint(city_id: str) -> Dict[str, Any]:
    city = get_city(city_id)
    if city is None:
        raise HTTPException(status_code=404, detail=f"City '{city_id}' not found")
    return city


@app.post("/api/cities/upload", response_model=Dict[str, Any])
async def upload_city(
    file: UploadFile = File(...),
    city_id: Optional[str] = Form(None),
    city_name: Optional[str] = Form(None),
) -> Dict[str, Any]:
    import tempfile
    import re as _re

    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".osm", ".pbf", ".graphml"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Expected .osm, .osm.pbf, or .graphml",
        )

    if city_id is None:
        city_id = _re.sub(r"[^a-z0-9]+", "-", filename.lower()).strip("-") or "city"

    if ".." in city_id or "/" in city_id or "\\" in city_id:
        raise HTTPException(status_code=400, detail="Invalid city_id")

    city_dir = os.path.join(DATA_DIR, city_id)
    os.makedirs(city_dir, exist_ok=True)

    raw_filename = f"raw{ext}"
    saved_path = os.path.join(city_dir, raw_filename)
    try:
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        result = import_osm(
            source_path=saved_path,
            city_id=city_id,
            city_name=city_name,
            out_dir=city_dir,
        )
    except Exception as e:
        if os.path.exists(city_dir):
            shutil.rmtree(city_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

    try:
        yaml_config = _load_cities_yaml()
        yaml_config[city_id] = {
            "query": f"{city_name or city_id} (user upload)",
            "chaos": 0.1,
            "cv_bbox": result.get("bbox"),
            "od_source": {"type": "uniform"},
            "note": f"User-uploaded OSM: {filename}",
        }
        _save_cities_yaml(yaml_config)
    except Exception:
        pass

    return {
        "city_id": result["city_id"],
        "city_name": result["city_name"],
        "status": result["status"],
        "node_count": result["node_count"],
        "edge_count": result["edge_count"],
        "bbox": result["bbox"],
        "center": result["center"],
        "message": f"City '{city_id}' imported successfully",
    }


# ---------------------------------------------------------------------------
# Simulation-as-a-Service
# ---------------------------------------------------------------------------

def _build_engine_args(city_id: str, config: Dict[str, Any]) -> List[str]:
    args = [
        "--city", city_id,
        "--duration", str(config.get("duration_min", 60)),
    ]
    agent_count = config.get("agent_count", 500)
    if agent_count > 0:
        args += ["--agents", str(agent_count)]
    od_path = config.get("od_path")
    if od_path:
        args += ["--od", od_path]
    demand_scale = config.get("demand_scale")
    if demand_scale is not None:
        args += ["--demand-scale", str(demand_scale)]
    start_hour = config.get("start_hour", 8.0)
    args += ["--start-hour", str(start_hour)]
    speed_factor = config.get("speed_factor", 0.55)
    args += ["--speed-factor", str(speed_factor)]
    route_spread = config.get("route_spread", 0.2)
    args += ["--route-spread", str(route_spread)]
    chaos = config.get("chaos", 0.1)
    args += ["--chaos", str(chaos)]
    signal_mode = config.get("signal_mode", "auto")
    args += ["--signal-mode", signal_mode]
    policy_path = config.get("policy_path")
    if policy_path:
        args += ["--policy", policy_path]
    onnx_provider = config.get("onnx_provider", "auto")
    args += ["--onnx-provider", onnx_provider]
    if config.get("fast"):
        args.append("--fast")
    return args


@app.post("/api/simulations", response_model=Dict[str, Any])
async def create_simulation(
    city_id: str = Form(...),
    workspace_id: str = Form("ws_default"),
    duration_min: int = Form(60),
    agent_count: int = Form(500),
    signal_mode: str = Form("auto"),
    od_path: Optional[str] = Form(None),
    demand_scale: Optional[float] = Form(None),
    start_hour: float = Form(8.0),
    speed_factor: float = Form(0.55),
    route_spread: float = Form(0.2),
    chaos: float = Form(0.1),
    current_user: Dict[str, Any] = Depends(require_workspace_access("ws_default")),
) -> Dict[str, Any]:
    """Start a new simulation run (SaaS)."""
    # Verify city exists
    city = get_city(city_id)
    if city is None:
        raise HTTPException(status_code=404, detail=f"City '{city_id}' not found")

    sim_id = f"sim_{uuid.uuid4().hex[:12]}"
    sim_config = {
        "city_id": city_id,
        "workspace_id": workspace_id,
        "duration_min": duration_min,
        "agent_count": agent_count,
        "signal_mode": signal_mode,
        "od_path": od_path,
        "demand_scale": demand_scale,
        "start_hour": start_hour,
        "speed_factor": speed_factor,
        "route_spread": route_spread,
        "chaos": chaos,
        "user": current_user["username"],
    }

    engine_args = _build_engine_args(city_id, sim_config)

    # Launch engine process
    try:
        proc = subprocess.Popen(
            [ENGINE_EXE] + engine_args,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"Engine executable not found at {ENGINE_EXE}. Build first.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start engine: {str(e)}")

    ENGINE_PROCESSES[sim_id] = proc

    now = datetime.now(timezone.utc).isoformat()
    SIMULATIONS[sim_id] = {
        "simulation_id": sim_id,
        "workspace_id": workspace_id,
        "city_id": city_id,
        "status": "running",
        "config": sim_config,
        "created_at": now,
        "started_at": now,
        "completed_at": None,
        "pid": proc.pid,
        "kpi_snapshot": None,
    }

    return {
        "simulation_id": sim_id,
        "status": "running",
        "city_id": city_id,
        "pid": proc.pid,
        "message": f"Simulation {sim_id} started for city {city_id}",
    }


@app.get("/api/simulations", response_model=List[Dict[str, Any]])
async def list_simulations(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List simulations (filtered by workspace access)."""
    user_workspaces = current_user["workspaces"]
    result = []
    for sim in SIMULATIONS.values():
        if sim["workspace_id"] in user_workspaces or current_user["role"] == "admin":
            entry = {k: sim[k] for k in sim if k != "pid"}
            entry["pid"] = sim.get("pid")
            result.append(entry)
    return sorted(result, key=lambda s: s["created_at"], reverse=True)


@app.get("/api/simulations/{sim_id}", response_model=Dict[str, Any])
async def get_simulation(
    sim_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    sim = SIMULATIONS.get(sim_id)
    if sim is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{sim_id}' not found")
    if sim["workspace_id"] not in current_user["workspaces"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied to this simulation")

    # Check if process is still running
    proc = ENGINE_PROCESSES.get(sim_id)
    if proc and sim["status"] == "running":
        poll = proc.poll()
        if poll is not None:
            sim["status"] = "completed"
            sim["completed_at"] = datetime.now(timezone.utc).isoformat()

    entry = {k: sim[k] for k in sim if k != "pid"}
    entry["pid"] = sim.get("pid")
    return entry


@app.delete("/api/simulations/{sim_id}", response_model=Dict[str, str])
async def delete_simulation(
    sim_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    sim = SIMULATIONS.get(sim_id)
    if sim is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{sim_id}' not found")
    if sim["workspace_id"] not in current_user["workspaces"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied to this simulation")

    proc = ENGINE_PROCESSES.get(sim_id)
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    if sim_id in ENGINE_PROCESSES:
        del ENGINE_PROCESSES[sim_id]
    if sim_id in SIMULATIONS:
        del SIMULATIONS[sim_id]

    return {"status": "deleted", "simulation_id": sim_id}


# ---------------------------------------------------------------------------
# What-If Scenario Engine
# ---------------------------------------------------------------------------

@app.post("/api/scenarios", response_model=Dict[str, Any])
async def create_scenario(
    base_simulation_id: str = Form(...),
    fork_tick: int = Form(0),
    signal_mode: Optional[str] = Form(None),
    incident_text: Optional[str] = Form(None),
    incident_edge_id: Optional[str] = Form(None),
    demand_scale: Optional[float] = Form(None),
    current_user: Dict[str, Any] = Depends(require_workspace_access("ws_default")),
) -> Dict[str, Any]:
    """Create a what-if scenario by forking a base simulation."""
    base = SIMULATIONS.get(base_simulation_id)
    if base is None:
        raise HTTPException(status_code=404, detail=f"Base simulation '{base_simulation_id}' not found")
    if base["workspace_id"] not in current_user["workspaces"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied to base simulation")

    scenario_id = f"sc_{uuid.uuid4().hex[:12]}"

    # Build mutated config from base
    mutated_config = dict(base["config"])
    if signal_mode is not None:
        mutated_config["signal_mode"] = signal_mode
    if demand_scale is not None:
        mutated_config["demand_scale"] = demand_scale

    scenario_config = {
        **mutated_config,
        "base_simulation_id": base_simulation_id,
        "fork_tick": fork_tick,
        "incident_text": incident_text,
        "incident_edge_id": incident_edge_id,
    }

    engine_args = _build_engine_args(base["city_id"], scenario_config)
    # Add scenario fork flag if engine supports it
    engine_args += ["--scenario-id", scenario_id, "--fork-tick", str(fork_tick)]

    try:
        proc = subprocess.Popen(
            [ENGINE_EXE] + engine_args,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f"Engine executable not found at {ENGINE_EXE}. Build first.",
        )

    ENGINE_PROCESSES[scenario_id] = proc

    now = datetime.now(timezone.utc).isoformat()
    SCENARIOS[scenario_id] = {
        "scenario_id": scenario_id,
        "workspace_id": base["workspace_id"],
        "base_simulation_id": base_simulation_id,
        "fork_tick": fork_tick,
        "mutations": {
            "signal_mode": signal_mode,
            "incident_text": incident_text,
            "incident_edge_id": incident_edge_id,
            "demand_scale": demand_scale,
        },
        "status": "running",
        "config": scenario_config,
        "created_at": now,
        "started_at": now,
        "completed_at": None,
        "pid": proc.pid,
        "comparison": None,
    }

    return {
        "scenario_id": scenario_id,
        "status": "running",
        "base_simulation_id": base_simulation_id,
        "message": f"Scenario {scenario_id} forked from {base_simulation_id}",
    }


@app.get("/api/scenarios", response_model=List[Dict[str, Any]])
async def list_scenarios(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    user_workspaces = current_user["workspaces"]
    result = []
    for sc in SCENARIOS.values():
        if sc["workspace_id"] in user_workspaces or current_user["role"] == "admin":
            entry = {k: sc[k] for k in sc if k != "pid"}
            entry["pid"] = sc.get("pid")
            result.append(entry)
    return sorted(result, key=lambda s: s["created_at"], reverse=True)


@app.get("/api/scenarios/{scenario_id}", response_model=Dict[str, Any])
async def get_scenario(
    scenario_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    sc = SCENARIOS.get(scenario_id)
    if sc is None:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    if sc["workspace_id"] not in current_user["workspaces"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied to this scenario")

    entry = {k: sc[k] for k in sc if k != "pid"}
    entry["pid"] = sc.get("pid")
    return entry


# ---------------------------------------------------------------------------
# Platform Services (algorithm registry, rate limiting, emissions, ingestion)
# ---------------------------------------------------------------------------

# Ephemeral simulation TTL (seconds). Engine processes and registry entries
# older than this are garbage-collected by the background task below.
SIMULATION_TTL_SECONDS = int(os.environ.get("NEXUSSIM_SIM_TTL_SECONDS", "86400"))
TTL_CHECK_INTERVAL_SECONDS = int(os.environ.get("NEXUSSIM_TTL_INTERVAL_SECONDS", "60"))


async def _garbage_collect_expired() -> None:
    """Background task: terminate engine processes and drop registry entries
    older than SIMULATION_TTL_SECONDS. Prevents resource leaks from abandoned runs."""
    while True:
        try:
            now = time.time()
            expired = []
            for sim_id, sim in list(SIMULATIONS.items()):
                started = sim.get("started_at")
                if not started:
                    continue
                try:
                    started_ts = datetime.fromisoformat(started).timestamp()
                except ValueError:
                    started_ts = now
                if now - started_ts > SIMULATION_TTL_SECONDS:
                    expired.append(sim_id)

            for sim_id in expired:
                proc = ENGINE_PROCESSES.get(sim_id)
                if proc and proc.poll() is None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=3)
                    except Exception:
                        proc.kill()
                SIMULATIONS.pop(sim_id, None)
                ENGINE_PROCESSES.pop(sim_id, None)
        except Exception as e:
            print(f"[TTL GC] error: {e}")
        await asyncio.sleep(TTL_CHECK_INTERVAL_SECONDS)


@app.on_event("startup")
async def _startup_gc() -> None:
    asyncio.create_task(_garbage_collect_expired())


@app.get("/api/platform/ttl")
async def get_ttl_config(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Return the TTL configuration and GC stats."""
    return {
        "ttl_seconds": SIMULATION_TTL_SECONDS,
        "ttl_interval_seconds": TTL_CHECK_INTERVAL_SECONDS,
        "active_simulations": len(SIMULATIONS),
        "active_scenarios": len(SCENARIOS),
        "active_engine_processes": len(ENGINE_PROCESSES),
    }


# ---- Scenario comparison --------------------------------------------------

@app.get("/api/simulations/{sim_id}/compare/{scenario_id}")
async def compare_simulation_scenario(
    sim_id: str,
    scenario_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Compare a baseline simulation against a forked scenario (KPI diff)."""
    base = SIMULATIONS.get(sim_id)
    sc = SCENARIOS.get(scenario_id)
    if base is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{sim_id}' not found")
    if sc is None:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    if base["workspace_id"] not in current_user["workspaces"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    baseline_kpis = base.get("kpi_snapshot") or {}
    scenario_kpis = sc.get("kpi_snapshot") or {}
    comparison = compare_kpis(baseline_kpis, scenario_kpis)

    # Persist comparison on the scenario for later retrieval
    sc["comparison"] = comparison
    return {
        "simulation_id": sim_id,
        "scenario_id": scenario_id,
        "comparison": comparison,
        "note": "KPI snapshots are recorded when a simulation completes; empty if still running.",
    }


# ---- Algorithm Registry ---------------------------------------------------

@app.get("/api/algo/registry")
async def list_registered_algorithms(
    discipline: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List marketplace-registered algorithms (in addition to the 48 built-ins)."""
    return algorithm_registry.list(discipline)


@app.post("/api/algo/register")
async def register_algorithm(
    algo_id: str = Form(...),
    name: str = Form(...),
    discipline: str = Form(...),
    version: str = Form(...),
    onnx_path: Optional[str] = Form(None),
    sidecar_url: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(require_role(["admin", "editor"])),
) -> Dict[str, Any]:
    """Register a new marketplace algorithm (versioned ONNX + sidecar)."""
    discipline = discipline.upper()
    if discipline not in ("CV", "SC", "NLP", "RL"):
        raise HTTPException(status_code=400, detail="discipline must be one of CV, SC, NLP, RL")
    existing = algorithm_registry.get(algo_id)
    if existing and existing.version == version:
        raise HTTPException(status_code=409, detail=f"Algorithm '{algo_id}' v{version} already registered")
    algo = RegisteredAlgorithm(
        algo_id=algo_id,
        name=name,
        discipline=discipline,
        version=version,
        onnx_path=onnx_path,
        sidecar_url=sidecar_url,
        author=author or current_user["username"],
        validation_status="pending",
    )
    algorithm_registry.register(algo)
    return {"status": "registered", "algo": algo.to_dict()}


@app.get("/api/algo/registry/{algo_id}")
async def get_registered_algorithm(
    algo_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    algo = algorithm_registry.get(algo_id)
    if algo is None:
        raise HTTPException(status_code=404, detail=f"Algorithm '{algo_id}' not registered")
    return algo.to_dict()


@app.post("/api/algo/registry/{algo_id}/validate")
async def validate_registered_algorithm(
    algo_id: str,
    status: str = Form(...),
    current_user: Dict[str, Any] = Depends(require_role(["admin"])),
) -> Dict[str, Any]:
    if status not in ("pending", "validated", "rejected"):
        raise HTTPException(status_code=400, detail="status must be pending, validated, or rejected")
    if not algorithm_registry.set_validation(algo_id, status):
        raise HTTPException(status_code=404, detail=f"Algorithm '{algo_id}' not registered")
    return {"status": "updated", "algo_id": algo_id, "validation_status": status}


# ---- Emissions & Carbon Accounting ---------------------------------------

@app.post("/api/emissions/estimate")
async def estimate_emissions_public(
    agent_type: str = Form("car"),
    distance_km: float = Form(...),
    idle_minutes: float = Form(0.0),
) -> Dict[str, Any]:
    """Public emissions estimate (pure computation, no side effects — used by
    the dashboard without auth). The authenticated /api/emissions is kept for
    API consumers that need auditability."""
    report = compute_emissions(agent_type, distance_km, idle_minutes)
    return report.to_dict()


@app.post("/api/emissions")
async def compute_emissions_endpoint(
    agent_type: str = Form("car"),
    distance_km: float = Form(...),
    idle_minutes: float = Form(0.0),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Estimate CO2/NOx/PM for a single agent over a distance + idle time."""
    report = compute_emissions(agent_type, distance_km, idle_minutes)
    return report.to_dict()


@app.post("/api/emissions/aggregate")
async def compute_emissions_aggregate(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Aggregate emissions for a list of agents. Body:
    {"agents": [{"agent_type": "car", "distance_km": 10.5, "idle_minutes": 2.0}, ...]}
    """
    body = await request.json()
    agents = body.get("agents", [])
    if not isinstance(agents, list):
        raise HTTPException(status_code=400, detail="body must contain an 'agents' array")
    reports = []
    for a in agents:
        reports.append(compute_emissions(
            a.get("agent_type", "car"),
            float(a.get("distance_km", 0.0)),
            float(a.get("idle_minutes", 0.0)),
        ))
    return aggregate_emissions(reports)


# ---- Real-Time Ingestion --------------------------------------------------

@app.post("/api/ingest/{feed_type}")
async def ingest_realtime(
    feed_type: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_role(["admin", "editor"])),
) -> Dict[str, Any]:
    """Normalize a real-time feed message (gtfs/cv2x/mqtt/weather) and forward
    it to the cross-subject event bus."""
    raw = await request.json()
    try:
        event = realtime_ingestion.normalize(feed_type, raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Forward to the event bus sidecar best-effort
    published = False
    try:
        async with httpx.AsyncClient(timeout=2.0, verify=False) as client:
            resp = await client.post(
                f"{EVENT_BUS_HTTP_URL}/publish/{event['topic']}",
                json=event["payload"],
            )
            published = resp.status_code == 200
    except Exception:
        published = False

    return {"status": "ingested" if published else "ingested_unpublished", "event": event}


@app.get("/api/ingest/feeds")
async def list_ingestion_feeds(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List supported real-time ingestion feed types and their event bus topics."""
    return {
        "feeds": [
            {"feed_type": ft, "topic": topic}
            for ft, topic in realtime_ingestion.TOPIC_MAP.items()
        ]
    }


# ---- Rate limiting stats --------------------------------------------------

@app.get("/api/platform/rate-limit")
async def get_rate_limit_stats(
    current_user: Dict[str, Any] = Depends(require_role(["admin"])),
) -> Dict[str, Any]:
    """Return rate limiter statistics (admin only)."""
    return rate_limiter.stats()


# ---------------------------------------------------------------------------
# Health & Status Endpoint
# ---------------------------------------------------------------------------

@app.get("/")
@app.get("/health")
@app.get("/api/health")
async def gateway_health() -> Dict[str, Any]:
    services: Dict[str, Any] = {
        "gateway": {"status": "ok", "port": GATEWAY_PORT},
        "engine": {"url": ENGINE_WS_URL, "status": "configured"},
        "camera": {"url": CAMERA_HTTP_URL, "status": "unknown"},
        "nlp": {"url": NLP_HTTP_URL, "status": "unknown"},
        "event_bus": {"url": EVENT_BUS_HTTP_URL, "status": "unknown"},
        "algo_explorer": {"url": ALGO_HTTP_URL, "status": "unknown"},
    }

    async with httpx.AsyncClient(timeout=1.0, verify=False) as client:
        for name, base_url in [
            ("camera", CAMERA_HTTP_URL),
            ("nlp", NLP_HTTP_URL),
            ("event_bus", EVENT_BUS_HTTP_URL),
            ("algo_explorer", ALGO_HTTP_URL),
        ]:
            try:
                r = await client.get(f"{base_url}/health")
                services[name]["status"] = "healthy" if r.status_code == 200 else f"http_{r.status_code}"
            except Exception:
                services[name]["status"] = "offline"

    # Add simulation service health
    services["simulation_service"] = {
        "status": "ok",
        "active_simulations": len([s for s in SIMULATIONS.values() if s["status"] == "running"]),
        "total_simulations": len(SIMULATIONS),
        "active_scenarios": len([s for s in SCENARIOS.values() if s["status"] == "running"]),
    }

    return {
        "gateway": "NexusSim Unified Backend",
        "port": GATEWAY_PORT,
        "services": services,
    }


# ---------------------------------------------------------------------------
# Generic HTTP Proxy Helper
# ---------------------------------------------------------------------------

async def _proxy_http(request: Request, target_url: str) -> Response:
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
        try:
            req = client.build_request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=request.query_params,
                content=body,
            )
            resp = await client.send(req)
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                media_type=resp.headers.get("content-type"),
            )
        except httpx.ConnectError:
            return Response(
                content=b'{"error": "Upstream microservice offline", "target": "%s"}' % target_url.encode(),
                status_code=503,
                media_type="application/json",
            )
        except Exception as e:
            return Response(
                content=f'{{"error": "Gateway proxy error: {str(e)}"}}'.encode(),
                status_code=502,
                media_type="application/json",
            )


# ---------------------------------------------------------------------------
# Service REST Routes
# ---------------------------------------------------------------------------

@app.api_route("/api/chat", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/chat", methods=["GET", "POST", "OPTIONS"])
async def proxy_chat(request: Request) -> Response:
    return await _proxy_http(request, f"{NLP_HTTP_URL}/chat")


@app.api_route("/api/incident", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/incident", methods=["GET", "POST", "OPTIONS"])
async def proxy_incident(request: Request) -> Response:
    return await _proxy_http(request, f"{NLP_HTTP_URL}/incident")


@app.api_route("/api/camera/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def proxy_camera(path: str, request: Request) -> Response:
    return await _proxy_http(request, f"{CAMERA_HTTP_URL}/api/camera/{path}")


@app.api_route("/api/events/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def proxy_events_rest(path: str, request: Request) -> Response:
    return await _proxy_http(request, f"{EVENT_BUS_HTTP_URL}/{path}")


@app.api_route("/api/algo/{path:path}", methods=["GET", "OPTIONS"])
async def proxy_algo(path: str, request: Request) -> Response:
    return await _proxy_http(request, f"{ALGO_HTTP_URL}/{path}")


@app.api_route("/api/algo", methods=["GET", "OPTIONS"])
async def proxy_algo_root(request: Request) -> Response:
    return await _proxy_http(request, f"{ALGO_HTTP_URL}/algorithms")


# ---------------------------------------------------------------------------
# WebSocket Proxies (C++ Engine & Event Bus)
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def proxy_engine_ws(client_ws: WebSocket) -> None:
    await client_ws.accept()
    try:
        async with websockets.connect(ENGINE_WS_URL, max_size=10 * 1024 * 1024, ssl=_SSL_CTX) as server_ws:
            async def forward_client_to_server():
                try:
                    while True:
                        msg = await client_ws.receive()
                        if "text" in msg and msg["text"]:
                            await server_ws.send(msg["text"])
                        elif "bytes" in msg and msg["bytes"]:
                            await server_ws.send(msg["bytes"])
                except (WebSocketDisconnect, asyncio.CancelledError):
                    pass

            async def forward_server_to_client():
                try:
                    async for msg in server_ws:
                        if isinstance(msg, bytes):
                            await client_ws.send_bytes(msg)
                        else:
                            await client_ws.send_text(msg)
                except (WebSocketDisconnect, asyncio.CancelledError):
                    pass

            await asyncio.gather(
                forward_client_to_server(),
                forward_server_to_client(),
                return_exceptions=True,
            )
    except Exception as e:
        await client_ws.close(code=1011, reason=f"Upstream Engine offline: {str(e)[:50]}")


@app.websocket("/ws/events")
async def proxy_event_bus_ws(client_ws: WebSocket) -> None:
    await client_ws.accept()
    try:
        async with websockets.connect(EVENT_BUS_WS_URL, ssl=_SSL_CTX) as server_ws:
            async def forward_client():
                try:
                    while True:
                        msg = await client_ws.receive_text()
                        await server_ws.send(msg)
                except (WebSocketDisconnect, asyncio.CancelledError):
                    pass

            async def forward_server():
                try:
                    async for msg in server_ws:
                        await client_ws.send_text(msg)
                except (WebSocketDisconnect, asyncio.CancelledError):
                    pass

            await asyncio.gather(forward_client(), forward_server(), return_exceptions=True)
    except Exception as e:
        await client_ws.close(code=1011, reason=f"Event bus offline: {str(e)[:50]}")


def main():
    print(f"Starting NexusSim Unified Backend Gateway on port {GATEWAY_PORT}...")
    ssl_cert = os.environ.get("SSL_CERT", "certs/server.crt")
    ssl_key = os.environ.get("SSL_KEY", "certs/server.key")
    ssl_kwargs = {}
    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        ssl_kwargs = {"ssl_certfile": ssl_cert, "ssl_keyfile": ssl_key}
        print(f"TLS enabled: {ssl_cert}")
    else:
        print("WARNING: certs/server.{crt,key} not found; serving plain HTTP")
    uvicorn.run("gateway.server:app", host="0.0.0.0", port=GATEWAY_PORT,
                reload=False, log_level="info", **ssl_kwargs)


if __name__ == "__main__":
    main()
