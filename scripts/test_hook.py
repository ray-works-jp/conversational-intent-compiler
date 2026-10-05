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



AG_HOOK = ROOT / "hooks" / "capture_antigravity.py"

def ag_fire(payload, env_extra):
    env = {**os.environ, **env_extra}
    return subprocess.run([sys.executable, str(AG_HOOK)], input=json.dumps(payload).encode("utf-8"),
                          capture_output=True, env=env)

class AntigravityHookTests(unittest.TestCase):
    def transcript(self, t, texts):
        p = Path(t) / "transcript_full.jsonl"
        steps = []
        for i, text in enumerate(texts):
            steps.append({"step_index": 2 * i, "source": "USER_EXPLICIT", "type": "USER_INPUT",
                          "content": f"<USER_REQUEST>\n{text}\n</USER_REQUEST>\n<ADDITIONAL_METADATA>\nx"})
            steps.append({"step_index": 2 * i + 1, "source": "MODEL", "type": "PLANNER_RESPONSE", "content": "<USER_REQUEST>no</USER_REQUEST>"})
        p.write_text("\n".join(json.dumps(s, ensure_ascii=False) for s in steps), encoding="utf-8")
        return p

    def test_records_user_steps_once_and_ignores_model_steps(self):
        with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as led:
            env = {"CIC_CAPTURE": "1", "CIC_LEDGER_DIR": led}
            msg = lambda p: {"conversationId": "conv-1", "transcriptPath": str(p)}
            r = ag_fire(msg(self.transcript(t, ["最初の依頼"])), env)
            self.assertEqual((r.returncode, r.stdout.strip()), (0, b"{}"), r.stderr)
            ag_fire(msg(self.transcript(t, ["最初の依頼", "二つ目 \n(空白保持)"])), env)
            ag_fire(msg(self.transcript(t, ["最初の依頼", "二つ目 \n(空白保持)"])), env)  # repeat: no duplicates
            evs = events(Path(led) / "conv-1.db")
            self.assertEqual([e["raw"] for e in evs], ["最初の依頼", "二つ目 \n(空白保持)"])
            self.assertEqual(evs[1]["parent_ids"], [evs[0]["event_id"]])
            self.assertEqual(evs[0]["attrs"]["source"], "antigravity-hook")

    def test_disabled_and_bad_input_are_silent(self):
        with tempfile.TemporaryDirectory() as t, tempfile.TemporaryDirectory() as led:
            p = self.transcript(t, ["x"])
            r = ag_fire({"conversationId": "c", "transcriptPath": str(p)}, {"CIC_LEDGER_DIR": led})
            self.assertEqual((r.returncode, r.stdout.strip()), (0, b"{}"))
            self.assertEqual(list(Path(led).iterdir()), [])
            r = ag_fire({"conversationId": "c", "transcriptPath": str(Path(t) / "missing.jsonl")},
                        {"CIC_CAPTURE": "1", "CIC_LEDGER_DIR": led})
            self.assertEqual((r.returncode, r.stdout.strip()), (0, b"{}"))

if __name__ == "__main__":
    unittest.main()
