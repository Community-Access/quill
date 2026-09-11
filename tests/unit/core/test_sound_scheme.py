"""Editing a sound scheme: the three states, the guards, and getting back.

The whole point of the draft model is that **nothing is destroyed**, so most of
what is asserted here is that the way back always exists and cannot fail. The
rest is the guard on what may be used as an earcon, which has to refuse at the
moment of choosing: a sound that fails at playback fails *silently*, and a
silent event is indistinguishable from one nobody set.
"""

from __future__ import annotations

import json
import struct
import wave
from pathlib import Path

import pytest

from quill.core.sound_scheme import (
    MAX_SOUND_SECONDS,
    SchemeDraft,
    SchemeError,
    delete_scheme,
    describe_sound,
    read_wave_facts,
    save_scheme,
    user_schemes,
    validate_sound_file,
)


def _wav(path: Path, seconds: float = 0.05, rate: int = 44100) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(rate * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(struct.pack(f"<{frames}h", *([0] * frames)))
    return path


@pytest.fixture()
def pack(tmp_path: Path) -> Path:
    base = tmp_path / "base"
    _wav(base / "save.wav")
    _wav(base / "open.wav")
    return base


@pytest.fixture()
def draft(pack: Path) -> SchemeDraft:
    return SchemeDraft(
        base_events={"document_saved": "save.wav", "document_opened": "open.wav"},
        base_dir=pack,
    )


# ---------------------------------------------------------------------------
# The three states


def test_an_untouched_event_plays_what_the_pack_says(draft: SchemeDraft, pack: Path) -> None:
    assert draft.source_for("document_saved") == pack / "save.wav"
    assert draft.is_default("document_saved")


def test_an_override_wins_over_the_pack(draft: SchemeDraft, tmp_path: Path) -> None:
    mine = _wav(tmp_path / "mine.wav")
    draft.set_sound("document_saved", mine)
    assert draft.source_for("document_saved") == mine
    assert not draft.is_default("document_saved")


def test_silence_is_a_third_state_not_an_absent_override(draft: SchemeDraft) -> None:
    """Different from disabling the event (a settings concern) and different
    from restoring the default (dropping an override)."""
    draft.silence("document_saved")
    assert draft.source_for("document_saved") is None
    assert draft.is_silent("document_saved")
    assert not draft.is_default("document_saved")


def test_an_event_the_pack_never_had_is_silent(draft: SchemeDraft) -> None:
    assert draft.source_for("text_pasted") is None


def test_a_pack_entry_whose_file_has_gone_is_silent(draft: SchemeDraft, pack: Path) -> None:
    """A manifest can outlive its files. Silence is the honest answer; a path
    that does not exist would be handed to the player to fail on."""
    (pack / "save.wav").unlink()
    assert draft.source_for("document_saved") is None


# ---------------------------------------------------------------------------
# Getting back


def test_restoring_one_event_puts_the_pack_sound_back(draft: SchemeDraft, tmp_path: Path) -> None:
    draft.set_sound("document_saved", _wav(tmp_path / "mine.wav"))
    draft.restore("document_saved")
    assert draft.is_default("document_saved")
    assert draft.source_for("document_saved") is not None


def test_restoring_a_silenced_event_brings_the_sound_back(draft: SchemeDraft) -> None:
    draft.silence("document_saved")
    draft.restore("document_saved")
    assert draft.source_for("document_saved") is not None


def test_restore_all_cannot_half_succeed(draft: SchemeDraft, tmp_path: Path) -> None:
    """Whatever somebody has done in the window, getting out of it must never
    be a sequence of steps that could be got wrong halfway."""
    draft.set_sound("document_saved", _wav(tmp_path / "mine.wav"))
    draft.silence("document_opened")
    draft.restore_all()
    assert not draft.dirty
    assert draft.is_default("document_saved")
    assert draft.is_default("document_opened")


def test_a_fresh_draft_is_not_dirty(draft: SchemeDraft) -> None:
    assert not draft.dirty


# ---------------------------------------------------------------------------
# What may be used as an earcon


def test_a_missing_file_is_refused_with_a_sentence(tmp_path: Path) -> None:
    with pytest.raises(SchemeError, match="not a file"):
        validate_sound_file(tmp_path / "nope.wav")


def test_something_that_is_not_a_wav_is_refused(tmp_path: Path) -> None:
    fake = tmp_path / "song.wav"
    fake.write_bytes(b"ID3 this is an mp3 wearing a hat")
    with pytest.raises(SchemeError, match="WAV"):
        validate_sound_file(fake)


def test_a_sound_longer_than_the_limit_is_refused(tmp_path: Path) -> None:
    """A sound this long would still be playing when the next one starts."""
    long_one = _wav(tmp_path / "epic.wav", seconds=MAX_SOUND_SECONDS + 2, rate=8000)
    with pytest.raises(SchemeError, match="seconds"):
        validate_sound_file(long_one)


def test_a_bad_pick_never_lands_in_the_draft(draft: SchemeDraft, tmp_path: Path) -> None:
    fake = tmp_path / "song.wav"
    fake.write_bytes(b"not audio")
    with pytest.raises(SchemeError):
        draft.set_sound("document_saved", fake)
    assert draft.is_default("document_saved")


def test_a_short_wav_is_accepted_and_measured(tmp_path: Path) -> None:
    facts = validate_sound_file(_wav(tmp_path / "blip.wav", seconds=0.06))
    assert 0.05 < facts.seconds < 0.07
    assert facts.channels == 1


def test_describe_leads_with_the_length(tmp_path: Path) -> None:
    """The fact that decides whether a sound belongs on an event that fires
    forty times an hour."""
    assert "ms" in describe_sound(_wav(tmp_path / "blip.wav", seconds=0.05))
    assert describe_sound(None) == "Silent"


def test_describing_an_unreadable_file_says_so_rather_than_lying(tmp_path: Path) -> None:
    broken = tmp_path / "broken.wav"
    broken.write_bytes(b"nope")
    assert "cannot be read" in describe_sound(broken)
    assert read_wave_facts(broken) is None


# ---------------------------------------------------------------------------
# Saving


def test_a_saved_scheme_is_an_ordinary_pack(draft: SchemeDraft, tmp_path: Path) -> None:
    """Same manifest every shipped pack has, so it can be zipped, sent, or read
    in a text editor. A format only the app that wrote it can read is a format
    that traps the work somebody put into it."""
    out = save_scheme(draft, "My Sounds", tmp_path / "data")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["format"] == "qsp"
    assert manifest["name"] == "My Sounds"
    assert set(manifest["events"]) == {"document_saved", "document_opened"}


def test_every_sound_is_copied_in_not_pointed_at(draft: SchemeDraft, tmp_path: Path) -> None:
    """A scheme pointing at somebody's Downloads folder breaks the first time
    they tidy it, and is useless to anyone they send it to."""
    mine = _wav(tmp_path / "elsewhere" / "mine.wav")
    draft.set_sound("document_saved", mine)
    out = save_scheme(draft, "Mine", tmp_path / "data")
    assert (out / "document_saved.wav").is_file()
    mine.unlink()
    assert (out / "document_saved.wav").is_file()  # survives the source going


def test_a_silenced_event_is_simply_absent_from_the_saved_scheme(
    draft: SchemeDraft, tmp_path: Path
) -> None:
    draft.silence("document_saved")
    out = save_scheme(draft, "Quiet", tmp_path / "data")
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert "document_saved" not in manifest["events"]
    assert "document_opened" in manifest["events"]


def test_a_scheme_needs_a_name(draft: SchemeDraft, tmp_path: Path) -> None:
    with pytest.raises(SchemeError, match="name"):
        save_scheme(draft, "   ", tmp_path / "data")


def test_a_hostile_name_becomes_a_harmless_folder(draft: SchemeDraft, tmp_path: Path) -> None:
    """The name becomes a path. "../.." must be a folder called something
    harmless rather than an interesting question about where the files went."""
    data = tmp_path / "data"
    out = save_scheme(draft, "../../etc", data)
    assert data.resolve() in out.resolve().parents


def test_saving_twice_replaces_rather_than_accumulating(draft: SchemeDraft, tmp_path: Path) -> None:
    data = tmp_path / "data"
    save_scheme(draft, "Mine", data)
    draft.silence("document_saved")
    out = save_scheme(draft, "Mine", data)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert "document_saved" not in manifest["events"]
    assert len(user_schemes(data)) == 1


def test_saved_schemes_are_listed_by_their_display_name(draft: SchemeDraft, tmp_path: Path) -> None:
    data = tmp_path / "data"
    save_scheme(draft, "Zebra", data)
    save_scheme(draft, "Apple", data)
    assert [scheme.name for scheme in user_schemes(data)] == ["Apple", "Zebra"]


def test_a_half_written_scheme_does_not_stop_the_list_opening(tmp_path: Path) -> None:
    """An interrupted save should cost the user that scheme, not the chooser."""
    data = tmp_path / "data"
    (data / "sound_schemes" / "broken").mkdir(parents=True)
    (data / "sound_schemes" / "broken" / "manifest.json").write_text("{not json", encoding="utf-8")
    assert user_schemes(data) == []


def test_a_deleted_scheme_is_gone(draft: SchemeDraft, tmp_path: Path) -> None:
    data = tmp_path / "data"
    save_scheme(draft, "Mine", data)
    delete_scheme(user_schemes(data)[0])
    assert user_schemes(data) == []


def test_no_schemes_yet_is_an_empty_list_not_an_error(tmp_path: Path) -> None:
    assert user_schemes(tmp_path / "nothing-here") == []
