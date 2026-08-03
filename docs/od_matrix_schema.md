# OD Matrix Schema

`data/<city>/od_matrix.json` produced by `pipeline/src/od_matrix.py` follows
this schema. The engine's OD demand spawner (`--od`) reads this file directly.

```json
{
  "schema_version": "1.0",
  "city": "chicago",
  "source": "free-text provenance note",
  "source_url": "data portal URL",
  "zone_count": 77,
  "units": {
    "demand": "vehicles per hour (avg sampled weekday)",
    "journey_time": "seconds"
  },
  "sampled_weekdays": 10,
  "year_month": "2019-10",
  "zones": {
    "8": { "name": "Near North Side", "lat": 41.9, "lon": -87.63 }
  },
  "od": [
    {
      "origin": 8,
      "destination": 76,
      "hourly": [0, 0, 0, 0, 5.2, 18.9, 54.1, 120.0],
      "hourly_tt": [0, 0, 0, 0, 742.0, 810.5, 943.2, 1010.3]
    }
  ]
}
```

## Fields

| Field             | Type             | Description                                                |
|-------------------|------------------|------------------------------------------------------------|
| `schema_version`  | string           | Schema version for forward compatibility                    |
| `city`            | string           | City id matching `cities.yaml`                              |
| `source`          | string           | Provenance of the demand data                               |
| `source_url`      | string           | Where the raw data was obtained                             |
| `zone_count`      | int              | Number of demand zones                                      |
| `units`           | object           | Units of `hourly` and `hourly_tt`                           |
| `sampled_weekdays`| int              | Number of weekdays aggregated to form the matrix            |
| `year_month`      | string           | Data period, `YYYY-MM`                                      |
| `zones`           | object           | `zone_id -> {name, lat, lon}`; the lon/lat is a zone centroid|
| `od`              | array            | One entry per origin-destination pair with non-zero demand  |
| `od[].origin`     | int              | Origin zone id (matches graph `node.zone_id`)               |
| `od[].destination`| int              | Destination zone id                                         |
| `od[].hourly`     | array[24]        | Vehicles/hour for hours 0-23 (average over sampled weekdays)|
| `od[].hourly_tt`  | array[24]        | Mean observed journey time (seconds) for hours 0-23, weighted by demand |

## Zone system

Zones are the city's real statistical zones (e.g. Chicago's 77 community
areas). Every graph node is tagged with the zone containing its coordinates
(`zone_id`); the engine maps OD zones to graph nodes through this id. Pairs
whose zones have no graph nodes are dropped when the engine loads the matrix.
