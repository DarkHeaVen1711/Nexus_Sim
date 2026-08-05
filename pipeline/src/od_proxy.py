"""Building-density-proxy OD matrix generator (Phases 6.6 / 6.7).

Some cities have no usable public origin-destination feed:

  * Paris      - OpenTraffic was decommissioned; no equivalent open OD release.
  * Ahmedabad  - Smart Cities Mission / AMC data is not exposed as a public API.

For those cities the implementation plan calls for a documented fallback rather
than a silent guess: "fallback to building-density proxy ... expect higher
uncertainty; document in calibration notes" (Phase 6.7).

This module is that fallback. It synthesises an OD matrix from the road graph
alone using a *gravity model*, the standard first-cut method in transport
planning: trips between two zones grow with the size of both zones and decay
with the distance between them.

    T_ij  =  K * (M_i^alpha * M_j^alpha) / d_ij^beta

where M_i is a zone's "mass" (here: its road-node count, used as a proxy for
built-up density) and d_ij is the great-circle distance between zone centroids.

IMPORTANT - what this output may and may not be used for
--------------------------------------------------------
The `hourly_tt` (journey time) values produced here are *derived from the same
model that generates the demand*. They are therefore *not* ground truth, and
validating the simulation against them would be circular - the simulation would
effectively be checked against its own assumptions.

    OK  : running the simulation for a city with no real OD feed
    NOT : computing a validation MAPE (that requires a real observed feed)

Every record is flagged `"confidence": "low"` and the matrix carries
`"method": "gravity-density-proxy"` so downstream consumers can tell proxy data
from measured data. `validate.py` refuses proxy matrices for this reason.

Output schema matches `od_matrix.py` exactly (schema_version 1.0) so the C++
engine loads it with no changes.
"""

import argparse
import json
import math
import os

# Fraction of a weekday's trips departing in each hour (0-23). Two-peak weekday
# profile: overnight trough, AM commute peak ~08:00, midday plateau, PM commute
# peak ~17:00-18:00. Sums to 1.0.
DIURNAL_PROFILE = [
    0.006, 0.004, 0.003, 0.003, 0.006, 0.015,  # 00-05
    0.035, 0.062, 0.078, 0.061, 0.045, 0.043,  # 06-11
    0.046, 0.045, 0.046, 0.055, 0.072, 0.085,  # 12-17
    0.073, 0.055, 0.040, 0.030, 0.020, 0.072,  # 18-23
]

# Congestion multiplier applied to free-flow journey time, by hour. Peak hours
# are slower; overnight is close to free-flow.
CONGESTION_PROFILE = [
    1.00, 1.00, 1.00, 1.00, 1.00, 1.05,
    1.20, 1.45, 1.60, 1.40, 1.20, 1.15,
    1.20, 1.18, 1.20, 1.35, 1.55, 1.65,
    1.50, 1.30, 1.15, 1.08, 1.02, 1.00,
]

# Gravity-model parameters. Both are conventional starting values for an
# uncalibrated urban gravity model; they are recorded in the output so a later
# calibration pass (e.g. the Phase 13 GA) can tune them.
MASS_EXPONENT = 1.0      # alpha
DISTANCE_EXPONENT = 2.0  # beta

# Assumed free-flow door-to-door speed used to turn distance into a journey
# time, in metres per second (~27 km/h, typical urban arterial average).
FREE_FLOW_MPS = 7.5

# Straight-line distance under-states real road distance. Standard detour
# (circuity) factor for urban road networks.
DETOUR_FACTOR = 1.3

# Trips per day generated per unit of zone mass (one road node). Scales the
# absolute size of the matrix; demand_scale at run time is the practical knob,
# so this only needs to be the right order of magnitude.
TRIPS_PER_NODE_PER_DAY = 4.0

MIN_DISTANCE_M = 250.0  # absolute floor on d_ij, guards against divide-by-zero

# Intra-zone trips (origin == destination) have no centroid-to-centroid
# distance, so the gravity term would divide by ~0 and swamp the matrix. A flat
# floor is not good enough either: with a squared distance decay it produced 94%
# intra-zone trips on Chicago, against 11.1% in the real measured matrix -- i.e.
# almost every agent would have started and finished inside one zone, generating
# nearly no network traffic.
#
# Instead the intra-zone distance is derived from the zone's own size: a trip
# that stays inside a zone covers some fraction of that zone's radius. The
# factor below was calibrated by sweeping it against Chicago's real measured
# matrix, the only city with observed data to calibrate against:
#
#     factor  1.0    1.5    2.0    2.37   2.5    3.0    4.0
#     intra%  41.2   23.8   14.9   11.1   10.1   7.2    4.2     (real: 11.09%)
#
# 2.37 reproduces the observed 11.09% intra-zone share. The assumption carried
# to Paris and Ahmedabad is that intra-zone trip-making behaves similarly
# relative to zone size -- reasonable for a first-cut proxy, but it is an
# assumption, which is why these matrices stay flagged confidence: low.
INTRA_ZONE_FACTOR = 2.37


def _haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres. Mirrors od_matrix.py::_haversine."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def zone_stats(graph):
    """Aggregate graph nodes into per-zone mass and centroid.

    Returns {zone_id: {"mass": int, "lat": float, "lon": float}} where mass is
    the node count in that zone - the density proxy - and lat/lon is the mean
    node position (the zone centroid).

    Zone 0 is the "untagged" sentinel used by export.py when a node has no zone,
    so it is skipped rather than treated as a real zone.
    """
    acc = {}
    for node in graph.get("nodes", []):
        zid = int(node.get("zone_id", 0))
        if zid == 0:
            continue
        if zid not in acc:
            acc[zid] = {"mass": 0, "lat_sum": 0.0, "lon_sum": 0.0}
        a = acc[zid]
        a["mass"] += 1
        a["lat_sum"] += float(node["lat"])
        a["lon_sum"] += float(node["lon"])

    out = {}
    for zid, a in acc.items():
        out[zid] = {
            "mass": a["mass"],
            "lat": a["lat_sum"] / a["mass"],
            "lon": a["lon_sum"] / a["mass"],
        }

    # Second pass: each zone's characteristic radius, i.e. the mean distance
    # from its centroid to its own nodes. This is what makes intra-zone trips
    # behave sensibly -- see INTRA_ZONE_FACTOR.
    spread = {zid: [0.0, 0] for zid in out}
    for node in graph.get("nodes", []):
        zid = int(node.get("zone_id", 0))
        if zid not in out:
            continue
        c = out[zid]
        spread[zid][0] += _haversine(float(node["lat"]), float(node["lon"]),
                                     c["lat"], c["lon"])
        spread[zid][1] += 1
    for zid, (dist_sum, n) in spread.items():
        out[zid]["radius_m"] = (dist_sum / n) if n else 0.0

    return out


def build_proxy_matrix(graph, city, source_note="",
                       trips_per_node=TRIPS_PER_NODE_PER_DAY):
    """Build a schema-1.0 OD matrix from a road graph via a gravity model.

    Deterministic: no randomness, so repeated runs on the same graph produce a
    byte-identical matrix.
    """
    zones = zone_stats(graph)
    if len(zones) < 2:
        raise ValueError(
            "need at least 2 tagged zones to build a proxy OD matrix, found %d "
            "- run zones.py first" % len(zones))

    zone_ids = sorted(zones)

    # Pre-compute pairwise distance and the raw (unnormalised) gravity weight.
    total_daily_trips = sum(
        zones[z]["mass"] for z in zone_ids) * trips_per_node

    weights = {}
    weight_sum = 0.0
    for o in zone_ids:
        zo = zones[o]
        for d in zone_ids:
            zd = zones[d]
            if o == d:
                # Intra-zone: no centroid separation exists, so use a fraction
                # of the zone's own radius (see INTRA_ZONE_FACTOR).
                dist = INTRA_ZONE_FACTOR * zo.get("radius_m", 0.0)
            else:
                dist = _haversine(zo["lat"], zo["lon"], zd["lat"], zd["lon"])
            dist = max(dist, MIN_DISTANCE_M)
            w = ((zo["mass"] ** MASS_EXPONENT) * (zd["mass"] ** MASS_EXPONENT)
                 / (dist ** DISTANCE_EXPONENT))
            weights[(o, d)] = (w, dist)
            weight_sum += w

    od_entries = []
    for o in zone_ids:
        for d in zone_ids:
            w, dist = weights[(o, d)]
            pair_daily = total_daily_trips * (w / weight_sum)
            if pair_daily < 0.01:
                # Negligible flow; omitting keeps the matrix a sane size on
                # large graphs and costs nothing in the simulation.
                continue

            hourly = [round(pair_daily * f, 4) for f in DIURNAL_PROFILE]

            free_flow_s = (dist * DETOUR_FACTOR) / FREE_FLOW_MPS
            hourly_tt = [round(free_flow_s * c, 1) for c in CONGESTION_PROFILE]

            od_entries.append({
                "origin": o,
                "destination": d,
                "hourly": hourly,
                "hourly_tt": hourly_tt,
                "confidence": "low",
            })

    zones_out = {}
    for zid in zone_ids:
        z = zones[zid]
        zones_out[str(zid)] = {
            "name": "zone-%d" % zid,
            "lat": round(z["lat"], 6),
            "lon": round(z["lon"], 6),
            "mass_nodes": z["mass"],
        }

    return {
        "schema_version": "1.0",
        "city": city,
        "source": source_note or (
            "Synthetic gravity-model proxy derived from OSM road-node density. "
            "No real trip data was available for this city."),
        "source_url": "",
        "zone_count": len(zone_ids),
        "units": {"demand": "vehicles per hour (modelled weekday)",
                  "journey_time": "seconds (modelled, not observed)"},
        "sampled_weekdays": 0,
        "year_month": "",
        # Proxy-specific provenance. Consumers use these to distinguish
        # modelled data from measured data.
        "method": "gravity-density-proxy",
        "confidence": "low",
        "validation_safe": False,
        "model_parameters": {
            "mass_exponent": MASS_EXPONENT,
            "distance_exponent": DISTANCE_EXPONENT,
            "free_flow_mps": FREE_FLOW_MPS,
            "detour_factor": DETOUR_FACTOR,
            "trips_per_node_per_day": trips_per_node,
            "mass_proxy": "road node count per zone",
            "intra_zone_factor": INTRA_ZONE_FACTOR,
            "intra_zone_calibration": (
                "INTRA_ZONE_FACTOR tuned against Chicago's measured matrix to "
                "reproduce its 11.1% intra-zone trip share"),
        },
        "zones": zones_out,
        "od": od_entries,
    }


def _root():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a proxy OD matrix from road-graph density for "
                    "cities with no real OD feed.")
    parser.add_argument("--city", required=True)
    parser.add_argument("--trips-per-node", type=float,
                        default=TRIPS_PER_NODE_PER_DAY,
                        help="daily trips generated per road node (default: "
                             "%(default)s)")
    parser.add_argument("--out", default=None,
                        help="output path (default: data/<city>/od_matrix.json)")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "..", "cities.yaml"), "r") as f:
        import yaml
        config = yaml.safe_load(f)
    if args.city not in config:
        raise ValueError("City %s not found in cities.yaml" % args.city)

    od_cfg = config[args.city].get("od_source") or {}
    if od_cfg.get("type") not in ("density-proxy", "uniform", None):
        print("WARNING: %s declares od_source.type=%r; a real OD feed exists "
              "for this city and should be preferred over the proxy."
              % (args.city, od_cfg.get("type")))

    data_dir = os.path.join(_root(), "data", args.city)
    graph_path = os.path.join(data_dir, "graph.json")
    if not os.path.isfile(graph_path):
        raise SystemExit(
            "graph.json not found at %s - run the Phase 1 pipeline "
            "(download -> clean -> lanes -> zones -> export) first."
            % graph_path)

    with open(graph_path, "r") as f:
        graph = json.load(f)

    matrix = build_proxy_matrix(graph, args.city,
                                source_note=od_cfg.get("note", ""),
                                trips_per_node=args.trips_per_node)

    out_path = args.out or os.path.join(data_dir, "od_matrix.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(matrix, f, indent=1)

    total_daily = sum(sum(e["hourly"]) for e in matrix["od"])
    print("Wrote %s" % out_path)
    print("  zones:        %d" % matrix["zone_count"])
    print("  OD pairs:     %d" % len(matrix["od"]))
    print("  daily trips:  %.0f (modelled)" % total_daily)
    print("  confidence:   low (gravity-density proxy, not measured data)")
    print("  NOTE: this matrix is NOT valid input for validate.py, because its "
          "journey times are modelled rather than observed.")


if __name__ == "__main__":
    main()
