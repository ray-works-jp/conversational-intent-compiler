"""Claude Code UserPromptSubmit hook: opt-in raw capture of each human prompt.

Records ONLY the verbatim human prompt via cic_cli.py. Never interprets or blocks the
prompt, prints nothing to stdout (it would be injected into the model context) and
always exits 0. Enable with CIC_CAPTURE=1. See cic_ledger.py for where ledgers live.
"""
import json, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import cic_ledger as L

def main():
    if not L.enabled():
        return
    data = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    prompt, sid = data.get("prompt"), data.get("session_id")
    if not isinstance(prompt, str) or not prompt or not sid:
        L.log("no prompt/session_id in hook input; nothing recorded")
        return
    L.append_human(sid, prompt, "claude-code-hook")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never break the user's turn
        L.log(f"error: {e!r}")
    sys.exit(0)
