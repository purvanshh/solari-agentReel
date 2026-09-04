"""Idempotent README.md 'Watch it work' section updates."""

from __future__ import annotations

import re
from pathlib import Path

from ..config import README_END_MARKER, README_START_MARKER
from ..errors import ReadmeUpdateError

_SECTION_RE = re.compile(
    re.escape(README_START_MARKER) + r".*?" + re.escape(README_END_MARKER),
    re.DOTALL,
)


def find_readme(repo_root: Path) -> Path | None:
    for name in ("README.md", "readme.md", "Readme.md"):
        candidate = repo_root / name
        if candidate.is_file():
            return candidate
    return None


def build_watch_section(gif_rel_path: str) -> str:
    return (
        f"{README_START_MARKER}\n"
        f"## Watch it work\n"
        f"\n"
        f"![Agent demo]({gif_rel_path})\n"
        f"{README_END_MARKER}"
    )


def update_readme(readme_path: Path, gif_rel_path: str) -> bool:
    """Insert or update the AgentReel section. Returns True if content changed."""
    try:
        original = readme_path.read_text(encoding="utf-8")
    except OSError as err:
        raise ReadmeUpdateError(f"Could not read {readme_path}: {err}") from err

    section = build_watch_section(gif_rel_path)

    if README_START_MARKER in original and README_END_MARKER in original:
        updated = _SECTION_RE.sub(section, original, count=1)
    elif re.search(r"^## Watch it work\s*$", original, re.MULTILINE):
        # Legacy section without markers — wrap/replace from heading to next ## or EOF.
        updated = _replace_legacy_section(original, section)
    else:
        sep = "" if original.endswith("\n") or not original else "\n"
        updated = original + sep + "\n" + section + "\n"

    if updated == original:
        return False

    try:
        readme_path.write_text(updated, encoding="utf-8")
    except OSError as err:
        raise ReadmeUpdateError(f"Could not write {readme_path}: {err}") from err
    return True


def _replace_legacy_section(text: str, new_section: str) -> str:
    pattern = re.compile(
        r"^## Watch it work\s*\n(?:.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return text.rstrip() + "\n\n" + new_section + "\n"
    return text[: match.start()] + new_section + "\n" + text[match.end() :]
