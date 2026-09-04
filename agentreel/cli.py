"""AgentReel CLI — `agentreel run` and `agentreel doctor`."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from . import __version__, console as ui
from .config import (
    DEFAULT_GIF_FPS,
    DEFAULT_GIF_WIDTH,
    DEFAULT_INTERVAL,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RETRIES,
    RunConfig,
)
from .console import setup_logging
from .doctor import run_doctor
from .errors import AgentExecutionError, AgentReelError
from .pipeline import run_pipeline

app = typer.Typer(
    name="agentreel",
    help="Turn Solari browser-agent runs into shareable WebM demos and README GIFs.",
    add_completion=False,
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        ui.info(f"agentreel {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """AgentReel — zero-config visual demos for Solari browser agents."""


@app.command("run")
def run_cmd(
    script_path: Path = typer.Argument(..., exists=True, readable=True, help="Agent Python script"),
    name: Optional[str] = typer.Option(None, "--name", help="Demo name (used in output folder)"),
    output: Path = typer.Option(DEFAULT_OUTPUT_DIR, "--output", help="Output directory"),
    retries: int = typer.Option(DEFAULT_RETRIES, "--retries", help="Recording poll attempts"),
    interval: float = typer.Option(DEFAULT_INTERVAL, "--interval", help="Seconds between polls"),
    gif_fps: int = typer.Option(DEFAULT_GIF_FPS, "--gif-fps", help="GIF frames per second"),
    gif_width: int = typer.Option(DEFAULT_GIF_WIDTH, "--gif-width", help="GIF width in pixels"),
    no_git: bool = typer.Option(False, "--no-git", help="Skip git commit"),
    no_readme: bool = typer.Option(False, "--no-readme", help="Skip README update"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Detailed logs"),
    debug: bool = typer.Option(False, "--debug", help="Show full tracebacks"),
) -> None:
    """Run an agent script, capture the Solari replay, and publish a demo."""
    setup_logging(verbose or debug)
    config = RunConfig(
        script_path=script_path,
        name=name,
        output_dir=output,
        retries=retries,
        interval=interval,
        gif_fps=gif_fps,
        gif_width=gif_width,
        no_git=no_git,
        no_readme=no_readme,
        verbose=verbose,
        debug=debug,
    )
    try:
        run_pipeline(config)
    except AgentExecutionError as err:
        ui.fail(str(err))
        if err.hint:
            ui.info("")
            ui.info(err.hint)
        raise typer.Exit(code=err.exit_code or 1) from err
    except AgentReelError as err:
        ui.fail(str(err))
        if err.hint:
            ui.info("")
            ui.info(err.hint)
        if debug:
            raise
        raise typer.Exit(code=1) from err
    except Exception:
        if debug:
            raise
        ui.fail("Unexpected error. Re-run with --debug for a traceback.")
        raise typer.Exit(code=1)


@app.command("doctor")
def doctor_cmd() -> None:
    """Check that AgentReel dependencies are installed."""
    code = run_doctor()
    raise typer.Exit(code=code)


@app.command("convert")
def convert_cmd(
    events: Path = typer.Argument(..., exists=True, readable=True, help="Path to events.json"),
    output: Path = typer.Option(Path("."), "--output", "-o", help="Output directory"),
    gif_fps: int = typer.Option(DEFAULT_GIF_FPS, "--gif-fps"),
    gif_width: int = typer.Option(DEFAULT_GIF_WIDTH, "--gif-width"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Convert a local events.json to WebM + GIF (no Solari / git)."""
    setup_logging(verbose)
    from .conversion.converter import convert_recording

    output.mkdir(parents=True, exist_ok=True)
    ui.step("Converting recording...")
    try:
        result = convert_recording(
            events,
            output,
            gif_fps=gif_fps,
            gif_width=gif_width,
            on_progress=lambda msg: ui.info(f"  {msg}") if verbose else None,
        )
    except AgentReelError as err:
        ui.fail(str(err))
        if err.hint:
            ui.info("")
            ui.info(err.hint)
        raise typer.Exit(code=1) from err
    ui.ok(f"WebM: {result.webm_path}")
    ui.ok(f"GIF:  {result.gif_path}")


if __name__ == "__main__":
    app()
