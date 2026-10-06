"""Persistent host conversation loop; no model calls, grants, or external execution.

The host calls prepare -> its compiler/Delta validator -> its responder -> complete.
Start/stop and raw turns are immutable user events. Session state is derived from
them, never from assistant text or a past IR. CLI attestations are not authentication.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

from cic import CICError, Conflict, canonical, validate_named, validate_schema
from cic_cli import open_ledger, checked_state, read_json, emit, prepare_output
from schema_spec import obj, S, ID, N, STRINGS

START = {":cic start", "/cic start", "コンパイラ開始", "コンパイラー開始"}
STOP = {":stop", "/stop", ":cic stop", "/cic stop", "コンパイラ停止", "コンパイラー停止",
        "コンパイラを停止して", "コンパイラーを停止して", "コンパイラを停止してください", "コンパイラーを停止してください",
        "コンパイラを止めて", "コンパイラーを止めて", "もうコンパイルしないで"}
PROTOCOL = "cic-host-loop/1"
REQUESTS = {
    "prepare": obj({"raw": S, "turn_id": ID}),
    "dispatch": obj({"human_event_id": ID, "dispatch_id": ID, "now": ID,
                     "routing": {"enum": ["PASS", "ANNOTATE", "CONTRACT", "VERIFY"]},
                     "node_ids": STRINGS, "required_event_ids": STRINGS, "task_id": ID}, ["human_event_id", "dispatch_id", "now"]),
    "complete": obj({"human_event_id": ID, "raw": S, "response_id": ID, "expected_state_version": N,
                     "deferred": ID, "turn_ir": {"type": "object"}, "dispatch_event_id": ID,
                     "response_status": {"enum": ["prepared", "observed"]}},
                    ["human_event_id", "raw", "response_id", "expected_state_version"]),
}


def control(raw):
    # Whole direct human message only. A quoted command or a server-stop request is data.
    value = raw.strip().lower()
    return "start" if value in START else "stop" if value in STOP else None


class Session:
    def __init__(self, database, conversation, branch="main", *, writable=True):
        if not isinstance(conversation, str) or not conversation or not isinstance(branch, str) or not branch:
            raise CICError("Conversation and branch IDs must be nonempty text")
        self.ledger = open_ledger(database, writable=writable)
        self.conversation, self.branch = conversation, branch

    def close(self):
        self.ledger.close()

    def _events(self):
        return self.ledger.events(self.conversation, self.branch)

    def status(self):
        state = checked_state(self.ledger, self.conversation, self.branch)
        active, last_control, turns = False, None, []
        for event in self._events():
            attrs = event["attrs"]
            if event["origin"] != "user" or event["kind"] != "human" or not event["trusted_identity"]:
                continue
            if attrs.get("cic_loop_protocol") != PROTOCOL:
                continue
            op = attrs.get("cic_loop_control")
            if op in {"start", "stop"}:
                active, last_control = op == "start", event["event_id"]
            if attrs.get("cic_loop_turn"):
                turns.append(event["event_id"])
        return {"protocol": PROTOCOL, "conversation_id": self.conversation, "branch_id": self.branch,
                "active": active, "state_version": state["state_version"], "ledger_watermark": state["watermark"],
                "last_control_event_id": last_control, "turn_event_ids": turns,
                "pending_human": state["pending_human"], "authority_changed_by_controller": False}

    def _request(self, eid, raw, origin, attrs, parents=()):
        return {"event_id": eid, "conversation_id": self.conversation, "branch_id": self.branch,
                "origin": origin, "kind": "human" if origin == "user" else "assistant",
                "principal": "current-human" if origin == "user" else None,
                "trusted_identity": origin == "user", "raw": raw, "effective_at": None,
                "parent_ids": list(parents), "reference_ids": [], "attrs": attrs}

    def prepare(self, raw, turn_id, *, start=False, ack_user=False):
        if not ack_user:
            raise CICError("prepare requires raw from a human-user transport and --ack-user-envelope")
        if not isinstance(raw, str) or not isinstance(turn_id, str) or not turn_id:
            raise CICError("raw must be text and turn_id must be a stable host turn ID")
        op = control(raw)
        if start and op != "stop":
            op = "start"  # Explicit host/user invocation; not inferred from file or model content.
        token = hashlib.sha256(turn_id.encode("utf-8")).hexdigest()
        eid = f"{self.conversation}:{self.branch}:loop:H:{token}"
        attrs = {"cic_loop_protocol": PROTOCOL, "host_turn_id": turn_id,
                 "cic_loop_turn": op != "stop", "cic_loop_control": op}
        request = self._request(eid, raw, "user", attrs)
        self.ledger.db.execute("BEGIN IMMEDIATE")
        try:
            duplicate = self.ledger.event(eid)
            if not duplicate and op != "start" and op != "stop" and not self.status()["active"]:
                raise CICError("Compiler loop is stopped; explicitly start it before preparing a turn")
            event, repeated = self.ledger._append(request)
            if not repeated and control(raw) in {"start", "stop"}:
                # Exact control-only human input changes the loop, never task intent or grants.
                delta = self.ledger.delta(eid)
                self.ledger._append({"event_id": "interpretation:" + delta["delta_id"],
                    "conversation_id": self.conversation, "branch_id": self.branch,
                    "origin": "compiler", "kind": "interpretation", "principal": None,
                    "trusted_identity": False, "raw": "", "effective_at": None,
                    "parent_ids": [eid], "reference_ids": [], "attrs": {"delta": delta,
                    "semantic_correctness": "unverified", "controller_control_only": True}})
            self.ledger.db.execute("COMMIT")
        except Exception:
            self.ledger.db.execute("ROLLBACK")
            raise
        # Control-only messages remain raw evidence. They have no intent/grant interpretation.
        return self.packet(eid, duplicate=repeated)

    def packet(self, human_id, *, duplicate=False):
        self.ledger.db.execute("BEGIN")
        try:
            return self._packet(human_id, duplicate=duplicate)
        finally:
            self.ledger.db.execute("ROLLBACK")

    def _packet(self, human_id, *, duplicate=False):
        event = self.ledger.event(human_id)
        if (not event or event["conversation_id"] != self.conversation or event["branch_id"] != self.branch or
                event["kind"] != "human" or not event["trusted_identity"] or event["origin"] != "user" or
                event["attrs"].get("cic_loop_protocol") != PROTOCOL):
            raise CICError("Human event missing or outside this conversation/branch")
        status = self.status()
        events = self._events()
        attrs = event["attrs"]
        op = attrs.get("cic_loop_control")
        stale = any(e["kind"] == "human" and e["seq"] > event["seq"] for e in events)
        return {"protocol": PROTOCOL, "duplicate": duplicate, "human_event_id": human_id,
                "current_human_raw": event["raw"], "session": status,
                "next_step": "stopped" if op == "stop" or not status["active"] else
                             "control_only" if control(event["raw"]) == "start" else
                             "compile_pending_only" if stale else "compile_then_respond",
                "base_state": checked_state(self.ledger, self.conversation, self.branch),
                "source_events": events,
                "context_coverage": {"included_branch_events": len(events), "raw_truncated": False,
                                     "known_omissions": ["Events the host did not capture are unavailable.",
                                                         "Fork ancestor raw requires explicit ledger lookup."]},
                "compiler_spec": "resources/intent-compiler/first-compiler-0.1.0/skills/compile-intent/references/system-prompt.md",
                "authority": {"controller_grants_external_actions": False, "compiler_stop_revokes_business_grants": False},
                "instructions": ["Interpret pending human raw against source events and active state, validate/apply Delta before answering.",
                                 "PASS skips overlay only. Preserve raw, changes, revocations, unknown and latitude.",
                                 "Answer the original task using validated Turn IR and raw; keep proposed/inferred content distinct.",
                                 "Dispatch saves the exact packaged IR before response; complete records the visible response with that dispatch ID.",
                                 "Recheck state before side effects. Dispatch ownership is not execution authority."]}

    def dispatch(self, human_id, dispatch_id, *, now, routing="ANNOTATE", node_ids=None, required_event_ids=None, task_id=None):
        if not isinstance(dispatch_id, str) or not dispatch_id:
            raise CICError("Dispatch requires a stable nonempty ID")
        token = hashlib.sha256(dispatch_id.encode("utf-8")).hexdigest()
        eid = f"{self.conversation}:{self.branch}:loop:D:{token}"
        self.ledger.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.ledger.event(eid)
            params = {"human_event_id": human_id, "now": now, "routing": routing,
                      "node_ids": node_ids, "required_event_ids": required_event_ids, "task_id": task_id}
            if existing:
                if existing["attrs"].get("packaging_parameters") != params:
                    raise Conflict("Same dispatch ID with different packaging parameters")
                human = self.ledger.event(human_id)
                if (not self.status()["active"] or self.status()["state_version"] != existing["attrs"]["state_version_before_dispatch"] + 1 or
                        not human or any(e["kind"] == "human" and e["seq"] > human["seq"] for e in self._events()) or
                        any(e["kind"] == "assistant" and human_id in e["parent_ids"] and
                            e["attrs"].get("cic_loop_protocol") == PROTOCOL for e in self._events())):
                    raise Conflict("Delivery is stale/completed/stopped; inspect ledger for audit and do not rerun the responder")
                result = existing
            else:
                human = self.ledger.event(human_id)
                if (not human or human["attrs"].get("cic_loop_protocol") != PROTOCOL or
                        human["conversation_id"] != self.conversation or human["branch_id"] != self.branch or
                        not self.status()["active"] or
                        any(e["kind"] == "human" and e["seq"] > human["seq"] for e in self._events())):
                    raise Conflict("Dispatch requires the current active human turn")
                if any(e["kind"] == "assistant" and human_id in e["parent_ids"] and
                       e["attrs"].get("cic_loop_protocol") == PROTOCOL for e in self._events()):
                    raise Conflict("This turn already has a response; do not dispatch it again")
                ir = self.ledger.package(human_id, now=now, routing=routing, node_ids=node_ids,
                                         required_event_ids=required_event_ids, task_id=task_id)
                if task_id is None and any(n["scope"]["kind"] == "task" and n["lifecycle"] == "active"
                                            for n in self.ledger.state(self.conversation, self.branch)["nodes"].values()):
                    raise CICError("Active task-scoped requirements exist; specify the actual task_id before dispatch to avoid silent omission")
                text = canonical(ir)
                attrs = {"cic_loop_protocol": PROTOCOL, "packaging_parameters": params,
                         "turn_ir_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                         "state_version_before_dispatch": ir["base_state_version"], "processing_claim": False,
                         "external_execution_authorized": False}
                request = self._request(eid, text, "assistant", attrs, [human_id])
                request.update(origin="compiler", kind="external")
                result, _ = self.ledger._append(request)
            self.ledger.db.execute("COMMIT")
        except Exception:
            self.ledger.db.execute("ROLLBACK")
            raise
        return {"dispatch_event_id": eid, "turn_ir": json.loads(result["raw"]),
                "turn_ir_sha256": result["attrs"]["turn_ir_sha256"],
                "duplicate": existing is not None, "dispatch_current": True,
                "expected_completion_state_version": result["attrs"]["state_version_before_dispatch"] + 1,
                "processing_claim": False, "external_execution_authorized": False}

    def complete(self, human_id, raw, response_id, expected_state_version, *, deferred=None, turn_ir=None, dispatch_event_id=None, response_status="prepared"):
        if not isinstance(raw, str) or not isinstance(response_id, str) or not response_id:
            raise CICError("Response raw and stable response_id are required")
        if deferred is not None and (not isinstance(deferred, str) or not deferred.strip()):
            raise CICError("Deferred interpretation requires a nonempty reason")
        if response_status not in {"prepared", "observed"}:
            raise CICError("response_status must distinguish prepared text from an observed visible response")
        if not isinstance(expected_state_version, int) or isinstance(expected_state_version, bool):
            raise CICError("expected_state_version must be an integer")
        ir_hash = None
        if turn_ir is not None:
            validate_named("turn_ir", turn_ir)
            ir_hash = hashlib.sha256(canonical(turn_ir).encode("utf-8")).hexdigest()
        token = hashlib.sha256(response_id.encode("utf-8")).hexdigest()
        eid = f"{self.conversation}:{self.branch}:loop:A:{token}"
        attrs = {"cic_loop_protocol": PROTOCOL, "host_response_id": response_id,
                 "interpretation_deferred": deferred, "source": "host-response", "response_status": response_status, "turn_ir_sha256": ir_hash,
                 "dispatch_event_id": dispatch_event_id}
        request = self._request(eid, raw, "assistant", attrs, [human_id])
        self.ledger.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.ledger.event(eid)
            if not existing:
                state = checked_state(self.ledger, self.conversation, self.branch)
                if state["state_version"] != expected_state_version:
                    raise Conflict("State changed after response preparation; re-read raw and recompile")
                event = self.ledger.event(human_id)
                if not event or event["kind"] != "human" or event["attrs"].get("cic_loop_protocol") != PROTOCOL:
                    raise CICError("Response must refer to a captured compiler-loop human turn")
                later_human = [e for e in self._events() if e["kind"] == "human" and e["seq"] > event["seq"]]
                if later_human or not self.status()["active"]:
                    raise Conflict("New human input or explicit stop supersedes this response; preserve it as an interrupted observation")
                if any(e["kind"] == "assistant" and human_id in e["parent_ids"] and
                       e["attrs"].get("cic_loop_protocol") == PROTOCOL for e in self._events()):
                    raise Conflict("This turn already has a response; explicit regeneration needs a separate attempt")
                if state["pending_human"] and not deferred:
                    raise CICError("Human interpretation is pending; process all captured corrections or specify an explicit deferred reason")
                if not deferred:
                    if turn_ir is None:
                        raise CICError("A completed compilation requires the exact Turn IR delivered to the responder")
                    delivery = self.ledger.event(dispatch_event_id) if dispatch_event_id else None
                    if (not delivery or delivery["origin"] != "compiler" or delivery["kind"] != "external" or
                            delivery["attrs"].get("cic_loop_protocol") != PROTOCOL or human_id not in delivery["parent_ids"] or
                            delivery["attrs"].get("turn_ir_sha256") != ir_hash or delivery["raw"] != canonical(turn_ir) or
                            delivery["attrs"].get("state_version_before_dispatch", -2) + 1 != state["state_version"]):
                        raise Conflict("Completion must match the immutable dispatched IR and its current state version")
                    if (turn_ir["turn_id"] != human_id or turn_ir["human_raw"] != event["raw"] or
                            turn_ir["human_raw_sha256"] != event["raw_sha256"] or
                            turn_ir["conversation_id"] != self.conversation or turn_ir["branch_id"] != self.branch or
                            turn_ir["base_state_version"] + 1 != state["state_version"] or
                            turn_ir["ledger_watermark"] + 1 != state["watermark"] or turn_ir["intent_delta"] != state["last_delta"]):
                        raise Conflict("Responder Turn IR differs from the current raw, Delta, branch, or state version")
            result, duplicate = self.ledger._append(request)
            self.ledger.db.execute("COMMIT")
        except Exception:
            self.ledger.db.execute("ROLLBACK")
            raise
        return {"event_id": result["event_id"], "duplicate": duplicate, "session": self.status()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True)
    ap.add_argument("--conversation", required=True)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--output")
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("prepare", "dispatch", "complete"):
        p = sub.add_parser(name)
        p.add_argument("--input", required=True)
        if name == "prepare":
            p.add_argument("--start", action="store_true")
            p.add_argument("--ack-user-envelope", action="store_true")
    sub.add_parser("status")
    p = sub.add_parser("packet")
    p.add_argument("--human-event-id", required=True)
    a = ap.parse_args()
    output = prepare_output(a.output, getattr(a, "input", None), a.db)
    req = read_json(a.input) if hasattr(a, "input") else None
    if req is not None:
        validate_schema(req, REQUESTS[a.command])
    if a.command == "prepare" and not a.ack_user_envelope:
        raise CICError("prepare requires --ack-user-envelope before creating or writing a session")
    if not Path(a.db).exists():
        if a.command != "prepare" or not a.start:
            raise CICError("A missing session DB requires explicit prepare --start")
        initial = open_ledger(a.db, writable=True, new_only=True)
        initial.close()
    session = Session(a.db, a.conversation, a.branch, writable=a.command in {"prepare", "dispatch", "complete"})
    try:
        if a.command == "status":
            result = session.status()
        elif a.command == "packet":
            result = session.packet(a.human_event_id)
        else:
            if a.command == "prepare":
                result = session.prepare(req["raw"], req["turn_id"], start=a.start, ack_user=a.ack_user_envelope)
            elif a.command == "dispatch":
                result = session.dispatch(req["human_event_id"], req["dispatch_id"], now=req["now"], routing=req.get("routing", "ANNOTATE"), node_ids=req.get("node_ids"), required_event_ids=req.get("required_event_ids"), task_id=req.get("task_id"))
            else:
                result = session.complete(req["human_event_id"], req["raw"], req["response_id"], req["expected_state_version"], deferred=req.get("deferred"), turn_ir=req.get("turn_ir"), dispatch_event_id=req.get("dispatch_event_id"), response_status=req.get("response_status", "prepared"))
        emit({"ok": True, "command": a.command, "result": result}, output)
    finally:
        session.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        main()
    except (CICError, OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        print(json.dumps({"ok": False, "error": {"type": type(error).__name__, "message": str(error)},
                          "recovery": "Read status/packet and retry with the same IDs. A write may precede an output failure."}, ensure_ascii=False))
        sys.exit(1)
