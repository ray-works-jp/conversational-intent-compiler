"""Shared helper for host hooks: append verbatim human turns to a per-session ledger."""
import json, os, re, subprocess, sys, tempfile
from pathlib import Path

CLI = Path(__file__).resolve().parent.parent / "scripts" / "cic_cli.py"

def log(msg):
    print(f"[cic-capture] {msg}", file=sys.stderr)

def enabled():
    return os.environ.get("CIC_CAPTURE") == "1"

def ledger_dir():
    # One fixed default so hooks and the skill's Bash (which lacks CLAUDE_PLUGIN_DATA) agree.
    base = os.environ.get("CIC_LEDGER_DIR") or str(Path.home() / ".cic" / "ledgers")
    Path(base).mkdir(parents=True, exist_ok=True)
    return Path(base)

def _run(db, *args):
    r = subprocess.run([sys.executable, str(CLI), "--db", str(db), *args], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stderr

def conv_id(session_id):
    return re.sub(r"[^A-Za-z0-9_-]", "-", str(session_id))[:64]

def append_human(session_id, raw, host, step=None):
    """Record one verbatim human turn. `step` (host-side ordinal) lets callers skip already-recorded turns."""
    conv = conv_id(session_id)
    db = ledger_dir() / f"{conv}.db"
    side = db.with_suffix(".count")
    st = json.loads(side.read_text("utf-8")) if side.exists() else {"n": 0, "last_step": -1}
    if step is not None and step <= st["last_step"]:
        return False
    if not db.exists():
        code, err = _run(db, "init", "--conversation", conv, "--branch", "main")
        if code != 0:
            log(f"init failed: {err.strip()[:200]}")
            return False
    n = st["n"] + 1
    req = {"event_id": f"{conv}:main:H{n}", "raw": raw, "conversation": conv, "branch": "main",
           "origin": "user", "kind": "human", "principal": "current-human", "attrs": {"source": host},
           "parent_ids": [f"{conv}:main:H{n-1}"] if n > 1 else [], "reference_ids": []}
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "req.json"
        p.write_text(json.dumps(req, ensure_ascii=False), encoding="utf-8")
        code, err = _run(db, "capture", "--input", str(p), "--output", str(Path(t) / "out.json"), "--ack-user-envelope")
    if code != 0:
        log(f"capture failed (turn {n}): {err.strip()[:200]}")
        return False
    st["n"] = n
    if step is not None:
        st["last_step"] = step
    side.write_text(json.dumps(st), encoding="utf-8")
    return True
