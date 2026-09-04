"""Unit tests for conversion helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentreel.conversion import ffmpeg as ffmpeg_mod
from agentreel.conversion import rrvideo as rrvideo_mod
from agentreel.conversion.converter import convert_recording
from agentreel.errors import ConversionError, DependencyError


def test_rrvideo_success(tmp_path: Path) -> None:
    events = tmp_path / "events.json"
    events.write_text("[]", encoding="utf-8")
    out = tmp_path / "demo.webm"

    def fake_run(cmd, **kwargs):
        Path(cmd[cmd.index("--output") + 1]).write_bytes(b"webm-bytes")
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "ok"
        proc.stderr = ""
        return proc

    with patch.object(rrvideo_mod, "find_rrvideo", return_value="/usr/bin/rrvideo"):
        with patch("agentreel.conversion.rrvideo.subprocess.run", side_effect=fake_run):
            path = rrvideo_mod.convert_with_rrvideo(events, out)
    assert path == out
    assert out.read_bytes() == b"webm-bytes"


def test_rrvideo_missing_executable(tmp_path: Path) -> None:
    with patch.object(rrvideo_mod, "find_rrvideo", return_value=None):
        with pytest.raises(DependencyError, match="rrvideo"):
            rrvideo_mod.convert_with_rrvideo(tmp_path / "e.json", tmp_path / "o.webm")


def test_rrvideo_nonzero_exit(tmp_path: Path) -> None:
    events = tmp_path / "events.json"
    events.write_text("[]", encoding="utf-8")
    proc = MagicMock(returncode=1, stdout="", stderr="boom")
    with patch.object(rrvideo_mod, "find_rrvideo", return_value="/usr/bin/rrvideo"):
        with patch("agentreel.conversion.rrvideo.subprocess.run", return_value=proc):
            with pytest.raises(ConversionError, match="rrvideo"):
                rrvideo_mod.convert_with_rrvideo(events, tmp_path / "o.webm")


def test_rrvideo_missing_output(tmp_path: Path) -> None:
    events = tmp_path / "events.json"
    events.write_text("[]", encoding="utf-8")
    proc = MagicMock(returncode=0, stdout="", stderr="")
    with patch.object(rrvideo_mod, "find_rrvideo", return_value="/usr/bin/rrvideo"):
        with patch("agentreel.conversion.rrvideo.subprocess.run", return_value=proc):
            with pytest.raises(ConversionError, match="no WebM"):
                rrvideo_mod.convert_with_rrvideo(events, tmp_path / "o.webm")


def test_ffmpeg_success(tmp_path: Path) -> None:
    webm = tmp_path / "demo.webm"
    webm.write_bytes(b"webm")
    gif = tmp_path / "demo.gif"

    def fake_run(cmd, **kwargs):
        Path(cmd[-1]).write_bytes(b"GIF89a")
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch.object(ffmpeg_mod, "find_ffmpeg", return_value="/usr/bin/ffmpeg"):
        with patch("agentreel.conversion.ffmpeg.subprocess.run", side_effect=fake_run):
            path = ffmpeg_mod.convert_webm_to_gif(webm, gif)
    assert path.exists()


def test_convert_recording_uses_fallback(tmp_path: Path) -> None:
    events = tmp_path / "events.json"
    events.write_text('[{"type":4,"timestamp":1}]', encoding="utf-8")

    def fail_rrvideo(*_a, **_k):
        raise ConversionError("primary failed")

    def ok_rrvideo(events_path, output_webm):
        output_webm.write_bytes(b"webm")
        return output_webm

    def ok_ffmpeg(webm, gif, **kwargs):
        gif.write_bytes(b"GIF")
        return gif

    with patch("agentreel.conversion.converter.rrvideo_mod.convert_with_rrvideo", side_effect=fail_rrvideo):
        with patch("agentreel.conversion.converter.convert_with_fallback", side_effect=ok_rrvideo):
            with patch("agentreel.conversion.converter.ffmpeg_mod.convert_webm_to_gif", side_effect=ok_ffmpeg):
                result = convert_recording(events, tmp_path)
    assert result.used_fallback is True
    assert result.gif_path.exists()
