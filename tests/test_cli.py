"""CLI / pipeline integration tests with mocked subsystems."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from agentreel.cli import app
from agentreel.errors import AgentExecutionError, ConversionError, RecordingTimeoutError
from agentreel.executor import ExecutionResult
from agentreel.recording.poller import PollResult
from agentreel.session import SessionMeta

runner = CliRunner()


def _fake_execution(script: Path) -> ExecutionResult:
    return ExecutionResult(
        exit_code=0,
        stdout="",
        stderr="",
        meta=SessionMeta(session_id="sess-cli", script=str(script), timestamp="t"),
        meta_path=Path("/tmp/fake-meta.json"),
    )


def test_cli_successful_execution(tmp_path: Path) -> None:
    script = tmp_path / "agent.py"
    script.write_text("print('hi')\n", encoding="utf-8")
    out = tmp_path / "reel"

    poll = PollResult(
        events_path=out / "demo" / "events.json",
        ndjson_path=out / "demo" / "events.ndjson",
        session_id="sess-cli",
        event_count=2,
        byte_size=10,
    )

    conversion = MagicMock()
    conversion.webm_path = out / "demo" / "demo.webm"
    conversion.gif_path = out / "demo" / "demo.gif"
    conversion.used_fallback = False

    with patch("agentreel.pipeline.run_agent_script", return_value=_fake_execution(script)):
        with patch("agentreel.pipeline.poll_and_download", new=AsyncMock(return_value=poll)):
            with patch("agentreel.pipeline.convert_recording", return_value=conversion):
                with patch("agentreel.pipeline.find_repo_root", return_value=tmp_path):
                    with patch("agentreel.pipeline.find_readme", return_value=None):
                        with patch("agentreel.pipeline._publish_git"):
                            result = runner.invoke(
                                app,
                                [
                                    "run",
                                    str(script),
                                    "--name",
                                    "demo",
                                    "--output",
                                    str(out),
                                    "--no-readme",
                                    "--no-git",
                                ],
                            )

    assert result.exit_code == 0, result.output
    assert "AgentReel complete" in result.output


def test_cli_agent_failure(tmp_path: Path) -> None:
    script = tmp_path / "bad.py"
    script.write_text("raise SystemExit(1)\n", encoding="utf-8")

    with patch(
        "agentreel.pipeline.run_agent_script",
        side_effect=AgentExecutionError(
            "Agent failed.", exit_code=1, stderr="boom", hint="Exit code: 1\n\nboom"
        ),
    ):
        result = runner.invoke(app, ["run", str(script), "--no-git", "--no-readme"])

    assert result.exit_code == 1
    assert "Agent failed" in result.output


def test_cli_poll_failure(tmp_path: Path) -> None:
    script = tmp_path / "agent.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    with patch("agentreel.pipeline.run_agent_script", return_value=_fake_execution(script)):
        with patch(
            "agentreel.pipeline.poll_and_download",
            new=AsyncMock(
                side_effect=RecordingTimeoutError(
                    "Recording was not available after 20 attempts.",
                    session_id="sess-cli",
                    attempts=20,
                    hint="retry",
                )
            ),
        ):
            result = runner.invoke(
                app, ["run", str(script), "--no-git", "--no-readme", "--output", str(tmp_path / "reel")]
            )

    assert result.exit_code == 1
    assert "Recording was not available" in result.output


def test_cli_conversion_failure(tmp_path: Path) -> None:
    script = tmp_path / "agent.py"
    script.write_text("print('ok')\n", encoding="utf-8")
    out = tmp_path / "reel"
    poll = PollResult(
        events_path=out / "x" / "events.json",
        ndjson_path=out / "x" / "events.ndjson",
        session_id="sess-cli",
        event_count=1,
        byte_size=5,
    )

    with patch("agentreel.pipeline.run_agent_script", return_value=_fake_execution(script)):
        with patch("agentreel.pipeline.poll_and_download", new=AsyncMock(return_value=poll)):
            with patch(
                "agentreel.pipeline.convert_recording",
                side_effect=ConversionError("Could not convert", hint="install rrvideo"),
            ):
                result = runner.invoke(
                    app,
                    ["run", str(script), "--name", "x", "--output", str(out), "--no-git", "--no-readme"],
                )

    assert result.exit_code == 1
    assert "Could not convert" in result.output


def test_cli_doctor() -> None:
    result = runner.invoke(app, ["doctor"])
    # May be 0 or 1 depending on environment; just ensure it runs.
    assert "AgentReel Environment" in result.output
    assert "Python" in result.output


def test_cli_no_git_skips_commit(tmp_path: Path) -> None:
    script = tmp_path / "agent.py"
    script.write_text("print('hi')\n", encoding="utf-8")
    out = tmp_path / "reel"
    poll = PollResult(
        events_path=out / "demo" / "events.json",
        ndjson_path=out / "demo" / "events.ndjson",
        session_id="sess-cli",
        event_count=1,
        byte_size=3,
    )
    conversion = MagicMock(
        webm_path=out / "demo" / "demo.webm",
        gif_path=out / "demo" / "demo.gif",
        used_fallback=False,
    )

    with patch("agentreel.pipeline.run_agent_script", return_value=_fake_execution(script)):
        with patch("agentreel.pipeline.poll_and_download", new=AsyncMock(return_value=poll)):
            with patch("agentreel.pipeline.convert_recording", return_value=conversion):
                with patch("agentreel.pipeline._publish_git") as publish:
                    result = runner.invoke(
                        app,
                        [
                            "run",
                            str(script),
                            "--name",
                            "demo",
                            "--output",
                            str(out),
                            "--no-git",
                            "--no-readme",
                        ],
                    )

    assert result.exit_code == 0
    publish.assert_not_called()
