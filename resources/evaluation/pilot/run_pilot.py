"""Run each pilot scenario through a real host (Claude Code headless) and store the resulting ledgers.

  python run_pilot.py --out OUT_DIR [--only S1-...]    # needs the `claude` CLI; makes model calls

Each scenario is processed in ONE headless session following the skill's capture ->
delta-template -> interpret -> validate -> apply loop. The ledger DB is written under OUT_DIR.
Score afterwards with score_pilot.py. No external action is performed by the scenarios.
"""
import argparse, json, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent

def prompt(sc, db):
    turns = "\n".join(f"H{i+1}: {t}" for i, t in enumerate(sc["turns"]))
    return (f"conversational-intent-compiler skill を使い、次の人間発話を、この順に1つずつ処理してください。"
            f"台帳DBは {db}、conversation は {sc['id'][:2].lower()}、branch は main。手順書(operation-guide.md / candidate-format.md)に従い、"
            f"各発話を capture(--ack-user-envelope、event IDは <conversation>:main:H1〜、parent_idsは直前のevent)→delta-template→"
            f"意味解釈でoperationsを作成→validate→apply の順に進めること。外部操作(予約・送信など)は一切しない。"
            f"全て終えたら state は出力せず、処理件数とapply成功件数だけ報告。\n{turns}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only")
    ap.add_argument("--timeout", type=int, default=580)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    scs = json.loads((HERE / "scenarios.json").read_text("utf-8"))["scenarios"]
    log = {}
    for sc in scs:
        if a.only and sc["id"] != a.only:
            continue
        db = (a.out / f"{sc['id']}.db").resolve()
        if db.exists():
            print(f"skip {sc['id']} (ledger exists)"); continue
        t0 = time.time()
        cmd = ["claude", "--plugin-dir", str(REPO), "--add-dir", str(REPO), "--allowedTools", "Read", "Write", "Bash(python:*)", "PowerShell", "-p", prompt(sc, db.as_posix())]
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=a.out, timeout=a.timeout)
        log[sc["id"]] = {"seconds": round(time.time() - t0), "returncode": r.returncode, "reply_tail": r.stdout[-400:]}
        print(sc["id"], log[sc["id"]]["seconds"], "s rc", r.returncode)
    (a.out / "run-log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
