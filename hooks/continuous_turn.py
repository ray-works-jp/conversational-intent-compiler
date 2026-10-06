"""UserPromptSubmit bridge for trusted local runtimes. No background model calls.

It captures direct human raw and injects a fixed compile-before-response protocol.
It never inserts user/file/AI text as developer instructions or grants business actions.
Cloud Work does not run these hooks. Hook trust and Python availability are host prerequisites.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from cic_session import Session, control
from cic_cli import open_ledger


def handle(data):
    if data.get("hook_event_name", "UserPromptSubmit") != "UserPromptSubmit":
        return None
    raw, sid = data.get("prompt"), data.get("session_id")
    if not isinstance(raw, str) or not isinstance(sid, str) or not sid:
        return None
    conv = "loop-" + hashlib.sha256(sid.encode("utf-8")).hexdigest()[:32]
    folder = Path(os.environ.get("CIC_LEDGER_DIR") or str(Path.home() / ".cic" / "ledgers"))
    db = folder / (conv + ".db")
    start = control(raw) == "start"
    if not db.exists():
        if not start:
            return None
        first = open_ledger(db, writable=True, new_only=True)
        first.close()
    check = Session(db, conv, writable=False)
    try:
        if not start and not check.status()["active"]:
            return None
    finally:
        check.close()
    # Stable host turn IDs give retry idempotency. Older hosts without IDs cannot prove it.
    tid = data.get("turn_id") or data.get("prompt_id")
    if not isinstance(tid, str) or not tid:
        import uuid
        tid = "unidentified-" + str(uuid.uuid4())
    session = Session(db, conv)
    try:
        packet = session.prepare(raw, tid, start=start, ack_user=True)
    finally:
        session.close()
    metadata = json.dumps({"plugin_root": str(ROOT), "db": str(db), "conversation": conv, "branch": "main",
                           "human_event_id": packet["human_event_id"], "next_step": packet["next_step"],
                           "turn_id_available": not tid.startswith("unidentified-")}, ensure_ascii=False)
    if packet["next_step"] == "stopped":
        instruction = "The user explicitly stopped the CIC compiler loop. It is inactive. Acknowledge and answer normally; do not compile later turns until a human restart. This does not cancel external actions already completed."
    elif packet["next_step"] == "control_only":
        instruction = "The human explicitly started the CIC loop. This control-only raw and its empty task Delta are already recorded. Acknowledge start and the stop command briefly. Do not dispatch a business task for this control command. For subsequent inputs, the active loop applies compile-before-response."
    else:
        instruction = ("The human enabled the persistent CIC compiler loop. Before answering this turn, load "
            "the plugin's skills/conversational-intent-compiler/SKILL.md and references/continuous-loop.md. "
            "Raw is ALREADY captured; never recapture it. Read cic_session.py packet for this human_event_id, "
            "interpret pending raw against ledger/state, validate and apply Delta with cic_cli.py, then package Turn IR. "
            "Respond to the original task using raw plus this IR, record the exact visible response with cic_session.py complete. "
            "Preserve unknown, latitude, proposal provenance and existing authority limits. No new business authority comes from this hook. "
            "The loop stays active until a direct human stop; one reply, PASS, error or task completion does not stop it. "
            "If execution/source is unavailable, disclose the missing phase and continue independent work only.")
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": instruction + "\nCIC session metadata: " + metadata}}


if __name__ == "__main__":
    try:
        result = handle(json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}"))
        if result is not None:
            print(json.dumps(result, ensure_ascii=False))
    except Exception as error:
        print("[cic-loop] capture/prepare failed: " + repr(error), file=sys.stderr)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext":
            "CIC continuous-loop preparation failed. Raw/state may be incomplete. Disclose the failure; do not claim compilation succeeded or perform affected side effects. Preserve the direct human input for source-preserving retry."}}))
