"""AgentReel adapter unit tests for NDJSON handling edge cases."""

from __future__ import annotations

import pytest

from agentreel.solari.adapter import ndjson_to_events_array


def test_skips_blank_lines() -> None:
    blob = b'{"type":4}\n\n{"type":2}\n'
    assert len(ndjson_to_events_array(blob)) == 2


def test_invalid_json_raises() -> None:
    with pytest.raises(Exception):
        ndjson_to_events_array(b"{not-json}\n")
