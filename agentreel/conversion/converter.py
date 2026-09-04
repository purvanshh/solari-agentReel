"""Orchestrate events.json → WebM → GIF."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from ..config import DEFAULT_GIF_FPS, DEFAULT_GIF_WIDTH
from ..errors import ConversionError, DependencyError
from . import ffmpeg as ffmpeg_mod
from . import rrvideo as rrvideo_mod
from .fallback import convert_with_fallback

log = logging.getLogger("agentreel.converter")

ProgressCallback = Callable[[str], None]


@dataclass
class ConversionResult:
    webm_path: Path
    gif_path: Path
    used_fallback: bool = False


def convert_recording(
    events_path: Path,
    output_dir: Path,
    *,
    gif_fps: int = DEFAULT_GIF_FPS,
    gif_width: int = DEFAULT_GIF_WIDTH,
    on_progress: Optional[ProgressCallback] = None,
) -> ConversionResult:
    """Convert rrweb events to WebM and GIF."""
    notify = on_progress or (lambda _m: None)
    webm_path = output_dir / "demo.webm"
    gif_path = output_dir / "demo.gif"
    used_fallback = False

    try:
        notify("Running rrvideo...")
        rrvideo_mod.convert_with_rrvideo(events_path, webm_path)
        notify("WebM generated")
    except DependencyError:
        raise
    except ConversionError as primary_err:
        log.warning("rrvideo failed, trying fallback: %s", primary_err)
        notify("rrvideo failed — trying fallback...")
        try:
            convert_with_fallback(events_path, webm_path)
            used_fallback = True
            notify("WebM generated (fallback)")
        except (ConversionError, DependencyError) as fallback_err:
            raise ConversionError(
                "Could not convert recording to WebM.",
                hint=(
                    f"Primary: {primary_err}\n"
                    f"Fallback: {fallback_err}\n\n"
                    "Make sure rrvideo is installed:\n\n"
                    "npm install -g rrvideo"
                ),
            ) from fallback_err

    notify("Running ffmpeg...")
    ffmpeg_mod.convert_webm_to_gif(
        webm_path, gif_path, fps=gif_fps, width=gif_width
    )
    notify("GIF generated")
    return ConversionResult(
        webm_path=webm_path, gif_path=gif_path, used_fallback=used_fallback
    )
