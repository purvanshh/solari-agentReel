"""recorded_session() — opt-in Solari recording context manager."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .config import ENV_META_PATH, ENV_SCRIPT
from .solari.adapter import create_client


@dataclass
class SessionMeta:
    session_id: str
    script: str = ""
    timestamp: str = ""
    recording: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class _RecordedSession:
    """Async context manager that launches a Solari browser with recording=True."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        region: str = "us-west",
        base_url: Optional[str] = None,
        meta_path: Optional[Path] = None,
        flush_seconds: float = 2.0,
        **launch_kwargs: Any,
    ) -> None:
        self._api_key = api_key
        self._region = region
        self._base_url = base_url
        self._meta_path = Path(meta_path) if meta_path else _meta_path_from_env()
        self._flush_seconds = flush_seconds
        # Force recording — this is the whole point of the wrapper.
        launch_kwargs = dict(launch_kwargs)
        launch_kwargs["recording"] = True
        self._launch_kwargs = launch_kwargs

        self._client: Any = None
        self._browser: Any = None
        self.session_id: Optional[str] = None
        self.meta: Optional[SessionMeta] = None

    async def __aenter__(self) -> Any:
        self._client = create_client(
            self._api_key,
            region=self._region,
            base_url=self._base_url,
        )
        self._browser = await self._client.launch(**self._launch_kwargs)
        self.session_id = self._browser.id
        return self._browser

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        import asyncio

        # Give rrweb a moment to flush batched events before release (cookbook pattern).
        if self._flush_seconds > 0 and self._browser is not None:
            try:
                await asyncio.sleep(self._flush_seconds)
            except Exception:  # noqa: BLE001
                pass

        close_error: Optional[BaseException] = None
        if self._browser is not None:
            try:
                await self._browser.close()
            except BaseException as err:  # noqa: BLE001 — always attempt client close
                close_error = err

        if self._client is not None:
            try:
                await self._client.close()
            except Exception:  # noqa: BLE001
                pass

        if self.session_id:
            self.meta = SessionMeta(
                session_id=self.session_id,
                script=os.environ.get(ENV_SCRIPT, ""),
                timestamp=datetime.now(timezone.utc).isoformat(),
                recording=True,
            )
            _write_meta(self._meta_path, self.meta)

        if close_error is not None and exc_type is None:
            raise close_error
        # Do not swallow exceptions from the agent body.
        return None


def recorded_session(
    api_key: Optional[str] = None,
    *,
    region: str = "us-west",
    base_url: Optional[str] = None,
    meta_path: Optional[Path] = None,
    flush_seconds: float = 2.0,
    **launch_kwargs: Any,
) -> _RecordedSession:
    """Launch a Solari browser session with recording enabled.

    Usage::

        from agentreel import recorded_session

        async def main():
            async with recorded_session() as browser:
                page = await browser.new_page()
                await page.goto("https://example.com")

    Accepts the same launch kwargs as ``Solari.launch`` (stealth, proxy, etc.).
    ``recording=True`` is always set and cannot be disabled.
    """
    return _RecordedSession(
        api_key,
        region=region,
        base_url=base_url,
        meta_path=meta_path,
        flush_seconds=flush_seconds,
        **launch_kwargs,
    )


def _meta_path_from_env() -> Optional[Path]:
    raw = os.environ.get(ENV_META_PATH)
    return Path(raw) if raw else None


def _write_meta(path: Optional[Path], meta: SessionMeta) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta.to_dict(), indent=2) + "\n", encoding="utf-8")


def load_session_meta(path: Path) -> SessionMeta:
    data = json.loads(path.read_text(encoding="utf-8"))
    return SessionMeta(
        session_id=data["session_id"],
        script=data.get("script", ""),
        timestamp=data.get("timestamp", ""),
        recording=bool(data.get("recording", True)),
    )
