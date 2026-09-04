"""Unit tests for the recording poller."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentreel.errors import RecordingNotFoundError, RecordingTimeoutError
from agentreel.recording.poller import poll_and_download
from agentreel.solari.adapter import ReplayResult, ReplayStatus


@pytest.mark.asyncio
async def test_poll_pending_then_ready(tmp_path: Path) -> None:
    events = [{"type": 4, "timestamp": 1}, {"type": 2, "timestamp": 2}]
    ndjson = ("\n".join(json.dumps(e) for e in events) + "\n").encode()

    results = [
        ReplayResult(status=ReplayStatus.PENDING, http_status=404),
        ReplayResult(status=ReplayStatus.PENDING, http_status=404),
        ReplayResult(status=ReplayStatus.READY, data=ndjson, http_status=200),
    ]

    client = MagicMock()
    with patch(
        "agentreel.recording.poller.download_replay_once",
        new=AsyncMock(side_effect=results),
    ):
        with patch("agentreel.recording.poller.asyncio.sleep", new=AsyncMock()):
            result = await poll_and_download(
                "sess-1",
                tmp_path,
                client=client,
                retries=5,
                interval=0.01,
            )

    assert result.session_id == "sess-1"
    assert result.event_count == 2
    assert result.events_path.exists()
    loaded = json.loads(result.events_path.read_text())
    assert loaded == events
    client.close.assert_not_called()  # we passed client; poller must not close it


@pytest.mark.asyncio
async def test_poll_timeout(tmp_path: Path) -> None:
    with patch(
        "agentreel.recording.poller.download_replay_once",
        new=AsyncMock(
            return_value=ReplayResult(status=ReplayStatus.PENDING, http_status=404)
        ),
    ):
        with patch("agentreel.recording.poller.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(RecordingTimeoutError) as exc:
                await poll_and_download(
                    "sess-timeout",
                    tmp_path,
                    client=MagicMock(),
                    retries=3,
                    interval=0.01,
                )
    assert exc.value.session_id == "sess-timeout"
    assert exc.value.attempts == 3


@pytest.mark.asyncio
async def test_poll_auth_failure(tmp_path: Path) -> None:
    with patch(
        "agentreel.recording.poller.download_replay_once",
        new=AsyncMock(
            return_value=ReplayResult(
                status=ReplayStatus.AUTH_ERROR, http_status=401, message="nope"
            )
        ),
    ):
        with pytest.raises(RecordingNotFoundError):
            await poll_and_download(
                "sess-auth",
                tmp_path,
                client=MagicMock(),
                retries=5,
                interval=0.01,
            )


@pytest.mark.asyncio
async def test_poll_server_error_then_ready(tmp_path: Path) -> None:
    ndjson = b'{"type":4,"timestamp":1}\n'
    results = [
        ReplayResult(status=ReplayStatus.SERVER_ERROR, http_status=503),
        ReplayResult(status=ReplayStatus.READY, data=ndjson, http_status=200),
    ]
    with patch(
        "agentreel.recording.poller.download_replay_once",
        new=AsyncMock(side_effect=results),
    ):
        with patch("agentreel.recording.poller.asyncio.sleep", new=AsyncMock()):
            result = await poll_and_download(
                "sess-5xx",
                tmp_path,
                client=MagicMock(),
                retries=5,
                interval=0.01,
            )
    assert result.event_count == 1
