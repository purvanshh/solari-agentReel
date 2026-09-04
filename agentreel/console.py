"""CLI output helpers — concise by default, verbose on request."""

from __future__ import annotations

import logging
import sys

from rich.console import Console

console = Console(stderr=False)
err_console = Console(stderr=True)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )


def step(message: str) -> None:
    console.print(f"[bold]▶[/bold] {message}")


def ok(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")


def fail(message: str) -> None:
    err_console.print(f"[red]✗[/red] {message}")


def info(message: str) -> None:
    console.print(message)


def warn(message: str) -> None:
    console.print(f"[yellow]![/yellow] {message}")
