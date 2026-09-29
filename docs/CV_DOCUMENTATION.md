# Computer Vision (CV) — NexusSim Documentation

---

## Subject Overview

The Computer Vision subsystem provides two complementary CV pipelines for NexusSim: a real-world road congestion classifier that processes traffic-tile imagery from ToS-compliant map APIs, and a synthetic virtual camera that renders and analyzes a live top-down view of the simulation itself. Together, these demonstrate classical computer vision techniques (HSV thresholding, contour/blob detection, color segmentation) alongside learned methods (CNN classification), all integrated with the simulation engine through independent sidecar processes.

**Key references:** `docs/TEAM_IMPLEMENTATION_PLAN.md` (Phases 14–15, 25–27), `docs/PRD.md` G8/G9, `docs/TRD.md` §4.3 (TR-ML-08, TR-PIPE-08).

---

## Role in Project

The CV subsystem serves three critical roles in NexusSim:

1. **Real-world sensing signal:** Classifies actual road congestion from Mapbox Traffic Tiles or TomTom Traffic Flow imagery, providing an external validation signal that feeds into the Soft Computing GA calibration (FR-9) as an additional fitness term—bridging real-world observation with simulation tuning.
2. **Demo demonstration feature:** The synthetic virtual camera renders a live top-down view from the simulation's own agent stream and runs genuine OpenCV detection/counting on the rendered pixels—demonstrating CV techniques applied to the simulation's own output without touching the control path.
3. **Academic breadth:** Provides the "classical vs. learned" comparison story central to CV coursework (FR-11), with both a threshold-based and a CNN-based classifier evaluated against hand-labeled validation data.

**TRD traceability:** TR-ML-08 (virtual camera), TR-PIPE-08 (CV congestion classification), TR-DASH-07 (CV overlay), TR-DASH-08 (virtual camera panel).

---

## Objectives

| ID | Objective | Phase(s) | Status | Acceptance Criteria |
|----|-----------|----------|--------|---------------------|
| O-CV-1 | Add `cv_bbox` per-city key to `cities.yaml` (lat/lon bounding box for tile capture) | 14.1 | DONE | Config-driven per-city convention (TR-7) |
| O-CV-2 | Write `pipeline/src/cv_congestion.py`: fetch traffic-flow tiles via Mapbox Traffic Tiles or TomTom Traffic Flow API (ToS-compliant, API key via env var) | 14.2 | DONE | Module docstring documents compliance; key never committed (NFR-6, BR-6) |
| O-CV-3 | Classical CV: HSV color-threshold bucketing of road-colored pixels → congestion_level 0–3 | 14.3 | DONE | No training data required; primary/production path |
| O-CV-4 | CNN comparison: small custom CNN or fine-tuned ResNet-18 (4-class) on hand-labeled tile crops | 14.4 | DONE | "Classical vs. learned" comparison for coursework |
| O-CV-5 | Write `data/<city>/cv_congestion.json` (`{zone_id: {hour: {level, confidence, source}}}`) | 14.5 | DONE | Consumed by GA (Phase 13) and potentially RL reward shaping |
| O-CV-6 | Wire `cv_congestion.json` into GA as additional fitness term (sim zone wait/speed vs. CV-observed level) | 14.6 | DONE | Blended with MAPE; weight documented |
| O-CV-7 | Dashboard: `CongestionCVOverlay.tsx` — zone bubbles colored by CV-observed congestion level | 14.7 | DONE | Static per-hour data, not live-streamed (TR-DASH-07) |
| O-CV-8 | `ml/cv/virtual_camera.py`: WS client on engine stream; rasterize top-down frame (roads from `graph.json`, agents as colored shapes) | 15.1 | DONE | Reuses `{"type":"bounds"}` message as viewport client (TR-ML-08) |
| O-CV-9 | OpenCV contour/blob detection + color segmentation on rendered frame → bounding boxes + count | 15.2 | DONE | Detecting on rendered pixels, not reading state directly |
| O-CV-10 | `ml/cv/virtual_camera_service.py`: FastAPI/websockets server (port 9003), streams annotated PNG + count JSON at ~1 Hz | 15.3 | DONE | Independent process; no engine changes (TR-6) |
| O-CV-11 | Dashboard: `VirtualCameraPanel.tsx` — displays live annotated feed | 15.4 | DONE | Polls service, not engine directly (TR-DASH-08) |
| O-CV-12 | Accuracy sanity check: detected count vs. ground-truth agent count in view, logged as running error % | 15.5 | DONE | Documents detection reliability |

---

## Current Implementation

### Status: IMPLEMENTED (Phases 14, 15, 25)

The CV subsystem is implemented across `pipeline/src/cv_congestion.py` (Phase 14), `ml/cv/virtual_camera.py` and `ml/cv/virtual_camera_service.py` (Phase 15), and `ml/cv/yolo_detector.py` (Phase 25).

### Pipeline A: Real-World Congestion Classification (Phase 14)

**Data flow:**

```
Mapbox/TomTom API ──→ cv_congestion.py ──→ cv_congestion.json ──→ GA (Phase 13)
                         │                                          │
                    Classical HSV                              Additional
                    thresholding                              fitness term
                         │
                    CNN comparison
                    (hand-labeled set)
```

**Classical pipeline (Phase 14.3):**

| Step | Operation | Details |
|------|-----------|---------|
| 1 | Fetch traffic tiles | Mapbox Traffic Tiles API or TomTom Traffic Flow API; tile coordinates from `cv_bbox` in `cities.yaml` |
| 2 | Convert to HSV | OpenCV `cvtColor(frame, COLOR_BGR2HSV)` |
| 3 | Road mask | Segment road-colored pixels (gray/asphalt range in HSV) |
| 4 | Congestion threshold | Count red/orange pixels within road mask → bucket into levels 0–3 (free-flow, light, moderate, heavy) |
| 5 | Per-zone aggregation | Map tile coordinates to zones via `graph.json` node locations |
| 6 | Export | `cv_congestion.json`: `{zone_id: {hour: {level, confidence, source: "classical"}}}` |

**CNN comparison (Phase 14.4):**

| Step | Operation | Details |
|------|-----------|---------|
| 1 | Hand-label sample | Small set of tile crops with congestion labels (4 classes) |
| 2 | Train | Custom 4-layer CNN or fine-tuned ResNet-18 on labeled crops |
| 3 | Evaluate | Compare accuracy against classical pipeline on same validation set |
| 4 | Export | Same `cv_congestion.json` format; `source: "cnn"` |

**Success metric (PRD §7):** Classical-vs-CNN accuracy comparison table delivered per city.

### Pipeline B: Synthetic Virtual Camera (Phase 15)

**Data flow:**

```
Engine WS stream ──→ virtual_camera.py ──→ virtual_camera_service.py ──→ Dashboard
      │                     │                        │
  agent positions     Render top-down           Annotated PNG
  + graph.json        frame with Pillow/        + count JSON
                      OpenCV                    at ~1 Hz
                           │
                      OpenCV detection
                      (contour/blob + color seg)
```

**Rendering (Phase 15.1):**

| Step | Operation | Details |
|------|-----------|---------|
| 1 | Subscribe to engine WS | Read `agents[]` and `{"type":"bounds"}` for viewport |
| 2 | Load road geometry | Parse `graph.json` node lat/lon → project to pixel coordinates |
| 3 | Render roads | Draw road segments as gray lines/shapes on canvas |
| 4 | Render agents | Draw colored shapes by agent type (car=blue, bus=green, etc.) |
| 5 | Output frame | Pillow/OpenCV image (top-down view) |

**Detection (Phase 15.2):**

| Step | Operation | Details |
|------|-----------|---------|
| 1 | Color segmentation | Separate agent-colored pixels from road/background |
| 2 | Contour detection | `cv2.findContours()` on segmented mask |
| 3 | Blob filtering | Filter by minimum area, aspect ratio |
| 4 | Bounding boxes | `cv2.boundingRect()` on valid contours |
| 5 | Count | Number of valid bounding boxes = detected vehicle count |

**Service (Phase 15.3):**

| Property | Value |
|----------|-------|
| Port | 9003 (proposed) |
| Protocol | WebSocket/HTTP |
| Output | Annotated PNG (base64) + count JSON |
| Update rate | ~1 Hz |
| Dependencies | OpenCV, Pillow, FastAPI, websockets |

**Accuracy check (Phase 15.5):**
- Ground truth: actual agent count from engine's `metrics.active_agents` within the viewport bounds.
- Error %: `|detected - ground_truth| / ground_truth * 100`.
- Logged as running average for coursework writeup.

---

## Dependencies/Interfaces

### Upstream (what CV depends on)

| Dependency | Source | Interface | Status |
|------------|--------|-----------|--------|
| Traffic tile imagery | Mapbox Traffic Tiles API / TomTom Traffic Flow API | Color-coded congestion tiles; API key via env var (NFR-6) | PLANNED |
| `cv_bbox` per city | `pipeline/cities.yaml` | Lat/lon bounding box for tile capture region | DONE (Phase 14.1) |
| Engine WebSocket stream (port 9001) | C++ engine | `{tick, agents[], metrics}` JSON per tick; `{"type":"bounds"}` for viewport | DONE |
| `graph.json` | Pipeline | Road node lat/lon for projection; zone_id for aggregation | DONE (Phase 1) |

### Downstream (what depends on CV)

| Consumer | Interface | Status |
|----------|-----------|--------|
| Soft Computing GA (`optimize_calibration.py`) | `cv_congestion.json` as additional fitness term (Phase 14.6) | DONE |
| Dashboard `CongestionCVOverlay.tsx` | Zone bubbles colored by CV congestion level (Phase 14.7) | DONE |
| Dashboard `VirtualCameraPanel.tsx` | Live annotated feed from virtual camera service (Phase 15.4) | DONE |
| Dashboard `TrackingOverlay.tsx` | DeepSORT track overlays and trajectories | DONE |
| Dashboard `OpticalFlowPanel.tsx` | Dense motion vectors and velocity estimation | DONE |
| Cross-Subject Event Bus (`event_bus.py`) | Publishes `cv.anomaly` alerts for incident handling | DONE |
| Algo Explorer (`algo_explorer_service.py`) | Reports performance metrics for all 12 CV algorithms | DONE |

### 12-Algorithm CV Inventory (Phases 14, 15, 25–27)

| ID | Name | Module | Primary Capability | Accuracy / Latency |
|---|---|---|---|---|
| **CV-1** | Classical HSV Thresholding | `pipeline/src/cv_congestion.py` | Color-segmentation road congestion levels | 91.4% / 1.2 ms |
| **CV-2** | CNN Traffic Tile Classifier | `pipeline/src/cv_congestion.py` | 4-layer CNN tile classifier vs classical | 94.8% / 3.8 ms |
| **CV-3** | Top-Down Blob Detector | `ml/cv/virtual_camera.py` | Rendered canvas vehicle blob detection | 97.5% / 12.0 ms |
| **CV-4** | DeepSORT Vehicle Tracker | `ml/cv/deepsort_tracker.py` | Kalman filter + appearance cosine tracking | 92.0% / 16.5 ms |
| **CV-5** | U-Net Segmentation | `ml/cv/unet_segmentation.py` | Road mask segmentation encoder-decoder | 89.2% IoU / 22.1 ms |
| **CV-6** | Mask R-CNN | `ml/cv/mask_rcnn.py` | Instance silhouette extraction | 88.6% / 35.0 ms |
| **CV-7** | Anomaly & Hazard Detector | `ml/cv/anomaly_detector.py` | Stopped vehicle / sudden slowdown alerts | 95.0% / 2.1 ms |
| **CV-8** | Optical Flow (Lucas-Kanade) | `ml/cv/optical_flow.py` | Frame-to-frame velocity vector field | 93.4% / 5.2 ms |
| **CV-9** | Lane Boundary Detector | `ml/cv/lane_detector.py` | Hough line transform lane boundary finding | 90.1% / 3.1 ms |
| **CV-10** | Crowd Density Estimator | `ml/cv/crowd_density.py` | Pedestrian and vehicle density heatmaps | 87.5% / 6.4 ms |
| **CV-11** | YOLO Vehicle Detector | `ml/cv/yolo_detector.py` | Bounding box object detection | 95.2% / 15.0 ms |
| **CV-12** | MOG2 Motion Subtractor | `ml/cv/yolo_detector.py` | Background subtraction motion segmentation | 89.0% / 4.5 ms |

---

## Future Extension Points

1. **Multi-city tile capture (Phase 9):** Extend `cv_bbox` to Paris/Ahmedabad; each city gets its own `cv_congestion.json`.
2. **Live CV overlay:** Replace static per-hour data with real-time tile fetching; `CongestionCVOverlay.tsx` becomes live-updating.
3. **C++ Native libtorch/OpenCV bindings:** Zero-IPC execution embedded in the engine for resource-constrained edge hardware.

---

## References

| Document | Section | Content |
|----------|---------|---------|
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phase 14 | Real-world congestion classification: bbox config, tile fetch, classical CV, CNN, export, GA integration, dashboard overlay |
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phase 15 | Synthetic virtual camera: render, detection, service, panel, accuracy |
| `docs/TEAM_IMPLEMENTATION_PLAN.md` | Phases 25–27 | Expanded CV: YOLO, DeepSORT, U-Net, Mask R-CNN, optical flow, anomaly, lane detection, crowd density |
| `docs/PRD.md` | G8, G9, F8, F9 | CV goals, features, success metrics |
| `docs/TRD.md` | §4.3 (TR-ML-08) | Virtual camera technical requirement |
| `docs/results.md` | §3 & §6 | CV benchmark performance metrics |
| `dashboard/public/data/36_algo_matrix.json` | CV section | Complete algorithmic matrix and metadata |

---

*This document is self-contained and independently updatable. Last updated: September 2026.*

