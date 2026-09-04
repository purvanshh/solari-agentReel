"""ffmpeg wrapper — WebM → GIF."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from ..config import DEFAULT_GIF_FPS, DEFAULT_GIF_WIDTH
from ..errors import ConversionError, DependencyError

log = logging.getLogger("agentreel.ffmpeg")


def find_ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def convert_webm_to_gif(
    webm_path: Path,
    gif_path: Path,
    *,
    fps: int = DEFAULT_GIF_FPS,
    width: int = DEFAULT_GIF_WIDTH,
) -> Path:
    """Convert WebM to GIF via ffmpeg."""
    exe = find_ffmpeg()
    if not exe:
        raise DependencyError(
            "ffmpeg not found",
            hint="Install ffmpeg and ensure it is available on PATH.",
        )

    gif_path.parent.mkdir(parents=True, exist_ok=True)
    if gif_path.exists():
        gif_path.unlink()

    vf = f"fps={fps},scale={width}:-1:flags=lanczos"
    cmd = [
        exe,
        "-y",
        "-i",
        str(webm_path),
        "-vf",
        vf,
        str(gif_path),
    ]
    log.debug("running: %s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as err:
        raise ConversionError(f"Failed to execute ffmpeg: {err}") from err

    if proc.returncode != 0:
        stderr = (proc.stderr or proc.stdout or "").strip()
        # Keep the hint short — ffmpeg stderr is very noisy.
        tail = "\n".join(stderr.splitlines()[-8:]) if stderr else f"Exit code {proc.returncode}"
        raise ConversionError("ffmpeg GIF conversion failed.", hint=tail)

    if not gif_path.exists() or gif_path.stat().st_size == 0:
        raise ConversionError("ffmpeg completed but produced an empty GIF.")
    return gif_path
