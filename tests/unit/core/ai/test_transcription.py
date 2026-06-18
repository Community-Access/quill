"""Unit tests for quill.core.ai.transcription."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.ai.transcription import (
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_AUDIO_EXTENSIONS,
    SUPPORTED_LANGUAGES,
    TranscriptionAuthError,
    TranscriptionError,
    TranscriptionFileTooLargeError,
    TranscriptionFormatError,
    _validate_file,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_max_file_size_is_25mb() -> None:
    assert MAX_FILE_SIZE_BYTES == 25 * 1024 * 1024


def test_supported_extensions_nonempty() -> None:
    assert len(SUPPORTED_AUDIO_EXTENSIONS) > 0


def test_mp3_supported() -> None:
    assert ".mp3" in SUPPORTED_AUDIO_EXTENSIONS


def test_wav_supported() -> None:
    assert ".wav" in SUPPORTED_AUDIO_EXTENSIONS


def test_mp4_supported() -> None:
    assert ".mp4" in SUPPORTED_AUDIO_EXTENSIONS


def test_auto_detect_in_languages() -> None:
    assert "Auto-detect" in SUPPORTED_LANGUAGES
    assert SUPPORTED_LANGUAGES["Auto-detect"] == ""


def test_english_in_languages() -> None:
    assert "English" in SUPPORTED_LANGUAGES
    assert SUPPORTED_LANGUAGES["English"] == "en"


# ---------------------------------------------------------------------------
# _validate_file
# ---------------------------------------------------------------------------


def test_validate_file_not_found_raises(tmp_path: Path) -> None:
    with pytest.raises(TranscriptionError, match="not found"):
        _validate_file(tmp_path / "ghost.mp3")


def test_validate_file_too_large_raises(tmp_path: Path) -> None:
    f = tmp_path / "big.mp3"
    # Write a file that is slightly above the limit
    f.write_bytes(b"\x00" * (MAX_FILE_SIZE_BYTES + 1))
    with pytest.raises(TranscriptionFileTooLargeError):
        _validate_file(f)


def test_validate_file_at_limit_passes(tmp_path: Path) -> None:
    f = tmp_path / "ok.mp3"
    f.write_bytes(b"\x00" * MAX_FILE_SIZE_BYTES)
    _validate_file(f)  # should not raise


def test_validate_file_unsupported_extension_raises(tmp_path: Path) -> None:
    f = tmp_path / "audio.xyz"
    f.write_bytes(b"\x00" * 100)
    with pytest.raises(TranscriptionFormatError, match="Unsupported"):
        _validate_file(f)


def test_validate_file_supported_extension_passes(tmp_path: Path) -> None:
    for ext in (".mp3", ".wav", ".m4a"):
        f = tmp_path / f"audio{ext}"
        f.write_bytes(b"\x00" * 100)
        _validate_file(f)  # should not raise


def test_validate_file_case_insensitive_extension(tmp_path: Path) -> None:
    f = tmp_path / "audio.MP3"
    f.write_bytes(b"\x00" * 100)
    _validate_file(f)  # .MP3 should be accepted


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


def test_file_too_large_is_transcription_error() -> None:
    assert issubclass(TranscriptionFileTooLargeError, TranscriptionError)


def test_format_error_is_transcription_error() -> None:
    assert issubclass(TranscriptionFormatError, TranscriptionError)


def test_auth_error_is_transcription_error() -> None:
    assert issubclass(TranscriptionAuthError, TranscriptionError)
