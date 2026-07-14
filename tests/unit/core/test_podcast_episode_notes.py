"""Tests for timestamped podcast episode notes (atomic-JSON store)."""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import paths
from quill.core.podcasts.episode_notes import (
    EpisodeNote,
    add_episode_note,
    delete_episode_note,
    load_episode_notes,
    notes_for_episode,
    save_episode_notes,
)


@pytest.fixture(autouse=True)
def data_dir_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    data_dir = fake_home / "quill-data"
    monkeypatch.setattr(paths, "_DEV_BUILD", True)
    monkeypatch.setattr(paths.Path, "home", classmethod(lambda cls: fake_home))
    monkeypatch.setenv("QUILL_DATA_DIR", str(data_dir))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("QUILL_PORTABLE_ROOT", raising=False)
    return data_dir


def test_load_missing_file_returns_empty() -> None:
    assert load_episode_notes() == []


def test_add_episode_note_persists_and_returns_updated_list() -> None:
    notes = add_episode_note("s1", "e1", 5000, "Great point here")
    assert len(notes) == 1
    assert notes[0].show_id == "s1"
    assert notes[0].episode_guid == "e1"
    assert notes[0].position_ms == 5000
    assert notes[0].text == "Great point here"
    assert load_episode_notes() == notes


def test_add_episode_note_clamps_negative_position() -> None:
    notes = add_episode_note("s1", "e1", -500, "Note")
    assert notes[0].position_ms == 0


def test_notes_for_episode_filters_and_sorts_by_position() -> None:
    add_episode_note("s1", "e1", 10_000, "Later point")
    add_episode_note("s1", "e1", 2_000, "Early point")
    add_episode_note("s1", "e2", 3_000, "Different episode")
    add_episode_note("s2", "e1", 4_000, "Different show, same guid")
    result = notes_for_episode(load_episode_notes(), "s1", "e1")
    assert [n.text for n in result] == ["Early point", "Later point"]


def test_delete_episode_note_removes_only_that_note() -> None:
    notes = add_episode_note("s1", "e1", 1000, "Keep me")
    notes = add_episode_note("s1", "e1", 2000, "Remove me")
    to_remove = next(n for n in notes if n.text == "Remove me")
    remaining = delete_episode_note(to_remove.note_id)
    assert [n.text for n in remaining] == ["Keep me"]


def test_delete_episode_note_missing_id_is_a_noop() -> None:
    add_episode_note("s1", "e1", 1000, "Keep me")
    remaining = delete_episode_note("not-a-real-id")
    assert [n.text for n in remaining] == ["Keep me"]


def test_from_dict_rejects_blank_text() -> None:
    assert (
        EpisodeNote.from_dict({
            "note_id": "n1",
            "show_id": "s1",
            "episode_guid": "e1",
            "text": "  ",
            "position_ms": 0,
        })
        is None
    )


def test_save_and_load_round_trip() -> None:
    note = EpisodeNote(
        note_id="n1",
        show_id="s1",
        episode_guid="e1",
        position_ms=1234,
        text="Something worth remembering",
        created_at="2026-07-13T00:00:00+00:00",
    )
    save_episode_notes([note])
    assert load_episode_notes() == [note]
