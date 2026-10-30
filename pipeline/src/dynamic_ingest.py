"""NexusTwin Dynamic Ingestion Engine (Two-Stage Pipeline).

Stage 1: Ingests user-provided files (.osm, .pbf, .graphml, .geojson)
Stage 2: Geocodes search query via Nominatim and fetches topology via Overpass API

Executes complete topology cleaning, lane inference, zone clustering,
C++ graph.json export, and gravity-model OD matrix synthesis with granular progress updates.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import networkx as nx
import osmnx as ox
import requests

# Ensure repo root and pipeline/src are in sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

try:
    from pipeline.src.clean import clean_graph  # type: ignore
    from pipeline.src.lanes import infer_lanes  # type: ignore
    from pipeline.src.zones import tag_zones  # type: ignore
    from pipeline.src.export import export_graph  # type: ignore
    from pipeline.src.od_proxy import build_proxy_matrix  # type: ignore
except ImportError:
    from clean import clean_graph  # type: ignore
    from lanes import infer_lanes  # type: ignore
    from zones import tag_zones  # type: ignore
    from export import export_graph  # type: ignore
    from od_proxy import build_proxy_matrix  # type: ignore

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "NexusSim-DigitalTwin/2.0 (nexus-sim-research@adani.edu)"


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "city"


class DynamicIngestionWorker:
    """Orchestrates end-to-end ingestion and synthesis for the digital twin."""

    def __init__(self, data_root: Optional[str] = None):
        if data_root is None:
            data_root = os.path.abspath(os.path.join(_HERE, "..", "..", "data"))
        self.data_root = data_root
        os.makedirs(self.data_root, exist_ok=True)

    def _notify(
        self,
        callback: Optional[Callable[[Dict[str, Any]], None]],
        stage: str,
        pct: int,
        message: str,
        metrics: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        if callback:
            payload = {
                "stage": stage,
                "progress_pct": pct,
                "message": message,
                "metrics": metrics or {},
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            callback(payload)

    def geocode_query(self, query: str) -> Tuple[float, float, float, float, str]:
        """Geocode query string to (south, west, north, east, display_name)."""
        headers = {"User-Agent": USER_AGENT}
        params = {
            "q": query,
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            raise ValueError(f"No geographic match found for '{query}'")

        res = data[0]
        bb = res["boundingbox"]
        # Nominatim returns [min_lat, max_lat, min_lon, max_lon]
        south, north = float(bb[0]), float(bb[1])
        west, east = float(bb[2]), float(bb[3])

        # If bounding box is too tiny (< 500m), pad it
        lat_span = north - south
        lon_span = east - west
        min_span = 0.012  # ~1.3km
        if lat_span < min_span:
            mid_lat = (south + north) / 2.0
            south = mid_lat - min_span / 2.0
            north = mid_lat + min_span / 2.0
        if lon_span < min_span:
            mid_lon = (west + east) / 2.0
            west = mid_lon - min_span / 2.0
            east = mid_lon + min_span / 2.0

        # Cap max bounding box to ~12km x 12km for sub-20s performance
        max_span = 0.12
        if north - south > max_span:
            mid_lat = (south + north) / 2.0
            south = mid_lat - max_span / 2.0
            north = mid_lat + max_span / 2.0
        if east - west > max_span:
            mid_lon = (west + east) / 2.0
            west = mid_lon - max_span / 2.0
            east = mid_lon + max_span / 2.0

        return south, west, north, east, res.get("display_name", query)

    def fetch_overpass_osm(
        self,
        bbox: Tuple[float, float, float, float],
        progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> str:
        """Query Overpass API with mirror failover and return raw OSM XML."""
        south, west, north, east = bbox
        ql_query = f"""
        [out:xml][timeout:20];
        (
          way["highway"~"motorway|trunk|primary|secondary|tertiary|residential|unclassified"]
             ({south:.6f},{west:.6f},{north:.6f},{east:.6f});
          node(w);
        );
        (._;>;);
        out meta;
        """

        headers = {"User-Agent": USER_AGENT}
        last_exc = None

        for mirror in OVERPASS_MIRRORS:
            try:
                self._notify(
                    progress_cb,
                    "QUERYING_OVERPASS",
                    25,
                    f"Fetching road network from Overpass mirror: {urllib.parse.urlparse(mirror).netloc}",
                )
                resp = requests.post(
                    mirror,
                    data={"data": ql_query},
                    headers=headers,
                    timeout=22,
                )
                if resp.status_code == 200 and len(resp.content) > 500:
                    return resp.text
            except Exception as e:
                last_exc = e
                continue

        raise RuntimeError(
            f"All Overpass mirrors failed or timed out. Last error: {last_exc}"
        )

    def ingest_query(
        self,
        query: str,
        city_id: Optional[str] = None,
        workspace_id: str = "default",
        progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Stage 2: Geocoded global search and full digital twin synthesis."""
        start_time = time.time()
        self._notify(
            progress_cb,
            "GEOCODING",
            10,
            f"Geocoding location: '{query}' via Nominatim",
        )

        south, west, north, east, display_name = self.geocode_query(query)
        bbox = (south, west, north, east)

        if city_id is None:
            # Short slug from first part of query or display_name
            first_part = query.split(",")[0].strip()
            city_id = _slugify(first_part)

        city_dir = os.path.join(self.data_root, city_id)
        os.makedirs(city_dir, exist_ok=True)

        osm_xml = self.fetch_overpass_osm(bbox, progress_cb)

        raw_osm_path = os.path.join(city_dir, "raw.osm")
        with open(raw_osm_path, "w", encoding="utf-8") as f:
            f.write(osm_xml)

        return self._process_osm_file(
            source_path=raw_osm_path,
            city_id=city_id,
            city_name=display_name,
            city_dir=city_dir,
            workspace_id=workspace_id,
            bbox_override=[south, west, north, east],
            start_time=start_time,
            progress_cb=progress_cb,
        )

    def ingest_file(
        self,
        file_path: str,
        city_id: Optional[str] = None,
        city_name: Optional[str] = None,
        workspace_id: str = "default",
        progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Stage 1: File drop ingestion (.osm, .pbf, .graphml)."""
        start_time = time.time()
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        base = os.path.basename(file_path)
        ext = os.path.splitext(base)[1].lower()
        if ext not in {".osm", ".pbf", ".graphml", ".xml"}:
            raise ValueError(f"Unsupported format '{ext}'. Must be .osm, .pbf, or .graphml")

        if city_id is None:
            city_id = _slugify(os.path.splitext(base)[0])
        if city_name is None:
            city_name = city_id.replace("-", " ").title()

        city_dir = os.path.join(self.data_root, city_id)
        os.makedirs(city_dir, exist_ok=True)

        target_source = os.path.join(city_dir, f"raw{ext}")
        if os.path.abspath(file_path) != os.path.abspath(target_source):
            with open(file_path, "rb") as sf, open(target_source, "wb") as df:
                df.write(sf.read())

        return self._process_osm_file(
            source_path=target_source,
            city_id=city_id,
            city_name=city_name,
            city_dir=city_dir,
            workspace_id=workspace_id,
            start_time=start_time,
            progress_cb=progress_cb,
        )

    def _process_osm_file(
        self,
        source_path: str,
        city_id: str,
        city_name: str,
        city_dir: str,
        workspace_id: str,
        start_time: float,
        bbox_override: Optional[List[float]] = None,
        progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """Runs the pipeline stages: Parse -> Clean -> Lanes -> Zones -> Export -> OD."""
        ext = os.path.splitext(source_path)[1].lower()
        raw_graphml = os.path.join(city_dir, "raw.graphml")

        # Stage 1: Parse to GraphML
        self._notify(progress_cb, "PARSING_SOURCE", 35, "Parsing OpenStreetMap road vectors into topological graph")
        if ext == ".graphml":
            G = ox.load_graphml(source_path)
            ox.save_graphml(G, raw_graphml)
        elif ext in {".osm", ".xml"}:
            if "highway" not in ox.settings.useful_tags_node:
                ox.settings.useful_tags_node.append("highway")
            G = ox.graph_from_xml(source_path, simplify=False)
            ox.save_graphml(G, raw_graphml)
        elif ext == ".pbf":
            from import_osm import import_osm
            res = import_osm(source_path, city_id=city_id, out_dir=city_dir)
            raw_graphml = res["raw_path"]

        # Stage 2: Topology Cleaning & Largest SCC
        self._notify(progress_cb, "TOPOLOGY_CLEANING", 50, "Simplifying graph topology and isolating largest connected component")
        cleaned_graphml = os.path.join(city_dir, "cleaned.graphml")
        clean_graph(city_id, raw_path=raw_graphml, out_path=cleaned_graphml)

        # Stage 3: Lane Inference
        self._notify(progress_cb, "LANE_INFERENCE", 65, "Synthesizing multi-lane corridors and capacity profiles")
        lanes_graphml = os.path.join(city_dir, "lanes.graphml")
        # infer_lanes expects ../data/<city_id>/cleaned.graphml, let's execute in-place
        G_clean = ox.load_graphml(cleaned_graphml)
        road_type_lanes = {
            "motorway": 3, "trunk": 2, "primary": 2,
            "secondary": 2, "tertiary": 1, "residential": 1, "unclassified": 1,
        }
        for u, v, k, data in G_clean.edges(keys=True, data=True):
            lanes = data.get("lanes")
            if lanes:
                if isinstance(lanes, list):
                    lanes = lanes[0]
                try:
                    data["lanes_inferred"] = int(float(lanes))
                    continue
                except (ValueError, TypeError):
                    pass
            hw = data.get("highway")
            if isinstance(hw, list):
                hw = hw[0]
            data["lanes_inferred"] = road_type_lanes.get(str(hw), 1)

        ox.save_graphml(G_clean, lanes_graphml)

        # Stage 4: Zone Tagging (1-indexed, since zone_id=0 is reserved as untagged)
        self._notify(progress_cb, "ZONE_CLUSTERING", 75, "Clustering nodes into Traffic Analysis Zones (TAZs)")
        zones_graphml = os.path.join(city_dir, "zones.graphml")
        G_lanes = ox.load_graphml(lanes_graphml)
        lats = [float(data["y"]) for _, data in G_lanes.nodes(data=True)]
        lons = [float(data["x"]) for _, data in G_lanes.nodes(data=True)]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        grid_size = 10
        assigned_zones = set()

        node_keys = list(G_lanes.nodes)
        for idx, n in enumerate(node_keys):
            data = G_lanes.nodes[n]
            lat_idx = int((float(data["y"]) - min_lat) / (max_lat - min_lat + 1e-9) * grid_size)
            lon_idx = int((float(data["x"]) - min_lon) / (max_lon - min_lon + 1e-9) * grid_size)
            zid = (lat_idx * grid_size + lon_idx) + 1  # 1-indexed
            data["zone_id"] = zid
            assigned_zones.add(zid)

        # Ensure at least 2 distinct zones for tiny graphs/fixtures (zone 1 and zone 2)
        if len(assigned_zones) < 2 and len(node_keys) >= 2:
            G_lanes.nodes[node_keys[0]]["zone_id"] = 1
            for n in node_keys[1:]:
                G_lanes.nodes[n]["zone_id"] = 2

        ox.save_graphml(G_lanes, zones_graphml)

        # Stage 5: Export C++ graph.json
        self._notify(progress_cb, "EXPORTING_GRAPH", 85, "Generating high-performance C++ engine graph.json")
        graph_json_path = os.path.join(city_dir, "graph.json")
        G_zones = ox.load_graphml(zones_graphml)
        output_graph: Dict[str, Any] = {"nodes": [], "edges": []}
        for n, data in G_zones.nodes(data=True):
            output_graph["nodes"].append({
                "id": int(n),
                "lat": float(data["y"]),
                "lon": float(data["x"]),
                "zone_id": int(data.get("zone_id", 0)),
                "is_signal": data.get("highway") == "traffic_signals",
            })
        for u, v, k, data in G_zones.edges(keys=True, data=True):
            output_graph["edges"].append({
                "u": int(u),
                "v": int(v),
                "length_m": float(data.get("length", 0.0)),
                "lanes": int(data.get("lanes_inferred", 1)),
            })
        with open(graph_json_path, "w", encoding="utf-8") as f:
            json.dump(output_graph, f, indent=2)

        # Stage 6: Synthesize Gravity OD Matrix
        self._notify(progress_cb, "OD_SYNTHESIS", 92, "Synthesizing gravity-model Origin-Destination demand matrix")
        od_matrix_path = os.path.join(city_dir, "od_matrix.json")
        matrix = build_proxy_matrix(
            output_graph,
            city_id,
            source_note=f"Synthetic OD for {city_name} via gravity model",
        )
        with open(od_matrix_path, "w", encoding="utf-8") as f:
            json.dump(matrix, f, indent=1)

        # Stage 7: Metadata & Registration
        bbox = bbox_override or [min_lat, min_lon, max_lat, max_lon]
        center = [(bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0]
        elapsed = time.time() - start_time

        metadata = {
            "city_id": city_id,
            "city_name": city_name,
            "workspace_id": workspace_id,
            "bbox": bbox,
            "center": center,
            "node_count": len(output_graph["nodes"]),
            "edge_count": len(output_graph["edges"]),
            "zone_count": matrix.get("zone_count", 100),
            "status": "ready",
            "elapsed_seconds": round(elapsed, 2),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(os.path.join(city_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        # Register into cities.yaml if present
        cities_yaml_path = os.path.join(_HERE, "..", "cities.yaml")
        if os.path.exists(cities_yaml_path):
            try:
                import yaml
                with open(cities_yaml_path, "r", encoding="utf-8") as yf:
                    cy = yaml.safe_load(yf) or {}
                cy[city_id] = {
                    "query": f"{city_name} (dynamic digital twin)",
                    "chaos": 0.1,
                    "cv_bbox": bbox,
                    "od_source": {"type": "density-proxy", "note": "Gravity model synthesis"},
                }
                with open(cities_yaml_path, "w", encoding="utf-8") as yf:
                    yaml.dump(cy, yf)
            except Exception:
                pass

        self._notify(
            progress_cb,
            "COMPLETE",
            100,
            f"Digital Twin for '{city_name}' generated successfully in {elapsed:.1f}s",
            metrics={
                "nodes": metadata["node_count"],
                "edges": metadata["edge_count"],
                "zones": metadata["zone_count"],
                "elapsed_s": metadata["elapsed_seconds"],
            },
        )

        return metadata
