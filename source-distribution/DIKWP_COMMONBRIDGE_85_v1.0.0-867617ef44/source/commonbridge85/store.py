from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator


def _canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class WorkspaceStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def conn(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def _init_db(self) -> None:
        with self.conn() as db:
            db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS objects (
                    object_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    object_id TEXT,
                    payload_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    previous_hash TEXT,
                    event_hash TEXT NOT NULL
                );
                """
            )

    def _audit(self, db: sqlite3.Connection, event_type: str, object_id: str | None, payload_sha256: str) -> None:
        prev = db.execute("SELECT event_hash FROM audit_events ORDER BY seq DESC LIMIT 1").fetchone()
        previous_hash = prev["event_hash"] if prev else None
        body = {
            "event_type": event_type,
            "object_id": object_id,
            "payload_sha256": payload_sha256,
            "created_at": _now(),
            "previous_hash": previous_hash,
        }
        event_hash = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
        db.execute(
            "INSERT INTO audit_events(event_type, object_id, payload_sha256, created_at, previous_hash, event_hash) VALUES(?,?,?,?,?,?)",
            (event_type, object_id, payload_sha256, body["created_at"], previous_hash, event_hash),
        )

    def put(self, kind: str, obj: dict[str, Any], object_id: str | None = None) -> str:
        object_id = object_id or str(
            obj.get("capsule_id")
            or obj.get("route_id")
            or obj.get("contribution_id")
            or obj.get("receipt_id")
            or obj.get("profile_id")
            or obj.get("sha256")
        )
        if not object_id or object_id == "None":
            object_id = f"{kind}-{hashlib.sha256(_canonical(obj).encode('utf-8')).hexdigest()[:16]}"
        payload = json.dumps(obj, ensure_ascii=False, sort_keys=True)
        sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        with self.conn() as db:
            db.execute(
                "INSERT OR REPLACE INTO objects(object_id,kind,payload_json,sha256,created_at) VALUES(?,?,?,?,?)",
                (object_id, kind, payload, sha, _now()),
            )
            self._audit(db, f"PUT_{kind.upper()}", object_id, sha)
        return object_id

    def get(self, object_id: str) -> dict[str, Any] | None:
        with self.conn() as db:
            row = db.execute("SELECT payload_json FROM objects WHERE object_id=?", (object_id,)).fetchone()
            return json.loads(row["payload_json"]) if row else None

    def list(self, kind: str | None = None) -> list[dict[str, Any]]:
        with self.conn() as db:
            if kind:
                rows = db.execute("SELECT payload_json FROM objects WHERE kind=? ORDER BY created_at", (kind,)).fetchall()
            else:
                rows = db.execute("SELECT payload_json FROM objects ORDER BY created_at").fetchall()
            return [json.loads(row["payload_json"]) for row in rows]

    def counts(self) -> dict[str, int]:
        with self.conn() as db:
            rows = db.execute("SELECT kind, COUNT(*) c FROM objects GROUP BY kind ORDER BY kind").fetchall()
            return {row["kind"]: int(row["c"]) for row in rows}

    def audit(self, limit: int = 200) -> list[dict[str, Any]]:
        with self.conn() as db:
            rows = db.execute(
                "SELECT seq,event_type,object_id,payload_sha256,created_at,previous_hash,event_hash FROM audit_events ORDER BY seq DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def verify_audit(self) -> dict[str, Any]:
        with self.conn() as db:
            rows = db.execute(
                "SELECT seq,event_type,object_id,payload_sha256,created_at,previous_hash,event_hash FROM audit_events ORDER BY seq"
            ).fetchall()
        errors: list[str] = []
        previous_hash: str | None = None
        for row in rows:
            body = {
                "event_type": row["event_type"],
                "object_id": row["object_id"],
                "payload_sha256": row["payload_sha256"],
                "created_at": row["created_at"],
                "previous_hash": row["previous_hash"],
            }
            expected = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
            if row["previous_hash"] != previous_hash:
                errors.append(f"seq {row['seq']}: previous hash mismatch")
            if row["event_hash"] != expected:
                errors.append(f"seq {row['seq']}: event hash mismatch")
            previous_hash = row["event_hash"]
        return {
            "valid": not errors,
            "event_count": len(rows),
            "head_hash": previous_hash,
            "errors": errors,
        }

    def reset(self) -> None:
        with self.conn() as db:
            db.execute("DELETE FROM objects")
            db.execute("DELETE FROM audit_events")
