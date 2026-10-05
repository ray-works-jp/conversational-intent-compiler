"""Explicit, stateful local CLI wrapper around the unchanged offline prototype.

This tool records and mechanically checks supplied interpretations. It neither
authenticates users nor proves semantic permission nor executes external actions.
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from cic import (Ledger, CICError, IntegrityError, apply_delta, canonical,
                 validate_named, operation, COMPILER_VERSION)
from schema_spec import VERSION, SCHEMAS

LIMITATIONS = [
    "Explicit invocation only; no all-turn interception or Work hooks.",
    "Candidate interpretation is supplied by the caller; semantic correctness is unverified.",
    "User-envelope and authority-review flags are caller attestations, not authentication or execution permission.",
    "No external side effect is executed or authorized by this CLI.",
    "Raw capture and projection share a transaction; a capture failure requires source-preserving retry.",
]

def read_json(path):
    # UTF-8 transport JSON may have a BOM. The raw string inside is not normalized.
    with Path(path).open("r", encoding="utf-8-sig", newline="") as source:
        return json.load(source)

def request(value, allowed, required=()):
    if not isinstance(value, dict): raise CICError("JSON input must be an object")
    unknown = set(value) - set(allowed)
    missing = set(required) - set(value)
    if unknown: raise CICError("Unsupported input fields: " + ", ".join(sorted(unknown)))
    if missing: raise CICError("Missing input fields: " + ", ".join(sorted(missing)))
    # The embedded prototype will enforce types and transition-specific contracts.
    canonical(value)
    return value

def open_ledger(path, *, writable, new_only=False):
    path = Path(path).resolve()
    if writable:
        if new_only:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Reserve the path atomically; init never reopens/replaces an existing file.
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
            return Ledger(path)
        if path.exists():
            # Refuse to retrofit CIC tables into an unrelated SQLite database.
            check = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
            try:
                objects = {row[0] for row in check.execute("SELECT name FROM sqlite_master")}
                if not {"events", "projections", "immutable_event_update", "immutable_event_delete"} <= objects:
                    raise CICError("Existing database is not an initialized CIC ledger")
                event_columns = [r[1] for r in check.execute("PRAGMA table_info(events)")]
                projection_columns = [r[1] for r in check.execute("PRAGMA table_info(projections)")]
                if event_columns != ["event_id", "conversation_id", "branch_id", "seq", "payload", "request_sha256"] or projection_columns != ["conversation_id", "branch_id", "state"]:
                    raise CICError("Existing CIC database schema is incompatible")
            finally: check.close()
        path.parent.mkdir(parents=True, exist_ok=True)
        return Ledger(path)
    if not path.is_file(): raise CICError("Read-only command requires an existing ledger database")
    # Avoid Ledger.__init__'s DDL, WAL configuration and creation side effects.
    ledger = Ledger.__new__(Ledger)
    ledger.path = str(path)
    ledger.db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, isolation_level=None, timeout=10)
    ledger.db.row_factory = sqlite3.Row
    ledger.db.execute("PRAGMA query_only=ON")
    return ledger

def checked_state(ledger, conversation, branch):
    state = ledger.state(conversation, branch)
    if state != ledger.replay(conversation, branch): raise IntegrityError("Projection differs from replay; use explicit rebuild")
    return state

def prepare_output(path, input_path, database_path):
    if path is None: return None
    result_path = Path(path).resolve()
    db_path = Path(database_path).resolve()
    protected = {db_path, *(Path(str(db_path) + suffix).resolve() for suffix in ["-wal", "-shm", "-journal"])}
    if input_path: protected.add(Path(input_path).resolve())
    protected |= {Path(__file__).resolve(), Path(__file__).with_name("cic.py").resolve(), Path(__file__).with_name("schema_spec.py").resolve()}
    if result_path in protected: raise CICError("Output may not overwrite input, ledger, or plugin source")
    if result_path.exists(): raise CICError("Output already exists; use a new result filename")
    return result_path

def emit(payload, output):
    text = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if output is None:
        sys.stdout.write(text)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    # O_EXCL provides a final race-safe no-overwrite check. Output is caller-owned.
    fd = os.open(str(output), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as target:
        target.write(text)
        target.flush()
        os.fsync(target.fileno())
    sys.stdout.write(json.dumps({"ok": True, "output": str(output)}, ensure_ascii=False) + "\n")

def parser():
    top = argparse.ArgumentParser(description=__doc__)
    top.add_argument("--db", required=True, help="Caller-selected persistent SQLite file")
    commands = top.add_subparsers(dest="command", required=True)
    for name in ["init", "capture", "delta-template", "apply", "validate", "package", "state", "replay", "rebuild", "preflight", "artifact", "tick", "fork"]:
        cmd = commands.add_parser(name)
        cmd.add_argument("--output", help="New JSON output file; existing files are refused")
        if name in {"capture", "apply", "validate", "package", "preflight", "artifact", "tick", "fork"}:
            cmd.add_argument("--input", required=True, help="UTF-8 JSON request file")
        if name in {"init", "state", "replay", "rebuild"}:
            cmd.add_argument("--conversation", default="c1")
            cmd.add_argument("--branch", default="main")
        if name == "capture": cmd.add_argument("--ack-user-envelope", action="store_true", help="Only for raw actually obtained from a human-user transport")
        if name == "apply": cmd.add_argument("--ack-authority-review", action="store_true", help="Caller review attestation; neither authentication nor external permission")
        if name == "delta-template": cmd.add_argument("--human-event-id", required=True)
        if name == "validate":
            cmd.add_argument("--kind", required=True, choices=list(SCHEMAS))
            cmd.add_argument("--transition", action="store_true", help="Delta dry-run against current ledger, without commit")
    return top

def run(args):
    output = prepare_output(args.output, getattr(args, "input", None), args.db)
    command = args.command
    data = read_json(args.input) if getattr(args, "input", None) else None
    # Schema-only validation needs no database connection or creation.
    if command == "validate" and not args.transition:
        validate_named(args.kind, data)
        return output, {"schema_valid": True, "transition_checked": False, "semantic_verified": False, "committed": False}
    writable = command in {"init", "capture", "apply", "rebuild", "artifact", "tick", "fork"}
    if writable and command != "init" and not Path(args.db).is_file(): raise CICError("Initialize the ledger before mutating it")
    ledger = open_ledger(args.db, writable=writable, new_only=command == "init")
    try:
        if command == "init":
            state = checked_state(ledger, args.conversation, args.branch)
            result = {"database": str(Path(args.db).resolve()), "state": state, "existing_events": len(ledger.events(args.conversation, args.branch))}
        elif command == "capture":
            request(data, ["event_id", "raw", "conversation", "branch", "origin", "kind", "principal", "attrs", "parent_ids", "reference_ids", "effective_at"], ["event_id", "raw", "origin"])
            origin = data["origin"]
            allowed_kinds = {"user": {"human"}, "assistant": {"assistant"}, "tool": {"tool_result", "action_status"}, "external": {"external"}}
            if origin not in allowed_kinds: raise CICError("Capture origin must be user, assistant, tool or external")
            if "kind" in data and data["kind"] not in allowed_kinds[origin]: raise CICError("Capture kind/origin mismatch; use artifact/tick/fork for structural events")
            if origin == "user" and not args.ack_user_envelope: raise CICError("User capture requires explicit --ack-user-envelope transport attestation")
            if origin != "user" and args.ack_user_envelope: raise CICError("Non-user capture may not claim a trusted human envelope")
            kwargs = {k: v for k, v in data.items() if k not in {"event_id", "raw"}}
            kwargs["trusted_identity"] = origin == "user" and args.ack_user_envelope
            result = ledger.capture(data["event_id"], data["raw"], **kwargs)
        elif command == "delta-template":
            delta = ledger.delta(args.human_event_id, [operation("NO_CHANGE")])
            delta["interpretation_method"] = "reviewed_external_candidate"
            result = {"candidate_delta": delta, "committed": False,
                      "instruction": "Replace NO_CHANGE only with source-supported operations. Recheck raw, scope, current base state and unresolved alternatives before apply."}
        elif command == "apply":
            validate_named("delta", data)
            if data["authority_operations"] and not args.ack_authority_review: raise CICError("Authority operations require separate --ack-authority-review; source text alone is insufficient")
            result = ledger.commit(data)
        elif command == "validate":
            if args.kind != "delta": raise CICError("--transition is supported only for Delta")
            validate_named("delta", data)
            state = checked_state(ledger, data["conversation_id"], data["branch_id"])
            preview = apply_delta(state, data, ledger._lookup(data["conversation_id"], data["branch_id"]))
            result = {"schema_valid": True, "transition_valid": True, "semantic_verified": False,
                      "committed": False, "projected_state_preview": preview}
        elif command == "package":
            request(data, ["human_event_id", "now", "routing", "node_ids", "task_id", "required_event_ids"], ["human_event_id", "now"])
            result = ledger.package(**data)
        elif command == "state":
            result = {"state": checked_state(ledger, args.conversation, args.branch), "integrity_verified": True}
        elif command == "replay":
            result = {"state": ledger.replay(args.conversation, args.branch), "cache_updated": False, "external_actions_reexecuted": False}
        elif command == "rebuild":
            result = {"state": ledger.rebuild(args.conversation, args.branch), "cache_updated": True, "external_actions_reexecuted": False}
        elif command == "preflight":
            request(data, ["actor", "action", "target_id", "target_version", "now", "conversation", "branch", "conditions", "turn_id", "task_id"], ["actor", "action", "target_id", "target_version", "now"])
            gate = ledger.preflight(**data)
            result = {"contract_check": gate, "mechanical_allowed": gate["allowed"],
                      "external_execution_authorized": False, "semantic_authority_verified": False,
                      "meaning": "Mechanical ledger compatibility only. The host must verify actual user authority and recheck immediately before a side effect."}
        elif command == "artifact":
            request(data, ["event_id", "artifact_id", "version", "path", "created_by", "conversation", "branch", "media_type"], ["event_id", "artifact_id", "version", "path", "created_by"])
            result = ledger.add_artifact(**data)
        elif command == "tick":
            request(data, ["event_id", "now", "conversation", "branch"], ["event_id", "now"])
            result = ledger.tick(**data)
        elif command == "fork":
            request(data, ["new_branch", "conversation", "parent_branch", "parent_watermark"], ["new_branch"])
            result = {"state": ledger.fork(**data)}
        else: raise CICError("Unsupported command")
        return output, result
    finally: ledger.close()

def main(argv=None):
    # Windows pipe defaults can be cp932; the CLI transport is always UTF-8.
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, "reconfigure"): stream.reconfigure(encoding="utf-8", errors="strict", newline="\n")
    args = parser().parse_args(argv)
    result = None
    try:
        output, result = run(args)
        payload = {"ok": True, "command": args.command, "schema_version": VERSION,
                   "compiler_version": COMPILER_VERSION, "result": result,
                   "external_execution_authorized": False, "limitations": LIMITATIONS}
        emit(payload, output)
        return 0
    except (ValueError, sqlite3.Error, OSError, UnicodeError, TypeError, KeyError) as exc:
        # stdout always remains machine-readable; no raw text or traceback is added.
        mutating = args.command in {"init", "capture", "apply", "rebuild", "artifact", "tick", "fork"}
        operation_ids = {}
        if getattr(args, "input", None):
            try:
                data = read_json(args.input)
                if isinstance(data, dict): operation_ids = {k: data[k] for k in ["event_id", "delta_id", "human_event_id"] if k in data}
            except (ValueError, OSError, UnicodeError): pass
        sys.stdout.write(json.dumps({"ok": False, "command": args.command,
                                     "error": {"type": type(exc).__name__, "message": str(exc)},
                                     "state_may_have_changed": mutating,
                                     "mutation_status": "confirmed_committed" if mutating and result is not None else "unknown_check_ledger" if mutating else "not_applicable",
                                     "operation_ids": operation_ids,
                                     "recovery": "Inspect state/replay and retry only with the same event/delta IDs and unchanged input; output publication may fail after commit.",
                                     "external_execution_authorized": False}, ensure_ascii=False) + "\n")
        return 2

if __name__ == "__main__": sys.exit(main())
