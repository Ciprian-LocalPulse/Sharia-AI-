"""SQLite audit trail for API compliance decisions.

The store is intentionally small, but production-oriented: events are written
with a hash chain so later verification can detect accidental or malicious
tampering with recorded compliance decisions.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    request_id: str
    endpoint: str
    subject: str
    decision: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class StoredAuditEvent:
    id: int
    created_at_utc: str
    request_id: str
    endpoint: str
    subject: str
    decision: str
    payload: dict[str, Any]
    previous_event_hash: str | None
    event_hash: str


class SQLiteAuditStore:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._lock = Lock()

    def record(self, event: AuditEvent) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, closing(sqlite3.connect(self.db_path)) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at_utc TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    previous_event_hash TEXT,
                    event_hash TEXT NOT NULL
                )
                """
            )
            self._ensure_hash_columns(connection)
            previous_hash = self._latest_event_hash(connection)
            created_at = datetime.now(timezone.utc).isoformat()
            payload_json = json.dumps(event.payload, ensure_ascii=False, sort_keys=True)
            event_hash = self._event_hash(
                created_at,
                event.request_id,
                event.endpoint,
                event.subject,
                event.decision,
                payload_json,
                previous_hash,
            )
            connection.execute(
                """
                INSERT INTO audit_events (
                    created_at_utc, request_id, endpoint, subject, decision, payload_json,
                    previous_event_hash, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    event.request_id,
                    event.endpoint,
                    event.subject,
                    event.decision,
                    payload_json,
                    previous_hash,
                    event_hash,
                ),
            )
    def fetch_recent(self, limit: int = 50, endpoint: str | None = None) -> list[StoredAuditEvent]:
        if not self.db_path.exists():
            return []
        query = """
            SELECT id, created_at_utc, request_id, endpoint, subject, decision,
                   payload_json, previous_event_hash, event_hash
            FROM audit_events
        """
        params: list[Any] = []
        if endpoint is not None:
            query += " WHERE endpoint = ?"
            params.append(endpoint)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self._lock, closing(sqlite3.connect(self.db_path)) as connection:
            rows = connection.execute(query, params).fetchall()
        return [
            StoredAuditEvent(
                id=row[0],
                created_at_utc=row[1],
                request_id=row[2],
                endpoint=row[3],
                subject=row[4],
                decision=row[5],
                payload=json.loads(row[6]),
                previous_event_hash=row[7],
                event_hash=row[8],
            )
            for row in rows
        ]

    def count(self) -> int:
        if not self.db_path.exists():
            return 0
        with self._lock, closing(sqlite3.connect(self.db_path)) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0])

    def verify_hash_chain(self) -> bool:
        if not self.db_path.exists():
            return True
        with self._lock, closing(sqlite3.connect(self.db_path)) as connection:
            rows = connection.execute(
                """
                SELECT created_at_utc, request_id, endpoint, subject, decision,
                       payload_json, previous_event_hash, event_hash
                FROM audit_events ORDER BY id ASC
                """
            ).fetchall()
        previous_hash: str | None = None
        for row in rows:
            if row[6] != previous_hash:
                return False
            expected = self._event_hash(
                row[0],
                row[1],
                row[2],
                row[3],
                row[4],
                row[5],
                previous_hash,
            )
            if row[7] != expected:
                return False
            previous_hash = row[7]
        return True

    @staticmethod
    def _event_hash(
        created_at_utc: str,
        request_id: str,
        endpoint: str,
        subject: str,
        decision: str,
        payload_json: str,
        previous_event_hash: str | None,
    ) -> str:
        material = "|".join([
            created_at_utc,
            request_id,
            endpoint,
            subject,
            decision,
            payload_json,
            previous_event_hash or "",
        ])
        return sha256(material.encode("utf-8")).hexdigest()

    @staticmethod
    def _ensure_hash_columns(connection: sqlite3.Connection) -> None:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(audit_events)")}
        if "previous_event_hash" not in columns:
            connection.execute("ALTER TABLE audit_events ADD COLUMN previous_event_hash TEXT")
        if "event_hash" not in columns:
            connection.execute("ALTER TABLE audit_events ADD COLUMN event_hash TEXT NOT NULL DEFAULT ''")

    @staticmethod
    def _latest_event_hash(connection: sqlite3.Connection) -> str | None:
        row = connection.execute(
            "SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return None if row is None else str(row[0])
