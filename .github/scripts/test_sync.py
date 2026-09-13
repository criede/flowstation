"""Exercise the actual sync script against local disposable Git repositories."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("sync-upstream.sh").resolve()


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.seed = self.root / "seed"
        self.fork = self.root / "fork"
        self.env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
                    "GIT_AUTHOR_NAME": "Test", "GIT_COMMITTER_NAME": "Test",
                    "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_COMMITTER_EMAIL": "test@example.invalid",
                    "GITHUB_OUTPUT": str(self.root / "output"),
                    "GITHUB_STEP_SUMMARY": str(self.root / "summary")}
        self.git(self.root, "init", "--bare", "upstream.git")
        self.git(self.root, "init", "--bare", "origin.git")
        self.git(self.root, "init", "-b", "main", "seed")
        (self.seed / ".github").mkdir()
        (self.seed / ".github" / "workflow").write_text("original\n")
        (self.seed / "source").write_text("original\n")
        self.commit(self.seed, "base")
        for name in ("upstream", "origin"):
            self.git(self.seed, "remote", "add", name, str(self.root / f"{name}.git"))
            self.git(self.seed, "push", name, "main")
        self.git(self.root, "clone", "-b", "main", str(self.root / "origin.git"), "fork")
        self.git(self.fork, "config", f"url.{self.root / 'upstream.git'}.insteadOf",
                 "https://github.com/razvanzeces/flowstation.git")

    def git(self, cwd, *args):
        return subprocess.check_output(["git", *args], cwd=cwd, env=self.env, text=True,
                                       stderr=subprocess.PIPE).strip()

    def commit(self, cwd, message):
        self.git(cwd, "add", ".")
        self.git(cwd, "commit", "-m", message)

    def sync(self):
        return subprocess.run(["bash", str(SCRIPT)], cwd=self.fork, env=self.env,
                              capture_output=True, text=True)

    def test_unchanged_does_not_build(self):
        result = self.sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("changed=false", (self.root / "output").read_text())

    def test_merge_preserves_own_automation_and_drops_new_upstream_workflows(self):
        (self.fork / ".github" / "workflow").write_text("fork automation\n")
        self.commit(self.fork, "fork automation")
        self.git(self.fork, "push", "origin", "main")
        (self.seed / ".github" / "workflow").write_text("upstream automation\n")
        (self.seed / ".github" / "new-workflow").write_text("upstream new\n")
        (self.seed / "source").write_text("upstream source\n")
        self.commit(self.seed, "upstream change")
        self.git(self.seed, "push", "upstream", "main")
        result = self.sync()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.fork / ".github" / "workflow").read_text(), "fork automation\n")
        self.assertFalse((self.fork / ".github" / "new-workflow").exists())
        self.assertEqual((self.fork / "source").read_text(), "upstream source\n")
        self.assertIn("changed=true", (self.root / "output").read_text())
        self.assertEqual(len(self.git(self.fork, "rev-list", "--parents", "-n", "1", "HEAD").split()), 3)

    def test_source_conflict_aborts_without_pushing(self):
        (self.fork / "source").write_text("fork source\n")
        self.commit(self.fork, "fork change")
        self.git(self.fork, "push", "origin", "main")
        before = self.git(self.fork, "rev-parse", "HEAD")
        (self.seed / "source").write_text("conflicting upstream\n")
        self.commit(self.seed, "upstream change")
        self.git(self.seed, "push", "upstream", "main")
        result = self.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git(self.fork, "rev-parse", "HEAD"), before)
        self.assertEqual(self.git(self.root / "origin.git", "rev-parse", "main"), before)
        self.assertEqual(self.git(self.fork, "status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
