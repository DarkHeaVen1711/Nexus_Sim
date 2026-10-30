"""Generate the runnable Postman v2.1 collection + environment for NexusSim.

Produces:
- postman/NexusSim_API_Collection.json  (v2.1, import into Postman / run with Newman)
- postman/NexusSim_Environment.json     (variables for the gateway + auth token)

The collection covers every endpoint: A-H (original) + I (city management) +
J (auth & simulation) + K (platform services), each with pm.test assertions.

Run with Newman:
    npx newman run postman/NexusSim_API_Collection.json \
        -e postman/NexusSim_Environment.json \
        --insecure --reporters cli,htmlextra

Requires all services running (run.bat) and the gateway serving
HTTPS with the local self-signed cert.
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def test_scripts(*lines: str) -> list:
    """Build a Postman v2.1 test event array from JS source lines."""
    return [{"listen": "test", "script": {"type": "text/javascript", "exec": list(lines)}}]


def auth_header() -> dict:
    return {"key": "Authorization", "value": "Bearer {{auth_token}}", "type": "text"}


def ct_json() -> dict:
    return {"key": "Content-Type", "value": "application/json"}


def ct_form() -> dict:
    return {"key": "Content-Type", "value": "application/x-www-form-urlencoded"}


def req(name, method, url, headers=None, body=None, tests=None):
    headers = headers or []
    r = {
        "name": name,
        "request": {
            "method": method,
            "header": headers,
            "url": url,
        },
    }
    if body:
        r["request"]["body"] = body
    if tests:
        r["event"] = test_scripts(*tests)
    return r


def json_body(obj) -> dict:
    return {"mode": "raw", "raw": json.dumps(obj, indent=2),
            "options": {"raw": {"language": "json"}}}


def form_body(fields) -> dict:
    return {
        "mode": "urlencoded",
        "urlencoded": [{"key": k, "value": v, "type": "text"} for k, v in fields],
    }


def raw_form_body(fields) -> dict:
    return {
        "mode": "formdata",
        "formdata": [{"key": k, "value": v, "type": "text"} for k, v in fields],
    }


def folder(name, requests):
    return {"name": name, "item": requests}


def status_test(expected: int, label: str):
    return f"pm.test('{label} - Status {expected}', () => {{ pm.response.to.have.status({expected}); }});"


# ---------------------------------------------------------------------------
# Collection definition
# ---------------------------------------------------------------------------

def build_collection() -> dict:
    items = []

    # ---- A. Gateway ------------------------------------------------------
    items.append(folder("A - Gateway (:8000)", [
        req("A1 GET /api/health", "GET", "{{gw}}/api/health", tests=[
            status_test(200, "A1"),
            "pm.test('A1 - has services', () => { pm.expect(pm.response.json()).to.have.property('services'); });",
        ]),
        req("A2 POST /api/chat", "POST", "{{gw}}/api/chat", [ct_json()],
            json_body({"query": "what is the average wait time", "city": "chicago"}), [
            status_test(200, "A2"),
            "pm.test('A2 - keys', () => { const k = Object.keys(pm.response.json()); pm.expect(k).to.include.members(['intent','answer','confidence','handler']); });",
        ]),
        req("A3 POST /api/incident", "POST", "{{gw}}/api/incident", [ct_json()],
            json_body({"text": "accident on main street", "city": "chicago"}), [
            status_test(200, "A3"),
            "pm.test('A3 - keys', () => { const k = Object.keys(pm.response.json()); pm.expect(k).to.include.members(['status','message','incident_spec']); });",
        ]),
        req("A4 GET /api/camera/feed", "GET", "{{gw}}/api/camera/feed", tests=[
            status_test(200, "A4"),
            "pm.test('A4 - json feed', () => { pm.expect(pm.response.headers.get('content-type')).to.include('application/json'); });",
        ]),
        req("A5 GET /api/algo", "GET", "{{gw}}/api/algo", tests=[
            status_test(200, "A5"),
            "pm.test('A5 - 48 algorithms', () => { const d = pm.response.json(); const n = Array.isArray(d) ? d.length : d.algorithms.length; pm.expect(n).to.eql(48); });",
        ]),
        req("A6 POST /api/events/publish/cv.anomaly", "POST",
            "{{gw}}/api/events/publish/cv.anomaly", [ct_json()],
            json_body({"message": "test anomaly", "severity": "low"}), [
            status_test(200, "A6"),
            "pm.test('A6 - keys', () => { const k = Object.keys(pm.response.json()); pm.expect(k).to.include.members(['status','topic']); });",
        ]),
    ]))

    # ---- B. Virtual Camera ----------------------------------------------
    items.append(folder("B - Virtual Camera (:9003)", [
        req("B9 GET /health", "GET", "{{camera}}/health", tests=[status_test(200, "B9")]),
        req("B10 GET /api/camera/feed", "GET", "{{camera}}/api/camera/feed", tests=[
            status_test(200, "B10"),
            "pm.test('B10 - json', () => { pm.expect(pm.response.headers.get('content-type')).to.include('application/json'); });",
        ]),
    ]))

    # ---- C. NLP Chat -----------------------------------------------------
    items.append(folder("C - NLP Chat (:9004)", [
        req("C11 GET /health", "GET", "{{nlp}}/health", tests=[status_test(200, "C11")]),
        req("C12 POST /chat", "POST", "{{nlp}}/chat", [ct_json()],
            json_body({"query": "set signal mode fuzzy", "city": "chicago"}), [
            status_test(200, "C12"),
            "pm.test('C12 - keys', () => { const k = Object.keys(pm.response.json()); pm.expect(k).to.include.members(['intent','answer','confidence','handler']); });",
        ]),
        req("C13 POST /incident", "POST", "{{nlp}}/incident", [ct_json()],
            json_body({"text": "road closed at 5th avenue", "city": "chicago"}), [
            status_test(200, "C13"),
            "pm.test('C13 - keys', () => { const k = Object.keys(pm.response.json()); pm.expect(k).to.include.members(['status','message','incident_spec']); });",
        ]),
        req("C14 POST /feedback", "POST", "{{nlp}}/feedback", [ct_json()],
            json_body({"text": "the simulation is great", "city": "chicago"}), [
            status_test(200, "C14"),
            "pm.test('C14 - keys', () => { const k = Object.keys(pm.response.json()); pm.expect(k).to.include.members(['category','city','sentiment','status','text']); });",
        ]),
    ]))

    # ---- D. Event Bus ----------------------------------------------------
    items.append(folder("D - Event Bus (:9005)", [
        req("D15 GET /health", "GET", "{{eventbus}}/health", tests=[status_test(200, "D15")]),
        req("D16 GET /events", "GET", "{{eventbus}}/events", tests=[
            status_test(200, "D16"),
            "pm.test('D16 - array', () => { pm.expect(pm.response.json()).to.be.an('array'); });",
        ]),
        req("D17 POST /publish/cv.anomaly", "POST", "{{eventbus}}/publish/cv.anomaly", [ct_json()],
            json_body({"message": "test anomaly", "severity": "low"}), [
            status_test(200, "D17"),
            "pm.test('D17 - published', () => { pm.expect(pm.response.json().status).to.eql('published'); });",
        ]),
    ]))

    # ---- E. Algo Explorer ------------------------------------------------
    items.append(folder("E - Algo Explorer (:9006)", [
        req("E19 GET /health", "GET", "{{algo}}/health", tests=[
            status_test(200, "E19"),
            "pm.test('E19 - total 48', () => { pm.expect(pm.response.json().total_algorithms).to.eql(48); });",
        ]),
        req("E20 GET /algorithms", "GET", "{{algo}}/algorithms", tests=[
            status_test(200, "E20"),
            "pm.test('E20 - 48 items', () => { pm.expect(pm.response.json()).to.be.an('array').with.lengthOf(48); });",
        ]),
        req("E21a POST toggle disable CV-1", "POST", "{{algo}}/algorithms/toggle", [ct_json()],
            json_body({"algo_id": "CV-1", "active": False}), [
            status_test(200, "E21a"),
            "pm.test('E21a - DISABLED', () => { pm.expect(pm.response.json().algo.status).to.eql('DISABLED'); });",
        ]),
        req("E21b POST toggle restore CV-1", "POST", "{{algo}}/algorithms/toggle", [ct_json()],
            json_body({"algo_id": "CV-1", "active": True}), [
            status_test(200, "E21b"),
            "pm.test('E21b - ACTIVE', () => { pm.expect(pm.response.json().algo.status).to.eql('ACTIVE'); });",
        ]),
    ]))

    # ---- F. Dashboard ----------------------------------------------------
    items.append(folder("F - Dashboard (:3000)", [
        req("F22 GET /", "GET", "{{dashboard}}/", tests=[
            status_test(200, "F22"),
            "pm.test('F22 - root div', () => { pm.expect(pm.response.text()).to.include('root'); });",
        ]),
        req("F23 GET /data/36_algo_matrix.json", "GET", "{{dashboard}}/data/36_algo_matrix.json", tests=[
            status_test(200, "F23"),
            "pm.test('F23 - 48 algorithms', () => { pm.expect(pm.response.json().total_algorithms).to.eql(48); });",
        ]),
    ]))

    # ---- H. Edge Cases ---------------------------------------------------
    items.append(folder("H - Edge Cases", [
        req("H25 POST /api/chat wrong field -> 422", "POST", "{{gw}}/api/chat", [ct_json()],
            json_body({"message": "x"}), [
            status_test(422, "H25"),
        ]),
        req("H27 GET /api/events no path -> 404", "GET", "{{gw}}/api/events", tests=[
            status_test(404, "H27"),
        ]),
    ]))

    # ---- I. City Management ----------------------------------------------
    items.append(folder("I - City Management", [
        req("I28 GET /api/cities", "GET", "{{gw}}/api/cities", tests=[
            status_test(200, "I28"),
            "pm.test('I28 - has chicago', () => { const ids = pm.response.json().map(c => c.city_id); pm.expect(ids).to.include('chicago'); });",
        ]),
        req("I29 GET /api/cities/chicago", "GET", "{{gw}}/api/cities/chicago", tests=[
            status_test(200, "I29"),
            "pm.test('I29 - city_id', () => { pm.expect(pm.response.json().city_id).to.eql('chicago'); });",
        ]),
        req("I30 GET /api/cities/nonexistent -> 404", "GET",
            "{{gw}}/api/cities/nonexistent-city-xyz", tests=[status_test(404, "I30")]),
    ]))

    # ---- J. Auth & Simulation (login sets the token) ---------------------
    items.append(folder("J - Auth & Simulation", [
        req("J32 POST /api/auth/login", "POST", "{{gw}}/api/auth/login", [ct_form()],
            form_body([("username", "admin"), ("password", "admin")]), [
            status_test(200, "J32"),
            "pm.test('J32 - access_token', () => { pm.expect(pm.response.json()).to.have.property('access_token'); });",
            "pm.collectionVariables.set('auth_token', pm.response.json().access_token);",
        ]),
        req("J33 GET /api/auth/me", "GET", "{{gw}}/api/auth/me", [auth_header()], tests=[
            status_test(200, "J33"),
            "pm.test('J33 - username', () => { pm.expect(pm.response.json().username).to.eql('admin'); });",
        ]),
        req("J34 GET /api/workspaces", "GET", "{{gw}}/api/workspaces", [auth_header()], tests=[
            status_test(200, "J34"),
            "pm.test('J34 - ws_default', () => { const ids = pm.response.json().map(w => w.workspace_id); pm.expect(ids).to.include('ws_default'); });",
        ]),
        req("J35 POST /api/simulations", "POST", "{{gw}}/api/simulations", [auth_header(), ct_form()],
            form_body([
                ("city_id", "chicago"), ("workspace_id", "ws_default"),
                ("duration_min", "5"), ("agent_count", "100"), ("signal_mode", "auto"),
            ]), [
            status_test(200, "J35"),
            "pm.test('J35 - running', () => { pm.expect(pm.response.json().status).to.eql('running'); });",
            "pm.collectionVariables.set('test_sim_id', pm.response.json().simulation_id);",
        ]),
        req("J36 GET /api/simulations", "GET", "{{gw}}/api/simulations", [auth_header()], tests=[
            status_test(200, "J36"),
            "pm.test('J36 - array', () => { pm.expect(pm.response.json()).to.be.an('array'); });",
        ]),
        req("J37 GET /api/simulations/{{test_sim_id}}", "GET",
            "{{gw}}/api/simulations/{{test_sim_id}}", [auth_header()], tests=[
            status_test(200, "J37"),
            "pm.test('J37 - city', () => { pm.expect(pm.response.json().city_id).to.eql('chicago'); });",
        ]),
        req("J38 POST /api/scenarios", "POST", "{{gw}}/api/scenarios", [auth_header(), ct_form()],
            form_body([
                ("base_simulation_id", "{{test_sim_id}}"), ("fork_tick", "0"),
                ("signal_mode", "fuzzy"),
            ]), [
            status_test(200, "J38"),
            "pm.test('J38 - scenario running', () => { pm.expect(pm.response.json().status).to.eql('running'); });",
            "pm.collectionVariables.set('test_scenario_id', pm.response.json().scenario_id);",
        ]),
        req("J39 GET /api/scenarios/{{test_scenario_id}}", "GET",
            "{{gw}}/api/scenarios/{{test_scenario_id}}", [auth_header()], tests=[
            status_test(200, "J39"),
            "pm.test('J39 - scenario id', () => { pm.expect(pm.response.json()).to.have.property('scenario_id'); });",
        ]),
        req("J40 DELETE /api/simulations/{{test_sim_id}}", "DELETE",
            "{{gw}}/api/simulations/{{test_sim_id}}", [auth_header()], tests=[
            status_test(200, "J40"),
            "pm.test('J40 - deleted', () => { pm.expect(pm.response.json().status).to.eql('deleted'); });",
        ]),
    ]))

    # ---- K. Platform Services --------------------------------------------
    items.append(folder("K - Platform Services", [
        req("K41 GET /api/platform/ttl", "GET", "{{gw}}/api/platform/ttl", [auth_header()], tests=[
            status_test(200, "K41"),
            "pm.test('K41 - ttl_seconds', () => { pm.expect(pm.response.json().ttl_seconds).to.be.above(0); });",
        ]),
        req("K42 GET /api/algo/registry", "GET", "{{gw}}/api/algo/registry", [auth_header()], tests=[
            status_test(200, "K42"),
            "pm.test('K42 - array', () => { pm.expect(pm.response.json()).to.be.an('array'); });",
        ]),
        req("K43 POST /api/algo/register", "POST", "{{gw}}/api/algo/register",
            [auth_header(), ct_form()],
            form_body([
                ("algo_id", "postman_custom_rl"), ("name", "Postman Custom RL"),
                ("discipline", "RL"), ("version", "1.0.0"),
                ("onnx_path", "s3://models/postman_custom_rl.onnx"),
            ]), [
            "pm.test('K43 - Status 200 or 409', () => { pm.expect(pm.response.code).to.be.oneOf([200, 409]); });",
            "pm.test('K43 - Response has expected structure', () => {",
            "  const json = pm.response.json();",
            "  if (pm.response.code === 200) {",
            "    pm.expect(json.status).to.eql('registered');",
            "    pm.expect(json.algo.algo_id).to.eql('postman_custom_rl');",
            "    pm.expect(json.algo.validation_status).to.eql('pending');",
            "    pm.collectionVariables.set('registered_algo_id', json.algo.algo_id);",
            "  } else {",
            "    // 409 - already exists, still set the variable for subsequent tests",
            "    pm.collectionVariables.set('registered_algo_id', 'postman_custom_rl');",
            "    pm.expect(json.detail).to.include('already registered');",
            "  }",
            "});",
        ]),
        req("K44 POST /api/algo/registry/{{registered_algo_id}}/validate", "POST",
            "{{gw}}/api/algo/registry/{{registered_algo_id}}/validate",
            [auth_header(), ct_form()], form_body([("status", "validated")]), [
            "pm.test('K44 - Status 200 or 404', () => { pm.expect(pm.response.code).to.be.oneOf([200, 404]); });",
            "if (pm.response.code === 200) {",
            "  pm.test('K44 - validated', () => { pm.expect(pm.response.json().validation_status).to.eql('validated'); });",
            "  pm.test('K44 - status is updated', () => { pm.expect(pm.response.json().status).to.eql('updated'); });",
            "  pm.test('K44 - algo_id matches', () => {",
            "    pm.expect(pm.response.json().algo_id).to.eql(pm.collectionVariables.get('registered_algo_id'));",
            "  });",
            "}",
        ]),
        req("K45 POST /api/emissions", "POST", "{{gw}}/api/emissions",
            [auth_header(), ct_form()],
            form_body([("agent_type", "car"), ("distance_km", "100"), ("idle_minutes", "10")]), [
            status_test(200, "K45"),
            "pm.test('K45 - co2', () => { pm.expect(pm.response.json().co2_g).to.be.above(0); });",
        ]),
        req("K46 POST /api/emissions/aggregate", "POST", "{{gw}}/api/emissions/aggregate",
            [auth_header(), ct_json()],
            json_body({"agents": [
                {"agent_type": "car", "distance_km": 50.0, "idle_minutes": 5.0},
                {"agent_type": "ev", "distance_km": 50.0, "idle_minutes": 5.0},
            ]}), [
            status_test(200, "K46"),
            "pm.test('K46 - 2 agents', () => { pm.expect(pm.response.json().total_agents).to.eql(2); });",
        ]),
        req("K47 GET /api/ingest/feeds", "GET", "{{gw}}/api/ingest/feeds", [auth_header()], tests=[
            status_test(200, "K47"),
            "pm.test('K47 - 4 feeds', () => { const t = pm.response.json().feeds.map(f => f.feed_type); pm.expect(t).to.have.members(['gtfs','cv2x','mqtt','weather']); });",
        ]),
        req("K48 POST /api/ingest/gtfs", "POST", "{{gw}}/api/ingest/gtfs",
            [auth_header(), ct_json()],
            json_body({"vehicle_id": "V1", "route_id": "R1", "lat": 19.07, "lon": 72.87, "speed_kph": 25.0}), [
            status_test(200, "K48"),
            "pm.test('K48 - nlp.incident', () => { pm.expect(pm.response.json().event.topic).to.eql('nlp.incident'); });",
        ]),
        req("K49 POST /api/ingest/weather", "POST", "{{gw}}/api/ingest/weather",
            [auth_header(), ct_json()],
            json_body({"city": "mumbai", "precip_mm": 10.0, "wind_kph": 50.0, "visibility_m": 1000}), [
            status_test(200, "K49"),
            "pm.test('K49 - demand < 1', () => { pm.expect(pm.response.json().event.payload.demand_multiplier).to.be.below(1.0); });",
        ]),
        req("K50 GET /api/platform/rate-limit", "GET", "{{gw}}/api/platform/rate-limit",
            [auth_header()], tests=[
            status_test(200, "K50"),
            "pm.test('K50 - stats', () => { pm.expect(pm.response.json()).to.have.property('tracked_requests'); });",
        ]),
    ]))

    # ---- L. NexusTwin Digital Twin ---------------------------------------
    items.append(folder("L - NexusTwin Digital Twin (:8000)", [
        req("L51 GET /api/v1/twin/cities", "GET", "{{gw}}/api/v1/twin/cities", tests=[
            status_test(200, "L51"),
            "pm.test('L51 - array response', () => { pm.expect(pm.response.json()).to.be.an('array'); });",
        ]),
        req("L52 POST /api/v1/twin/search empty query -> 400", "POST", "{{gw}}/api/v1/twin/search", [ct_json()],
            json_body({"query": "   "}), [
            status_test(400, "L52"),
            "pm.test('L52 - validation error detail', () => { pm.expect(pm.response.json().detail).to.include('empty'); });",
        ]),
        req("L53 POST /api/v1/twin/search valid query", "POST", "{{gw}}/api/v1/twin/search", [ct_json()],
            json_body({"query": "Shantigram, Ahmedabad", "workspace_id": "ws_default"}), [
            status_test(200, "L53"),
            "pm.test('L53 - status queued', () => { pm.expect(pm.response.json().status).to.eql('queued'); });",
            "pm.test('L53 - has job_id', () => { pm.expect(pm.response.json()).to.have.property('job_id'); });",
            "pm.collectionVariables.set('twin_job_id', pm.response.json().job_id);",
        ]),
        req("L54 GET /api/v1/twin/progress/:job_id", "GET", "{{gw}}/api/v1/twin/progress/{{twin_job_id}}", tests=[
            "pm.test('L54 - Status 200 or 404', () => { pm.expect(pm.response.code).to.be.oneOf([200, 404]); });",
            "if (pm.response.code === 200) {",
            "  pm.test('L54 - progress has stage & pct', () => {",
            "    const d = pm.response.json();",
            "    pm.expect(d).to.have.property('stage');",
            "    pm.expect(d).to.have.property('progress_pct');",
            "  });",
            "}",
        ]),
        req("L55 GET /api/v1/twin/progress/nonexistent -> 404", "GET", "{{gw}}/api/v1/twin/progress/nonexistent_twin_job", tests=[
            status_test(404, "L55"),
        ]),
        req("L56 DELETE /api/v1/twin/cities/invalid..path -> 400", "DELETE", "{{gw}}/api/v1/twin/cities/..invalid", tests=[
            status_test(400, "L56"),
            "pm.test('L56 - invalid path detail', () => { pm.expect(pm.response.json().detail).to.include('Invalid'); });",
        ]),
        req("L57 DELETE /api/v1/twin/cities/nonexistent -> 404", "DELETE", "{{gw}}/api/v1/twin/cities/nonexistent-twin-city", tests=[
            status_test(404, "L57"),
            "pm.test('L57 - city not found detail', () => { pm.expect(pm.response.json().detail).to.include('not found'); });",
        ]),
    ]))

    return {
        "info": {
            "name": "NexusSim API",
            "description": (
                "Full-stack API collection for NexusSim. Import into Postman (File > Import) "
                "and run top to bottom. Covers A-H (original), I (city management), "
                "J (auth & simulation), K (platform services), L (NexusTwin dynamic digital twin). All services must be running "
                "(run.bat). Gateway serves HTTPS with a local self-signed cert."
            ),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [
            {"key": "gw", "value": "https://localhost:8000"},
            {"key": "engine", "value": "https://localhost:9001"},
            {"key": "camera", "value": "https://localhost:9003"},
            {"key": "nlp", "value": "https://localhost:9004"},
            {"key": "eventbus", "value": "https://localhost:9005"},
            {"key": "algo", "value": "https://localhost:9006"},
            {"key": "dashboard", "value": "https://localhost:3000"},
            {"key": "auth_token", "value": ""},
            {"key": "test_sim_id", "value": ""},
            {"key": "test_scenario_id", "value": ""},
            {"key": "registered_algo_id", "value": ""},
            {"key": "twin_job_id", "value": ""},
        ],
        "item": items,
    }


def build_environment() -> dict:
    # NOTE: only static base URLs live here. Dynamic values (auth_token,
    # test_sim_id, ...) must NOT be in the environment, because environment
    # variables override collection variables and would blank the token set by
    # the J32 login test script.
    return {
        "id": "nexussim-local-env",
        "name": "NexusSim Local (HTTPS)",
        "values": [
            {"key": "gw", "value": "https://localhost:8000", "enabled": True},
            {"key": "engine", "value": "https://localhost:9001", "enabled": True},
            {"key": "camera", "value": "https://localhost:9003", "enabled": True},
            {"key": "nlp", "value": "https://localhost:9004", "enabled": True},
            {"key": "eventbus", "value": "https://localhost:9005", "enabled": True},
            {"key": "algo", "value": "https://localhost:9006", "enabled": True},
            {"key": "dashboard", "value": "https://localhost:3000", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
    }


def main():
    collection = build_collection()
    env = build_environment()

    col_path = os.path.join(HERE, "NexusSim_API_Collection.json")
    env_path = os.path.join(HERE, "NexusSim_Environment.json")

    with open(col_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2)
    with open(env_path, "w", encoding="utf-8") as f:
        json.dump(env, f, indent=2)

    n_folders = len(collection["item"])
    n_requests = sum(len(fo["item"]) for fo in collection["item"])
    print(f"Wrote {col_path} ({n_folders} folders, {n_requests} requests)")
    print(f"Wrote {env_path}")


if __name__ == "__main__":
    main()
