import json
import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from sharia_ai.api.audit import AuditEvent, SQLiteAuditStore
from sharia_ai.api.main import _require_configured_api_key, readiness


def _tempdir() -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory(ignore_cleanup_errors=True)


def _event(request_id: str = "r1", endpoint: str = "screening.equity") -> AuditEvent:
    return AuditEvent(
        request_id=request_id,
        endpoint=endpoint,
        subject="issuer",
        decision="compliant",
        payload={"decision": "compliant"},
    )


def test_audit_store_empty_database_branches():
    with _tempdir() as directory:
        store = SQLiteAuditStore(str(Path(directory) / "missing.sqlite3"))
        assert store.fetch_recent() == []
        assert store.count() == 0
        assert store.verify_hash_chain() is True


def test_audit_store_filters_and_detects_tampering():
    with _tempdir() as directory:
        store = SQLiteAuditStore(str(Path(directory) / "audit.sqlite3"))
        store.record(_event("r1", "screening.equity"))
        store.record(_event("r2", "zakat.calculate"))

        assert store.count() == 2
        assert len(store.fetch_recent(endpoint="zakat.calculate")) == 1
        assert store.verify_hash_chain() is True

        with sqlite3.connect(store.db_path) as connection:
            connection.execute(
                "UPDATE audit_events SET previous_event_hash = 'tampered' WHERE id = 2"
            )
            connection.commit()

        assert store.verify_hash_chain() is False


def test_audit_store_detects_event_hash_tampering():
    with _tempdir() as directory:
        store = SQLiteAuditStore(str(Path(directory) / "audit.sqlite3"))
        store.record(_event())

        with sqlite3.connect(store.db_path) as connection:
            connection.execute("UPDATE audit_events SET event_hash = 'tampered' WHERE id = 1")
            connection.commit()

        assert store.verify_hash_chain() is False


def test_audit_store_migrates_legacy_schema():
    with _tempdir() as directory:
        db_path = Path(directory) / "legacy.sqlite3"
        with sqlite3.connect(db_path) as connection:
            connection.execute(
                """
                CREATE TABLE audit_events (
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
                    "2026-01-01T00:00:00+00:00",
                    "old",
                    "screening.equity",
                    "issuer",
                    "ok",
                    "{}",
                ),
            )
            connection.commit()

        store = SQLiteAuditStore(str(db_path))
        store.record(_event("new"))
        recent = store.fetch_recent(limit=1)
        assert recent[0].previous_event_hash == ""
        assert json.loads(json.dumps(recent[0].payload)) == {"decision": "compliant"}


def test_readiness_degraded_and_disabled_branches():
    with patch("sharia_ai.api.main.config", SimpleNamespace(audit_enabled=False, api_version="test")):
        assert readiness()["audit"] == "disabled"

    with (
        patch("sharia_ai.api.main.config", SimpleNamespace(audit_enabled=True, api_version="test")),
        patch("sharia_ai.api.main._audit_store") as store,
    ):
        store.verify_hash_chain.return_value = False
        body = readiness()
        assert body["status"] == "degraded"
        assert body["audit"] == "hash_chain_invalid"

    with (
        patch("sharia_ai.api.main.config", SimpleNamespace(audit_enabled=True, api_version="test")),
        patch("sharia_ai.api.main._audit_store") as store,
    ):
        store.verify_hash_chain.side_effect = sqlite3.Error("boom")
        body = readiness()
        assert body["status"] == "degraded"
        assert body["audit"] == "unavailable"


def test_audit_recent_requires_configured_keys():
    with patch("sharia_ai.api.main.config", SimpleNamespace(api_keys=(), audit_enabled=True)):
        try:
            _require_configured_api_key()
        except HTTPException as exc:
            assert exc.status_code == 401
        else:
            raise AssertionError("audit access should require configured API keys")
