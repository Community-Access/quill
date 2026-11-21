"""What QUILL meant to say and did not goes in the log, with why (from EdSharp)."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from quill.ui.unspoken_log import log_unspoken


def test_the_reason_and_whether_quill_was_in_front(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="quill.unspoken"):
        log_unspoken(SimpleNamespace(IsActive=lambda: False), "Saved notes.md", "Quiet Mode")
        log_unspoken(SimpleNamespace(IsActive=lambda: True), "word " * 100, "a repeat")
    first, second = (record.getMessage() for record in caplog.records)
    assert first == (
        "Not spoken (Quiet Mode, while QUILL was not the window in front): Saved notes.md"
    )
    assert second.startswith("Not spoken (a repeat): word word") and second.endswith("...")
    assert len(second) < 260


def test_a_dead_frame_never_raises(caplog: pytest.LogCaptureFixture) -> None:
    def gone() -> bool:
        raise RuntimeError("wrapped C/C++ object has been deleted")

    with caplog.at_level(logging.INFO, logger="quill.unspoken"):
        log_unspoken(SimpleNamespace(IsActive=gone), "Hi", "speech failed: no reader")
    assert "not the window in front" in caplog.records[0].getMessage()


def test_a_key_or_password_in_the_message_is_logged_redacted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    key = "sk-proj-" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"
    password = "abcd EFGH 1234 ijkl MNOP 5678"
    with caplog.at_level(logging.INFO, logger="quill.unspoken"):
        log_unspoken(None, f"Key saved: {key}", "Quiet Mode")
        log_unspoken(None, f"Application password: {password}", "Quiet Mode")
    logged = " ".join(record.getMessage() for record in caplog.records)
    assert key not in logged and "A1b2C3d4E5f6" not in logged
    assert password not in logged
    assert logged.count("Not spoken (Quiet Mode)") == 2
