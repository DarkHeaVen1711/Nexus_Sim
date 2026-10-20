"""OSM import for dynamic city onboarding.

Parses user-uploaded OSM files (.osm, .osm.pbf, .graphml) into a GraphML
that the existing pipeline (clean.py -> export.py) can consume.

Requires:
- osmnx>=1.9.0 (for .osm via graph_from_xml, for .graphml via load_graphml)
- networkx>=3.0 (for graph validation)

For .osm.pbf files, either install pyosmium or ensure osmium-tool is on PATH
and convert to .osm first:  osmium cat input.osm.pbf -o output.osm
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Optional

import networkx as nx
import osmnx as ox

VALID_EXTENSIONS = {".osm", ".pbf", ".graphml"}
MAX_FILE_SIZE_MB = 500


def _slugify(name: str) -> str:
    """Turn a city name into a filesystem-safe city_id."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "city"


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def import_osm(
    source_path: str,
    city_id: Optional[str] = None,
    city_name: Optional[str] = None,
    out_dir: Optional[str] = None,
) -> dict:
    """Import an OSM file into the NexusSim pipeline format.

    Args:
        source_path: Path to the uploaded .osm / .osm.pbf / .graphml file.
        city_id: Optional explicit city id (slug). Derived from filename if absent.
        city_name: Optional human-readable label. Derived from city_id if absent.
        out_dir: Optional output directory. Defaults to ../data/<city_id>/ relative
                 to this file (matching download.py / clean.py / export.py).

    Returns:
        dict with city_id, city_name, source_path, source_hash, node_count,
        edge_count, bbox, center, raw_path, cleaned_path, graph_json_path,
        status.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file not found: {source_path}")

    ext = os.path.splitext(source_path)[1].lower()
    if ext not in VALID_EXTENSIONS:
        raise ValueError(
            f"Unsupported extension '{ext}'. Expected one of {sorted(VALID_EXTENSIONS)}"
        )

    size_mb = os.path.getsize(source_path) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(
            f"File too large: {size_mb:.1f} MB (max {MAX_FILE_SIZE_MB} MB)"
        )

    if city_id is None:
        city_id = _slugify(os.path.splitext(os.path.basename(source_path))[0])
    if city_name is None:
        city_name = city_id.replace("-", " ").title()

    here = os.path.dirname(os.path.abspath(__file__))
    if out_dir is None:
        out_dir = os.path.join(here, "..", "data", city_id)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)

    source_hash = _file_hash(source_path)

    # ── Stage 1: source → raw.graphml ─────────────────────────────────────
    raw_path = os.path.join(out_dir, "raw.graphml")

    if ext == ".graphml":
        # Already GraphML: copy (or load + re-save to normalise)
        G = ox.load_graphml(source_path)
        ox.save_graphml(G, raw_path)
    elif ext == ".osm":
        # Keep highway tags on nodes so we can identify traffic signals
        if "highway" not in ox.settings.useful_tags_node:
            ox.settings.useful_tags_node.append("highway")
        G = ox.graph_from_xml(source_path, simplify=False)
        ox.save_graphml(G, raw_path)
    elif ext == ".pbf":
        # Try pyosmium if available; otherwise instruct the user to convert first.
        try:
            import pyosmium  # type: ignore

            class OSMToGraphMLHandler(pyosmium.SimpleHandler):
                def __init__(self):
                    super().__init__()
                    self.G = nx.MultiDiGraph()

                def node(self, n):
                    self.G.add_node(
                        n.id,
                        lat=n.location.lat,
                        lon=n.location.lon,
                    )

                def way(self, w):
                    if w.nodes is None or len(w.nodes) < 2:
                        return
                    # Only keep drivable ways (basic heuristic)
                    highway = w.tags.get("highway")
                    if highway is None:
                        return
                    oneway = w.tags.get("oneway")
                    nodes = [n.ref for n in w.nodes]
                    for i in range(len(nodes) - 1):
                        u, v = nodes[i], nodes[i + 1]
                        self.G.add_edge(u, v, highway=highway, length_m=0.0)
                        if oneway not in ("yes", "true", "1", "-1"):
                            self.G.add_edge(v, u, highway=highway, length_m=0.0)

            handler = OSMToGraphMLHandler()
            handler.apply_file(source_path)
            nx.write_graphml(handler.G, raw_path)
        except ImportError:
            raise RuntimeError(
                ".pbf import requires pyosmium or osmium-tool. "
                "Convert first: osmium cat input.osm.pbf -o output.osm, "
                "then re-upload the .osm file."
            )

    # ── Validate the raw graph ────────────────────────────────────────────
    G_raw = ox.load_graphml(raw_path)
    node_count = len(G_raw.nodes)
    edge_count = len(G_raw.edges)
    if node_count == 0:
        raise ValueError("Imported graph has no nodes.")

    # Bounding box + center
    lats = [float(d["y"]) for _, d in G_raw.nodes(data=True)]
    lons = [float(d["x"]) for _, d in G_raw.nodes(data=True)]
    bbox = [min(lats), min(lons), max(lats), max(lons)]
    center = [(min(lats) + max(lats)) / 2.0, (min(lons) + max(lons)) / 2.0]

    # ── Stage 2: raw → cleaned (delegates to clean.py) ────────────────────
    # Use absolute import so this module works both as a package and as a script.
    try:
        from clean import clean_graph  # type: ignore
    except ImportError:
        from pipeline.src.clean import clean_graph  # type: ignore

    cleaned_path = os.path.join(out_dir, "cleaned.graphml")
    graph_json_path = os.path.join(out_dir, "graph.json")

    clean_graph(city_id, raw_path=raw_path, out_path=cleaned_path)

    # ── Stage 3: cleaned → graph.json (delegates to export.py) ────────────
    try:
        from export import export_graph  # type: ignore
    except ImportError:
        from pipeline.src.export import export_graph  # type: ignore

    export_graph(city_id, in_path=cleaned_path, out_path=graph_json_path)

    return {
        "city_id": city_id,
        "city_name": city_name,
        "source_path": source_path,
        "source_hash": source_hash,
        "node_count": node_count,
        "edge_count": edge_count,
        "bbox": bbox,
        "center": center,
        "raw_path": raw_path,
        "cleaned_path": cleaned_path,
        "graph_json_path": graph_json_path,
        "status": "ready",
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Import an OSM file into NexusSim")
    parser.add_argument("--file", required=True, help="Path to .osm / .pbf / .graphml")
    parser.add_argument("--city-id", help="Explicit city id (slug)")
    parser.add_argument("--city-name", help="Human-readable city label")
    args = parser.parse_args()

    result = import_osm(args.file, city_id=args.city_id, city_name=args.city_name)
    print(json.dumps(result, indent=2))
