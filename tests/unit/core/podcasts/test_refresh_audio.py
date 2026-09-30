"""Refresh Episode Audio (ear.md R3): the file is replaced, the listening is not.

The one rule worth a test each way: a refresh changes where the audio comes from
and **never** what you did with it. The alternative a listener has today is
unsubscribing and re-subscribing, which throws away every position in the show to
fix one episode -- so if this verb loses a position, it has no reason to exist.
"""

from __future__ import annotations

from quill.core.podcasts import refresh_audio
from quill.core.podcasts.models import PodcastEpisode, PodcastShow


def _episode(**kwargs) -> PodcastEpisode:
    base = {
        "guid": "g1",
        "title": "Episode One",
        "audio_url": "https://old.example/a.mp3",
        "published": "2026-09-01T00:00:00",
    }
    base.update(kwargs)
    return PodcastEpisode(**base)


def _show(**kwargs) -> PodcastShow:
    base = {"id": "s1", "title": "The Daily", "feed_url": "https://e/f.xml"}
    base.update(kwargs)
    return PodcastShow(**base)


# -- what a refresh is for ---------------------------------------------------- #


def test_a_moved_address_is_taken_from_the_feed() -> None:
    episode = _episode(downloaded_path="C:/d/old.mp3")
    plan = refresh_audio.plan_for(_show(), episode, "https://new.example/a.mp3")

    assert plan.ok
    assert plan.moved
    assert plan.new_url == "https://new.example/a.mp3"
    assert plan.delete_path == "C:/d/old.mp3"
    assert "moved to a new address" in plan.message


def test_an_unchanged_address_still_refreshes_because_the_file_may_be_the_problem() -> None:
    """The common case is not a moved file, it is a bad one -- truncated, or
    silent. Answering "nothing to do" would refuse the repair asked for."""
    plan = refresh_audio.plan_for(_show(), _episode(), "https://old.example/a.mp3")

    assert plan.ok
    assert not plan.moved
    assert "same address" in plan.message
    assert "in case the file itself is the problem" in plan.message


def test_the_listening_survives_a_refresh() -> None:
    """The whole reason this verb beats unsubscribing and re-subscribing."""
    episode = _episode(
        downloaded_path="C:/d/old.mp3",
        played=True,
        position_ms=612_000,
        intro_skipped=True,
        speed_override=1.5,
    )
    plan = refresh_audio.plan_for(_show(), episode, "https://new.example/a.mp3")
    assert refresh_audio.apply_plan(episode, plan)

    assert episode.audio_url == "https://new.example/a.mp3"
    assert episode.downloaded_path == ""
    assert episode.played is True
    assert episode.position_ms == 612_000
    assert episode.intro_skipped is True
    assert episode.speed_override == 1.5


def test_the_stored_hash_of_the_discarded_file_is_forgotten() -> None:
    """It described the file being thrown away. Keeping it would make the
    replacement look like a duplicate of its own predecessor."""
    episode = _episode(downloaded_path="C:/d/old.mp3", content_hash="abc123")
    plan = refresh_audio.plan_for(_show(), episode, "https://new.example/a.mp3")
    refresh_audio.apply_plan(episode, plan)
    assert episode.content_hash == ""


def test_the_record_stops_claiming_the_file_before_the_download_starts() -> None:
    """A failed download then leaves an episode that will stream, rather than
    one claiming a file it no longer has."""
    episode = _episode(downloaded_path="C:/d/old.mp3")
    plan = refresh_audio.plan_for(_show(), episode, "https://new.example/a.mp3")
    refresh_audio.apply_plan(episode, plan)
    assert episode.downloaded_path == ""


# -- the two refusals, each with its own sentence ----------------------------- #


def test_a_local_file_says_your_file_is_where_you_put_it() -> None:
    plan = refresh_audio.plan_for(
        _show(feed_url="", is_local=True), _episode(audio_url=""), "https://e/a.mp3"
    )
    assert not plan.ok
    assert "your own files" in plan.message
    assert "where you put it" in plan.message


def test_an_episode_the_feed_no_longer_lists_says_so_and_keeps_the_download() -> None:
    """A different situation from a changed address, and it wants a different
    answer from the listener."""
    episode = _episode(downloaded_path="C:/d/old.mp3")
    plan = refresh_audio.plan_for(_show(), episode, "")

    assert not plan.ok
    assert "no longer lists" in plan.message
    assert "left alone" in plan.message
    assert refresh_audio.apply_plan(episode, plan) is False
    assert episode.downloaded_path == "C:/d/old.mp3"


def test_a_show_with_no_feed_address_is_refused_by_name() -> None:
    plan = refresh_audio.plan_for(_show(feed_url=""), _episode(), "https://e/a.mp3")
    assert not plan.ok
    assert "no feed address" in plan.message


# -- the confirmation names the one cost -------------------------------------- #


def test_the_confirmation_names_the_download_because_somebody_may_be_metered() -> None:
    plan = refresh_audio.plan_for(
        _show(), _episode(downloaded_path="C:/d/old.mp3"), "https://new.example/a.mp3"
    )
    text = refresh_audio.confirm_message(plan)
    assert "will be deleted first" in text
    assert text.endswith("Refresh it now?")


def test_nothing_downloaded_says_there_is_nothing_to_delete() -> None:
    plan = refresh_audio.plan_for(_show(), _episode(), "https://new.example/a.mp3")
    assert "nothing to delete" in refresh_audio.confirm_message(plan)


def test_a_refused_plan_confirms_nothing_and_asks_nothing() -> None:
    plan = refresh_audio.plan_for(_show(), _episode(), "")
    text = refresh_audio.confirm_message(plan)
    assert "?" not in text.split("\n")[-1] or not text.endswith("Refresh it now?")


def test_removable_is_none_when_the_file_is_not_really_there(tmp_path) -> None:
    plan = refresh_audio.plan_for(
        _show(), _episode(downloaded_path=str(tmp_path / "gone.mp3")), "https://new/a.mp3"
    )
    assert refresh_audio.removable(plan) is None

    real = tmp_path / "there.mp3"
    real.write_bytes(b"\x00")
    plan2 = refresh_audio.plan_for(
        _show(), _episode(downloaded_path=str(real)), "https://new/a.mp3"
    )
    assert refresh_audio.removable(plan2) == real
