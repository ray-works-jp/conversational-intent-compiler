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
