import os
import tempfile
import unittest

from sharia_ai.audit.audit_log import AuditLog


class TestAuditLog(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        os.unlink(self.db_path)  # AuditLog must be able to create it from scratch
        self.audit_log = AuditLog(self.db_path)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            path = self.db_path + suffix
            if os.path.exists(path):
                os.unlink(path)

    def test_record_returns_entry_with_generated_id(self):
        entry = self.audit_log.record(
            event_type="equity_screening",
            subject="شركة الاختبار",
            outcome_summary="متوافق",
            payload={"is_compliant": True},
            client_id="ip:127.0.0.1",
        )
        self.assertTrue(entry.entry_id)
        self.assertEqual(entry.event_type, "equity_screening")
        self.assertEqual(entry.subject, "شركة الاختبار")

    def test_count_reflects_number_of_records(self):
        self.assertEqual(self.audit_log.count(), 0)
        self.audit_log.record("zakat_calculation", "s1", "ok", {"a": 1})
        self.audit_log.record("zakat_calculation", "s2", "ok", {"a": 2})
        self.assertEqual(self.audit_log.count(), 2)

    def test_fetch_recent_returns_most_recent_first(self):
        self.audit_log.record("contract_screening", "c1", "clean", {})
        self.audit_log.record("contract_screening", "c2", "clean", {})
        self.audit_log.record("contract_screening", "c3", "clean", {})
        entries = self.audit_log.fetch_recent(limit=2)
        self.assertEqual(len(entries), 2)

    def test_fetch_recent_filters_by_event_type(self):
        self.audit_log.record("equity_screening", "e1", "ok", {})
        self.audit_log.record("zakat_calculation", "z1", "ok", {})
        entries = self.audit_log.fetch_recent(event_type="zakat_calculation")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].event_type, "zakat_calculation")

    def test_payload_round_trips_as_json(self):
        import json

        self.audit_log.record(
            "compliance_report", "s", "ok", {"nested": {"value": 42}, "list": [1, 2]}
        )
        entry = self.audit_log.fetch_recent(limit=1)[0]
        parsed = json.loads(entry.payload_json)
        self.assertEqual(parsed["nested"]["value"], 42)
        self.assertEqual(parsed["list"], [1, 2])

    def test_two_instances_share_same_underlying_file(self):
        self.audit_log.record("equity_screening", "s1", "ok", {})
        second_handle = AuditLog(self.db_path)
        self.assertEqual(second_handle.count(), 1)

    def test_concurrent_writes_from_multiple_threads_are_all_recorded(self):
        import threading

        def _write(i: int) -> None:
            self.audit_log.record("equity_screening", f"s{i}", "ok", {"i": i})

        threads = [threading.Thread(target=_write, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(self.audit_log.count(), 20)


if __name__ == "__main__":
    unittest.main()
