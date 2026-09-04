"""Environment diagnostics — `agentreel doctor`."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from dataclasses import dataclass

from . import console as ui
from .conversion.ffmpeg import find_ffmpeg
from .conversion.rrvideo import find_rrvideo
from .publishing.git import find_git


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


def run_doctor() -> int:
    ui.info("AgentReel Environment\n")
    checks = collect_checks()
    for check in checks:
        if check.ok:
            ui.ok(check.name + (f" ({check.detail})" if check.detail else ""))
        else:
            ui.fail(check.name + (f" — {check.detail}" if check.detail else ""))

    ui.info("")
    if all(c.ok for c in checks):
        ui.info("Environment ready.")
        return 0

    ui.info("Some dependencies are missing. Fix the items above and re-run.")
    return 1


def collect_checks() -> list[Check]:
    return [
        _check_python(),
        _check_solari(),
        _check_rrvideo(),
        _check_ffmpeg(),
        _check_git(),
        _check_node(),
    ]


def _check_python() -> Check:
    return Check("Python", True, f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def _check_solari() -> Check:
    if importlib.util.find_spec("solari_browser") is None:
        return Check(
            "Solari SDK",
            False,
            "not installed — pip install solari-browser",
        )
    try:
        import solari_browser

        ver = getattr(solari_browser, "__version__", "unknown")
        return Check("Solari SDK", True, ver)
    except Exception as err:  # noqa: BLE001
        return Check("Solari SDK", False, str(err))


def _check_rrvideo() -> Check:
    path = find_rrvideo()
    if path:
        return Check("rrvideo", True, path)
    return Check("rrvideo", False, "not found — npm install -g rrvideo")


def _check_ffmpeg() -> Check:
    path = find_ffmpeg()
    if path:
        return Check("ffmpeg", True, path)
    return Check("ffmpeg", False, "not found — install ffmpeg and add it to PATH")


def _check_git() -> Check:
    path = find_git()
    if path:
        return Check("git", True, path)
    return Check("git", False, "not found — install Git")


def _check_node() -> Check:
    path = shutil.which("node")
    if path:
        return Check("Node.js", True, path)
    return Check("Node.js", False, "not found — required to run rrvideo")
