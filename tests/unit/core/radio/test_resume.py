"""Tests for remembering where you stopped in a streamed recording."""

from __future__ import annotations

import pytest

from quill.core.radio.resume import (
    END_MARGIN_MS,
    MAX_ENTRIES,
    MIN_RESUME_MS,
    ResumeStore,
    spoken_resume,
    stream_identity,
)


@pytest.fixture
def store(tmp_path) -> ResumeStore:
    return ResumeStore(tmp_path)


# --- identity ------------------------------------------------------------------


def test_scheme_and_case_do_not_change_identity() -> None:
    assert stream_identity("https://Archive.org/download/x/1.mp3") == stream_identity(
        "http://archive.org/download/x/1.mp3"
    )


def test_a_session_token_does_not_change_identity() -> None:
    # The case that would otherwise lose every position silently: a CDN hands
    # out a fresh token per play, so yesterday's entry would never match.
    first = stream_identity("https://cdn.example/ep1.mp3?jwt_auth=AAA&quality=high")
    second = stream_identity("https://cdn.example/ep1.mp3?jwt_auth=BBB&quality=high")
    assert first == second
    assert "quality=high" in first, "a real parameter is part of the identity"


def test_tunein_and_archive_session_parameters_are_stripped() -> None:
    a = stream_identity("https://x.example/s.mp3?aw_0_1st.skey=1&aw_0_1st.playerid=RadioTime")
    b = stream_identity("https://x.example/s.mp3?aw_0_1st.skey=2&aw_0_1st.playerid=RadioTime")
    assert a == b


def test_a_different_recording_is_a_different_identity() -> None:
    assert stream_identity("https://a.example/1.mp3") != stream_identity("https://a.example/2.mp3")


def test_default_ports_do_not_change_identity_but_others_do() -> None:
    assert stream_identity("https://a.example:443/x") == stream_identity("https://a.example/x")
    assert stream_identity("http://a.example:8000/x") != stream_identity("http://a.example/x")


def test_a_blank_url_has_no_identity() -> None:
    assert stream_identity("") == ""
    assert stream_identity("   ") == ""


# --- remembering ---------------------------------------------------------------


def test_a_position_round_trips(store) -> None:
    store.remember("https://a.example/1.mp3", 120_000, duration_ms=3_600_000)
    point = store.position_for("https://a.example/1.mp3")
    assert point is not None
    assert point.position_ms == 120_000
    assert point.duration_ms == 3_600_000
    assert 0 < point.fraction < 1


def test_a_position_survives_a_new_session_token(store) -> None:
    store.remember("https://cdn.example/ep.mp3?jwt=AAA", 300_000, duration_ms=1_800_000)
    point = store.position_for("https://cdn.example/ep.mp3?jwt=ZZZ")
    assert point is not None and point.position_ms == 300_000


def test_the_beginning_is_not_a_position(store) -> None:
    # "Four seconds in" is the start; a resume prompt there is pure noise.
    store.remember("https://a.example/1.mp3", MIN_RESUME_MS - 1, duration_ms=600_000)
    assert store.position_for("https://a.example/1.mp3") is None


def test_saving_the_beginning_clears_an_earlier_position(store) -> None:
    url = "https://a.example/1.mp3"
    store.remember(url, 200_000, duration_ms=600_000)
    store.remember(url, 1_000, duration_ms=600_000)
    assert store.position_for(url) is None


def test_finishing_clears_the_position(store) -> None:
    # Replaying a finished episode must start at the start, not the credits.
    url = "https://a.example/1.mp3"
    store.remember(url, 200_000, duration_ms=600_000)
    store.remember(url, 600_000 - (END_MARGIN_MS // 2), duration_ms=600_000)
    assert store.position_for(url) is None


def test_a_position_with_no_known_duration_is_still_kept(store) -> None:
    store.remember("https://a.example/1.mp3", 90_000)
    point = store.position_for("https://a.example/1.mp3")
    assert point is not None and point.duration_ms == 0 and point.fraction == 0.0


def test_forget_and_clear(store) -> None:
    store.remember("https://a.example/1.mp3", 90_000)
    store.remember("https://a.example/2.mp3", 90_000)
    store.forget("https://a.example/1.mp3")
    assert store.position_for("https://a.example/1.mp3") is None
    assert store.position_for("https://a.example/2.mp3") is not None
    store.clear()
    assert store.count() == 0


def test_the_store_is_bounded_and_drops_the_oldest(store) -> None:
    for n in range(MAX_ENTRIES + 25):
        store.remember(f"https://a.example/{n}.mp3", 60_000 + n)
    assert store.count() == MAX_ENTRIES
    assert store.position_for("https://a.example/0.mp3") is None, "oldest fell off"
    assert store.position_for(f"https://a.example/{MAX_ENTRIES + 24}.mp3") is not None


def test_an_unknown_recording_has_no_position(store) -> None:
    assert store.position_for("https://never.example/x.mp3") is None


def test_a_corrupt_file_reads_as_no_positions(store, tmp_path) -> None:
    store.remember("https://a.example/1.mp3", 90_000)
    (tmp_path / "radio-resume.json").write_text("{not json", encoding="utf-8")
    assert store.position_for("https://a.example/1.mp3") is None
    store.remember("https://a.example/1.mp3", 90_000)  # and it recovers


def test_a_blank_url_is_ignored_rather_than_stored(store) -> None:
    store.remember("", 90_000)
    assert store.count() == 0


# --- speech --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("ms", "expected"),
    [
        (0, "0 seconds"),
        (8_000, "8 seconds"),
        (68_000, "1 minute 8 seconds"),
        (728_000, "12 minutes 8 seconds"),
        (3_600_000, "1 hour"),
        (5_425_000, "1 hour 30 minutes 25 seconds"),
    ],
)
def test_spoken_resume_is_words_not_a_clock(ms, expected) -> None:
    # "12:08" read aloud is an ambiguous pair of numbers.
    assert spoken_resume(ms) == expected
