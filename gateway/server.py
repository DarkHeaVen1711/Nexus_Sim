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
import sys
from typing import Any, Dict

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
import websockets

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
ENGINE_WS_URL = os.environ.get("ENGINE_WS_URL", "ws://127.0.0.1:9001")
CAMERA_HTTP_URL = os.environ.get("CAMERA_HTTP_URL", "http://127.0.0.1:9003")
NLP_HTTP_URL = os.environ.get("NLP_HTTP_URL", "http://127.0.0.1:9004")
EVENT_BUS_HTTP_URL = os.environ.get("EVENT_BUS_HTTP_URL", "http://127.0.0.1:9005")
EVENT_BUS_WS_URL = os.environ.get("EVENT_BUS_WS_URL", "ws://127.0.0.1:9005/ws/events")
ALGO_HTTP_URL = os.environ.get("ALGO_HTTP_URL", "http://127.0.0.1:9006")

GATEWAY_PORT = int(os.environ.get("GATEWAY_PORT", "8000"))


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
    async with httpx.AsyncClient(timeout=1.0) as client:
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
# Generic HTTP Proxy Helper
# ---------------------------------------------------------------------------

async def _proxy_http(request: Request, target_url: str) -> Response:
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    async with httpx.AsyncClient(timeout=10.0) as client:
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
        async with websockets.connect(ENGINE_WS_URL, max_size=10 * 1024 * 1024) as server_ws:
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
        async with websockets.connect(EVENT_BUS_WS_URL) as server_ws:
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
    uvicorn.run("gateway.server:app", host="0.0.0.0", port=GATEWAY_PORT, reload=False, log_level="info")


if __name__ == "__main__":
    main()
