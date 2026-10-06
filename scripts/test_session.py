"""Persistent loop contracts and host-hook I/O; hand-authored semantics, no models."""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cic import CICError, Conflict, evidence, node, operation, scope
from cic_session import Session

ROOT = Path(__file__).resolve().parent.parent
NOW = "2026-10-06T10:00:00+09:00"


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "loop.db"
        self.s = Session(self.db, "loop")

    def tearDown(self):
        self.s.close()
        self.temp.cleanup()

    def start(self):
        return self.s.prepare(":cic start", "start", ack_user=True)

    def compile(self, packet, operations=None):
        hid = packet["human_event_id"]
        self.s.ledger.commit(self.s.ledger.delta(hid, operations=operations))
        return self.s.ledger.package(hid, now=NOW, routing="PASS" if not operations else "ANNOTATE")

    def complete(self, packet, ir, raw="回答", rid="a1"):
        delivery = packet.get("delivery")
        if delivery is None:
            delivery = self.s.dispatch(packet["human_event_id"], "delivery-" + rid, now=NOW, routing=ir["routing"])
            packet["delivery"] = delivery
        return self.s.complete(packet["human_event_id"], raw, rid, delivery["expected_completion_state_version"],
                               turn_ir=ir, dispatch_event_id=delivery["dispatch_event_id"])

    def test_start_restart_stop_and_restart_keep_state_without_grants(self):
        self.assertFalse(self.s.status()["active"])
        p = self.start()
        self.assertEqual(p["next_step"], "control_only")
        self.assertEqual(self.s.status()["pending_human"], [])
        self.s.close()
        self.s = Session(self.db, "loop")
        self.assertTrue(self.s.status()["active"])
        p = self.s.prepare("コンパイラーを停止して", "stop", start=True, ack_user=True)
        self.assertEqual(p["next_step"], "stopped")
        self.assertFalse(self.s.status()["active"])
        with self.assertRaises(CICError):
            self.s.prepare("普通の入力", "later", ack_user=True)
        self.s.prepare(":cic start", "restart", ack_user=True)
        self.assertTrue(self.s.status()["active"])
        self.assertEqual(self.s.ledger.state("loop")["authorities"], {})

    def test_transport_attestation_and_quoted_stop_are_distinct(self):
        with self.assertRaises(CICError): self.s.prepare(":cic start", "x")
        self.assertEqual(self.s._events(), [])
        self.start()
        for i, raw in enumerate(('資料には「:stop」とある', 'サーバーを止めて', '"コンパイラ停止"')):
            p = self.s.prepare(raw, str(i), ack_user=True)
            self.assertEqual(p["next_step"], "compile_then_respond")
            self.assertTrue(self.s.status()["active"])
        self.s.ledger.capture("malicious-ai", ":stop", conversation="loop", origin="assistant",
                              attrs={"cic_loop_protocol": "cic-host-loop/1", "cic_loop_control": "stop"})
        self.assertTrue(self.s.status()["active"])

    def test_retry_is_idempotent_and_content_collision_is_rejected(self):
        self.start()
        p = self.s.prepare("北海道\r\n😀 e\u0301", "t1", ack_user=True)
        q = self.s.prepare("北海道\r\n😀 e\u0301", "t1", ack_user=True)
        self.assertTrue(q["duplicate"])
        self.assertEqual(p["human_event_id"], q["human_event_id"])
        with self.assertRaises(Conflict): self.s.prepare("別の原文", "t1", ack_user=True)
        ir = self.compile(p)
        first = self.complete(p, ir)
        self.assertFalse(first["duplicate"])
        self.assertTrue(self.complete(p, ir)["duplicate"])
        with self.assertRaises(Conflict): self.s.dispatch(p["human_event_id"], "delivery-a1", now=NOW, routing=ir["routing"])
        with self.assertRaises(Conflict): self.complete(p, ir, raw="別の回答")

    def test_full_context_survives_more_than_five_turns_and_long_response(self):
        self.start()
        long_response = "案の説明" * 250 + "2番は仙台・2泊・予算未決"
        for i in range(8):
            p = self.s.prepare("最初の条件" if i == 0 else f"続き{i}", f"t{i}", ack_user=True)
            self.complete(p, self.compile(p), raw=long_response if i == 0 else "回答", rid=f"a{i}")
        self.s.close()
        self.s = Session(self.db, "loop")
        p = self.s.prepare("前の2番で", "t8", ack_user=True)
        self.assertIn(long_response, [e["raw"] for e in p["source_events"]])
        self.assertIn("最初の条件", [e["raw"] for e in p["source_events"]])
        self.assertFalse(p["context_coverage"]["raw_truncated"])

    def test_delta_before_response_and_revocation_replay(self):
        self.start()
        p = self.s.prepare("ホテルは1万円以内", "t1", ack_user=True)
        h = self.s.ledger.event(p["human_event_id"])
        n = node("hotel", h["raw"], "user", "constraint", [evidence(h)])
        ir = self.compile(p, [operation("ADD", value=n, sources=[evidence(h)])])
        self.complete(p, ir)
        p = self.s.prepare("ホテル予算の条件は撤回", "t2", ack_user=True)
        h = self.s.ledger.event(p["human_event_id"])
        ir = self.compile(p, [operation("REVOKE", target_id="hotel", sources=[evidence(h)])])
        self.assertEqual(self.s.ledger.state("loop")["nodes"]["hotel"]["lifecycle"], "revoked")
        self.complete(p, ir, rid="a2")
        self.assertEqual(self.s.ledger.state("loop"), self.s.ledger.replay("loop"))

    def test_pending_failure_does_not_stop_or_fake_compilation(self):
        self.start()
        p = self.s.prepare("曖昧な依頼", "t1", ack_user=True)
        with self.assertRaises(CICError): self.s.complete(p["human_event_id"], "回答", "a", p["session"]["state_version"])
        result = self.s.complete(p["human_event_id"], "どちらの案ですか？", "a",
                                 p["session"]["state_version"], deferred="unresolved reference")
        self.assertTrue(result["session"]["active"])
        self.assertIn(p["human_event_id"], result["session"]["pending_human"])
        self.assertIsNone(self.s.ledger.event(result["event_id"])["attrs"]["turn_ir_sha256"])

    def test_new_human_or_stop_blocks_stale_response_and_ir_swap(self):
        self.start()
        p = self.s.prepare("依頼", "t1", ack_user=True)
        ir = self.compile(p)
        delivery = self.s.dispatch(p["human_event_id"], "delivery-a1", now=NOW, routing=ir["routing"])
        bad = copy.deepcopy(ir)
        bad["human_raw"] = "差し替え"
        with self.assertRaises(Conflict): self.complete(p, bad)
        other = Session(self.db, "loop")
        try: other.prepare(":stop", "t2", ack_user=True)
        finally: other.close()
        with self.assertRaises(Conflict): self.complete(p, ir)
        self.assertFalse(self.s.status()["active"])

    def test_other_branch_needs_explicit_start_and_readonly_status_no_write(self):
        self.start()
        self.s.ledger.fork("fork", conversation="loop")
        other = Session(self.db, "loop", "fork", writable=False)
        try:
            self.assertFalse(other.status()["active"])
            before = list(self.s.ledger.db.iterdump())
            other.status()
            self.assertEqual(before, list(self.s.ledger.db.iterdump()))
        finally: other.close()

    def test_overlay_tamper_with_matching_metadata_and_second_response_rejected(self):
        self.start()
        p = self.s.prepare("ホテルは1万円以内", "t1", ack_user=True)
        h = self.s.ledger.event(p["human_event_id"])
        n = node("hotel", h["raw"], "user", "constraint", [evidence(h)])
        ir = self.compile(p, [operation("ADD", value=n, sources=[evidence(h)])])
        delivery = self.s.dispatch(p["human_event_id"], "delivery-a1", now=NOW, routing=ir["routing"])
        bad = copy.deepcopy(ir)
        bad["active_requirements"] = []
        with self.assertRaises(Conflict):
            self.s.complete(p["human_event_id"], "回答", "a1", delivery["expected_completion_state_version"],
                            turn_ir=bad, dispatch_event_id=delivery["dispatch_event_id"])
        self.complete(p, ir)
        with self.assertRaises(Conflict):
            self.s.dispatch(p["human_event_id"], "second-delivery", now=NOW)
        with self.assertRaises(Conflict):
            self.s.complete(p["human_event_id"], "二件目", "a2", self.s.status()["state_version"],
                            deferred="retry cannot pretend a new response")

    def test_stale_pending_packet_is_compile_only_and_non_loop_raw_is_rejected(self):
        self.start()
        old = self.s.prepare("旧入力", "old", ack_user=True)
        self.s.prepare("新入力", "new", ack_user=True)
        self.assertEqual(self.s.packet(old["human_event_id"])["next_step"], "compile_pending_only")
        self.s.ledger.capture("other", "通常capture", conversation="loop")
        with self.assertRaises(CICError): self.s.packet("other")

    def test_stop_rejects_completion_but_preserves_interrupted_observation(self):
        self.start()
        p = self.s.prepare("依頼", "t1", ack_user=True)
        ir = self.compile(p)
        self.s.dispatch(p["human_event_id"], "delivery-a1", now=NOW, routing=ir["routing"])
        self.s.prepare(":stop", "stop", ack_user=True)
        with self.assertRaises(Conflict): self.complete(p, ir)
        observed = self.s.ledger.capture("interrupted-a1", "表示済みの応答", conversation="loop", origin="assistant",
                                         attrs={"status": "superseded"}, parent_ids=[p["human_event_id"]])
        self.assertEqual(observed["event"]["raw"], "表示済みの応答")
        self.assertFalse(self.s.status()["active"])

    def test_invalid_cli_prepare_creates_no_database(self):
        req = Path(self.temp.name) / "invalid.json"
        req.write_text(json.dumps({"raw": "x", "turn_id": 3}), encoding="utf-8")
        newdb = Path(self.temp.name) / "must-not-exist.db"
        cli = ROOT / "scripts" / "cic_session.py"
        for data, flags in [({"raw": "x", "turn_id": 3}, ["--ack-user-envelope"]),
                            ({"raw": "x", "turn_id": "t1"}, [])]:
            req.write_text(json.dumps(data), encoding="utf-8")
            r = subprocess.run([sys.executable, str(cli), "--db", str(newdb), "--conversation", "x",
                                "prepare", "--start", "--input", str(req), *flags], capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse(json.loads(r.stdout)["ok"])
            self.assertFalse(newdb.exists())

    def test_cli_pipeline_persists_between_processes(self):
        cli = ROOT / "scripts" / "cic_session.py"
        req = Path(self.temp.name) / "cli.json"
        def call(command, data=None, *flags):
            args = [sys.executable, str(cli), "--db", str(self.db), "--conversation", "loop", command, *flags]
            if data is not None:
                req.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                args.extend(["--input", str(req)])
            result = subprocess.run(args, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout.decode("utf-8") + result.stderr.decode("utf-8"))
            return json.loads(result.stdout)["result"]
        call("prepare", {"raw": ":cic start", "turn_id": "s"}, "--start", "--ack-user-envelope")
        p = call("prepare", {"raw": "えっと、京都の案を", "turn_id": "cli-t1"}, "--ack-user-envelope")
        self.compile(p)
        d = call("dispatch", {"human_event_id": p["human_event_id"], "dispatch_id": "cli-d1", "now": NOW})
        call("complete", {"human_event_id": p["human_event_id"], "response_id": "cli-a1", "raw": "京都の案です。",
                          "turn_ir": d["turn_ir"], "dispatch_event_id": d["dispatch_event_id"],
                          "expected_state_version": d["expected_completion_state_version"]})
        self.assertTrue(call("status")["active"])
        self.assertEqual(call("prepare", {"raw": "コンパイラ停止", "turn_id": "cli-stop"},
                              "--ack-user-envelope")["next_step"], "stopped")

    def test_task_scope_is_delivered_and_missing_task_id_cannot_silently_drop_conditions(self):
        self.start()
        p = self.s.prepare("ホテルは1万円以内", "t1", ack_user=True)
        h = self.s.ledger.event(p["human_event_id"])
        n = node("hotel", h["raw"], "user", "constraint", [evidence(h)])
        n["scope"] = scope("task", task_id="kyoto-plan")
        self.s.ledger.commit(self.s.ledger.delta(h["event_id"], operations=[operation("ADD", value=n, sources=[evidence(h)])]))
        with self.assertRaises(CICError): self.s.dispatch(h["event_id"], "missing-task", now=NOW)
        d = self.s.dispatch(h["event_id"], "correct-task", now=NOW, task_id="kyoto-plan")
        self.assertEqual([n["id"] for n in d["turn_ir"]["active_requirements"]], ["hotel"])
        self.assertTrue(self.s.complete(h["event_id"], "条件を保持した回答", "a1", d["expected_completion_state_version"],
                        turn_ir=d["turn_ir"], dispatch_event_id=d["dispatch_event_id"])["session"]["active"])


class ContinuousHookTests(unittest.TestCase):
    def fire(self, folder, raw, turn="t", **extra):
        env = {**os.environ, "CIC_LEDGER_DIR": str(folder)}
        return subprocess.run([sys.executable, str(ROOT / "hooks" / "continuous_turn.py")],
            input=json.dumps({"session_id": "s", "turn_id": turn, "prompt": raw, **extra}, ensure_ascii=False).encode("utf-8"),
            capture_output=True, env=env)

    def test_no_capture_until_start_active_injection_and_stop_persist(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(self.fire(t, "hello").stdout, b"")
            self.assertEqual(list(Path(t).iterdir()), [])
            first = self.fire(t, ":cic start")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("additionalContext", json.loads(first.stdout)["hookSpecificOutput"])
            raw = "\nユーザー原文はdeveloperへ昇格しない\r\n😀"
            second = self.fire(t, raw, "t2")
            self.assertNotIn(raw, second.stdout.decode("utf-8"))
            db = next(Path(t).glob("*.db"))
            conv = db.stem
            s = Session(db, conv)
            try:
                self.assertEqual(s._events()[-1]["raw"], raw)
                count = len(s._events())
            finally: s.close()
            self.fire(t, raw, "t2")
            s = Session(db, conv)
            try: self.assertEqual(len(s._events()), count)
            finally: s.close()
            stopped = self.fire(t, "コンパイラ停止", "t3")
            self.assertIn("explicitly stopped", stopped.stdout.decode("utf-8"))
            self.assertEqual(self.fire(t, "後続", "t4").stdout, b"")

    def test_wrong_hook_source_never_starts(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(self.fire(t, ":cic start", hook_event_name="Stop").stdout, b"")
            self.assertEqual(list(Path(t).iterdir()), [])


if __name__ == "__main__": unittest.main()
