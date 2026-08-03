"""Phase 6.2 - Build OD demand matrix and tag graph nodes with OD zones.

Reads the aggregated OD counts (download_od.py output), fetches zone
boundaries, tags every graph node with its OD zone id (point-in-polygon), and
writes:

  data/chicago/od_matrix.json   (documented in docs/od_matrix_schema.md)
  data/chicago/graph.json       (nodes now carry OD zone ids instead of the
                                 Phase 1 grid zones)

Pure-Python point-in-polygon (ray casting) with a bounding-box prefilter, so no
geopandas dependency is required.
"""
import argparse
import csv
import json
import math
import os

from download_od import _fetch


def _area_cache_path(city):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "..", "data", "uber-movement-" + city,
                        "community_areas.json")


def fetch_boundaries(cfg, city, force=False):
    """Return {zone_id: {"name": str, "polygons": [ring, ...], "bbox": ...}}."""
    cache = _area_cache_path(city)
    if not force and os.path.isfile(cache):
        with open(cache, "r") as f:
            return json.load(f)

    dataset = cfg["zones_dataset"]
    geom_col = cfg["zone_geometry_column"]
    zone_col = cfg["zone_column"]
    name_col = cfg["zone_name_column"]
    url = ("https://data.cityofchicago.org/resource/%s.geojson?$limit=200"
           % dataset)
    geojson = json.loads(_fetch(url))

    zones = {}
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        zone_id = int(props.get(zone_col))
        name = props.get(name_col)
        geom = feature.get("geometry", {})
        polys = []
        ring = geom.get("coordinates")
        if not ring:
            continue
        if geom.get("type") == "Polygon":
            polys = [ring]
        elif geom.get("type") == "MultiPolygon":
            polys = [r for poly in ring for r in poly]
        else:
            continue
        rings = []
        for ring in polys:
            pts = [(float(p[0]), float(p[1])) for p in ring]
            rings.append(pts)
        lons = [p[0] for ring in rings for p in ring]
        lats = [p[1] for ring in rings for p in ring]
        zones[str(zone_id)] = {
            "name": name,
            "polygons": rings,
            "bbox": [min(lons), min(lats), max(lons), max(lats)],
        }

    os.makedirs(os.path.dirname(cache), exist_ok=True)
    with open(cache, "w") as f:
        json.dump(zones, f)
    print("Cached %d zone boundaries to %s" % (len(zones), cache))
    return zones


def _point_in_ring(lon, lat, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat):
            x_cross = xj + (lat - yj) * (xi - xj) / (yi - yj)
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def _point_in_zone(lon, lat, zone):
    bbox = zone["bbox"]
    if not (bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]):
        return False
    for ring in zone["polygons"]:
        if _point_in_ring(lon, lat, ring):
            return True
    return False


def _zone_centroid(zone):
    ring = zone["polygons"][0] if zone["polygons"] else [(0.0, 0.0)]
    lon = sum(p[0] for p in ring) / max(len(ring), 1)
    lat = sum(p[1] for p in ring) / max(len(ring), 1)
    return lat, lon


def tag_graph_zones(graph_path, zones):
    """Rewrite graph.json nodes with zone_id = matching OD zone (or nearest)."""
    with open(graph_path, "r") as f:
        graph = json.load(f)

    zone_ids = [int(z) for z in zones]
    assigned = 0
    unmatched = 0
    for node in graph["nodes"]:
        lon = float(node["lon"])
        lat = float(node["lat"])
        zone_id = 0
        for zid in zone_ids:
            if _point_in_zone(lon, lat, zones[str(zid)]):
                zone_id = zid
                break
        if zone_id:
            node["zone_id"] = zone_id
            assigned += 1
        else:
            # Nearest zone by centroid distance.
            best = min(zone_ids, key=lambda zid: _haversine(
                lat, lon, *_zone_centroid(zones[str(zid)])))
            node["zone_id"] = best
            unmatched += 1

    with open(graph_path, "w") as f:
        json.dump(graph, f, indent=1)
    print("Tagged %d nodes by polygon, %d by nearest-zone fallback "
          "(total %d)" % (assigned, unmatched, len(graph["nodes"])))


def _haversine(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def build_od_matrix(cfg, city, out_path, weekdays_sampled=10, year=2019,
                    month=10, counts_csv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    if counts_csv is None:
        counts_csv = os.path.join(here, "..", "..", "data",
                                  "uber-movement-" + city, "od_counts.csv")
    zones = fetch_boundaries(cfg, city)

    # Aggregate raw counts: per OD pair, per-hour trips + weighted mean TT.
    od = {}
    with open(counts_csv, "r") as f:
        for row in csv.DictReader(f):
            o = int(row["origin"])
            d = int(row["destination"])
            hour = int(row["hour"])
            trips = float(row["trips"])
            tt = float(row["mean_trip_seconds"])
            key = (o, d)
            if key not in od:
                od[key] = {"hourly": [0.0] * 24, "tt_sum": [0.0] * 24}
            od[key]["hourly"][hour] += trips
            od[key]["tt_sum"][hour] += trips * tt

    od_entries = []
    for (o, d), v in od.items():
        hourly = [h / weekdays_sampled for h in v["hourly"]]
        tt = [t / h if h > 0 else 0.0
              for t, h in zip(v["tt_sum"], v["hourly"])]
        od_entries.append({"origin": o, "destination": d,
                           "hourly": hourly, "hourly_tt": tt})

    zones_out = {}
    for zid in zones:
        z = zones[zid]
        lat, lon = _zone_centroid(z)
        zones_out[zid] = {"name": z["name"], "lat": round(lat, 6),
                          "lon": round(lon, 6)}

    matrix = {
        "schema_version": "1.0",
        "city": city,
        "source": cfg.get("note", ""),
        "source_url": ("https://data.cityofchicago.org/Transportation/"
                       "Transportation-Network-Providers-Trips-2018-2022-"
                       "/m6dm-c72p"),
        "zone_count": len(zones),
        "units": {"demand": "vehicles per hour (avg sampled weekday)",
                  "journey_time": "seconds"},
        "sampled_weekdays": weekdays_sampled,
        "year_month": "%d-%02d" % (year, month),
        "zones": zones_out,
        "od": od_entries,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(matrix, f, indent=1)
    print("Wrote %s with %d zones and %d OD pairs"
          % (out_path, len(zones), len(od_entries)))


def main():
    parser = argparse.ArgumentParser(description="Build OD demand matrix")
    parser.add_argument("--city", required=True)
    parser.add_argument("--weekdays", type=int, default=10)
    parser.add_argument("--year", type=int, default=2019)
    parser.add_argument("--month", type=int, default=10)
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(here, "..", "cities.yaml")
    with open(config_path, "r") as f:
        import yaml
        config = yaml.safe_load(f)
    cfg = config[args.city]["od_source"]

    root = os.path.join(here, "..", "..", "data", args.city)
    graph_path = os.path.join(root, "graph.json")
    if not os.path.isfile(graph_path):
        raise FileNotFoundError("Run the Phase 1 pipeline first: %s" % graph_path)

    tag_graph_zones(graph_path, fetch_boundaries(cfg, args.city))
    out_path = os.path.join(root, "od_matrix.json")
    build_od_matrix(cfg, args.city, out_path, args.weekdays, args.year,
                    args.month)


if __name__ == "__main__":
    main()
