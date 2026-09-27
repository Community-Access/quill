"""Cover art is carried into the converted copy without breaking the file."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

pytest.importorskip("mutagen")

from quill.core.audio.cover_art import _read_picture, carry_cover_art  # noqa: E402


def _silent_wav(path: Path) -> Path:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(8000)
        out.writeframes(b"\x00\x00" * 800)
    return path


def _with_cover(path: Path) -> Path:
    from mutagen.id3 import APIC
    from mutagen.wave import WAVE

    riff = WAVE(str(path))
    riff.add_tags()
    riff.tags.add(APIC(encoding=3, mime="image/png", type=3, desc="Cover", data=b"\x89PNGfake"))
    riff.save()
    return path


def test_a_wav_keeps_playing_after_its_cover_is_added(tmp_path: Path) -> None:
    source = _with_cover(_silent_wav(tmp_path / "source.wav"))
    dest = _silent_wav(tmp_path / "dest.wav")
    assert carry_cover_art(source, dest) is True
    # The RIFF container must still open: the first build prepended an ID3
    # header to the file and every player refused it.
    with wave.open(str(dest), "rb") as check:
        assert check.getnframes() == 800
    assert _read_picture(dest) == (b"\x89PNGfake", "image/png")


def test_nothing_happens_without_a_cover_or_with_one_already(tmp_path: Path) -> None:
    plain = _silent_wav(tmp_path / "plain.wav")
    dest = _silent_wav(tmp_path / "dest.wav")
    assert carry_cover_art(plain, dest) is False
    covered = _with_cover(_silent_wav(tmp_path / "covered.wav"))
    already = _with_cover(_silent_wav(tmp_path / "already.wav"))
    assert carry_cover_art(covered, already) is False


def test_an_unreadable_source_is_never_an_error(tmp_path: Path) -> None:
    junk = tmp_path / "junk.mp3"
    junk.write_bytes(b"not audio")
    assert carry_cover_art(junk, _silent_wav(tmp_path / "dest.wav")) is False
