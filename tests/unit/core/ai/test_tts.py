"""Unit tests for quill.core.ai.tts - chunking and error hierarchy."""

from __future__ import annotations

import pytest

from quill.core.ai.tts import (
    DEFAULT_MODEL,
    DEFAULT_VOICE,
    TTS_CHUNK_CHARS,
    VOICES,
    TTSAuthError,
    TTSCancelledError,
    TTSError,
    TTSQuotaError,
    chunk_text,
)

# ---------------------------------------------------------------------------
# chunk_text
# ---------------------------------------------------------------------------


def test_short_text_is_single_chunk() -> None:
    result = chunk_text("Hello, world.", max_chars=200)
    assert result == ["Hello, world."]


def test_empty_text_returns_empty_list() -> None:
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_at_paragraph_boundary() -> None:
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_text(text, max_chars=30)
    assert len(chunks) == 3
    assert all(len(c) <= 30 for c in chunks)
    assert (
        "".join(chunks).replace("\n\n", "") == "First paragraph.Second paragraph.Third paragraph."
    )


def test_chunk_falls_back_to_sentence_boundary() -> None:
    # One long paragraph - should split at sentence boundary
    text = "This is sentence one. This is sentence two. This is sentence three."
    chunks = chunk_text(text, max_chars=30)
    assert len(chunks) > 1
    assert all(len(c) <= 30 for c in chunks)


def test_chunk_hard_splits_when_no_boundary() -> None:
    # No spaces or punctuation - hard split at max_chars
    text = "x" * 50
    chunks = chunk_text(text, max_chars=20)
    assert len(chunks) == 3
    assert all(len(c) <= 20 for c in chunks)
    assert "".join(chunks) == text


def test_chunk_text_respects_default_limit() -> None:
    # Default should use TTS_CHUNK_CHARS (4000)
    short = "a" * 100
    result = chunk_text(short)
    assert result == [short]


def test_chunk_text_large_document() -> None:
    text = "Paragraph. " * 500  # ~5500 chars
    chunks = chunk_text(text, max_chars=TTS_CHUNK_CHARS)
    assert len(chunks) > 1
    assert all(len(c) <= TTS_CHUNK_CHARS for c in chunks)
    # Every chunk is non-empty
    assert all(c.strip() for c in chunks)


def test_chunk_text_single_word_exceeding_limit() -> None:
    long_word = "supercalifragilisticexpialidocious" * 10
    chunks = chunk_text(long_word, max_chars=20)
    assert all(len(c) <= 20 for c in chunks)
    assert "".join(chunks) == long_word


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


def test_tts_auth_error_is_tts_error() -> None:
    assert issubclass(TTSAuthError, TTSError)


def test_tts_quota_error_is_tts_error() -> None:
    assert issubclass(TTSQuotaError, TTSError)


def test_tts_cancelled_error_is_tts_error() -> None:
    assert issubclass(TTSCancelledError, TTSError)


def test_tts_error_can_be_raised_with_message() -> None:
    with pytest.raises(TTSError, match="something went wrong"):
        raise TTSError("something went wrong")


def test_tts_auth_error_caught_as_tts_error() -> None:
    with pytest.raises(TTSError):
        raise TTSAuthError("invalid key")


# ---------------------------------------------------------------------------
# Constants and defaults
# ---------------------------------------------------------------------------


def test_voices_list_nonempty() -> None:
    assert len(VOICES) > 0


def test_voices_are_id_label_tuples() -> None:
    for voice_id, label in VOICES:
        assert isinstance(voice_id, str) and voice_id
        assert isinstance(label, str) and label


def test_default_voice_in_voices() -> None:
    voice_ids = [v[0] for v in VOICES]
    assert DEFAULT_VOICE in voice_ids


def test_default_model_nonempty() -> None:
    assert DEFAULT_MODEL and isinstance(DEFAULT_MODEL, str)


def test_chunk_chars_positive() -> None:
    assert TTS_CHUNK_CHARS > 0
    assert TTS_CHUNK_CHARS <= 4096  # OpenAI hard limit
