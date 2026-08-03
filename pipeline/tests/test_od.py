import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from download_od import _od_weekdays, FetchError
from od_matrix import _point_in_ring, _point_in_zone, _haversine


def test_weekday_selection():
    # October 2019: first weekday is Tue Oct 1.
    days = _od_weekdays(2019, 10, 3)
    assert len(days) == 3
    assert all(d.weekday() < 5 for d in days)
    assert str(days[0]) == "2019-10-01"


def test_fetch_error():
    try:
        raise FetchError("boom")
    except FetchError as e:
        assert "boom" in str(e)


def test_point_in_ring():
    square = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]
    assert _point_in_ring(0.5, 0.5, square)
    assert not _point_in_ring(1.5, 0.5, square)
    assert not _point_in_ring(-0.1, 0.5, square)


def test_point_in_zone():
    zone = {
        "bbox": [0.0, 0.0, 1.0, 1.0],
        "polygons": [[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0),
                      (0.0, 0.0)]],
    }
    assert _point_in_zone(0.25, 0.25, zone)
    assert not _point_in_zone(2.0, 0.5, zone)  # outside bbox


def test_haversine():
    # Chicago -> New York approx 1145 km.
    d = _haversine(41.878, -87.629, 40.7128, -74.006)
    assert 1_000_000 < d < 1_300_000


def _write_graph(nodes, edges):
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8")
    json.dump({"nodes": nodes, "edges": edges}, tmp)
    tmp.close()
    return tmp.name


def test_od_matrix_has_schema():
    from od_matrix import build_od_matrix
    cfg = {
        "dataset": "m6dm-c72p",
        "origin_column": "pickup_community_area",
        "destination_column": "dropoff_community_area",
        "timestamp_column": "trip_start_timestamp",
        "trip_seconds_column": "trip_seconds",
        "zones_dataset": "igwz-8jzy",
        "zone_column": "area_numbe",
        "zone_name_column": "community",
        "zone_geometry_column": "the_geom",
        "zone_type": "community-area",
        "note": "test",
    }
    out = os.path.join(tempfile.gettempdir(), "od_matrix_test.json")
    # Only exercises weighting math with a stub CSV we control.
    csv_path = os.path.join(tempfile.gettempdir(), "od_counts_test.csv")
    with open(csv_path, "w", newline="") as f:
        f.write("origin,destination,hour,trips,mean_trip_seconds\n")
        f.write("8,76,8,10,900\n")
        f.write("8,76,9,20,1000\n")
        f.write("32,76,8,30,1100\n")

    from od_matrix import build_od_matrix as _bom

    def _monkey(cfg, city, force=False):
        return {"8": {"name": "A", "polygons": [], "bbox": [0, 0, 0, 0]},
                "76": {"name": "B", "polygons": [], "bbox": [0, 0, 0, 0]},
                "32": {"name": "C", "polygons": [], "bbox": [0, 0, 0, 0]}}

    original = _bom.__globals__["fetch_boundaries"]
    _bom.__globals__["fetch_boundaries"] = _monkey
    try:
        _bom(cfg, "chicago", out, weekdays_sampled=1, counts_csv=csv_path)
    finally:
        _bom.__globals__["fetch_boundaries"] = original

    with open(out, "r") as f:
        m = json.load(f)
    assert m["schema_version"] == "1.0"
    assert m["zone_count"] == 3
    entry = next(e for e in m["od"]
                 if e["origin"] == 8 and e["destination"] == 76)
    assert entry["hourly"][8] == 10
    # Weighted mean TT over hours 8-9.
    w = 10 * 900 + 20 * 1000
    assert entry["hourly_tt"][8] == 900.0
    assert m["zones"]["8"]["name"] == "A"
    os.unlink(out)
    os.unlink(csv_path)
