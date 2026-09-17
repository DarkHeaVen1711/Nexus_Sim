"""Phase 15 - Synthetic Virtual Camera Sidecar Service (Port 9003).

Provides REST/WebSocket API endpoints serving annotated camera feed frames
and bounding box vehicle detection counts to the dashboard.
"""

import os
import sys
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

here = os.path.dirname(os.path.abspath(__file__))
if here not in sys.path:
    sys.path.insert(0, here)

from virtual_camera import VirtualCamera

app = FastAPI(title="NexusSim Virtual Camera Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

camera = VirtualCamera(width=480, height=320)


@app.get("/health")
def health():
    return {"status": "ok", "service": "virtual_camera", "port": 9003}


@app.get("/api/camera/feed")
def get_camera_feed(agent_count: int = 35):
    """Return top-down annotated camera feed frame with OpenCV detection counts."""
    result = camera.render_and_detect(agent_count=agent_count)
    result["timestamp"] = time.time()
    return result


def main():
    print("Starting Virtual Camera Sidecar Service on port 9003...")
    uvicorn.run(app, host="0.0.0.0", port=9003, log_level="info")


if __name__ == "__main__":
    main()
