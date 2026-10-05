"""Score pilot ledgers against scenarios.json (deterministic keyword checks; read mismatches by hand).

  python score_pilot.py --dir OUT_DIR
Reads each ledger through cic_cli.py `state` (no writes) and prints per-check PASS/FAIL plus
apply counts (state_version, pending_human). A FAIL is a prompt for human review, not proof of error.
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLI = HERE.parent.parent.parent / "scripts" / "cic_cli.py"

def state(db, conv):
    r = subprocess.run([sys.executable, str(CLI), "--db", str(db), "state", "--conversation", conv, "--branch", "main"],
                       capture_output=True, text=True, encoding="utf-8")
    return json.loads(r.stdout)["result"]["state"] if r.returncode == 0 else None

def check(st, c):
    nodes = list(st["nodes"].values())
    if "authority" in c:
        grants = [a for a in st["authorities"].values() if a.get("lifecycle", a.get("status")) == "active"]
        unconditional = [g for g in grants if not g.get("conditions") and not g.get("condition")]
        return not unconditional, f"{len(grants)} active grants, {len(unconditional)} without condition"
    hits = [n for n in nodes if c["kw"] in n["content"] and (not c.get("role") or n["role"] in c["role"])]
    active = [n for n in hits if n["lifecycle"] == "active"]
    ok = bool(active) if c["expect"] == "active" else not active
    return ok, f"{len(hits)} matching nodes, {len(active)} active"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    a = ap.parse_args()
    scs = json.loads((HERE / "scenarios.json").read_text("utf-8"))["scenarios"]
    tot = ok_n = 0
    for sc in scs:
        db = a.dir / f"{sc['id']}.db"
        if not db.exists():
            print(f"{sc['id']}: no ledger"); continue
        st = state(db, sc["id"][:2].lower())
        if st is None:
            print(f"{sc['id']}: state unreadable"); continue
        print(f"{sc['id']}: state_version={st['state_version']} pending_human={len(st['pending_human'])} (turns={len(sc['turns'])})")
        for c in sc["checks"]:
            ok, why = check(st, c); tot += 1; ok_n += ok
            print(f"  {'PASS' if ok else 'FAIL'} {json.dumps(c, ensure_ascii=False)} -- {why}")
    print(f"checks passed: {ok_n}/{tot}")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
