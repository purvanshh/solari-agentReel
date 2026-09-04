"""Unit tests for README patching."""

from __future__ import annotations

from pathlib import Path

from agentreel.publishing.readme import build_watch_section, update_readme


def test_section_absent_inserted(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# My Agent\n\nHello.\n", encoding="utf-8")
    changed = update_readme(readme, "reel/demo/demo.gif")
    assert changed is True
    text = readme.read_text(encoding="utf-8")
    assert "<!-- agentreel:start -->" in text
    assert "## Watch it work" in text
    assert "![Agent demo](reel/demo/demo.gif)" in text
    assert "<!-- agentreel:end -->" in text


def test_section_exists_gif_updated(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Title\n\n"
        + build_watch_section("reel/old/demo.gif")
        + "\n",
        encoding="utf-8",
    )
    changed = update_readme(readme, "reel/new/demo.gif")
    assert changed is True
    text = readme.read_text(encoding="utf-8")
    assert "reel/new/demo.gif" in text
    assert "reel/old/demo.gif" not in text
    assert text.count("<!-- agentreel:start -->") == 1


def test_multiple_executions_no_duplicates(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n", encoding="utf-8")
    update_readme(readme, "reel/a/demo.gif")
    update_readme(readme, "reel/b/demo.gif")
    update_readme(readme, "reel/c/demo.gif")
    text = readme.read_text(encoding="utf-8")
    assert text.count("## Watch it work") == 1
    assert text.count("<!-- agentreel:start -->") == 1
    assert "reel/c/demo.gif" in text


def test_idempotent_same_path(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n", encoding="utf-8")
    assert update_readme(readme, "reel/demo/demo.gif") is True
    assert update_readme(readme, "reel/demo/demo.gif") is False


def test_legacy_section_without_markers(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Title\n\n## Watch it work\n\n![old](old.gif)\n\n## Next\n\nMore.\n",
        encoding="utf-8",
    )
    update_readme(readme, "reel/x/demo.gif")
    text = readme.read_text(encoding="utf-8")
    assert text.count("## Watch it work") == 1
    assert "<!-- agentreel:start -->" in text
    assert "reel/x/demo.gif" in text
    assert "## Next" in text
