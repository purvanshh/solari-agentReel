"""End-to-end pipeline for `agentreel run`."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import __version__, console as ui
from .config import RunConfig
from .conversion.converter import convert_recording
from .errors import GitError
from .executor import run_agent_script
from .publishing.git import commit_files, find_repo_root, inspect_status
from .publishing.readme import find_readme, update_readme
from .recording.poller import poll_and_download


def run_pipeline(config: RunConfig) -> Path:
    """Execute agent → poll → convert → publish. Returns the demo output directory."""
    demo_dir = _demo_dir(config)
    demo_dir.mkdir(parents=True, exist_ok=True)

    ui.step("Running agent...")
    execution = run_agent_script(config.script_path)
    assert execution.meta is not None
    session_id = execution.meta.session_id
    ui.ok("Agent completed")
    if config.verbose:
        ui.info(f"  session: {session_id}")

    ui.step("Waiting for recording...")

    def _poll_progress(msg: str) -> None:
        if config.verbose:
            ui.info(f"  {msg}")

    poll = asyncio.run(
        poll_and_download(
            session_id,
            demo_dir,
            retries=config.retries,
            interval=config.interval,
            on_progress=_poll_progress,
        )
    )
    ui.ok("Recording available")

    ui.step("Downloading events...")
    ui.ok(
        f"events.json downloaded ({poll.event_count} events, {poll.byte_size} bytes)"
    )

    ui.step("Converting recording...")
    conversion = convert_recording(
        poll.events_path,
        demo_dir,
        gif_fps=config.gif_fps,
        gif_width=config.gif_width,
        on_progress=_poll_progress,
    )
    ui.ok("WebM generated")
    ui.ok("GIF generated")

    _write_meta(
        demo_dir,
        script=str(config.script_path),
        session_id=session_id,
        timestamp=execution.meta.timestamp
        or datetime.now(timezone.utc).isoformat(),
    )

    readme_path: Optional[Path] = None
    if not config.no_readme:
        ui.step("Updating README...")
        repo_root = find_repo_root(Path.cwd()) or Path.cwd()
        readme_path = find_readme(repo_root)
        if readme_path is None:
            ui.warn("No README.md found — skipping README update.")
        else:
            gif_rel = _repo_relative(repo_root, conversion.gif_path)
            changed = update_readme(readme_path, gif_rel)
            if changed:
                ui.ok("README updated")
            else:
                ui.ok("README already up to date")

    if not config.no_git:
        ui.step("Committing changes...")
        _publish_git(
            demo_dir=demo_dir,
            readme_path=readme_path if not config.no_readme else None,
            verbose=config.verbose,
        )
    elif config.verbose:
        ui.info("  --no-git: skipping commit")

    ui.info("")
    ui.ok("AgentReel complete.")
    ui.info(f"  Output: {demo_dir}")
    return demo_dir


def _demo_dir(config: RunConfig) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if config.name:
        base = _slug(config.name)
    else:
        base = _slug(config.script_path.stem)
    return config.output_dir / f"{base}-{stamp}"


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "demo"


def _write_meta(
    demo_dir: Path,
    *,
    script: str,
    session_id: str,
    timestamp: str,
) -> dict[str, Any]:
    meta = {
        "tool": "agentreel",
        "version": __version__,
        "script": script,
        "session_id": session_id,
        "recording_id": session_id,
        "timestamp": timestamp,
        "duration": None,
        "webm": "demo.webm",
        "gif": "demo.gif",
        "events": "events.json",
    }
    path = demo_dir / "agentreel-meta.json"
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _publish_git(
    *,
    demo_dir: Path,
    readme_path: Optional[Path],
    verbose: bool,
) -> None:
    repo_root = find_repo_root(Path.cwd())
    if repo_root is None:
        raise GitError(
            "Not inside a Git repository.",
            hint="Initialize a repo or pass --no-git.",
        )

    root = repo_root.resolve()
    owned: set[str] = set()
    for path in demo_dir.rglob("*"):
        if path.is_file():
            try:
                owned.add(str(path.resolve().relative_to(root)))
            except ValueError:
                pass
    if readme_path and readme_path.exists():
        try:
            owned.add(str(readme_path.resolve().relative_to(root)))
        except ValueError:
            pass

    status = inspect_status(repo_root)
    unrelated = [p for p in status.dirty_paths if p not in owned]
    if unrelated:
        ui.warn(
            "Repository has unrelated uncommitted changes. "
            "Only AgentReel files will be staged."
        )
        if verbose:
            for path in unrelated[:10]:
                ui.info(f"  dirty: {path}")

    files = [
        demo_dir / "events.json",
        demo_dir / "events.ndjson",
        demo_dir / "demo.webm",
        demo_dir / "demo.gif",
        demo_dir / "agentreel-meta.json",
    ]
    files = [f for f in files if f.exists()]
    if readme_path and readme_path.exists():
        files.append(readme_path)

    try:
        sha = commit_files(repo_root, files)
    except GitError as err:
        hint = (err.hint or "").rstrip()
        hint = (hint + "\n\n" if hint else "") + f"Generated files were kept at:\n{demo_dir}"
        raise GitError(str(err), hint=hint) from err
    ui.ok(f"Commit created ({sha[:8]})")
