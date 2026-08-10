"""SQLite audit trail for API compliance decisions."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
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
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO audit_events (
                    created_at_utc, request_id, endpoint, subject, decision, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    event.request_id,
                    event.endpoint,
                    event.subject,
                    event.decision,
                    json.dumps(event.payload, ensure_ascii=False, sort_keys=True),
                ),
            )
