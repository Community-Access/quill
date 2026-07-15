"""Tests for the recently-played podcast episode history store."""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts.history import PodcastHistory, load_history, save_history


def test_record_moves_repeat_plays_to_the_front_without_duplicates() -> None:
    history = PodcastHistory()
    history.record("show-a", "guid-1", show_title="Show A", episode_title="Ep 1")
    history.record("show-b", "guid-2", show_title="Show B", episode_title="Ep 2")
    history.record("show-a", "guid-1", show_title="Show A", episode_title="Ep 1")
    assert [e.episode_guid for e in history.episodes] == ["guid-1", "guid-2"]
    assert history.last_played is not None and history.last_played.episode_guid == "guid-1"


def test_history_is_capped() -> None:
    history = PodcastHistory()
    for i in range(30):
        history.record(f"show-{i}", f"guid-{i}", show_title=f"Show {i}", episode_title=f"Ep {i}")
    assert len(history.episodes) == 15
    assert history.episodes[0].episode_guid == "guid-29"


def test_round_trip_and_missing_file(tmp_path: Path) -> None:
    assert load_history(tmp_path).episodes == []
    history = PodcastHistory(resume_on_launch=True)
    history.record("show-a", "guid-1", show_title="Show A", episode_title="Keep")
    save_history(tmp_path, history)
    loaded = load_history(tmp_path)
    assert loaded.resume_on_launch is True
    assert loaded.last_played is not None and loaded.last_played.episode_title == "Keep"


def test_corrupt_file_reads_empty(tmp_path: Path) -> None:
    (tmp_path / "podcast_history.json").write_text("nope", encoding="utf-8")
    history = load_history(tmp_path)
    assert history.episodes == [] and history.resume_on_launch is False


def test_check_updates_on_startup_defaults_on() -> None:
    assert PodcastHistory().check_updates_on_startup is True


def test_check_updates_on_startup_round_trips(tmp_path: Path) -> None:
    history = PodcastHistory(
        check_updates_on_startup=False, last_update_check="2026-07-16T00:00:00"
    )
    save_history(tmp_path, history)
    loaded = load_history(tmp_path)
    assert loaded.check_updates_on_startup is False
    assert loaded.last_update_check == "2026-07-16T00:00:00"


def test_check_updates_on_startup_missing_from_file_defaults_on(tmp_path: Path) -> None:
    (tmp_path / "podcast_history.json").write_text(
        '{"resume_on_launch": true, "episodes": []}', encoding="utf-8"
    )
    loaded = load_history(tmp_path)
    assert loaded.check_updates_on_startup is True
    assert loaded.last_update_check == ""


def test_sound_enhancements_default_off() -> None:
    history = PodcastHistory()
    assert history.eq_preset == "Flat"
    assert history.compressor_enabled is False


def test_sound_enhancements_round_trip(tmp_path: Path) -> None:
    history = PodcastHistory(eq_preset="Voice Clarity", compressor_enabled=True)
    save_history(tmp_path, history)
    loaded = load_history(tmp_path)
    assert loaded.eq_preset == "Voice Clarity"
    assert loaded.compressor_enabled is True


def test_sound_enhancements_missing_from_file_default_off(tmp_path: Path) -> None:
    (tmp_path / "podcast_history.json").write_text(
        '{"resume_on_launch": true, "episodes": []}', encoding="utf-8"
    )
    loaded = load_history(tmp_path)
    assert loaded.eq_preset == "Flat"
    assert loaded.compressor_enabled is False
