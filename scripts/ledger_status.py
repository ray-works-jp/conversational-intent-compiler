"""List hook-captured ledgers and their not-yet-interpreted human turns (read-only).

  python scripts/ledger_status.py [--dir DIR] [--conversation ID] [--limit N]

Prints JSON: for each ledger (newest first) the conversation id, state_version and
`pending`: the human events captured by the hooks that no applied Delta covers yet, with
their verbatim raw text. Interpretation (delta-template -> validate -> apply) stays with
the host AI; this tool never writes to a ledger.
"""
import argparse, json, os, sqlite3, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = Path(__file__).resolve().parent / "cic_cli.py"

def default_dir():
    base = os.environ.get("CIC_LEDGER_DIR")
    return Path(base) if base else Path.home() / ".cic" / "ledgers"

def raw_of(db, event_ids):
    c = sqlite3.connect(f"file:{Path(db).as_posix()}?mode=ro", uri=True)
    try:
        out = []
        for eid in event_ids:
            row = c.execute("select payload from events where event_id=?", (eid,)).fetchone()
            out.append({"event_id": eid, "raw": json.loads(row[0])["raw"] if row else None})
        return out
    finally:
        c.close()

def status(db):
    conv = Path(db).stem
    r = subprocess.run([sys.executable, str(CLI), "--db", str(db), "state", "--conversation", conv, "--branch", "main"],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        return {"conversation": conv, "error": (r.stderr or r.stdout).strip()[:200]}
    st = json.loads(r.stdout)["result"]["state"]
    return {"conversation": conv, "ledger": str(db), "state_version": st["state_version"],
            "pending": raw_of(db, st.get("pending_human", []))}

def main():
    sys.stdout.reconfigure(encoding="utf-8")  # raw text is Japanese; never depend on the console code page
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", type=Path)
    ap.add_argument("--conversation")
    ap.add_argument("--limit", type=int, default=5)
    a = ap.parse_args()
    d = a.dir or default_dir()
    dbs = sorted(d.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True) if d.exists() else []
    if a.conversation:
        dbs = [p for p in dbs if p.stem == a.conversation]
    print(json.dumps({"ledger_dir": str(d), "ledgers": [status(p) for p in dbs[: a.limit]]}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
