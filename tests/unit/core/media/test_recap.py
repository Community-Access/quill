"""Unit tests for the AI recap orchestration (no network, no model, no audio)."""

from __future__ import annotations

import pytest

from quill.core.media.recap import (
    ChapterContext,
    RecapService,
    RecapUnavailable,
    recap_key,
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


def test_path_a_uses_the_books_own_text() -> None:
    service = RecapService(transcriber=lambda p, s, d: "never")
    ctx = ChapterContext(book_key="b", chapter_index=3, text="Chapter twelve happened.")
    assert service.text_for(ctx) == "Chapter twelve happened."


def test_an_answer_is_remembered_per_kind_and_place() -> None:
    service = RecapService()
    ctx = ChapterContext(book_key="b", chapter_index=1, text="Words.")
    assert service.cached("chapter", ctx) == ""
    service.remember("chapter", ctx, "  Summary.  ")
    assert service.cached("chapter", ctx) == "Summary."
    assert service.cached("recap", ctx) == ""  # a recap is a different answer
    other = ChapterContext(book_key="b", chapter_index=2, text="Words.")
    assert service.cached("chapter", other) == ""


def test_an_empty_answer_is_not_remembered() -> None:
    service = RecapService()
    ctx = ChapterContext(book_key="b", chapter_index=1)
    service.remember("chapter", ctx, "   ")
    assert service.cached("chapter", ctx) == ""


def test_path_b_transcribes_when_no_text() -> None:
    transcribed: list[tuple[str, int, int]] = []

    def transcriber(path: str, start_ms: int, duration_ms: int) -> str:
        transcribed.append((path, start_ms, duration_ms))
        return "Transcribed words."

    service = RecapService(transcriber=transcriber)
    ctx = ChapterContext(
        book_key="b", chapter_index=0, audio_path="a.mp3", start_ms=1000, duration_ms=5000
    )
    assert service.text_for(ctx) == "Transcribed words."
    assert transcribed == [("a.mp3", 1000, 5000)]


def test_an_empty_transcript_raises() -> None:
    service = RecapService(transcriber=lambda p, s, d: "  ")
    ctx = ChapterContext(book_key="b", chapter_index=0, audio_path="a.mp3")
    with pytest.raises(RecapUnavailable):
        service.text_for(ctx)


def test_no_text_and_no_transcriber_raises() -> None:
    service = RecapService()
    ctx = ChapterContext(book_key="b", chapter_index=0, audio_path="a.mp3")
    with pytest.raises(RecapUnavailable):
        service.text_for(ctx)


def test_no_text_no_audio_raises() -> None:
    service = RecapService(transcriber=lambda p, s, d: "t")
    ctx = ChapterContext(book_key="b", chapter_index=0)  # no text, no audio_path
    with pytest.raises(RecapUnavailable):
        service.text_for(ctx)


def test_shared_cache_can_persist() -> None:
    store: dict[str, str] = {}
    ctx = ChapterContext(book_key="b", chapter_index=5, text="t")
    RecapService(cache=store).remember("chapter", ctx, "S.")
    # A fresh service sharing the same cache dict already has the answer.
    assert RecapService(cache=store).cached("chapter", ctx) == "S."
    assert store == {recap_key("chapter", ctx): "S."}
