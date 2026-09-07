from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from pathlib import Path
from urllib.parse import urlparse
import json
import os
from typing import Any

from .core import (
    VERSION,
    compile_capsule,
    route_capsule,
    record_contribution,
    issue_true_value_receipt,
    generate_open_calls,
    summary,
)
from .store import WorkspaceStore


class AppHandler(SimpleHTTPRequestHandler):
    server_version = f"COMMONBRIDGE85/{VERSION}"

    @property
    def app(self) -> "CommonBridgeServer":
        return self.server  # type: ignore[return-value]

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; connect-src 'self'")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length > 2_000_000:
            raise ValueError("request body too large")
        data = self.rfile.read(length) if length else b"{}"
        obj = json.loads(data.decode("utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("JSON object required")
        return obj

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json(200, {"status": "ok", "version": VERSION, "system": "DIKWP COMMONBRIDGE-85"})
            return
        if path == "/api/summary":
            payload = summary()
            payload["workspace_counts"] = self.app.store.counts()
            payload["audit"] = self.app.store.verify_audit()
            self._json(200, payload)
            return
        if path == "/api/open-calls":
            result = generate_open_calls(
                self.app.store.list("capsule"),
                self.app.store.list("route"),
                self.app.store.list("contribution"),
            )
            self._json(200, result)
            return
        if path == "/api/audit":
            self._json(200, {"events": self.app.store.audit()})
            return
        if path == "/api/audit/verify":
            self._json(200, self.app.store.verify_audit())
            return
        if path.startswith("/api/object/"):
            object_id = path.rsplit("/", 1)[-1]
            obj = self.app.store.get(object_id)
            if obj is None:
                self._json(404, {"error": "not found"})
            else:
                self._json(200, obj)
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/capsules":
                obj = compile_capsule(payload)
                self.app.store.put("capsule", obj, obj["capsule_id"])
                self._json(201, obj)
                return
            if path == "/api/routes":
                capsule = payload.get("capsule")
                profile = payload.get("profile")
                if not isinstance(capsule, dict) or not isinstance(profile, dict):
                    raise ValueError("capsule and profile objects required")
                obj = route_capsule(capsule, profile)
                self.app.store.put("route", obj, obj["route_id"])
                self._json(201, obj)
                return
            if path == "/api/contributions":
                capsule = payload.get("capsule")
                route = payload.get("route")
                contribution = payload.get("contribution")
                if not isinstance(capsule, dict) or not isinstance(route, dict) or not isinstance(contribution, dict):
                    raise ValueError("capsule, route and contribution objects required")
                obj = record_contribution(capsule, route, contribution)
                self.app.store.put("contribution", obj, obj["contribution_id"])
                self._json(201, obj)
                return
            if path == "/api/value-receipts":
                contribution = payload.get("contribution")
                outcome = payload.get("outcome")
                if not isinstance(contribution, dict) or not isinstance(outcome, dict):
                    raise ValueError("contribution and outcome objects required")
                obj = issue_true_value_receipt(contribution, outcome)
                self.app.store.put("receipt", obj, obj["receipt_id"])
                self._json(201, obj)
                return
            if path == "/api/demo/reset":
                self.app.store.reset()
                self._json(200, {"status": "reset"})
                return
            self._json(404, {"error": "unknown endpoint"})
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
        except Exception as exc:  # safe boundary: no stack trace to client
            self._json(500, {"error": "internal error", "detail": type(exc).__name__})

    def log_message(self, fmt: str, *args: Any) -> None:
        if os.environ.get("COMMONBRIDGE85_QUIET") != "1":
            super().log_message(fmt, *args)


class CommonBridgeServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], directory: str | Path, db_path: str | Path):
        self.directory = str(directory)
        self.store = WorkspaceStore(db_path)

        handler = partial(AppHandler, directory=self.directory)
        super().__init__(address, handler)


def serve(directory: str | Path, host: str = "127.0.0.1", port: int = 8784, db_path: str | Path | None = None) -> None:
    directory = Path(directory)
    db_path = db_path or directory / "var" / "commonbridge85.db"
    server = CommonBridgeServer((host, port), directory, db_path)
    print(f"DIKWP COMMONBRIDGE-85 v{VERSION} -> http://{host}:{port}")
    print("External network and external write-back are disabled in the reference runtime.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
