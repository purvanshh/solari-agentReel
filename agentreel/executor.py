"""Run the user agent script in a subprocess."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from .config import ENV_META_PATH, ENV_SCRIPT
from .errors import AgentExecutionError
from .session import SessionMeta, load_session_meta

log = logging.getLogger("agentreel.executor")


@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    meta: Optional[SessionMeta]
    meta_path: Path


def run_agent_script(
    script_path: Path,
    *,
    python_executable: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    cwd: Optional[Path] = None,
) -> ExecutionResult:
    """Execute ``python script_path`` in a subprocess; capture session metadata."""
    script_path = script_path.resolve()
    if not script_path.is_file():
        raise AgentExecutionError(
            f"Script not found: {script_path}",
            exit_code=1,
        )

    python = python_executable or sys.executable
    work_cwd = cwd or Path.cwd()

    with tempfile.TemporaryDirectory(prefix="agentreel-") as tmp:
        meta_path = Path(tmp) / "session.json"
        child_env = dict(os.environ)
        if env:
            child_env.update(env)
        child_env[ENV_META_PATH] = str(meta_path)
        child_env[ENV_SCRIPT] = str(script_path)

        cmd = [python, str(script_path)]
        log.debug("running agent: %s", " ".join(cmd))
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(work_cwd),
                env=child_env,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as err:
            raise AgentExecutionError(
                f"Failed to execute agent script: {err}",
                exit_code=1,
            ) from err

        meta: Optional[SessionMeta] = None
        # Copy meta out of the temp dir before it disappears.
        persisted = Path(tempfile.gettempdir()) / f"agentreel-session-{os.getpid()}.json"
        if meta_path.exists():
            persisted.write_bytes(meta_path.read_bytes())
            try:
                meta = load_session_meta(persisted)
            except (OSError, KeyError, ValueError) as err:
                log.warning("Could not parse session metadata: %s", err)
                meta = None

        result = ExecutionResult(
            exit_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            meta=meta,
            meta_path=persisted if meta else meta_path,
        )

    if result.exit_code != 0:
        raise AgentExecutionError(
            "Agent failed.",
            exit_code=result.exit_code,
            stderr=result.stderr,
            hint=_format_agent_failure(result),
        )

    if result.meta is None:
        raise AgentExecutionError(
            "Agent completed but did not report a recorded session.",
            exit_code=0,
            stderr=result.stderr,
            hint=(
                "Your script must use AgentReel's context manager:\n\n"
                "  from agentreel import recorded_session\n\n"
                "  async with recorded_session() as browser:\n"
                "      ...\n\n"
                "Recording is opt-in per session — without recorded_session()/"
                "recording=True there is nothing to download."
            ),
        )

    return result


def _format_agent_failure(result: ExecutionResult) -> str:
    parts = [f"Exit code: {result.exit_code}"]
    err = (result.stderr or "").strip()
    out = (result.stdout or "").strip()
    if err:
        # Truncate — never dump huge logs / potential secrets sprawl.
        lines = err.splitlines()
        tail = "\n".join(lines[-40:])
        parts.append("")
        parts.append(tail)
    elif out:
        lines = out.splitlines()
        parts.append("")
        parts.append("\n".join(lines[-20:]))
    return "\n".join(parts)
