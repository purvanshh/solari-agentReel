"""Poll Solari for a session replay and save events.json."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from solari_browser import Solari

from ..errors import RecordingNotFoundError, RecordingTimeoutError
from ..solari.adapter import (
    ReplayStatus,
    create_client,
    download_replay_once,
    ndjson_to_events_array,
)

log = logging.getLogger("agentreel.poller")

ProgressCallback = Callable[[str], None]


@dataclass
class PollResult:
    events_path: Path
    ndjson_path: Path
    session_id: str
    event_count: int
    byte_size: int


async def poll_and_download(
    session_id: str,
    output_dir: Path,
    *,
    client: Optional[Solari] = None,
    retries: int = 20,
    interval: float = 3.0,
    api_key: Optional[str] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> PollResult:
    """Poll until the replay is ready, then write events.json (+ raw NDJSON)."""
    owns_client = client is None
    solari = client or create_client(api_key)
    notify = on_progress or (lambda _msg: None)

    try:
        for attempt in range(1, retries + 1):
            notify(f"Attempt {attempt}/{retries}...")
            log.debug("poll attempt %s/%s session=%s", attempt, retries, session_id)

            if attempt > 1:
                await asyncio.sleep(interval)

            result = await download_replay_once(solari, session_id)

            if result.status == ReplayStatus.READY and result.data is not None:
                notify("Recording ready")
                return _save_events(result.data, output_dir, session_id)

            if result.status == ReplayStatus.AUTH_ERROR:
                raise RecordingNotFoundError(
                    f"Authentication failed while fetching recording for session {session_id}.",
                    hint="Check that SOLARI_API_KEY is valid and has access to this session.",
                )

            if result.status == ReplayStatus.SERVER_ERROR:
                log.warning("server error on poll: %s", result.message)
                # Transient — keep retrying.
                continue

            if result.status == ReplayStatus.NETWORK_ERROR:
                log.warning("network error on poll: %s", result.message)
                continue

            if result.status == ReplayStatus.ERROR:
                raise RecordingNotFoundError(
                    f"Unexpected error fetching recording: {result.message}",
                )

            # PENDING — keep going.
            log.debug("pending: %s", result.message)

        raise RecordingTimeoutError(
            f"Recording was not available after {retries} attempts.",
            session_id=session_id,
            attempts=retries,
            hint=(
                f"Session ID:\n{session_id}\n\n"
                "You can retry with:\n\n"
                f"agentreel run <script> --retries {retries * 2} --interval {max(interval, 5):.0f}\n\n"
                "Confirm the script used recorded_session() / recording=True."
            ),
        )
    finally:
        if owns_client:
            await solari.close()


def _save_events(blob: bytes, output_dir: Path, session_id: str) -> PollResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    ndjson_path = output_dir / "events.ndjson"
    events_path = output_dir / "events.json"

    ndjson_path.write_bytes(blob)
    events = ndjson_to_events_array(blob)
    events_path.write_text(json.dumps(events), encoding="utf-8")

    return PollResult(
        events_path=events_path,
        ndjson_path=ndjson_path,
        session_id=session_id,
        event_count=len(events),
        byte_size=len(blob),
    )
