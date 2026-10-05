"""Install the skill as a self-contained folder for hosts that load bare skills
(e.g. Antigravity: <workspace>/.agent/skills/ or ~/.gemini/antigravity/skills/).

Layout written: <target>/<name>/{SKILL.md, references/, scripts/, schemas/}
so that SKILL_ROOT == PLUGIN_ROOT. Refuses to overwrite unless --force."""
import argparse, shutil, sys
from pathlib import Path

NAME = "conversational-intent-compiler"
ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ("cic.py", "cic_cli.py", "schema_spec.py")

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("target", type=Path, help="skills directory, e.g. .agent/skills")
    ap.add_argument("--force", action="store_true", help="replace an existing install")
    a = ap.parse_args()
    dest = a.target.resolve() / NAME
    if dest.exists():
        if not a.force:
            sys.exit(f"exists: {dest} (use --force)")
        shutil.rmtree(dest)
    shutil.copytree(ROOT / "skills" / NAME, dest)
    (dest / "scripts").mkdir()
    for f in RUNTIME:
        shutil.copy2(ROOT / "scripts" / f, dest / "scripts" / f)
    shutil.copytree(ROOT / "schemas", dest / "schemas")
    print(dest)

if __name__ == "__main__":
    main()
