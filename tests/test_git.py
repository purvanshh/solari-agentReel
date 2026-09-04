"""Unit tests for Git publishing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentreel.errors import GitError
from agentreel.publishing import git as git_mod


def test_commit_files_stages_only_expected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "demo.gif").write_bytes(b"gif")
    (repo / "demo.webm").write_bytes(b"webm")
    (repo / "other.py").write_text("x", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_run(exe, args, *, cwd, check=True):
        calls.append(args)
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "abc123deadbeef\n" if args[:2] == ["rev-parse", "HEAD"] else ""
        proc.stderr = ""
        return proc

    with patch.object(git_mod, "find_git", return_value="/usr/bin/git"):
        with patch.object(git_mod, "_run", side_effect=fake_run):
            sha = git_mod.commit_files(
                repo,
                [repo / "demo.gif", repo / "demo.webm"],
                message="chore: update agent demo [agentreel]",
            )

    assert sha == "abc123deadbeef"
    add_call = next(c for c in calls if c[0] == "add")
    assert add_call[0:2] == ["add", "--"]
    assert "demo.gif" in add_call
    assert "demo.webm" in add_call
    assert "other.py" not in add_call
    assert not any(c == ["add", "."] for c in calls)

    commit_call = next(c for c in calls if c[0] == "commit")
    assert commit_call == ["commit", "-m", "chore: update agent demo [agentreel]"]


def test_commit_rejects_missing_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with patch.object(git_mod, "find_git", return_value="/usr/bin/git"):
        with pytest.raises(GitError, match="missing"):
            git_mod.commit_files(repo, [repo / "nope.gif"])


def test_commit_requires_git() -> None:
    with patch.object(git_mod, "find_git", return_value=None):
        with pytest.raises(GitError, match="git not found"):
            git_mod.commit_files(Path("/tmp"), [Path("/tmp/x")])
