# Graph Schema

The `graph.json` output by the pipeline follows this schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "nodes": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "integer" },
          "lat": { "type": "number" },
          "lon": { "type": "number" },
          "zone_id": { "type": "integer" }
        },
        "required": ["id", "lat", "lon", "zone_id"]
      }
    },
    "edges": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "u": { "type": "integer" },
          "v": { "type": "integer" },
          "length_m": { "type": "number" },
          "lanes": { "type": "integer" }
        },
        "required": ["u", "v", "length_m", "lanes"]
      }
    }
  },
  "required": ["nodes", "edges"]
}
```
