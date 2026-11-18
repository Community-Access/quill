"""What QUILL meant to say and did not goes in the log, with why (from EdSharp)."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from quill.ui.unspoken_log import log_unspoken


def test_the_reason_and_whether_quill_was_in_front(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="quill.unspoken"):
        log_unspoken(SimpleNamespace(IsActive=lambda: False), "Saved notes.md", "Quiet Mode")
        log_unspoken(SimpleNamespace(IsActive=lambda: True), "x" * 500, "a repeat")
    first, second = (record.getMessage() for record in caplog.records)
    assert first == (
        "Not spoken (Quiet Mode, while QUILL was not the window in front): Saved notes.md"
    )
    assert second.startswith("Not spoken (a repeat): xxx") and second.endswith("...")
    assert len(second) < 260


def test_a_dead_frame_never_raises(caplog: pytest.LogCaptureFixture) -> None:
    def gone() -> bool:
        raise RuntimeError("wrapped C/C++ object has been deleted")

    with caplog.at_level(logging.INFO, logger="quill.unspoken"):
        log_unspoken(SimpleNamespace(IsActive=gone), "Hi", "speech failed: no reader")
    assert "not the window in front" in caplog.records[0].getMessage()
