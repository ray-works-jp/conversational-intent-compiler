"""Packaging contract tests: manifest versions, skill frontmatter, install_skill.py."""
import json, re, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "conversational-intent-compiler"
INSTALL = ROOT / "scripts" / "install_skill.py"
MANIFESTS = ["plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json"]

def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)

class PackageTests(unittest.TestCase):
    def test_manifest_versions_agree(self):
        versions = {m: json.loads((ROOT / m).read_text("utf-8"))["version"] for m in MANIFESTS}
        self.assertEqual(len(set(versions.values())), 1, versions)
        v = next(iter(versions.values()))
        self.assertIn(f"version {v}", (ROOT / "README.md").read_text("utf-8"))
        self.assertEqual(json.loads((ROOT / "release-verification.json").read_text("utf-8"))["release"], v)
        self.assertIn(f"## {v} ", (ROOT / "CHANGELOG.md").read_text("utf-8"))

    def test_upstream_hashes_match_files(self):
        import hashlib
        files = json.loads((ROOT / "resources" / "upstream-files.json").read_text("utf-8"))["files"]
        bad = [f["packaged"] for f in files
               if hashlib.sha256((ROOT / f["packaged"]).read_bytes()).hexdigest() != f["sha256"]]
        self.assertEqual(bad, [])

    def test_antigravity_plugin_hooks_json(self):
        cfg = json.loads((ROOT / "hooks.json").read_text("utf-8"))
        cmds = [h["command"] for v in cfg.values() for h in v.get("PreInvocation", [])]
        self.assertEqual(len(cmds), 1)
        script = cmds[0].split()[-1]
        self.assertFalse(Path(script).is_absolute())  # Antigravity runs plugin hooks with cwd = plugin dir
        self.assertTrue((ROOT / script).exists())

    def test_skill_frontmatter(self):
        head = (SKILL / "SKILL.md").read_text("utf-8").split("---")[1]
        self.assertRegex(head, r"(?m)^name: conversational-intent-compiler$")
        self.assertRegex(head, r"(?m)^description: \S")

    def test_install_layout_and_cli(self):
        with tempfile.TemporaryDirectory() as t:
            r = run(INSTALL, Path(t) / "skills")
            self.assertEqual(r.returncode, 0, r.stderr)
            dest = Path(t) / "skills" / "conversational-intent-compiler"
            for f in ("cic.py", "cic_cli.py", "schema_spec.py"):
                self.assertEqual((dest / "scripts" / f).read_bytes(), (ROOT / "scripts" / f).read_bytes())
            self.assertFalse((dest / "scripts" / "test_cli.py").exists())
            self.assertEqual(sorted(p.name for p in (dest / "schemas").iterdir()),
                             sorted(p.name for p in (ROOT / "schemas").iterdir()))
            self.assertTrue((dest / "references" / "operation-guide.md").exists())
            self.assertTrue((dest / "scripts" / "cic_loop.py").exists())
            self.assertTrue((dest / "resources" / "intent-compiler" / "first-compiler-0.1.0" / "skills" / "compile-intent" / "references" / "system-prompt.md").exists())
            for f in ("cic_ledger.py", "capture_antigravity.py"):
                self.assertTrue((dest / "hooks" / f).exists())
            r = run(dest / "scripts" / "install_antigravity_hook.py", "--workspace", Path(t) / "ws")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn((dest / "hooks" / "capture_antigravity.py").as_posix(), (Path(t) / "ws" / ".agents" / "hooks.json").read_text("utf-8"))
            self.assertEqual((dest / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
            r = run(dest / "scripts" / "cic_cli.py", "--db", Path(t) / "s.db", "init",
                    "--conversation", "c", "--branch", "main")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(json.loads(r.stdout)["ok"])

    def test_install_refuses_overwrite_unless_force(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(run(INSTALL, t).returncode, 0)
            marker = Path(t) / "conversational-intent-compiler" / "stale.txt"
            marker.write_text("x")
            self.assertNotEqual(run(INSTALL, t).returncode, 0)
            self.assertTrue(marker.exists())
            self.assertEqual(run(INSTALL, t, "--force").returncode, 0)
            self.assertFalse(marker.exists())

if __name__ == "__main__":
    unittest.main()
