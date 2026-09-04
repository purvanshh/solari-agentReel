"""Fallback conversion backend.

rrvideo itself already replays events in a headless Chromium (Playwright).
When it fails, we attempt a second pass after validating/normalizing the
events file. A full custom Puppeteer capture pipeline is intentionally not
bundled for MVP complexity; this module is the extension point.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ..errors import ConversionError
from .rrvideo import convert_with_rrvideo

log = logging.getLogger("agentreel.fallback")


def convert_with_fallback(events_path: Path, output_webm: Path) -> Path:
    """Retry conversion after rewriting events.json into a clean JSON array."""
    log.info("Attempting fallback conversion for %s", events_path)
    normalized = events_path.with_name("events.normalized.json")
    try:
        raw = json.loads(events_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ConversionError(
            "events.json is not valid JSON; cannot run fallback converter.",
            hint=str(err),
        ) from err

    if not isinstance(raw, list) or not raw:
        raise ConversionError(
            "events.json must be a non-empty JSON array of rrweb events.",
        )

    # Drop any non-object entries that would crash the player.
    cleaned = [e for e in raw if isinstance(e, dict) and "type" in e]
    if not cleaned:
        raise ConversionError("No valid rrweb events found after normalization.")

    normalized.write_text(json.dumps(cleaned), encoding="utf-8")
    try:
        return convert_with_rrvideo(normalized, output_webm)
    except ConversionError as err:
        raise ConversionError(
            "Fallback conversion also failed.",
            hint=(
                f"{err}\n\n"
                "rrvideo uses headless Chromium under the hood. Ensure Playwright "
                "browsers are installed (`npx playwright install`), then retry.\n"
                "Raw events were preserved next to the output directory."
            ),
        ) from err
