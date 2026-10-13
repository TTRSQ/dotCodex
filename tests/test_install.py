"""Exercise committed-template install/update/restore in isolated Git repositories."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import tomlkit

SOURCE = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dotcodex-test-", dir="/private/tmp" if Path("/private/tmp").exists() else None)
        self.base = Path(self.tmp.name).resolve()
        self.repo = self.base / "repo"
        self.repo.mkdir()
        for name in ("install.py", "AGENTS.md", "subagent-working-principles.md", "config.toml", "skills", "rules"):
            src = SOURCE / name
            if src.is_dir():
                shutil.copytree(src, self.repo / name)
            else:
                shutil.copy2(src, self.repo / name)
        self.codex = self.base / "config"
        self.skills = self.base / "agents/skills"
        self.codex.mkdir()
        self.env = dict(os.environ)
        self.env.pop("WORKTREE_BASE_DIR", None)
        self.git("init", "-b", "main")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "test")
        self.commit()
        self.git("update-ref", "refs/remotes/origin/main", "HEAD")
        self.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True).stdout

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-m", "template")

    def run_install(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(self.repo / "install.py"), "--codex-dir", str(self.codex), "--skills-dir", str(self.skills), *args], capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode, 0 if ok else 1, result.stdout + result.stderr)
        return result

    def settings(self):
        return tomlkit.parse((self.codex / "config.toml").read_text()).unwrap()

    def backups(self):
        return sorted((self.repo / "backups").glob("*/manifest.json"))

    def test_dry_run_committed_source_and_idempotence(self):
        (self.repo / "AGENTS.md").write_text("UNCOMMITTED")
        self.run_install("--dry-run")
        self.assertFalse((self.codex / "AGENTS.md").exists())
        self.assertFalse((self.repo / "backups").exists())
        self.run_install()
        self.assertNotIn("UNCOMMITTED", (self.codex / "AGENTS.md").read_text())
        self.assertTrue((self.skills / "self-review/SKILL.md").exists())
        self.assertTrue(Path(self.settings()["sandbox_workspace_write"]["writable_roots"][0]).is_absolute())
        self.run_install()
        self.assertEqual(len(self.backups()), 1)

    def test_personal_values_comments_and_secrets_remain(self):
        personal = '# personal comment\nmodel = "my-model" # chosen\napproval_policy = "never"\n[mcp_servers.personal]\ncommand = "custom"\nenv = { API_KEY = "private-value" }\n'
        (self.codex / "config.toml").write_text(personal)
        result = self.run_install()
        text = (self.codex / "config.toml").read_text()
        self.assertIn('# chosen', text)
        self.assertIn('# personal comment', text)
        self.assertEqual(self.settings()["model"], "my-model")
        self.assertEqual(self.settings()["approval_policy"], "never")
        self.assertNotIn("private-value", result.stdout + result.stderr)
        name = self.backups()[0].parent.name
        self.run_install("--restore", name)
        self.assertEqual((self.codex / "config.toml").read_text(), personal)
        self.assertFalse((self.skills / "self-review/SKILL.md").exists())

    def test_array_comments_survive_new_worktree_root(self):
        personal = '[sandbox_workspace_write]\nwritable_roots = [\n  "/personal", # keep my projects\n  # tail comment\n]\n'
        (self.codex / "config.toml").write_text(personal)
        self.run_install()
        result = (self.codex / "config.toml").read_text()
        self.assertIn('# keep my projects', result)
        self.assertIn('# tail comment', result)
        self.assertEqual(self.settings()["sandbox_workspace_write"]["writable_roots"][0], "/personal")
        self.run_install("--worktree-dir", str(self.base / "new"))
        result = (self.codex / "config.toml").read_text()
        self.assertIn('# keep my projects', result)
        self.assertIn('# tail comment', result)

    def test_ordered_template_arrays_preserve_duplicates(self):
        template = self.repo / "config.toml"
        template.write_text(template.read_text() + '\n[mcp_servers.example]\nargs = ["a", "a", "b"]\n')
        self.commit()
        self.run_install("--ref", "HEAD")
        self.assertEqual(self.settings()["mcp_servers"]["example"]["args"], ["a", "a", "b"])
        self.run_install("--ref", "HEAD")
        self.assertEqual(len(self.backups()), 1)

    def test_backup_directory_symlinks_are_rejected(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.repo / "backups").symlink_to(outside, target_is_directory=True)
        self.run_install(ok=False)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.codex / "AGENTS.md").exists())

    def test_update_preserves_edits_removals_and_personal_files(self):
        self.run_install()
        doc = tomlkit.parse((self.codex / "config.toml").read_text())
        doc["approval_policy"] = "never"
        del doc["features"]["multi_agent"]
        doc["sandbox_workspace_write"]["writable_roots"].append("/personal")
        (self.codex / "config.toml").write_text(tomlkit.dumps(doc))
        (self.codex / "rules/personal.rules").write_text("personal")
        (self.repo / "config.toml").write_text((self.repo / "config.toml").read_text().replace('network_access = false', 'network_access = true').replace('approval_policy = "on-request"', 'approval_policy = "untrusted"'))
        self.commit()
        self.run_install("--ref", "HEAD", "--worktree-dir", str(self.base / "new worktrees"))
        cfg = self.settings()
        self.assertEqual(cfg["approval_policy"], "never")
        self.assertNotIn("multi_agent", cfg["features"])
        self.assertTrue(cfg["sandbox_workspace_write"]["network_access"])
        self.assertEqual(cfg["sandbox_workspace_write"]["writable_roots"], ["/personal", str(self.base / "new worktrees")])
        self.assertEqual((self.codex / "rules/personal.rules").read_text(), "personal")

    def test_removed_template_files_preserve_modified_files(self):
        (self.repo / "rules/extra.rules").write_text("original")
        self.commit()
        self.run_install("--ref", "HEAD")
        (self.codex / "rules/extra.rules").write_text("personal")
        (self.repo / "rules/extra.rules").unlink()
        (self.repo / "rules/dotcodex.rules").unlink()
        self.commit()
        self.run_install("--ref", "HEAD")
        self.assertEqual((self.codex / "rules/extra.rules").read_text(), "personal")
        self.assertFalse((self.codex / "rules/dotcodex.rules").exists())

    def test_symlinks_and_path_traversal_are_rejected(self):
        outside = self.base / "outside"
        outside.write_text("keep")
        (self.codex / "AGENTS.md").symlink_to(outside)
        self.run_install(ok=False)
        self.assertEqual(outside.read_text(), "keep")
        (self.codex / "AGENTS.md").unlink()
        self.run_install()
        state_path = self.codex / ".dotcodex-state.json"
        state = json.loads(state_path.read_text())
        state["files"]["codex/../outside"] = "invalid"
        state_path.write_text(json.dumps(state))
        self.run_install(ok=False)
        self.assertEqual(outside.read_text(), "keep")

    def test_restore_can_be_undone_and_target_mismatch_rejected(self):
        self.run_install()
        original_backup = self.backups()[0].parent.name
        contents = (self.codex / "AGENTS.md").read_bytes()
        self.run_install("--restore", original_backup, "--dry-run")
        self.assertTrue((self.codex / "AGENTS.md").exists())
        self.run_install("--restore", original_backup)
        self.assertFalse((self.codex / "AGENTS.md").exists())
        restore_backup = next(p.parent.name for p in self.backups() if p.parent.name != original_backup)
        self.run_install("--restore", restore_backup)
        self.assertEqual((self.codex / "AGENTS.md").read_bytes(), contents)
        self.codex = self.base / "different"
        self.run_install("--restore", original_backup, ok=False)
        self.assertFalse(self.codex.exists())

    def test_invalid_toml_does_not_change_destination(self):
        (self.codex / "config.toml").write_text('broken = [')
        self.run_install(ok=False)
        self.assertFalse((self.codex / "AGENTS.md").exists())
        self.assertFalse((self.repo / "backups").exists())


if __name__ == "__main__":
    unittest.main()
