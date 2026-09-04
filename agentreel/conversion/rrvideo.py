"""rrvideo wrapper — events.json → WebM."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from ..errors import ConversionError, DependencyError

log = logging.getLogger("agentreel.rrvideo")


def find_rrvideo() -> str | None:
    return shutil.which("rrvideo")


def convert_with_rrvideo(events_path: Path, output_webm: Path) -> Path:
    """Run `rrvideo --input events.json --output demo.webm`."""
    exe = find_rrvideo()
    if not exe:
        raise DependencyError(
            "rrvideo not found",
            hint="Install rrvideo and ensure it is on PATH:\n\nnpm install -g rrvideo",
        )

    output_webm.parent.mkdir(parents=True, exist_ok=True)
    if output_webm.exists():
        output_webm.unlink()

    cmd = [exe, "--input", str(events_path), "--output", str(output_webm)]
    log.debug("running: %s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as err:
        raise ConversionError(f"Failed to execute rrvideo: {err}") from err

    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or "").strip()
        raise ConversionError(
            "rrvideo conversion failed.",
            hint=stderr or f"Exit code {proc.returncode}",
        )

    if not output_webm.exists() or output_webm.stat().st_size == 0:
        raise ConversionError(
            "rrvideo completed but produced no WebM output.",
            hint=(proc.stdout or proc.stderr or "").strip() or None,
        )
    return output_webm
