"""Write an Antigravity hooks.json that runs hooks/capture_antigravity.py on PreInvocation.

  python scripts/install_antigravity_hook.py --workspace DIR   -> DIR/.agents/hooks.json
  python scripts/install_antigravity_hook.py --global          -> ~/.gemini/config/hooks.json

Refuses to touch an existing hooks.json that already has a "cic-capture" entry unless --force,
and merges into other entries otherwise. The hook only records when CIC_CAPTURE=1 is set.
"""
import argparse, json, sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "capture_antigravity.py"

def hook_arg():
    # Antigravity runs the command without a shell: embedded quotes break the path.
    p = HOOK.as_posix()
    if any(c.isspace() for c in p):
        sys.exit(f"hook path contains whitespace, which Antigravity cannot run reliably: {p}")
    return p

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--workspace", type=Path)
    g.add_argument("--global", dest="glob", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    target = Path.home() / ".gemini" / "config" / "hooks.json" if a.glob else a.workspace.resolve() / ".agents" / "hooks.json"
    cfg = json.loads(target.read_text("utf-8")) if target.exists() else {}
    if "cic-capture" in cfg and not a.force:
        sys.exit(f"cic-capture already present in {target} (use --force)")
    cfg["cic-capture"] = {"enabled": True, "PreInvocation": [{"command": f"python {hook_arg()}"}]}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(target)

if __name__ == "__main__":
    main()
