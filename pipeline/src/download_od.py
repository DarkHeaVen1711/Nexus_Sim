"""Phase 6.1 - Download real origin-destination demand data for a city.

For Chicago this fetches the City of Chicago Transportation Network Provider
(Uber/Lyft) trips dataset via the Socrata API, aggregated server-side by
origin community area x destination community area x hour-of-day. This is the
same underlying rideshare data Uber Movement was built on.

Output: data/<city>/od_counts.csv
Columns: origin,destination,hour,trips,mean_trip_seconds

The pipeline reads city configuration from cities.yaml (od_source block).
"""
import argparse
import calendar
import csv
import datetime as dt
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


class FetchError(RuntimeError):
    pass


def _fetch(url, retries=3, timeout=180):
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
    for attempt in range(retries):
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return raw.decode("utf-8")
        except Exception as exc:
            if attempt == retries - 1:
                raise FetchError("fetch failed: %s" % exc) from exc
            time.sleep(2 * (attempt + 1))
    raise FetchError("unreachable")


def _od_weekdays(year, month, max_weekdays):
    out = []
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        d = dt.date(year, month, day)
        if d.weekday() < 5:
            out.append(d)
        if len(out) >= max_weekdays:
            break
    return out


def _query_hour_grouped(cfg, day, hour):
    """Server-side group-by OD pair for a single hour bucket."""
    dataset = cfg["dataset"]
    origin_col = cfg["origin_column"]
    dest_col = cfg["destination_column"]
    ts_col = cfg["timestamp_column"]
    seconds_col = cfg["trip_seconds_column"]
    base = "https://data.cityofchicago.org/resource/%s.csv" % dataset
    lo = "%sT%02d:00:00" % (day.isoformat(), hour)
    if hour == 23:
        hi_day = day + dt.timedelta(days=1)
        hi = "%sT00:00:00" % hi_day.isoformat()
    else:
        hi = "%sT%02d:00:00" % (day.isoformat(), hour + 1)
    where = "%s >= '%s' AND %s < '%s'" % (ts_col, lo, ts_col, hi)
    sel = "%s,%s,count(*) as trips,avg(%s) as mean_trip_seconds" % (
        origin_col, dest_col, seconds_col)
    grp = "%s,%s" % (origin_col, dest_col)
    url = (base + "?$select=" + urllib.parse.quote(sel)
           + "&$where=" + urllib.parse.quote(where)
           + "&$group=" + urllib.parse.quote(grp))
    text = _fetch(url)
    rows = []
    for line in csv.DictReader(text.splitlines()):
        origin = (line.get(origin_col) or "").strip()
        dest = (line.get(dest_col) or "").strip()
        if not origin or not dest:
            continue
        rows.append({
            "origin": int(origin),
            "destination": int(dest),
            "trips": float(line.get("trips") or 0),
            "mean_trip_seconds": float(line.get("mean_trip_seconds") or 0),
        })
    return rows


def download_city(cfg, out_csv, weekdays=10, year=2019, month=10):
    """Aggregate OD counts over sampled weekdays into a single CSV."""
    days = _od_weekdays(year, month, weekdays)
    print("Fetching %d weekdays (%s-%s) x 24 hours..." % (
        len(days), days[0], days[-1]))
    n_queries = 0
    all_rows = {}
    for day in days:
        for hour in range(24):
            rows = _query_hour_grouped(cfg, day, hour)
            n_queries += 1
            if n_queries % 12 == 0:
                print("... %d/%d queries done" % (
                    n_queries, len(days) * 24), file=sys.stderr)
                sys.stderr.flush()
            for r in rows:
                key = (r["origin"], r["destination"], hour)
                prev = all_rows.setdefault(key, {
                    "origin": r["origin"],
                    "destination": r["destination"],
                    "hour": hour,
                    "trips": 0.0,
                    "trip_seconds_sum": 0.0,
                })
                prev["trips"] += r["trips"]
                prev["trip_seconds_sum"] += r["trips"] * r["mean_trip_seconds"]
            time.sleep(0.1)
    print("Done: %d queries, %d OD x hour pairs" % (n_queries, len(all_rows)))

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["origin", "destination", "hour",
                         "trips", "mean_trip_seconds"])
        for key in sorted(all_rows):
            r = all_rows[key]
            mean_tt = (r["trip_seconds_sum"] / r["trips"]
                       if r["trips"] > 0 else 0.0)
            writer.writerow([r["origin"], r["destination"], r["hour"],
                             r["trips"], "%.1f" % mean_tt])
    print("Saved OD counts to %s" % out_csv)
    return out_csv


def main():
    parser = argparse.ArgumentParser(description="Download OD demand data")
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
    if args.city not in config:
        raise ValueError("City %s not found in cities.yaml" % args.city)
    od_cfg = config[args.city].get("od_source")
    if not od_cfg or od_cfg.get("type") != "socrata":
        raise ValueError(
            "City %s has no socrata od_source configured" % args.city)

    out_csv = os.path.join(here, "..", "..", "data",
                           "uber-movement-" + args.city, "od_counts.csv")
    download_city(od_cfg, out_csv, args.weekdays, args.year, args.month)


if __name__ == "__main__":
    main()
