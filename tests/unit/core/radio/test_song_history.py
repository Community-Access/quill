"""Tests for the per-station song log behind Song History.

The rules that matter are the ones that keep the log readable: a poll that sees
the same song six times must produce one entry, a station that talks about
itself must not fill the log, and one busy station must not evict another's.
"""

from pathlib import Path

from quill.core.radio.song_history import (
    MAX_PER_STATION,
    MAX_STATIONS,
    SongHistory,
    SongPlay,
    build_song_background_prompt,
    load_song_history,
    save_song_history,
)

_STRUCTURED = 'title="YOUR SONG",artist="Elton John"'


def test_record_parses_structured_icy_metadata() -> None:
    history = SongHistory()
    song = history.record("s1", "Jazz FM", _STRUCTURED)
    assert song is not None
    assert (song.title, song.artist) == ("YOUR SONG", "Elton John")


def test_record_parses_the_artist_dash_title_shape() -> None:
    history = SongHistory()
    song = history.record("s1", "Jazz FM", "Queen - Bohemian Rhapsody")
    assert song is not None
    assert (song.title, song.artist) == ("Bohemian Rhapsody", "Queen")


def test_repeat_of_the_current_song_folds_into_one_entry() -> None:
    """The title poll fires every 30s, so a 3-minute song is seen ~6 times."""
    history = SongHistory()
    history.record("s1", "Jazz FM", _STRUCTURED, when="2026-08-12T10:00:00+00:00")
    for minute in range(1, 6):
        assert (
            history.record("s1", "Jazz FM", _STRUCTURED, when=f"2026-08-12T10:0{minute}:00+00:00")
            is None
        )
    songs = history.songs_for("s1")
    assert len(songs) == 1
    assert songs[0].play_count == 6
    assert songs[0].first_heard == "2026-08-12T10:00:00+00:00"
    assert songs[0].last_heard == "2026-08-12T10:05:00+00:00"


def test_same_song_again_later_is_a_new_entry() -> None:
    """Only a repeat of the *current* song folds; a re-play an hour on is news."""
    history = SongHistory()
    history.record("s1", "Jazz FM", _STRUCTURED)
    history.record("s1", "Jazz FM", "Queen - Bohemian Rhapsody")
    history.record("s1", "Jazz FM", _STRUCTURED)
    assert len(history.songs_for("s1")) == 3


def test_newest_song_is_first() -> None:
    history = SongHistory()
    history.record("s1", "Jazz FM", "A - One")
    history.record("s1", "Jazz FM", "B - Two")
    assert history.songs_for("s1")[0].title == "Two"


def test_station_name_as_title_is_not_logged() -> None:
    history = SongHistory()
    assert history.record("s1", "Jazz FM", "Jazz FM") is None
    assert history.songs_for("s1") == []


def test_empty_and_placeholder_titles_are_not_logged() -> None:
    history = SongHistory()
    for junk in ("", "   ", "Live", "unknown", "N/A", "Advertisement", "commercial"):
        assert history.record("s1", "Jazz FM", junk) is None
    assert history.songs_for("s1") == []


def test_a_station_without_a_key_is_ignored() -> None:
    history = SongHistory()
    assert history.record("", "Jazz FM", _STRUCTURED) is None


def test_each_station_keeps_its_own_log() -> None:
    history = SongHistory()
    history.record("s1", "Jazz FM", "A - One")
    history.record("s2", "Rock FM", "B - Two")
    assert [s.title for s in history.songs_for("s1")] == ["One"]
    assert [s.title for s in history.songs_for("s2")] == ["Two"]


def test_per_station_cap_evicts_the_oldest_song_only_for_that_station() -> None:
    history = SongHistory()
    history.record("s2", "Rock FM", "Keeper - Kept")
    for index in range(MAX_PER_STATION + 10):
        history.record("s1", "Jazz FM", f"Artist{index} - Song{index}")
    assert len(history.songs_for("s1")) == MAX_PER_STATION
    # Newest kept, oldest dropped...
    assert history.songs_for("s1")[0].title == f"Song{MAX_PER_STATION + 9}"
    assert all(song.title != "Song0" for song in history.songs_for("s1"))
    # ...and the other station is untouched.
    assert [s.title for s in history.songs_for("s2")] == ["Kept"]


def test_station_cap_drops_the_least_recently_active_station() -> None:
    history = SongHistory()
    for index in range(MAX_STATIONS + 5):
        history.record(
            f"s{index}",
            f"Station {index}",
            f"Artist{index} - Song{index}",
            when=f"2026-08-12T10:{index:02d}:00+00:00",
        )
    assert len(history.stations) == MAX_STATIONS
    assert history.find("s0") is None
    assert history.find(f"s{MAX_STATIONS + 4}") is not None


def test_a_renamed_station_keeps_one_log() -> None:
    history = SongHistory()
    history.record("s1", "Jazz FM", "A - One")
    history.record("s1", "Jazz FM (HD)", "B - Two")
    assert len(history.stations) == 1
    assert history.find("s1") is not None
    assert history.find("s1").station_name == "Jazz FM (HD)"


def test_known_stations_lists_most_recently_active_first() -> None:
    history = SongHistory()
    history.record("s1", "Jazz FM", "A - One", when="2026-08-12T10:00:00+00:00")
    history.record("s2", "Rock FM", "B - Two", when="2026-08-12T11:00:00+00:00")
    assert [s.station_key for s in history.known_stations()] == ["s2", "s1"]


def test_known_stations_omits_a_station_with_no_songs() -> None:
    history = SongHistory()
    history.record("s1", "Jazz FM", "Jazz FM")  # noise only
    assert history.known_stations() == []


def test_clear_station_leaves_other_stations() -> None:
    history = SongHistory()
    history.record("s1", "Jazz FM", "A - One")
    history.record("s2", "Rock FM", "B - Two")
    history.clear_station("s1")
    assert history.songs_for("s1") == []
    assert len(history.songs_for("s2")) == 1


def test_clear_all_empties_every_station() -> None:
    history = SongHistory()
    history.record("s1", "Jazz FM", "A - One")
    history.record("s2", "Rock FM", "B - Two")
    history.clear_all()
    assert history.known_stations() == []


def test_display_and_clip_text_prefer_title_by_artist() -> None:
    song = SongPlay(title="Song", artist="Artist", raw='title="Song",artist="Artist"')
    assert song.display() == "Song by Artist"
    # Never the raw broadcast noise -- this is what gets pasted into a search.
    assert song.clip_text() == "Song by Artist"


def test_display_falls_back_when_there_is_no_artist() -> None:
    assert SongPlay(title="Just A Title").display() == "Just A Title"


def test_round_trips_through_disk(tmp_path: Path) -> None:
    history = SongHistory()
    history.record("s1", "Jazz FM", _STRUCTURED, when="2026-08-12T10:00:00+00:00")
    history.record("s1", "Jazz FM", "Queen - Bohemian Rhapsody")
    save_song_history(tmp_path, history)

    reloaded = load_song_history(tmp_path)
    assert [s.title for s in reloaded.songs_for("s1")] == ["Bohemian Rhapsody", "YOUR SONG"]
    assert reloaded.find("s1").station_name == "Jazz FM"


def test_a_missing_store_reads_as_empty(tmp_path: Path) -> None:
    assert load_song_history(tmp_path).known_stations() == []


def test_a_corrupt_store_reads_as_empty_rather_than_raising(tmp_path: Path) -> None:
    (tmp_path / "radio_song_history.json").write_text("{not json", encoding="utf-8")
    assert load_song_history(tmp_path).known_stations() == []


def test_background_prompt_names_the_song_artist_and_station() -> None:
    song = SongPlay(title="Your Song", artist="Elton John")
    prompt = build_song_background_prompt(song, "Jazz FM")
    assert "Your Song" in prompt
    assert "Elton John" in prompt
    assert "Jazz FM" in prompt


def test_background_prompt_asks_the_model_to_admit_uncertainty() -> None:
    """A confident invention about an unknown local band is the failure mode."""
    prompt = build_song_background_prompt(SongPlay(title="Some Demo"), "")
    assert "not confident" in prompt.lower()


def test_background_prompt_omits_an_unknown_artist_cleanly() -> None:
    prompt = build_song_background_prompt(SongPlay(title="Solo Title"), "")
    assert "Artist:" not in prompt
