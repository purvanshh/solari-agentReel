"""Thin Solari SDK adapter — isolates SDK-specific behavior."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from solari_browser import Solari
from solari_browser.errors import SolariError


class ReplayStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    AUTH_ERROR = "AUTH_ERROR"
    NOT_FOUND = "NOT_FOUND"
    SERVER_ERROR = "SERVER_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    ERROR = "ERROR"


@dataclass
class ReplayResult:
    status: ReplayStatus
    data: Optional[bytes] = None
    message: str = ""
    http_status: Optional[int] = None


def create_client(
    api_key: Optional[str] = None,
    *,
    region: str = "us-west",
    base_url: Optional[str] = None,
    **kwargs: Any,
) -> Solari:
    """Create a Solari client. API key defaults to SOLARI_API_KEY."""
    key = api_key or os.environ.get("SOLARI_API_KEY")
    if not key:
        raise SolariError(
            "Solari: api_key is required (set SOLARI_API_KEY or pass api_key=...)"
        )
    return Solari(api_key=key, region=region, base_url=base_url, **kwargs)


async def download_replay_once(client: Solari, session_id: str) -> ReplayResult:
    """Attempt a single replay download and classify the outcome."""
    try:
        blob = await client.sessions.download_replay(session_id)
    except SolariError as err:
        status_code = err.status
        if status_code == 404:
            # Upload still processing, OR session never had recording=True.
            return ReplayResult(
                status=ReplayStatus.PENDING,
                message=str(err),
                http_status=404,
            )
        if status_code in (401, 403):
            return ReplayResult(
                status=ReplayStatus.AUTH_ERROR,
                message=str(err),
                http_status=status_code,
            )
        if status_code is not None and status_code >= 500:
            return ReplayResult(
                status=ReplayStatus.SERVER_ERROR,
                message=str(err),
                http_status=status_code,
            )
        return ReplayResult(
            status=ReplayStatus.ERROR,
            message=str(err),
            http_status=status_code,
        )
    except OSError as err:
        return ReplayResult(status=ReplayStatus.NETWORK_ERROR, message=str(err))
    except Exception as err:  # noqa: BLE001 — classify unexpected transport failures
        msg = str(err).lower()
        if any(tok in msg for tok in ("timeout", "connection", "network", "dns")):
            return ReplayResult(status=ReplayStatus.NETWORK_ERROR, message=str(err))
        return ReplayResult(status=ReplayStatus.ERROR, message=str(err))

    if not blob:
        return ReplayResult(
            status=ReplayStatus.PENDING,
            message="empty replay body",
            http_status=200,
        )
    return ReplayResult(status=ReplayStatus.READY, data=blob, http_status=200)


def ndjson_to_events_array(blob: bytes) -> list[Any]:
    """Convert Solari's gzip-decoded NDJSON replay into a JSON array for rrvideo.

    Solari returns one rrweb event per line. rrvideo expects `JSON.parse` → array.
    """
    import json

    text = blob.decode("utf-8")
    events: list[Any] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events
