"""Install the skill as a self-contained folder for hosts that load bare skills
(e.g. Antigravity: <workspace>/.agents/skills/ or the global dir for the Antigravity variant).

Layout written: <target>/<name>/{SKILL.md, references/, scripts/, schemas/}
so that SKILL_ROOT == PLUGIN_ROOT. Refuses to overwrite unless --force."""
import argparse, os, shutil, stat, sys
from pathlib import Path

NAME = "conversational-intent-compiler"
ROOT = Path(__file__).resolve().parent.parent
def _writable_retry(func, path, exc):
    # Windows: directories/files may carry a read-only attribute that blocks removal.
    os.chmod(path, stat.S_IWRITE)
    func(path)

RUNTIME = ("cic.py", "cic_cli.py", "schema_spec.py", "install_antigravity_hook.py")
HOOKS = ("cic_ledger.py", "capture_antigravity.py")

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("target", type=Path, help="skills directory, e.g. .agents/skills")
    ap.add_argument("--force", action="store_true", help="replace an existing install")
    a = ap.parse_args()
    dest = a.target.resolve() / NAME
    if dest.exists():
        if not a.force:
            sys.exit(f"exists: {dest} (use --force)")
        shutil.rmtree(dest, onexc=_writable_retry)
    shutil.copytree(ROOT / "skills" / NAME, dest)
    (dest / "scripts").mkdir()
    for f in RUNTIME:
        shutil.copy2(ROOT / "scripts" / f, dest / "scripts" / f)
    (dest / "hooks").mkdir()
    for f in HOOKS:
        shutil.copy2(ROOT / "hooks" / f, dest / "hooks" / f)
    shutil.copytree(ROOT / "schemas", dest / "schemas")
    shutil.copy2(ROOT / "LICENSE", dest / "LICENSE")
    print(dest)

if __name__ == "__main__":
    main()
