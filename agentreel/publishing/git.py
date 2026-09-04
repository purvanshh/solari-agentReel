"""Safe Git publishing — only stage AgentReel-owned files."""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ..config import DEFAULT_COMMIT_MESSAGE
from ..errors import GitError

log = logging.getLogger("agentreel.git")


@dataclass
class GitStatus:
    repo_root: Path
    dirty: bool
    dirty_paths: list[str]


def find_git() -> str | None:
    return shutil.which("git")


def find_repo_root(start: Path | None = None) -> Path | None:
    exe = find_git()
    if not exe:
        return None
    cwd = start or Path.cwd()
    try:
        proc = subprocess.run(
            [exe, "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


def inspect_status(repo_root: Path) -> GitStatus:
    exe = _require_git()
    proc = _run(exe, ["status", "--porcelain"], cwd=repo_root)
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    paths = []
    for line in lines:
        # format: XY PATH or XY ORIG -> PATH
        entry = line[3:] if len(line) > 3 else line
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        paths.append(entry.strip())
    return GitStatus(repo_root=repo_root, dirty=bool(lines), dirty_paths=paths)


def commit_files(
    repo_root: Path,
    files: Sequence[Path],
    *,
    message: str = DEFAULT_COMMIT_MESSAGE,
) -> str:
    """Stage only the given files and create a commit. Returns the commit SHA."""
    exe = _require_git()
    if not files:
        raise GitError("No files to commit.")

    rel_files: list[str] = []
    for path in files:
        resolved = path.resolve()
        try:
            rel = resolved.relative_to(repo_root.resolve())
        except ValueError as err:
            raise GitError(f"File is outside the repository: {path}") from err
        if not resolved.exists():
            raise GitError(f"Cannot stage missing file: {path}")
        rel_files.append(str(rel))

    # Never `git add .` — only explicit paths.
    _run(exe, ["add", "--"] + rel_files, cwd=repo_root)
    proc = _run(
        exe,
        ["commit", "-m", message],
        cwd=repo_root,
        check=False,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or "").strip()
        raise GitError(
            "git commit failed.",
            hint=stderr or "Check that user.name / user.email are configured.",
        )

    sha_proc = _run(exe, ["rev-parse", "HEAD"], cwd=repo_root)
    return sha_proc.stdout.strip()


def _require_git() -> str:
    exe = find_git()
    if not exe:
        raise GitError(
            "git not found",
            hint="Install Git and ensure it is available on PATH.",
        )
    return exe


def _run(
    exe: str,
    args: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    cmd = [exe, *args]
    log.debug("running: %s (cwd=%s)", " ".join(cmd), cwd)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as err:
        raise GitError(f"Failed to execute git: {err}") from err
    if check and proc.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed.",
            hint=(proc.stderr or proc.stdout or "").strip() or None,
        )
    return proc
