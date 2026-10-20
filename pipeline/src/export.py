import os
import json
from typing import Optional

import osmnx as ox
import argparse


def export_graph(city_id: str, in_path: Optional[str] = None, out_path: Optional[str] = None):
    """Export a cleaned GraphML to the graph.json format used by the C++ engine.

    Args:
        city_id: City identifier (used for default paths).
        in_path: Optional path to cleaned GraphML. Defaults to ../data/<city_id>/cleaned.graphml.
        out_path: Optional path for graph.json. Defaults to ../data/<city_id>/graph.json.
    """
    if in_path is None:
        in_path = f"../data/{city_id}/cleaned.graphml"
    if out_path is None:
        out_path = f"../data/{city_id}/graph.json"

    G = ox.load_graphml(in_path)

    output = {
        "nodes": [],
        "edges": []
    }

    for n, data in G.nodes(data=True):
        output["nodes"].append({
            "id": int(n),
            "lat": float(data['y']),
            "lon": float(data['x']),
            "zone_id": int(data.get('zone_id', 0)),
            "is_signal": data.get('highway') == 'traffic_signals'
        })

    for u, v, key, data in G.edges(keys=True, data=True):
        output["edges"].append({
            "u": int(u),
            "v": int(v),
            "length_m": float(data.get('length', 0.0)),
            "lanes": int(data.get('lanes_inferred', 1))
        })

    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Exported graph to {out_path} with {len(output['nodes'])} nodes and {len(output['edges'])} edges.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", required=True)
    args = parser.parse_args()
    export_graph(args.city)
