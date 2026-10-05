"""Claude Code UserPromptSubmit hook: opt-in raw capture of each human prompt.

Records ONLY the verbatim human prompt into a per-session ledger via cic_cli.py.
It never interprets, summarises or blocks the prompt, prints nothing to stdout
(stdout would be injected into the model context) and always exits 0.

Enable with CIC_CAPTURE=1 in the environment that starts Claude Code.
Ledgers live in $CIC_LEDGER_DIR, else $CLAUDE_PLUGIN_DATA/ledgers, else ~/.cic/ledgers.
"""
import json, os, re, subprocess, sys, tempfile
from pathlib import Path

CLI = Path(__file__).resolve().parent.parent / "scripts" / "cic_cli.py"

def log(msg):
    print(f"[cic-capture] {msg}", file=sys.stderr)

def ledger_dir():
    base = os.environ.get("CIC_LEDGER_DIR")
    if not base:
        data = os.environ.get("CLAUDE_PLUGIN_DATA")
        base = str(Path(data) / "ledgers") if data else str(Path.home() / ".cic" / "ledgers")
    Path(base).mkdir(parents=True, exist_ok=True)
    return Path(base)

def run(db, *args):
    r = subprocess.run([sys.executable, str(CLI), "--db", str(db), *args], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout, r.stderr

def main():
    if os.environ.get("CIC_CAPTURE") != "1":
        return
    data = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    prompt, sid = data.get("prompt"), data.get("session_id")
    if not isinstance(prompt, str) or not prompt or not sid:
        log("no prompt/session_id in hook input; nothing recorded")
        return
    conv = re.sub(r"[^A-Za-z0-9_-]", "-", str(sid))[:64]
    db = ledger_dir() / f"{conv}.db"
    counter = db.with_suffix(".count")
    if not db.exists():
        code, _, err = run(db, "init", "--conversation", conv, "--branch", "main")
        if code != 0:
            log(f"init failed: {err.strip()[:200]}")
            return
    n = int(counter.read_text()) + 1 if counter.exists() else 1
    request = {"event_id": f"{conv}:main:H{n}", "raw": prompt, "conversation": conv, "branch": "main",
               "origin": "user", "kind": "human", "principal": "current-human", "attrs": {"source": "claude-code-hook"},
               "parent_ids": [f"{conv}:main:H{n-1}"] if n > 1 else [], "reference_ids": []}
    with tempfile.TemporaryDirectory() as t:
        req = Path(t) / "req.json"
        req.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        code, _, err = run(db, "capture", "--input", str(req), "--output", str(Path(t) / "out.json"), "--ack-user-envelope")
    if code != 0:
        log(f"capture failed (turn {n}): {err.strip()[:200]}")
        return
    counter.write_text(str(n))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never break the user's turn
        log(f"error: {e!r}")
    sys.exit(0)
