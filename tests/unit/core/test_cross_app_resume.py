"""11.11: an episode started in one app picks up in the other.

The rule that carries the feature is *last write wins, not furthest wins*.
Furthest-wins sounds generous and overrules the listener: somebody who
skipped to the outro to check something and came back has decided where they
are, and an app that dragged them forward again would be arguing with them.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.podcasts import cross_app_resume, radio_listens
from quill.core.podcasts.cross_app_resume import Place


def test_the_later_decision_wins_even_when_it_is_earlier_in_the_episode() -> None:
    early_but_newer = Place(position_ms=300_000, updated_at=200.0, app="cast")
    far_but_older = Place(position_ms=3_000_000, updated_at=100.0, app="radio")
    assert cross_app_resume.better_place(far_but_older, early_but_newer) is early_but_newer


def test_a_finish_is_sticky_whichever_side_is_newer() -> None:
    finished = Place(position_ms=0, updated_at=100.0, finished=True, app="cast")
    later_place = Place(position_ms=90_000, updated_at=500.0, app="radio")
    chosen = cross_app_resume.better_place(later_place, finished)
    assert chosen is finished
    assert cross_app_resume.should_seek(0, chosen) is False


def test_no_opinion_is_not_the_same_as_position_zero() -> None:
    """A fresh install has no view on an episode the other machine is inside."""
    shared = Place(position_ms=600_000, updated_at=100.0, app="radio")
    assert cross_app_resume.better_place(None, shared) is shared


def test_two_places_too_near_the_start_are_not_places_at_all() -> None:
    assert (
        cross_app_resume.better_place(
            Place(position_ms=2_000, updated_at=100.0),
            Place(position_ms=1_000, updated_at=200.0),
        )
        is None
    )


def test_nothing_at_all_answers_none() -> None:
    assert cross_app_resume.better_place(None, None) is None


def test_a_seek_is_refused_when_playback_is_already_there() -> None:
    """A two-second seek is noise, and on a stream it costs a rebuffer."""
    place = Place(position_ms=600_000, updated_at=100.0, app="radio")
    assert cross_app_resume.should_seek(600_000, place) is False
    assert cross_app_resume.should_seek(599_000, place) is False
    assert cross_app_resume.should_seek(500_000, place) is True


def test_the_sentence_only_explains_a_cross_app_jump() -> None:
    from_radio = Place(position_ms=3_723_000, updated_at=100.0, app="radio")
    assert cross_app_resume.describe_resume(from_radio, this_app="cast") == (
        "Picking up where you left off in Quill Radio, at 1 hour 2 minutes 3 seconds."
    )
    assert cross_app_resume.describe_resume(from_radio, this_app="radio") == ""


def test_a_finish_is_never_narrated_as_a_resume() -> None:
    done = Place(position_ms=0, updated_at=100.0, finished=True, app="radio")
    assert cross_app_resume.describe_resume(done, this_app="cast") == ""


# -- the shared store ------------------------------------------------------------


def test_a_place_written_by_either_app_is_read_back_by_the_other(tmp_path: Path) -> None:
    radio_listens.record_listen(
        tmp_path,
        feed_url="https://example.com/feed.xml",
        audio_url="https://example.com/ep1.mp3",
        title="Episode 1",
        position_ms=600_000,
        app="cast",
    )
    place = radio_listens.latest_place(tmp_path, "https://example.com/ep1.mp3")
    assert place is not None
    assert place.position_ms == 600_000
    assert place.app == "cast"
    assert place.finished is False
    assert place.updated_at > 0


def test_the_latest_word_replaces_the_earlier_one(tmp_path: Path) -> None:
    for position, app in ((100_000, "radio"), (900_000, "cast")):
        radio_listens.record_listen(
            tmp_path,
            feed_url="https://example.com/feed.xml",
            audio_url="https://example.com/ep1.mp3",
            position_ms=position,
            app=app,
        )
    place = radio_listens.latest_place(tmp_path, "https://example.com/ep1.mp3")
    assert place is not None
    assert (place.position_ms, place.app) == (900_000, "cast")


def test_an_episode_nobody_has_played_has_no_shared_place(tmp_path: Path) -> None:
    assert radio_listens.latest_place(tmp_path, "https://example.com/never.mp3") is None
    assert radio_listens.latest_place(tmp_path, "") is None


def test_an_old_record_without_an_app_reads_as_radios(tmp_path: Path) -> None:
    """Files written before 11.11 carry no app field; they are all Radio's."""
    import json

    (tmp_path / "radio-listens.json").write_text(
        json.dumps([
            {
                "feed": "f",
                "audio": "https://example.com/ep1.mp3",
                "position_ms": 60_000,
                "finished": False,
                "at": 1.0,
            }
        ]),
        encoding="utf-8",
    )
    place = radio_listens.latest_place(tmp_path, "https://example.com/ep1.mp3")
    assert place is not None and place.app == "radio"


def test_a_finish_round_trips_as_a_finish(tmp_path: Path) -> None:
    radio_listens.record_listen(
        tmp_path,
        feed_url="f",
        audio_url="https://example.com/ep1.mp3",
        position_ms=0,
        finished=True,
        app="cast",
    )
    place = radio_listens.latest_place(tmp_path, "https://example.com/ep1.mp3")
    assert place is not None and place.finished is True
    assert place.is_a_place is True, "a finish is a place even at position zero"
