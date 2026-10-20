"""Unified Backend API Gateway for NexusSim (Port 8000).

Consolidates all internal backend microservices under a single entry point:
- C++ Simulation Engine (Port 9001)        -> /ws
- Virtual Camera Service (Port 9003)      -> /api/camera/*
- NLP Chat & Incident Service (Port 9004) -> /api/chat, /api/incident
- Cross-Subject Event Bus (Port 9005)     -> /ws/events, /api/events/*
- Algo Explorer Catalog (Port 9006)       -> /api/algo/*
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import yaml
from typing import Any, Dict, List, Optional

# Ensure the repo root is on sys.path so uvicorn can import "gateway.server"
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
import ssl
import websockets

# Trust the local self-signed cert for ALL upstream connections (the
# sidecars and engine serve TLS with certs/server.{crt,key}).
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

app = FastAPI(
    title="NexusSim Unified Backend Gateway",
    description="Single-port API Gateway routing to Engine, NLP, CV, Event Bus, and Algo Explorer services.",
    version="1.0.0",
)

# Enable CORS for frontend dashboard (port 3000)
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
# City Registry (dynamic city onboarding)
# ---------------------------------------------------------------------------

# Root of the repo (gateway/ is at <repo>/gateway, so data/ is <repo>/data/)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
CITIES_YAML = os.path.join(REPO_ROOT, "pipeline", "cities.yaml")

# Ensure data dir exists
os.makedirs(DATA_DIR, exist_ok=True)


def _load_cities_yaml() -> Dict[str, Any]:
    """Load cities.yaml if it exists."""
    if os.path.exists(CITIES_YAML):
        with open(CITIES_YAML, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_cities_yaml(config: Dict[str, Any]) -> None:
    """Persist cities.yaml with a new city entry."""
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
    """Build a city entry by scanning the data directory for graph.json."""
    city_dir = os.path.join(DATA_DIR, city_id)
    graph_json = os.path.join(city_dir, "graph.json")
    if not os.path.isdir(city_dir) or not os.path.exists(graph_json):
        return None

    # Try to load metadata from graph.json if available
    node_count = 0
    edge_count = 0
    try:
        import json
        with open(graph_json, "r") as f:
            graph = json.load(f)
        node_count = len(graph.get("nodes", []))
        edge_count = len(graph.get("edges", []))
    except Exception:
        pass

    # Check if it's also in cities.yaml
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
    """List all known cities: from cities.yaml and from data/ directories."""
    cities: Dict[str, Dict[str, Any]] = {}

    # Start with cities.yaml entries
    yaml_config = _load_cities_yaml()
    for city_id, cfg in yaml_config.items():
        cities[city_id] = _city_entry_from_yaml(city_id, cfg)

    # Add / override with data/ directory entries (uploads)
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
    """Get a single city by id."""
    for c in list_cities():
        if c["city_id"] == city_id:
            return c
    return None


# ---------------------------------------------------------------------------
# Health & Status Endpoint
# ---------------------------------------------------------------------------

@app.get("/")
@app.get("/health")
@app.get("/api/health")
async def gateway_health() -> Dict[str, Any]:
    """Aggregated health status of the unified gateway and internal services."""
    services: Dict[str, Any] = {
        "gateway": {"status": "ok", "port": GATEWAY_PORT},
        "engine": {"url": ENGINE_WS_URL, "status": "configured"},
        "camera": {"url": CAMERA_HTTP_URL, "status": "unknown"},
        "nlp": {"url": NLP_HTTP_URL, "status": "unknown"},
        "event_bus": {"url": EVENT_BUS_HTTP_URL, "status": "unknown"},
        "algo_explorer": {"url": ALGO_HTTP_URL, "status": "unknown"},
    }

    # Ping HTTP sidecars asynchronously
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

    return {
        "gateway": "NexusSim Unified Backend",
        "port": GATEWAY_PORT,
        "services": services,
    }


# ---------------------------------------------------------------------------
# City Management Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/cities", response_model=List[Dict[str, Any]])
async def list_cities_endpoint() -> List[Dict[str, Any]]:
    """List all cities available for simulation (configured + uploaded)."""
    return list_cities()


@app.get("/api/cities/{city_id}", response_model=Dict[str, Any])
async def get_city_endpoint(city_id: str) -> Dict[str, Any]:
    """Get details for a specific city."""
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
    """Upload an OSM file (.osm, .osm.pbf, .graphml) and run the import pipeline.

    The file is saved to data/<city_id>/raw.<ext>, then clean.py and export.py
    are invoked to produce data/<city_id>/graph.json for the engine.
    """
    import tempfile

    # Validate extension
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".osm", ".pbf", ".graphml"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Expected .osm, .osm.pbf, or .graphml",
        )

    # Determine city_id
    if city_id is None:
        # Derive from filename
        import re as _re
        city_id = _re.sub(r"[^a-z0-9]+", "-", filename.lower()).strip("-") or "city"

    # Validate city_id doesn't contain path traversal
    if ".." in city_id or "/" in city_id or "\\" in city_id:
        raise HTTPException(status_code=400, detail="Invalid city_id")

    # Save uploaded file to a temp location first
    city_dir = os.path.join(DATA_DIR, city_id)
    os.makedirs(city_dir, exist_ok=True)

    # Save uploaded file
    raw_filename = f"raw{ext}"
    saved_path = os.path.join(city_dir, raw_filename)
    try:
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    # Run the import pipeline
    try:
        # Add pipeline/src to path for import_osm
        sys.path.insert(0, os.path.join(REPO_ROOT, "pipeline", "src"))
        from import_osm import import_osm  # type: ignore

        result = import_osm(
            source_path=saved_path,
            city_id=city_id,
            city_name=city_name,
            out_dir=city_dir,
        )
    except Exception as e:
        # Clean up on failure
        import shutil as _shutil
        if os.path.exists(city_dir):
            _shutil.rmtree(city_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

    # Update cities.yaml with the new city entry
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
        # Non-fatal: the city still works from data/ scan
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

# 1. NLP Chat & Incident Service (port 9004)
@app.api_route("/api/chat", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/chat", methods=["GET", "POST", "OPTIONS"])
async def proxy_chat(request: Request) -> Response:
    return await _proxy_http(request, f"{NLP_HTTP_URL}/chat")


@app.api_route("/api/incident", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/incident", methods=["GET", "POST", "OPTIONS"])
async def proxy_incident(request: Request) -> Response:
    return await _proxy_http(request, f"{NLP_HTTP_URL}/incident")


# 2. Virtual Camera Service (port 9003)
@app.api_route("/api/camera/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def proxy_camera(path: str, request: Request) -> Response:
    return await _proxy_http(request, f"{CAMERA_HTTP_URL}/api/camera/{path}")


# 3. Cross-Subject Event Bus REST (port 9005)
@app.api_route("/api/events/{path:path}", methods=["GET", "POST", "OPTIONS"])
async def proxy_events_rest(path: str, request: Request) -> Response:
    return await _proxy_http(request, f"{EVENT_BUS_HTTP_URL}/{path}")


# 4. Algo Explorer Service (port 9006)
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
    """Bidirectional WebSocket proxy to C++ Simulation Engine (port 9001)."""
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
    """Bidirectional WebSocket proxy to Cross-Subject Event Bus (port 9005)."""
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
    # HTTPS by default: serve TLS when certs are present (certs/ is generated
    # by scripts/gen_certs.sh; override with SSL_CERT/SSL_KEY env vars).
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
