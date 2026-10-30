"""NexusTwin Dynamic Ingestion API Router.

Exposes REST and SSE endpoints for:
- Stage 1: Drag-and-drop file ingestion (/api/v1/twin/upload)
- Stage 2: Global geocoded search ingestion (/api/v1/twin/search)
- Real-time progress tracking (/api/v1/twin/progress/{job_id})
- Dynamic city catalog (/api/v1/twin/cities)
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# Ensure pipeline/src is in sys.path
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PIPELINE_SRC = os.path.join(_REPO_ROOT, "pipeline", "src")
if _PIPELINE_SRC not in sys.path:
    sys.path.insert(0, _PIPELINE_SRC)

try:
    from pipeline.src.dynamic_ingest import DynamicIngestionWorker  # type: ignore
except ImportError:
    from dynamic_ingest import DynamicIngestionWorker  # type: ignore

router = APIRouter(prefix="/api/v1/twin", tags=["NexusTwin Digital Twin"])

# In-memory storage for asynchronous ingestion jobs
INGESTION_JOBS: Dict[str, Dict[str, Any]] = {}
DATA_ROOT = os.path.join(_REPO_ROOT, "data")
worker = DynamicIngestionWorker(data_root=DATA_ROOT)


class SearchIngestRequest(BaseModel):
    query: str = Field(..., description="Free-text location or city name (e.g. 'Shantigram, Ahmedabad')")
    workspace_id: Optional[str] = Field("default", description="Workspace tenant identifier")
    city_id: Optional[str] = Field(None, description="Optional custom city slug")


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    stage: str
    progress_pct: int
    message: str
    elapsed_seconds: float
    metrics: Dict[str, Any]
    error: Optional[str] = None


def _update_job(job_id: str, payload: Dict[str, Any]) -> None:
    if job_id in INGESTION_JOBS:
        job = INGESTION_JOBS[job_id]
        job.update(payload)
        job["elapsed_seconds"] = round(time.time() - job["start_time"], 2)


def _run_search_job(job_id: str, query: str, workspace_id: str, city_id: Optional[str]) -> None:
    def progress_cb(event: Dict[str, Any]) -> None:
        _update_job(job_id, {
            "stage": event.get("stage", "PROCESSING"),
            "progress_pct": event.get("progress_pct", 0),
            "message": event.get("message", ""),
            "metrics": event.get("metrics", {}),
            "error": event.get("error"),
        })

    try:
        res = worker.ingest_query(
            query=query,
            city_id=city_id,
            workspace_id=workspace_id,
            progress_cb=progress_cb,
        )
        _update_job(job_id, {
            "status": "completed",
            "stage": "COMPLETE",
            "progress_pct": 100,
            "message": f"City '{res['city_name']}' ready for simulation",
            "result": res,
        })
    except Exception as e:
        _update_job(job_id, {
            "status": "failed",
            "stage": "ERROR",
            "message": f"Ingestion failed: {str(e)}",
            "error": str(e),
        })


def _run_file_job(job_id: str, file_path: str, city_id: Optional[str], city_name: Optional[str], workspace_id: str) -> None:
    def progress_cb(event: Dict[str, Any]) -> None:
        _update_job(job_id, {
            "stage": event.get("stage", "PROCESSING"),
            "progress_pct": event.get("progress_pct", 0),
            "message": event.get("message", ""),
            "metrics": event.get("metrics", {}),
            "error": event.get("error"),
        })

    try:
        res = worker.ingest_file(
            file_path=file_path,
            city_id=city_id,
            city_name=city_name,
            workspace_id=workspace_id,
            progress_cb=progress_cb,
        )
        _update_job(job_id, {
            "status": "completed",
            "stage": "COMPLETE",
            "progress_pct": 100,
            "message": f"City '{res['city_name']}' ready for simulation",
            "result": res,
        })
    except Exception as e:
        _update_job(job_id, {
            "status": "failed",
            "stage": "ERROR",
            "message": f"File ingestion failed: {str(e)}",
            "error": str(e),
        })
    finally:
        # Clean up temporary upload file if in temp directory
        if "temp" in file_path.lower() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


@router.post("/search", response_model=Dict[str, Any])
async def search_and_ingest(req: SearchIngestRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Stage 2: Initiate Overpass-based global search & dynamic twin synthesis."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Search query must not be empty")

    job_id = f"twin_search_{uuid.uuid4().hex[:8]}"
    INGESTION_JOBS[job_id] = {
        "job_id": job_id,
        "type": "search",
        "query": req.query,
        "workspace_id": req.workspace_id or "default",
        "status": "queued",
        "stage": "INITIALIZING",
        "progress_pct": 0,
        "message": f"Queued digital twin synthesis for '{req.query}'",
        "start_time": time.time(),
        "elapsed_seconds": 0.0,
        "metrics": {},
        "error": None,
        "result": None,
    }

    background_tasks.add_task(_run_search_job, job_id, req.query, req.workspace_id or "default", req.city_id)

    return {
        "job_id": job_id,
        "status": "queued",
        "query": req.query,
        "stream_url": f"/api/v1/twin/progress/{job_id}",
    }


@router.post("/upload", response_model=Dict[str, Any])
async def upload_and_ingest(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    city_id: Optional[str] = Form(None),
    city_name: Optional[str] = Form(None),
    workspace_id: Optional[str] = Form("default"),
) -> Dict[str, Any]:
    """Stage 1: Upload an .osm, .pbf, or .graphml file and trigger asynchronous ingestion."""
    filename = file.filename or "upload.osm"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".osm", ".pbf", ".graphml", ".xml"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Must be .osm, .pbf, or .graphml",
        )

    temp_dir = tempfile.mkdtemp(prefix="twin_upload_")
    temp_path = os.path.join(temp_dir, filename)

    with open(temp_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    job_id = f"twin_upload_{uuid.uuid4().hex[:8]}"
    INGESTION_JOBS[job_id] = {
        "job_id": job_id,
        "type": "file",
        "filename": filename,
        "workspace_id": workspace_id or "default",
        "status": "queued",
        "stage": "FILE_UPLOADED",
        "progress_pct": 5,
        "message": f"Received '{filename}', queuing pipeline processing",
        "start_time": time.time(),
        "elapsed_seconds": 0.0,
        "metrics": {},
        "error": None,
        "result": None,
    }

    background_tasks.add_task(
        _run_file_job,
        job_id,
        temp_path,
        city_id,
        city_name,
        workspace_id or "default",
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "filename": filename,
        "stream_url": f"/api/v1/twin/progress/{job_id}",
    }


@router.get("/progress/{job_id}")
async def get_progress(job_id: str, request: Request) -> Any:
    """Retrieve current progress. Supports Server-Sent Events (SSE) or JSON polling."""
    if job_id not in INGESTION_JOBS:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    # If client requests SSE stream
    accept = request.headers.get("accept", "")
    if "text/event-stream" in accept:
        async def event_generator():
            while True:
                if job_id not in INGESTION_JOBS:
                    break
                job = INGESTION_JOBS[job_id]
                job["elapsed_seconds"] = round(time.time() - job["start_time"], 2)
                yield f"data: {json.dumps(job)}\n\n"
                if job["status"] in {"completed", "failed"}:
                    break
                await asyncio.sleep(0.5)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    job = INGESTION_JOBS[job_id]
    job["elapsed_seconds"] = round(time.time() - job["start_time"], 2)
    return job


@router.get("/cities", response_model=List[Dict[str, Any]])
async def list_twin_cities() -> List[Dict[str, Any]]:
    """List all synthesized digital twin cities."""
    results = []
    if not os.path.exists(DATA_ROOT):
        return results

    for item in os.listdir(DATA_ROOT):
        cdir = os.path.join(DATA_ROOT, item)
        if os.path.isdir(cdir):
            meta_path = os.path.join(cdir, "metadata.json")
            graph_path = os.path.join(cdir, "graph.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        results.append(json.load(f))
                except Exception:
                    pass
            elif os.path.exists(graph_path):
                # Legacy or basic directory
                results.append({
                    "city_id": item,
                    "city_name": item.replace("-", " ").title(),
                    "status": "ready",
                    "source": "precomputed",
                })

    return results


@router.delete("/cities/{city_id}")
async def delete_twin_city(city_id: str) -> Dict[str, Any]:
    """Delete a dynamically generated twin city."""
    if ".." in city_id or "/" in city_id or "\\" in city_id:
        raise HTTPException(status_code=400, detail="Invalid city_id")

    cdir = os.path.join(DATA_ROOT, city_id)
    if not os.path.exists(cdir):
        raise HTTPException(status_code=404, detail=f"City '{city_id}' not found")

    shutil.rmtree(cdir, ignore_errors=True)

    # Clean up entry in pipeline/cities.yaml if present
    cities_yaml = os.path.join(_REPO_ROOT, "pipeline", "cities.yaml")
    if os.path.exists(cities_yaml):
        try:
            import yaml
            with open(cities_yaml, "r", encoding="utf-8") as f:
                cfgs = yaml.safe_load(f) or {}
            if city_id in cfgs:
                del cfgs[city_id]
                with open(cities_yaml, "w", encoding="utf-8") as f:
                    yaml.dump(cfgs, f, sort_keys=True)
        except Exception:
            pass

    return {"status": "deleted", "city_id": city_id}
