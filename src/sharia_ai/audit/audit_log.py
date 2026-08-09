"""
audit_log.py — سجلّ تدقيق دائم (persistent audit trail) لكل قرارات
الامتثال الصادرة عن النظام، مخزَّن في SQLite (مكتبة قياسية، بدون
اعتماديات خارجية، ملف واحد قابل للنسخ الاحتياطي بسهولة).

هذا يُغلق فجوة إنتاجية جوهرية: بدون سجلّ دائم، لا يمكن لأي هيئة رقابة
شرعية أو مدقّق خارجي إعادة بناء *متى* و*لماذا* صدر قرار امتثال معيّن.

كل إدخال غير قابل للتعديل منطقيًا (append-only) — لا توجد عمليات
UPDATE أو DELETE مكشوفة في هذه الوحدة عمدًا.

المؤلف: Ciprian Ștefan Pleșca
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class AuditEntry:
    entry_id: str
    created_at_utc: str
    event_type: str  # مثال: "equity_screening" / "contract_screening" / "zakat_calculation"
    subject: str  # مثال: اسم الشركة، أو معرِّف مجهول للعقد
    outcome_summary: str
    payload_json: str
    client_id: str


class AuditLog:
    """سجلّ تدقيق SQLite، آمن للتزامن (thread-safe) عبر قفل واحد
    ومسار اتصال جديد لكل عملية (نمط بسيط ومتين لعبء عمل خفيف/متوسط).
    """

    def __init__(self, db_path: str = "sharia_ai_audit.sqlite3"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _ensure_schema(self) -> None:
        parent_dir = Path(self.db_path).parent
        if str(parent_dir) not in ("", "."):
            parent_dir.mkdir(parents=True, exist_ok=True)
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_entries (
                    entry_id        TEXT PRIMARY KEY,
                    created_at_utc  TEXT NOT NULL,
                    event_type      TEXT NOT NULL,
                    subject         TEXT NOT NULL,
                    outcome_summary TEXT NOT NULL,
                    payload_json    TEXT NOT NULL,
                    client_id       TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_entries(event_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_entries(created_at_utc)"
            )
            conn.commit()

    def record(
        self,
        event_type: str,
        subject: str,
        outcome_summary: str,
        payload: dict,
        client_id: str = "unknown",
    ) -> AuditEntry:
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            created_at_utc=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            subject=subject,
            outcome_summary=outcome_summary,
            payload_json=json.dumps(payload, ensure_ascii=False, default=str),
            client_id=client_id,
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_entries
                    (entry_id, created_at_utc, event_type, subject,
                     outcome_summary, payload_json, client_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.entry_id,
                    entry.created_at_utc,
                    entry.event_type,
                    entry.subject,
                    entry.outcome_summary,
                    entry.payload_json,
                    entry.client_id,
                ),
            )
            conn.commit()
        return entry

    def fetch_recent(self, limit: int = 50, event_type: str | None = None) -> list[AuditEntry]:
        query = "SELECT entry_id, created_at_utc, event_type, subject, outcome_summary, payload_json, client_id FROM audit_entries"
        params: tuple = ()
        if event_type:
            query += " WHERE event_type = ?"
            params = (event_type,)
        query += " ORDER BY created_at_utc DESC LIMIT ?"
        params = params + (limit,)

        with self._lock, self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [AuditEntry(*row) for row in rows]

    def count(self) -> int:
        with self._lock, self._connect() as conn:
            (total,) = conn.execute("SELECT COUNT(*) FROM audit_entries").fetchone()
        return int(total)
