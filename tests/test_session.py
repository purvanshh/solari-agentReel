"""Unit tests for recorded_session and adapter helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentreel.session import load_session_meta, recorded_session
from agentreel.solari.adapter import ReplayStatus, download_replay_once, ndjson_to_events_array


def test_ndjson_to_events_array() -> None:
    blob = b'{"type":4,"data":{}}\n{"type":2,"data":{}}\n'
    events = ndjson_to_events_array(blob)
    assert len(events) == 2
    assert events[0]["type"] == 4


@pytest.mark.asyncio
async def test_download_replay_classifies_404() -> None:
    from solari_browser.errors import SolariError

    client = MagicMock()
    client.sessions.download_replay = AsyncMock(
        side_effect=SolariError("missing", 404)
    )
    result = await download_replay_once(client, "abc")
    assert result.status == ReplayStatus.PENDING


@pytest.mark.asyncio
async def test_download_replay_classifies_auth() -> None:
    from solari_browser.errors import SolariError

    client = MagicMock()
    client.sessions.download_replay = AsyncMock(
        side_effect=SolariError("denied", 401)
    )
    result = await download_replay_once(client, "abc")
    assert result.status == ReplayStatus.AUTH_ERROR


@pytest.mark.asyncio
async def test_recorded_session_enables_recording_and_writes_meta(tmp_path: Path) -> None:
    meta_path = tmp_path / "session.json"
    browser = MagicMock()
    browser.id = "sess-xyz"
    browser.close = AsyncMock()

    client = MagicMock()
    client.launch = AsyncMock(return_value=browser)
    client.close = AsyncMock()

    with patch("agentreel.session.create_client", return_value=client):
        with patch("asyncio.sleep", new=AsyncMock()):
            async with recorded_session(
                api_key="test-key",
                meta_path=meta_path,
                flush_seconds=0.01,
                stealth=True,
            ) as b:
                assert b is browser

    client.launch.assert_awaited_once()
    kwargs = client.launch.await_args.kwargs
    assert kwargs["recording"] is True
    assert kwargs["stealth"] is True
    browser.close.assert_awaited_once()
    client.close.assert_awaited_once()

    meta = load_session_meta(meta_path)
    assert meta.session_id == "sess-xyz"
    assert meta.recording is True


@pytest.mark.asyncio
async def test_recorded_session_closes_on_agent_error(tmp_path: Path) -> None:
    meta_path = tmp_path / "session.json"
    browser = MagicMock()
    browser.id = "sess-err"
    browser.close = AsyncMock()
    client = MagicMock()
    client.launch = AsyncMock(return_value=browser)
    client.close = AsyncMock()

    with patch("agentreel.session.create_client", return_value=client):
        with patch("asyncio.sleep", new=AsyncMock()):
            with pytest.raises(RuntimeError, match="boom"):
                async with recorded_session(meta_path=meta_path, flush_seconds=0):
                    raise RuntimeError("boom")

    browser.close.assert_awaited_once()
    assert meta_path.exists()
    assert json.loads(meta_path.read_text())["session_id"] == "sess-err"
