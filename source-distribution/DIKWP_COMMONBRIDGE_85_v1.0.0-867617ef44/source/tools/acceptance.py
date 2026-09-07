from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import time
import urllib.request
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from commonbridge85.core import compile_capsule, route_capsule
from commonbridge85.server import CommonBridgeServer

checks = []

def check(name, ok, detail=""):
    checks.append({"name": name, "passed": bool(ok), "detail": detail})

with tempfile.TemporaryDirectory() as td:
    server = CommonBridgeServer(("127.0.0.1", 0), ROOT, Path(td) / "db.sqlite")
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(.15)
    def get(path):
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
            return r.status, json.loads(r.read()) if path.startswith("/api/") else r.read()
    status, health = get("/api/health")
    check("health", status == 200 and health["status"] == "ok")
    status, summary = get("/api/summary")
    check("summary", status == 200 and summary["invariants"]["no_person_grading"])
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=5) as r:
        body = r.read().decode("utf-8")
        check("frontend", "COMMONBRIDGE" in body and "创建协作胶囊" in body)
    payload = json.dumps({"title":"demo","problem":"offline"}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/capsules", data=payload, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        capsule = json.loads(r.read())
        check("create_capsule", r.status == 201 and capsule["mesh85"]["semantic_11111"])
    route_payload = json.dumps({"capsule":capsule,"profile":{"tier":"H0_MANUAL"}}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/routes", data=route_payload, headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as r:
        route = json.loads(r.read())
        check("route", r.status == 201 and route["lawful_resilience"]["controls_bypassed"] is False)
    status, calls = get("/api/open-calls")
    check("open_calls", status == 200 and calls["count"] > 0)
    status, audit = get("/api/audit/verify")
    check("audit", status == 200 and audit["valid"])
    server.shutdown(); server.server_close(); thread.join(timeout=2)

failed=[c for c in checks if not c["passed"]]
report={"suite":"acceptance","passed":len(checks)-len(failed),"total":len(checks),"checks":checks}
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(1 if failed else 0)
