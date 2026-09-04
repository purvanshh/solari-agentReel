"""Defaults and shared configuration for AgentReel."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_RETRIES = 20
DEFAULT_INTERVAL = 3.0
DEFAULT_OUTPUT_DIR = Path("reel")
DEFAULT_GIF_FPS = 10
DEFAULT_GIF_WIDTH = 800
DEFAULT_COMMIT_MESSAGE = "chore: update agent demo [agentreel]"

# Env vars used for subprocess ↔ CLI metadata handoff.
ENV_META_PATH = "AGENTREEL_META_PATH"
ENV_SCRIPT = "AGENTREEL_SCRIPT"

README_START_MARKER = "<!-- agentreel:start -->"
README_END_MARKER = "<!-- agentreel:end -->"


@dataclass
class RunConfig:
    script_path: Path
    name: str | None = None
    output_dir: Path = DEFAULT_OUTPUT_DIR
    retries: int = DEFAULT_RETRIES
    interval: float = DEFAULT_INTERVAL
    gif_fps: int = DEFAULT_GIF_FPS
    gif_width: int = DEFAULT_GIF_WIDTH
    no_git: bool = False
    no_readme: bool = False
    verbose: bool = False
    debug: bool = False
