"""Isolated regression checks for the repository's commit-hook configuration.

Run explicitly with unittest; these checks never run against the working tree.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class CommitHookConfigurationTests(unittest.TestCase):
    """Exercise real pre-commit selection without changing project source."""

    def setUp(self):
        self.pre_commit = shutil.which("pre-commit")
        self.git = Path.home() / ".local/bin/harness-git"
        if not self.pre_commit or not self.git.is_file():
            self.skipTest("pre-commit and the configured harness-git are required")
        temporary = tempfile.TemporaryDirectory(prefix="commit-hook-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.environment = os.environ.copy()
        # Git invokes hooks with repository-specific variables. Do not let
        # those redirect this disposable fixture into the caller's repository.
        for name in (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
            "GIT_COMMON_DIR",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        ):
            self.environment.pop(name, None)
        self.run_command(str(self.git), "init", "--quiet")
        configuration = Path(__file__).resolve().parents[1] / ".pre-commit-config.yaml"
        shutil.copyfile(configuration, self.root / ".pre-commit-config.yaml")

    def run_command(self, *arguments):
        result = subprocess.run(
            arguments,
            cwd=self.root,
            env=self.environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert result.returncode == 0, result.stdout
        return result.stdout

    def test_readme_only_installed_hook_leaves_python_untouched(self):
        readme = self.root / "README.md"
        readme.write_text("# Fixture\n", encoding="utf-8")
        unrelated = self.root / "unrelated.py"
        original = "deliberately invalid python   "
        unrelated.write_text(original, encoding="utf-8")
        self.run_command(str(self.git), "add", "--", "README.md")
        self.run_command(self.pre_commit, "install", "--overwrite")
        hook = self.root / ".git/hooks/pre-commit"
        output = self.run_command(str(hook))
        assert "Skipped" in output
        assert unrelated.read_text(encoding="utf-8") == original
        staged = self.run_command(str(self.git), "diff", "--cached", "--name-only")
        assert staged.strip() == "README.md"

    def test_mypy_checks_both_server_paths_without_duplicate_module(self):
        package = self.root / "lab_testing"
        (package / "server").mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "server.py").write_text("VALUE: int = 1\n", encoding="utf-8")
        (package / "server/__init__.py").write_text("VALUE: int = 2\n", encoding="utf-8")
        output = self.run_command(
            self.pre_commit,
            "run",
            "mypy",
            "--files",
            "lab_testing/server.py",
            "lab_testing/server/__init__.py",
        )
        assert "mypy (package and tests)" in output
        assert "mypy (legacy server entrypoint)" in output
        assert output.count("Passed") == 2, output

    def test_vendored_python_is_excluded_without_rewriting(self):
        vendor = self.root / "node_modules/vendor.py"
        vendor.parent.mkdir()
        original = "deliberately invalid python   "
        vendor.write_text(original, encoding="utf-8")
        output = self.run_command(self.pre_commit, "run", "--files", "node_modules/vendor.py")
        assert "Passed" not in output
        assert "Failed" not in output
        assert vendor.read_text(encoding="utf-8") == original


if __name__ == "__main__":
    unittest.main()
