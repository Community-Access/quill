"""Unit tests for the AI recap orchestration (no network, no model, no audio)."""

from __future__ import annotations

import pytest

from quill.core.media.recap import (
    ChapterContext,
    RecapService,
    RecapUnavailable,
    recap_prompt,
)


def test_recap_prompt_shapes() -> None:
    chapter = recap_prompt("chapter", "Some text.")
    recap = recap_prompt("recap", "Some text.")
    assert "chapter" in chapter.lower()
    assert "resume" in recap.lower()
    assert chapter.endswith("Some text.")
    assert recap.endswith("Some text.")


def test_prompt_trims_long_text() -> None:
    long_text = "x" * 10_000
    prompt = recap_prompt("chapter", long_text)
    # Only the trailing 6000 chars of body are kept.
    assert prompt.count("x") == 6_000


def test_chapter_summary_path_a_text() -> None:
    calls: list[str] = []

    def summarizer(prompt: str) -> str:
        calls.append(prompt)
        return "A tidy summary."

    service = RecapService(summarizer)
    ctx = ChapterContext(book_key="b", chapter_index=3, text="Chapter twelve happened.")
    assert service.chapter_summary(ctx) == "A tidy summary."
    assert "Chapter twelve happened." in calls[0]


def test_summary_is_cached() -> None:
    calls: list[str] = []

    def summarizer(prompt: str) -> str:
        calls.append(prompt)
        return "Summary."

    service = RecapService(summarizer)
    ctx = ChapterContext(book_key="b", chapter_index=1, text="Words.")
    service.chapter_summary(ctx)
    service.chapter_summary(ctx)
    assert len(calls) == 1  # second call served from cache


def test_path_b_transcribes_when_no_text() -> None:
    transcribed: list[tuple[str, int, int]] = []

    def transcriber(path: str, start_ms: int, duration_ms: int) -> str:
        transcribed.append((path, start_ms, duration_ms))
        return "Transcribed words."

    def summarizer(prompt: str) -> str:
        assert "Transcribed words." in prompt
        return "Audio summary."

    service = RecapService(summarizer, transcriber=transcriber)
    ctx = ChapterContext(
        book_key="b", chapter_index=0, audio_path="a.mp3", start_ms=1000, duration_ms=5000
    )
    assert service.chapter_summary(ctx) == "Audio summary."
    assert transcribed == [("a.mp3", 1000, 5000)]


def test_no_text_and_no_transcriber_raises() -> None:
    service = RecapService(lambda prompt: "x")
    ctx = ChapterContext(book_key="b", chapter_index=0, audio_path="a.mp3")
    with pytest.raises(RecapUnavailable):
        service.chapter_summary(ctx)


def test_no_text_no_audio_raises() -> None:
    service = RecapService(lambda prompt: "x", transcriber=lambda p, s, d: "t")
    ctx = ChapterContext(book_key="b", chapter_index=0)  # no text, no audio_path
    with pytest.raises(RecapUnavailable):
        service.chapter_summary(ctx)


def test_welcome_back_uses_recap_prompt() -> None:
    def summarizer(prompt: str) -> str:
        assert "resume" in prompt.lower()
        return "Welcome back recap."

    service = RecapService(summarizer)
    ctx = ChapterContext(book_key="b", chapter_index=2, text="Earlier events.")
    assert service.welcome_back(ctx) == "Welcome back recap."


def test_shared_cache_can_persist() -> None:
    store: dict[str, str] = {}
    calls = 0

    def summarizer(prompt: str) -> str:
        nonlocal calls
        calls += 1
        return "S."

    ctx = ChapterContext(book_key="b", chapter_index=5, text="t")
    RecapService(summarizer, cache=store).chapter_summary(ctx)
    # A fresh service sharing the same cache dict does not re-summarize.
    RecapService(summarizer, cache=store).chapter_summary(ctx)
    assert calls == 1
    assert store  # summary persisted into the injected store
