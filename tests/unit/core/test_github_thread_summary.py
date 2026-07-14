"""AI thread summaries: prompt composition, bounds, and failure mapping."""

from __future__ import annotations

import pytest

from quill.core.github import thread_summary
from quill.core.github.thread_summary import (
    ThreadSummaryError,
    compose_thread_text,
    summarize_thread,
)


def test_compose_thread_text_carries_title_body_and_comments() -> None:
    text = compose_thread_text(
        "Fix the thing",
        "alice",
        "It breaks.",
        [
            {"author": "bob", "created_at": "2026-07-01T10:00:00", "body": "Repro confirmed."},
            {"author": "alice", "created_at": "2026-07-02T10:00:00", "body": "PR up."},
        ],
    )
    assert "Title: Fix the thing" in text
    assert "Opened by: alice" in text
    assert "Comment by bob (2026-07-01):" in text
    assert "PR up." in text


def test_compose_thread_text_truncates_middle_out() -> None:
    huge = compose_thread_text("T", "a", "start-marker " + "x" * 50_000 + " end-marker", [])
    assert len(huge) <= thread_summary._MAX_THREAD_CHARS + 100
    assert "start-marker" in huge and "end-marker" in huge
    assert "truncated" in huge


def test_summarize_thread_happy_path(monkeypatch) -> None:
    captured: dict = {}

    def fake_generate(connection, api_key, prompt, **kwargs):
        captured["prompt"] = prompt
        return "The thread decided X.", ""

    monkeypatch.setattr("quill.core.assistant_ai.generate_assistant_response", fake_generate)
    out = summarize_thread(object(), "key", "some thread text")
    assert out == "The thread decided X."
    assert "some thread text" in captured["prompt"]
    assert "screen reader" in captured["prompt"]


def test_summarize_thread_maps_failures_to_coded_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        "quill.core.assistant_ai.generate_assistant_response",
        lambda *a, **k: ("", "401 bad key"),
    )
    with pytest.raises(ThreadSummaryError, match="401"):
        summarize_thread(object(), "key", "text")
    monkeypatch.setattr(
        "quill.core.assistant_ai.generate_assistant_response",
        lambda *a, **k: ("   ", ""),
    )
    with pytest.raises(ThreadSummaryError, match="empty"):
        summarize_thread(object(), "key", "text")
    with pytest.raises(ThreadSummaryError, match="no discussion"):
        summarize_thread(object(), "key", "   ")
