"""Contract tests for hooks/capture_turn.py (opt-in raw capture of human prompts)."""
import json, os, sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "capture_turn.py"

def fire(payload, env_extra, raw=None):
    env = {**os.environ, **env_extra}
    for k in ("CIC_CAPTURE", "CIC_LEDGER_DIR"):
        if k not in env_extra:
            env.pop(k, None)
    data = raw if raw is not None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return subprocess.run([sys.executable, str(HOOK)], input=data, capture_output=True, env=env)

def events(db):
    c = sqlite3.connect(db)
    try:
        return [json.loads(p) for (p,) in c.execute("select payload from events order by seq")]
    finally:
        c.close()

class HookTests(unittest.TestCase):
    def test_disabled_by_default_writes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            r = fire({"session_id": "s", "prompt": "hello"}, {"CIC_LEDGER_DIR": t})
            self.assertEqual((r.returncode, r.stdout), (0, b""))
            self.assertEqual(list(Path(t).iterdir()), [])

    def test_enabled_records_verbatim_human_turns_in_order(self):
        prompts = ["2番で。ホテルだけもう少し安くして", "  やっぱり日程は来週に\n(改行と空白も保持)"]
        with tempfile.TemporaryDirectory() as t:
            for p in prompts:
                r = fire({"session_id": "sess 1", "prompt": p}, {"CIC_CAPTURE": "1", "CIC_LEDGER_DIR": t})
                self.assertEqual((r.returncode, r.stdout), (0, b""), r.stderr)
            evs = events(Path(t) / "sess-1.db")
            self.assertEqual([e["raw"] for e in evs], prompts)
            self.assertTrue(all(e["origin"] == "user" and e["kind"] == "human" for e in evs))
            self.assertEqual(evs[1]["parent_ids"], [evs[0]["event_id"]])

    def test_never_breaks_the_turn_on_bad_input(self):
        with tempfile.TemporaryDirectory() as t:
            env = {"CIC_CAPTURE": "1", "CIC_LEDGER_DIR": t}
            for raw in (b"not json", b"{}", b'{"session_id":"s"}'):
                r = fire(None, env, raw=raw)
                self.assertEqual((r.returncode, r.stdout), (0, b""))

if __name__ == "__main__":
    unittest.main()
