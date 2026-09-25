import urllib.request
import json
import os
import math

CITIES = {
    "ahmedabad": {"bbox": (22.99, 72.55, 23.05, 72.62), "name": "Ahmedabad"},
    "chicago": {"bbox": (41.86, -87.66, 41.90, -87.61), "name": "Chicago"},
    "paris": {"bbox": (48.84, 2.31, 48.88, 2.38), "name": "Paris"},
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def fetch_or_generate_graph(city_id, config):
    out_dir = os.path.join("data", city_id)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "graph.json")
    if os.path.exists(out_path):
        print(f"Graph already exists at {out_path}")
        return

    min_lat, min_lon, max_lat, max_lon = config["bbox"]
    query = f"""[out:json][timeout:30];
(
  way["highway"~"primary|secondary|tertiary|residential|trunk"]({min_lat},{min_lon},{max_lat},{max_lon});
);
out body;
>;
out skel qt;"""

    data = None
    try:
        print(f"Fetching OSM road network for {config['name']}...")
        url = "https://overpass-api.de/api/interpreter"
        req = urllib.request.Request(url, data=query.encode('utf-8'), headers={'User-Agent': 'NexusSim/1.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Overpass fetch failed for {city_id}: {e}")

    nodes_dict = {}
    edges_list = []

    if data and "elements" in data and len(data["elements"]) > 0:
        for elem in data["elements"]:
            if elem.get("type") == "node":
                nodes_dict[elem["id"]] = {
                    "id": elem["id"],
                    "lat": elem["lat"],
                    "lon": elem["lon"],
                    "zone_id": int((elem["lat"] - min_lat) / (max_lat - min_lat + 1e-6) * 10),
                    "is_signal": elem.get("tags", {}).get("highway") == "traffic_signals"
                }

        for elem in data["elements"]:
            if elem.get("type") == "way":
                node_ids = elem.get("nodes", [])
                lanes = 1
                try:
                    lanes = int(elem.get("tags", {}).get("lanes", 1))
                except Exception:
                    lanes = 1
                oneway = elem.get("tags", {}).get("oneway") == "yes"

                for i in range(len(node_ids) - 1):
                    u = node_ids[i]
                    v = node_ids[i + 1]
                    if u in nodes_dict and v in nodes_dict:
                        u_node = nodes_dict[u]
                        v_node = nodes_dict[v]
                        dist = haversine(u_node["lat"], u_node["lon"], v_node["lat"], v_node["lon"])
                        edges_list.append({
                            "u": u,
                            "v": v,
                            "length_m": round(max(dist, 5.0), 2),
                            "lanes": max(1, min(lanes, 4))
                        })
                        if not oneway:
                            edges_list.append({
                                "u": v,
                                "v": u,
                                "length_m": round(max(dist, 5.0), 2),
                                "lanes": max(1, min(lanes, 4))
                            })

    # Filter connected nodes that are part of edges
    used_node_ids = set()
    for e in edges_list:
        used_node_ids.add(e["u"])
        used_node_ids.add(e["v"])

    final_nodes = [nodes_dict[nid] for nid in used_node_ids if nid in nodes_dict]

    # Fallback synthetic grid if Overpass returned empty
    if len(final_nodes) < 10 or len(edges_list) < 10:
        print(f"Generating synthetic structured grid for {city_id}...")
        final_nodes = []
        edges_list = []
        grid_rows, grid_cols = 12, 12
        node_id_counter = 1
        grid = {}
        for r in range(grid_rows):
            for c in range(grid_cols):
                lat = min_lat + (max_lat - min_lat) * (r / (grid_rows - 1))
                lon = min_lon + (max_lon - min_lon) * (c / (grid_cols - 1))
                nid = node_id_counter
                node_id_counter += 1
                is_sig = (r % 3 == 0 and c % 3 == 0)
                zone_id = (r // 4) * 3 + (c // 4)
                grid[(r, c)] = nid
                final_nodes.append({
                    "id": nid,
                    "lat": lat,
                    "lon": lon,
                    "zone_id": zone_id,
                    "is_signal": is_sig
                })

        for r in range(grid_rows):
            for c in range(grid_cols):
                u = grid[(r, c)]
                u_lat = min_lat + (max_lat - min_lat) * (r / (grid_rows - 1))
                u_lon = min_lon + (max_lon - min_lon) * (c / (grid_cols - 1))
                if r + 1 < grid_rows:
                    v = grid[(r + 1, c)]
                    v_lat = min_lat + (max_lat - min_lat) * ((r + 1) / (grid_rows - 1))
                    d = haversine(u_lat, u_lon, v_lat, u_lon)
                    edges_list.append({"u": u, "v": v, "length_m": round(d, 2), "lanes": 2})
                    edges_list.append({"u": v, "v": u, "length_m": round(d, 2), "lanes": 2})
                if c + 1 < grid_cols:
                    v = grid[(r, c + 1)]
                    v_lon = min_lon + (max_lon - min_lon) * ((c + 1) / (grid_cols - 1))
                    d = haversine(u_lat, u_lon, u_lat, v_lon)
                    edges_list.append({"u": u, "v": v, "length_m": round(d, 2), "lanes": 2})
                    edges_list.append({"u": v, "v": u, "length_m": round(d, 2), "lanes": 2})

    output = {
        "nodes": final_nodes,
        "edges": edges_list
    }

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Generated {out_path} with {len(final_nodes)} nodes and {len(edges_list)} edges.")

if __name__ == "__main__":
    for city, cfg in CITIES.items():
        fetch_or_generate_graph(city, cfg)
