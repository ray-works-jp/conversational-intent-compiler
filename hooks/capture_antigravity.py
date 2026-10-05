"""Antigravity PreInvocation hook: opt-in raw capture of human turns from the transcript.

Antigravity passes no prompt text to hooks, only `transcriptPath` and `conversationId`.
This reads the transcript JSONL and records every USER_EXPLICIT USER_INPUT step not yet
recorded, with the text inside <USER_REQUEST>...</USER_REQUEST> kept verbatim.
Prints `{}` to stdout, always exits 0. Enable with CIC_CAPTURE=1.
"""
import json, re, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import cic_ledger as L

REQ = re.compile(r"<USER_REQUEST>\n?(.*?)\n?</USER_REQUEST>", re.S)

def main():
    if not L.enabled():
        return
    data = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
    cid, path = data.get("conversationId"), data.get("transcriptPath")
    if not cid or not path:
        L.log("no conversationId/transcriptPath in hook input; nothing recorded")
        return
    with open(path, encoding="utf-8") as f:
        steps = [json.loads(l) for l in f if l.strip()]
    for s in steps:
        if s.get("type") != "USER_INPUT" or s.get("source") != "USER_EXPLICIT":
            continue
        m = REQ.search(s.get("content", ""))
        if m and m.group(1):
            L.append_human(cid, m.group(1), "antigravity-hook", step=int(s.get("step_index", 0)))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never break the user's turn
        L.log(f"error: {e!r}")
    print("{}")
    sys.exit(0)
