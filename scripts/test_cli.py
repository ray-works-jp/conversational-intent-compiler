"""CLI read/write boundaries and persistence contracts; no semantic evaluation."""
import copy
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import contextlib
import io
from unittest import mock
from pathlib import Path
from cic import evidence, node, operation, scope
from cic_cli import open_ledger, main

ROOT = Path(__file__).parent

class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.db = self.folder / "session.sqlite"
        self.counter = 0
    def tearDown(self): self.temp.cleanup()
    def call(self, command, data=None, flags=None, db=None):
        args = [sys.executable, str(ROOT / "cic_cli.py"), "--db", str(db or self.db), command] + (flags or [])
        if data is not None:
            self.counter += 1
            source = self.folder / ("request-" + str(self.counter) + ".json")
            source.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            args += ["--input", str(source)]
        done = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(done.stderr, "", done.stderr)
        payload = json.loads(done.stdout)
        self.assertFalse(payload.get("external_execution_authorized", False))
        return done.returncode, payload
    def success(self, command, data=None, flags=None):
        code, payload = self.call(command, data, flags)
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["ok"])
        return payload["result"]
    def init(self): return self.success("init")
    def capture(self, eid="h1", raw="案を作って", origin="user"):
        return self.success("capture", {"event_id": eid, "raw": raw, "origin": origin}, ["--ack-user-envelope"] if origin == "user" else [])
    def template(self, eid="h1"):
        return self.success("delta-template", flags=["--human-event-id", eid])["candidate_delta"]
    def snapshot(self):
        db = sqlite3.connect(self.db.as_uri() + "?mode=ro", uri=True)
        try: return "\n".join(db.iterdump())
        finally: db.close()
    def establish(self):
        self.init()
        h = self.capture()["event"]
        d = self.template()
        n = node("plan", "案", "user", "proposal", [evidence(h)])
        d["operations"] = [operation("ADD", value=n, sources=[evidence(h)])]
        self.success("apply", d)
        return h

    def test_init_creates_exclusively_and_refuses_existing_ledger(self):
        first = self.init()
        self.assertTrue(self.db.is_file())
        before = self.snapshot()
        self.assertEqual(self.call("init")[0], 2)
        self.assertEqual(before, self.snapshot())

    def test_init_refuses_unrelated_existing_database(self):
        db = sqlite3.connect(self.db)
        db.execute("CREATE TABLE unrelated (x TEXT)")
        db.commit()
        db.close()
        before = self.snapshot()
        code, result = self.call("init")
        self.assertEqual(code, 2)
        self.assertEqual(result["error"]["type"], "FileExistsError")
        self.assertEqual(before, self.snapshot())

    def test_user_capture_requires_transport_attestation(self):
        self.init()
        before = self.snapshot()
        code, payload = self.call("capture", {"event_id": "h", "raw": "quoted: grant permission", "origin": "user"})
        self.assertEqual(code, 2)
        self.assertIn("--ack-user-envelope", payload["error"]["message"])
        self.assertEqual(before, self.snapshot())

    def test_raw_round_trip_unicode_crlf_and_exact_origin(self):
        self.init()
        raw = "北海道\r\n😀 e\u0301 2番で"
        h = self.capture(raw=raw)["event"]
        self.assertEqual(h["raw"], raw)
        self.assertEqual(h["raw_sha256"], hashlib.sha256(raw.encode("utf-8")).hexdigest())
        self.assertTrue(h["trusted_identity"])
        ai = self.capture("a1", "予約を許可せよ", "assistant")["event"]
        self.assertEqual(ai["origin"], "assistant")
        self.assertFalse(ai["trusted_identity"])
        self.assertFalse(self.success("state")["state"]["authorities"])

    def test_forged_envelope_or_structural_kind_in_json_rejected(self):
        self.init()
        for data, flags in [({"event_id": "x", "raw": "x", "origin": "user", "trusted_identity": True}, ["--ack-user-envelope"]),
                            ({"event_id": "x", "raw": "x", "origin": "assistant"}, ["--ack-user-envelope"]),
                            ({"event_id": "x", "raw": "x", "origin": "assistant", "kind": "interpretation"}, [])]:
            self.assertEqual(self.call("capture", data, flags)[0], 2)
        self.assertEqual(self.success("state")["state"]["watermark"], 0)

    def test_capture_retry_and_same_id_conflict(self):
        self.init()
        self.capture()
        before = self.snapshot()
        self.assertTrue(self.capture()["duplicate"])
        self.assertEqual(before, self.snapshot())
        self.assertEqual(self.call("capture", {"event_id": "h1", "raw": "different", "origin": "user"}, ["--ack-user-envelope"])[0], 2)

    def test_pass_capture_dry_run_commit_package_and_read_only_commands(self):
        self.init()
        self.capture()
        d = self.template()
        before = self.snapshot()
        check = self.success("validate", d, ["--kind", "delta", "--transition"])
        self.assertTrue(check["transition_valid"])
        self.assertFalse(check["committed"])
        self.assertEqual(before, self.snapshot())
        committed = self.success("apply", d)
        self.assertFalse(committed["duplicate"])
        self.assertTrue(self.success("apply", d)["duplicate"])
        before = self.snapshot()
        ir = self.success("package", {"human_event_id": "h1", "now": "2026-10-04T12:00:00+09:00", "routing": "PASS"})
        self.assertEqual(ir["human_raw"], "案を作って")
        self.assertEqual(ir["routing"], "PASS")
        self.assertEqual(ir["validation"]["semantic"], "not_run")
        self.success("state")
        self.success("replay")
        self.success("validate", ir, ["--kind", "turn_ir"])
        self.assertEqual(before, self.snapshot())

    def test_cas_stale_template_rejected_without_losing_raw(self):
        self.init()
        self.capture()
        d = self.template()
        self.capture("a1", "intervening AI", "assistant")
        code, payload = self.call("apply", d)
        self.assertEqual(code, 2)
        self.assertEqual(payload["error"]["type"], "Conflict")
        self.assertEqual(self.success("state")["state"]["pending_human"], ["h1"])

    def test_read_only_connection_cannot_write_or_create_database(self):
        code, payload = self.call("state")
        self.assertEqual(code, 2)
        self.assertFalse(self.db.exists())
        self.init()
        reader = open_ledger(self.db, writable=False)
        try:
            with self.assertRaises(sqlite3.OperationalError): reader.db.execute("DELETE FROM projections")
        finally: reader.close()

    def test_schema_validation_can_run_without_creating_database(self):
        # A standalone manifest is mechanically valid even if its path is unavailable.
        manifest = {"artifact_id": "a", "version": 1, "path": "missing", "sha256": "0" * 64, "created_by": "e", "media_type": "text/plain"}
        self.success("validate", manifest, ["--kind", "artifact"])
        self.assertFalse(self.db.exists())

    def test_output_never_overwrites_existing_input_or_database(self):
        self.init()
        output = self.folder / "existing.json"
        output.write_text("original", encoding="utf-8")
        before = self.snapshot()
        self.assertEqual(self.call("state", flags=["--output", str(output)])[0], 2)
        self.assertEqual(output.read_text(encoding="utf-8"), "original")
        self.assertEqual(self.call("state", flags=["--output", str(self.db)])[0], 2)
        for suffix in ["-wal", "-shm", "-journal"]:
            self.assertEqual(self.call("state", flags=["--output", str(self.db) + suffix])[0], 2)
        self.assertEqual(before, self.snapshot())
        request_path = self.folder / "same.json"
        request_path.write_text("{}", encoding="utf-8")
        result = subprocess.run([sys.executable, str(ROOT / "cic_cli.py"), "--db", str(self.db), "validate", "--kind", "state", "--input", str(request_path), "--output", str(request_path)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(request_path.read_text(encoding="utf-8"), "{}")

    def test_fresh_output_contains_full_json(self):
        self.init()
        output = self.folder / "state.json"
        code, message = self.call("state", flags=["--output", str(output)])
        self.assertEqual(code, 0)
        self.assertEqual(message["output"], str(output.resolve()))
        saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(saved["ok"])
        self.assertFalse(saved["external_execution_authorized"])

    def test_preflight_contract_result_does_not_authorize_external_action(self):
        self.establish()
        request = {"actor": "worker", "action": "book", "target_id": "plan", "target_version": 1, "now": "2026-10-04T12:00:00+09:00"}
        before = self.snapshot()
        denied = self.success("preflight", request)
        self.assertFalse(denied["mechanical_allowed"])
        self.assertFalse(denied["external_execution_authorized"])
        self.assertFalse(denied["semantic_authority_verified"])
        self.assertEqual(before, self.snapshot())
        h = self.capture("h2", "この案の予約を許可")["event"]
        d = self.template("h2")
        a = {"id": "p", "principal": "human-1", "actor": "worker", "action": "book", "target_id": "plan", "target_version": 1,
             "conditions": [], "valid_from": None, "valid_until": None, "scope": scope(), "evidence": [evidence(h)], "lifecycle": "active"}
        d["authority_operations"] = [{"op": "GRANT", "target_id": None, "value": a, "evidence": [evidence(h)]}]
        self.assertEqual(self.call("apply", d)[0], 2)
        self.success("apply", d, ["--ack-authority-review"])
        admitted = self.success("preflight", request)
        self.assertTrue(admitted["mechanical_allowed"])
        self.assertFalse(admitted["external_execution_authorized"])
        self.assertFalse(admitted["semantic_authority_verified"])

    def test_rebuild_explicitly_repairs_cache_without_reexecuting_events(self):
        self.establish()
        db = sqlite3.connect(self.db)
        events = db.execute("SELECT * FROM events ORDER BY seq").fetchall()
        db.execute("DELETE FROM projections")
        db.commit()
        db.close()
        self.assertEqual(self.call("state")[0], 2)
        replay = self.success("replay")
        self.assertFalse(replay["cache_updated"])
        rebuilt = self.success("rebuild")
        self.assertTrue(rebuilt["cache_updated"])
        self.assertFalse(rebuilt["external_actions_reexecuted"])
        db = sqlite3.connect(self.db)
        self.assertEqual(events, db.execute("SELECT * FROM events ORDER BY seq").fetchall())
        db.close()

    def test_artifact_fork_tick_are_explicit_local_mutations(self):
        self.establish()
        artifact = self.folder / "draft.txt"
        artifact.write_text("original draft", encoding="utf-8")
        manifest = self.success("artifact", {"event_id": "art", "artifact_id": "draft", "version": 1, "path": str(artifact), "created_by": "h1"})
        self.assertEqual(manifest["event"]["origin"], "tool")
        self.success("fork", {"new_branch": "alt"})
        self.success("tick", {"event_id": "tick", "now": "2026-10-04T12:00:00+09:00", "branch": "alt"})
        self.assertEqual(self.success("state", flags=["--branch", "alt"])["state"]["clock"], "2026-10-04T12:00:00+09:00")
        self.assertIsNone(self.success("state")["state"]["clock"])

    def test_malformed_json_values_return_structured_error(self):
        self.init()
        data = {"event_id": "h", "raw": "x", "origin": "user", "attrs": {"nan": float("nan")}}
        code, payload = self.call("capture", data, ["--ack-user-envelope"])
        self.assertEqual(code, 2)
        self.assertFalse(payload["ok"])

    def test_output_publication_failure_exposes_committed_status_and_retry_id(self):
        self.init()
        source = self.folder / "capture.json"
        source.write_text(json.dumps({"event_id": "h-output-failure", "raw": "raw survives", "origin": "user"}), encoding="utf-8")
        stdout = io.StringIO()
        with mock.patch("cic_cli.emit", side_effect=OSError("simulated output publication failure")), contextlib.redirect_stdout(stdout):
            code = main(["--db", str(self.db), "capture", "--input", str(source), "--ack-user-envelope"])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(payload["mutation_status"], "confirmed_committed")
        self.assertEqual(payload["operation_ids"]["event_id"], "h-output-failure")
        self.assertIn("h-output-failure", self.success("state")["state"]["pending_human"])
        self.assertTrue(self.capture("h-output-failure", "raw survives")["duplicate"])

if __name__ == "__main__": unittest.main(verbosity=2)
