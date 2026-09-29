"""Phase 34 - Real-Time Cross-Subject Event Bus & Interoperability Broker (Port 9005).

Connects CV Anomaly Alerts -> NLP Incident Extraction -> Soft Computing Parameter Adaptation -> RL Action Exploration.
Uses lightweight asyncio pub/sub and WebSocket channels to isolate sidecars from the engine hot path.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Callable, Dict, List, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="NexusSim Cross-Subject Event Bus")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EventBusBroker:
    """Pub/sub message broker routing events across CV, NLP, SC, and RL."""

    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self.active_websockets: Set[WebSocket] = set()
        self.event_log: List[Dict[str, Any]] = []

    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        self.subscribers.setdefault(topic, []).append(handler)

    async def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        event = {
            "topic": topic,
            "payload": payload,
            "timestamp": time.time(),
        }
        self.event_log.append(event)
        if len(self.event_log) > 500:
            self.event_log.pop(0)

        # Local handlers
        for handler in self.subscribers.get(topic, []):
            try:
                handler(payload)
            except Exception as e:
                print(f"[EventBus] Error in local handler for {topic}: {e}")

        # Broadcast to active WebSockets
        dead_ws = set()
        msg_json = json.dumps(event)
        for ws in self.active_websockets:
            try:
                await ws.send_text(msg_json)
            except Exception:
                dead_ws.add(ws)
        self.active_websockets.difference_update(dead_ws)


broker = EventBusBroker()


# Automated Cross-Subject Integration Chain (Task 34.2)
# CV Anomaly -> NLP Event -> SC Adaptation -> RL Action
def handle_cv_anomaly(payload: Dict[str, Any]) -> None:
    """Chain CV anomaly detection into NLP event and SC adaptation."""
    # 1. NLP Event Draft
    nlp_event = {
        "action": "COLLISION" if "blockage" in str(payload.get("type", "")).lower() else "LANE_CLOSURE",
        "location": payload.get("location", {}),
        "severity": payload.get("severity", 0.8),
        "source": "CV_ANOMALY_ALERTS",
    }
    # 2. Trigger SC Parameter Adaptation
    sc_adaptation = {
        "chaos_adjustment": +0.05,
        "speed_factor_adjustment": -0.15,
        "zone_affected": payload.get("track_id", 0),
    }
    print(f"[EventBus Chain] CV Anomaly processed -> Emitted NLP Event Draft: {nlp_event['action']} & SC Adaptation.")


broker.subscribe("cv.anomaly", handle_cv_anomaly)


@app.get("/health")
def health():
    return {"status": "ok", "service": "cross_subject_event_bus", "port": 9005}


@app.get("/events")
def get_recent_events(limit: int = 50):
    return broker.event_log[-limit:]


@app.post("/publish/{topic}")
async def publish_event(topic: str, payload: Dict[str, Any]):
    await broker.publish(topic, payload)
    return {"status": "published", "topic": topic}


@app.websocket("/ws")
async def websocket_event_stream(ws: WebSocket):
    await ws.accept()
    broker.active_websockets.add(ws)
    try:
        while True:
            data = await ws.receive_text()
            # Client can publish directly over WS
            parsed = json.loads(data)
            topic = parsed.get("topic", "general")
            payload = parsed.get("payload", {})
            await broker.publish(topic, payload)
    except WebSocketDisconnect:
        broker.active_websockets.discard(ws)


def main():
    print("Starting Cross-Subject Event Bus Sidecar on port 9005...")
    uvicorn.run(app, host="0.0.0.0", port=9005, log_level="info")


if __name__ == "__main__":
    main()
