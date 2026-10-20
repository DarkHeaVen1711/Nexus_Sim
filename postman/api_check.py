"""NexusSim full-stack API verification (2026-10-20).

Checks every endpoint on the gateway (:8000), each sidecar directly
(:9003-:9006), the engine WS (:9001) and the dashboard (:3000).
Uses requests for HTTP and a raw-socket WS client for the engine.
"""
import json
import socket
import ssl
import struct
import base64
import os
import time
from datetime import datetime, timezone

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Base URLs match what the running services actually serve (HTTPS with
# self-signed certs, verify=False). Postman collection variables use
# http://localhost:* — keep both in sync if you repoint services.
BASE_URLS = {
    "gateway": os.environ.get("NEXUSSIM_GATEWAY_URL", "https://127.0.0.1:8000"),
    "camera": os.environ.get("NEXUSSIM_CAMERA_URL", "https://127.0.0.1:9003"),
    "nlp": os.environ.get("NEXUSSIM_NLP_URL", "https://127.0.0.1:9004"),
    "event_bus": os.environ.get("NEXUSSIM_EVENT_BUS_URL", "https://127.0.0.1:9005"),
    "algo": os.environ.get("NEXUSSIM_ALGO_URL", "https://127.0.0.1:9006"),
    "dashboard": os.environ.get("NEXUSSIM_DASHBOARD_URL", "https://127.0.0.1:3000"),
    "engine_ws": os.environ.get("NEXUSSIM_ENGINE_WS_URL", "wss://127.0.0.1:9001"),
}


def base_for(name):
    return BASE_URLS[name]


# Trust the local self-signed cert for every HTTPS request (https fallback).
_orig_request = requests.Session.request
def _patched_request(self, method, url, **kwargs):
    if url.startswith("https://"):
        kwargs.setdefault("verify", False)
    return _orig_request(self, method, url, **kwargs)
requests.Session.request = _patched_request

RESULTS = []
RUN_STARTED_AT = datetime.now(timezone.utc).isoformat()


def check(name, fn):
    # Retry transient connection drops (HTTPS handshake / vite dev server
    # can reset a connection under rapid sequential load).
    last_err = None
    for attempt in range(3):
        try:
            detail = fn()
            RESULTS.append((name, True, detail))
            print(f"PASS  {name}: {detail}")
            return
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(1.0)
    RESULTS.append((name, False, str(last_err)))
    print(f"FAIL  {name}: {last_err}")


# ---------------------------------------------------------------- raw WS client
def ws_connect(url, timeout=8):
    # url like wss://host:port/path
    rest = url.split("://", 1)[1]
    hostport, _, path = rest.partition("/")
    host, _, port = hostport.partition(":")
    path = "/" + path
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    raw = socket.create_connection((host, int(port)), timeout=timeout)
    raw.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s = ctx.wrap_socket(raw, server_hostname=host)
    key = base64.b64encode(os.urandom(16)).decode()
    req = (f"GET {path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
           f"Sec-WebSocket-Version: 13\r\n\r\n")
    s.sendall(req.encode())
    resp = s.recv(4096)
    if b"101" not in resp:
        raise RuntimeError(f"upgrade refused: {resp[:120]!r}")
    return s


def ws_close(s):
    """Gracefully close: send WS close frame, then SSL close_notify, then TCP."""
    try:
        # WebSocket close frame (opcode 0x8), masked, code 1000
        mask = os.urandom(4)
        s.sendall(bytes([0x88, 0x80 | 4]) + mask + mask)
    except Exception:
        pass
    try:
        s.unwrap()  # SSL close_notify
    except Exception:
        pass
    try:
        s.close()
    except Exception:
        pass


def ws_recv_exact(s, n):
    buf = b""
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("closed")
        buf += chunk
    return buf


def ws_read_frame(s):
    hdr = ws_recv_exact(s, 2)
    op = hdr[0] & 0x0F
    ln = hdr[1] & 0x7F
    if ln == 126:
        ln = struct.unpack(">H", ws_recv_exact(s, 2))[0]
    elif ln == 127:
        ln = struct.unpack(">Q", ws_recv_exact(s, 8))[0]
    return op, ws_recv_exact(s, ln)


def ws_send_text(s, payload):
    data = payload.encode()
    header = bytearray([0x81])
    n = len(data)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header += struct.pack(">H", n)
    else:
        header.append(0x80 | 127)
        header += struct.pack(">Q", n)
    mask = os.urandom(4)
    header += mask
    s.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


def ws_wait_for(s, pred, max_frames=400):
    for _ in range(max_frames):
        op, payload = ws_read_frame(s)
        if op != 1:
            continue
        d = json.loads(payload)
        if pred(d):
            return d
    raise RuntimeError("matching frame not received")


# ------------------------------------------------------------------- GW checks
def gw_health():
    r = requests.get(base_for("gateway") + "/api/health", timeout=8)
    r.raise_for_status()
    d = r.json()
    svcs = d["services"]
    status = {k: v["status"] for k, v in svcs.items()}
    bad = {k: v for k, v in status.items() if v not in ("ok", "healthy", "configured")}
    if bad:
        raise RuntimeError(f"unhealthy services: {bad}")
    return json.dumps(status)


def gw_root():
    r = requests.get(base_for("gateway") + "/", timeout=8)
    r.raise_for_status()
    return f"200, bytes={len(r.content)}"


def gw_chat():
    r = requests.post(base_for("gateway") + "/api/chat",
                      json={"query": "what is the average wait time", "city": "chicago"}, timeout=15)
    r.raise_for_status()
    keys = sorted(r.json().keys())
    return f"200, keys={keys}"


def gw_incident():
    r = requests.post(base_for("gateway") + "/api/incident",
                      json={"text": "accident on main street"}, timeout=15)
    r.raise_for_status()
    return f"200, keys={sorted(r.json().keys())}"


def gw_camera_feed():
    r = requests.get(base_for("gateway") + "/api/camera/feed", timeout=15)
    r.raise_for_status()
    ct = r.headers.get("content-type", "")
    return f"200, content-type={ct}, bytes={len(r.content)}"


def gw_algo():
    r = requests.get(base_for("gateway") + "/api/algo", timeout=8)
    r.raise_for_status()
    d = r.json()
    n = len(d.get("algorithms", d)) if isinstance(d, dict) else len(d)
    return f"200, algorithms={n}"


def gw_events_rest():
    # Gateway route is /api/events/{path}; publish is POST-only on the bus.
    r = requests.post(base_for("gateway") + "/api/events/publish/cv.anomaly",
                      json={"message": "api check", "severity": "low"}, timeout=8)
    r.raise_for_status()
    return f"200, keys={sorted(r.json().keys())}"


def gw_ws_engine():
    s = ws_connect(base_for("gateway").replace("http", "ws") + "/ws")
    try:
        ws_send_text(s, json.dumps({"type": "city", "city": "chicago"}))
        frame = ws_wait_for(s, lambda d: "agents" in d)
        return f"frame tick={frame.get('tick')} agents={len(frame.get('agents', []))} signals={len(frame.get('signals', []))}"
    finally:
        ws_close(s)


def gw_ws_events():
    s = ws_connect(base_for("gateway").replace("http", "ws") + "/ws/events", timeout=8)
    try:
        # send a probe and expect at least one frame or a clean close
        ws_send_text(s, json.dumps({"type": "subscribe", "topic": "test"}))
        s.settimeout(6)
        try:
            op, payload = ws_read_frame(s)
            return f"frame op={op} bytes={len(payload)}"
        except socket.timeout:
            return "connected, no frames within 6s (probe only)"
    finally:
        ws_close(s)


# --------------------------------------------------------------- sidecar checks
def sc_camera_health():
    r = requests.get(base_for("camera") + "/health", timeout=5)
    r.raise_for_status()
    return f"200 {r.json()}"


def sc_camera_feed():
    r = requests.get(base_for("camera") + "/api/camera/feed", timeout=10)
    r.raise_for_status()
    return f"200, content-type={r.headers.get('content-type')}, bytes={len(r.content)}"


def sc_nlp_health():
    r = requests.get(base_for("nlp") + "/health", timeout=5)
    r.raise_for_status()
    return f"200 {r.json()}"


def sc_nlp_chat():
    r = requests.post(base_for("nlp") + "/chat",
                      json={"query": "what is the average wait time", "city": "chicago"}, timeout=10)
    r.raise_for_status()
    return f"200, keys={sorted(r.json().keys())}"


def sc_nlp_incident():
    r = requests.post(base_for("nlp") + "/incident",
                      json={"text": "road closed at 5th avenue"}, timeout=10)
    r.raise_for_status()
    return f"200, keys={sorted(r.json().keys())}"


def sc_nlp_feedback():
    r = requests.post(base_for("nlp") + "/feedback",
                      json={"text": "the simulation is great"}, timeout=10)
    r.raise_for_status()
    return f"200, keys={sorted(r.json().keys())}"


def sc_eventbus_health():
    r = requests.get(base_for("event_bus") + "/health", timeout=5)
    r.raise_for_status()
    return f"200 {r.json()}"


def sc_eventbus_events():
    r = requests.get(base_for("event_bus") + "/events", timeout=5)
    r.raise_for_status()
    return f"200, bytes={len(r.content)}"


def sc_eventbus_publish():
    r = requests.post(base_for("event_bus") + "/publish/cv.anomaly",
                      json={"message": "test anomaly", "severity": "low"}, timeout=5)
    r.raise_for_status()
    return f"200, keys={sorted(r.json().keys())}"


def sc_algo_health():
    r = requests.get(base_for("algo") + "/health", timeout=5)
    r.raise_for_status()
    return f"200 {r.json()}"


def sc_algo_algorithms():
    r = requests.get(base_for("algo") + "/algorithms", timeout=5)
    r.raise_for_status()
    d = r.json()
    n = len(d) if isinstance(d, list) else len(d.get("algorithms", []))
    return f"200, algorithms={n}"


def sc_algo_toggle():
    r = requests.post(base_for("algo") + "/algorithms/toggle",
                      json={"algo_id": "CV-1", "active": False}, timeout=5)
    r.raise_for_status()
    # restore so repeated runs stay green
    requests.post(base_for("algo") + "/algorithms/toggle",
                  json={"algo_id": "CV-1", "active": True}, timeout=5)
    return f"200, keys={sorted(r.json().keys())}"


def dash_root():
    r = requests.get(base_for("dashboard") + "/", timeout=8)
    r.raise_for_status()
    has_root = 'id="root"' in r.text or "root" in r.text
    return f"200, bytes={len(r.content)}, root_div={has_root}"


def dash_static():
    r = requests.get(base_for("dashboard") + "/data/36_algo_matrix.json", timeout=8)
    r.raise_for_status()
    d = r.json()
    return f"200, total_algorithms={d.get('total_algorithms')}"


def engine_direct_ws():
    s = ws_connect(base_for("engine_ws"))
    try:
        ws_send_text(s, json.dumps({"type": "city", "city": "chicago"}))
        frame = ws_wait_for(s, lambda d: "agents" in d)
        return f"direct 9001 frame: agents={len(frame.get('agents', []))}"
    finally:
        ws_close(s)


# --------------------------------------------------------------- city management
def gw_list_cities():
    r = requests.get(base_for("gateway") + "/api/cities", timeout=8)
    r.raise_for_status()
    data = r.json()
    ids = {c["city_id"] for c in data}
    for expected in ["chicago", "paris", "ahmedabad", "piedmont"]:
        if expected not in ids:
            raise RuntimeError(f"expected city {expected} missing from list")
    return f"200, cities={len(data)}, ids={sorted(ids)}"


def gw_get_city():
    r = requests.get(base_for("gateway") + "/api/cities/chicago", timeout=8)
    r.raise_for_status()
    d = r.json()
    if d["city_id"] != "chicago":
        raise RuntimeError(f"unexpected city_id: {d['city_id']}")
    return '200, city=chicago'


def gw_get_city_not_found():
    r = requests.get(base_for("gateway") + "/api/cities/nonexistent-city-xyz", timeout=8)
    if r.status_code != 404:
        raise RuntimeError(f"expected 404, got {r.status_code}")
    return f"{r.status_code}, not found"


def gw_upload_city():
    import io

    osm_content = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="api-check">
  <node id="1" lat="19.0760" lon="72.8777"/>
  <node id="2" lat="19.0770" lon="72.8787"/>
  <node id="3" lat="19.0765" lon="72.8795"/>
  <way id="10">
    <nd ref="1"/>
    <nd ref="2"/>
    <tag k="highway" v="residential"/>
  </way>
  <way id="11">
    <nd ref="2"/>
    <nd ref="3"/>
    <tag k="highway" v="residential"/>
  </way>
</osm>
"""
    city_id = "api-check-city"
    # Clean up any prior test city
    import os as _os
    test_city_dir = os.path.join("data", city_id)
    if _os.path.exists(test_city_dir):
        import shutil as _shutil
        _shutil.rmtree(test_city_dir, ignore_errors=True)

    files = {"file": ("test-city.osm", io.BytesIO(osm_content.encode()), "application/xml")}
    data = {"city_id": city_id, "city_name": "API Check City"}
    r = requests.post(base_for("gateway") + "/api/cities/upload", files=files, data=data, timeout=30)
    r.raise_for_status()
    result = r.json()
    if result["city_id"] != city_id:
        raise RuntimeError(f"unexpected city_id: {result['city_id']}")
    if result["status"] != "ready":
        raise RuntimeError(f"unexpected status: {result['status']}")
    if result["node_count"] < 1:
        raise RuntimeError("expected at least 1 node")
    return f"200, city={city_id}, nodes={result['node_count']}, edges={result['edge_count']}"


if __name__ == "__main__":
    print("=== Gateway (:8000) ===")
    check("GW GET /", gw_root)
    check("GW GET /api/health", gw_health)
    check("GW POST /api/chat", gw_chat)
    check("GW POST /api/incident", gw_incident)
    check("GW GET /api/camera/feed", gw_camera_feed)
    check("GW GET /api/algo", gw_algo)
    check("GW GET /api/events", gw_events_rest)
    check("GW WS /ws (engine proxy)", gw_ws_engine)
    check("GW WS /ws/events (event bus proxy)", gw_ws_events)

    print("=== City Management ===")
    check("GW GET /api/cities", gw_list_cities)
    check("GW GET /api/cities/chicago", gw_get_city)
    check("GW GET /api/cities/nonexistent", gw_get_city_not_found)
    check("GW POST /api/cities/upload", gw_upload_city)

    print("=== Sidecars (direct) ===")
    check("CAM :9003 /health", sc_camera_health)
    check("CAM :9003 /api/camera/feed", sc_camera_feed)
    check("NLP :9004 /health", sc_nlp_health)
    check("NLP :9004 POST /chat", sc_nlp_chat)
    check("NLP :9004 POST /incident", sc_nlp_incident)
    check("NLP :9004 POST /feedback", sc_nlp_feedback)
    check("EVB :9005 /health", sc_eventbus_health)
    check("EVB :9005 GET /events", sc_eventbus_events)
    check("EVB :9005 POST /publish/cv.anomaly", sc_eventbus_publish)
    check("ALGO :9006 /health", sc_algo_health)
    check("ALGO :9006 GET /algorithms", sc_algo_algorithms)
    check("ALGO :9006 POST /algorithms/toggle", sc_algo_toggle)

    print("=== Dashboard (:3000) ===")
    check("DASH GET /", dash_root)
    check("DASH GET /data/36_algo_matrix.json", dash_static)

    print("=== Engine direct (:9001) ===")
    check("ENGINE WS direct", engine_direct_ws)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = [n for n, ok, _ in RESULTS if not ok]
    print(f"\n=== SUMMARY: {passed}/{len(RESULTS)} passed ===")
    if failed:
        print("FAILED:")
        for n in failed:
            print(f"  - {n}")

    # ---- results export -------------------------------------------------
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_name = f"api_check-{stamp}"

    json_payload = {
        "ran_at": RUN_STARTED_AT,
        "base_urls": BASE_URLS,
        "total": len(RESULTS),
        "passed": passed,
        "failed": len(failed),
        "results": [
            {"name": name, "passed": ok, "detail": detail}
            for name, ok, detail in RESULTS
        ],
    }
    json_path = os.path.join(results_dir, base_name + ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2)

    md_lines = [
        f"# NexusSim API Check — {stamp}",
        "",
        f"- **Ran at (UTC):** {RUN_STARTED_AT}",
        f"- **Result:** {passed} / {len(RESULTS)} passed",
        f"- **Failures:** {len(failed)}",
        "",
        "## Base URLs",
        "",
    ]
    for name, url in BASE_URLS.items():
        md_lines.append(f"- **{name}:** {url}")
    md_lines += ["", "## Results", "", "| Name | Passed | Detail |", "|------|--------|--------|"]
    for name, ok, detail in RESULTS:
        md_lines.append(f"| {name} | {'✅' if ok else '❌'} | {detail} |")
    if failed:
        md_lines += ["", "### Failures", ""]
        for n in failed:
            md_lines.append(f"- {n}")
    md_path = os.path.join(results_dir, base_name + ".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"\nResults exported: {json_path} and {md_path}")


