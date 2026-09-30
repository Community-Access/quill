"""Saying what a delete deletes (ear.md R13)."""

from __future__ import annotations

from quill.core.podcasts.delete_copy import confirm_message, forget_position, is_cast_copy
from quill.core.podcasts.models import PodcastEpisode, PodcastShow


def _show(local: bool) -> PodcastShow:
    return PodcastShow(
        id="s1", title="Show", feed_url="" if local else "https://e/f.xml", is_local=local
    )


def _episode(position: int = 0) -> PodcastEpisode:
    return PodcastEpisode(
        guid="e1",
        title="Interview with Ada",
        audio_url="",
        published="2026-07-01T00:00:00",
        position_ms=position,
    )


def test_a_local_file_is_promised_its_original_survives() -> None:
    """Somebody who cannot see a file manager has no way to check."""
    message = confirm_message(_show(True), _episode())
    assert "Cast's copy" in message
    assert "original file stays where it was" in message


def test_a_downloaded_episode_is_told_it_can_come_back() -> None:
    message = confirm_message(_show(False), _episode())
    assert "downloaded copy" in message
    assert "downloaded again" in message
    assert "original file" not in message


def test_the_episode_is_named_in_both() -> None:
    """A confirmation that says "this episode" has to be taken on trust."""
    for local in (True, False):
        assert "Interview with Ada" in confirm_message(_show(local), _episode())


def test_an_untitled_episode_still_reads_as_a_sentence() -> None:
    episode = _episode()
    episode.title = ""
    assert "this episode" in confirm_message(_show(True), episode)


def test_only_a_local_show_counts_as_a_cast_copy() -> None:
    assert is_cast_copy(_show(True)) is True
    assert is_cast_copy(_show(False)) is False


def test_the_resume_point_is_cleared_and_reported() -> None:
    """A position into a file that no longer exists is a promise it cannot keep."""
    episode = _episode(position=600_000)
    assert forget_position(episode) is True
    assert episode.position_ms == 0
    assert episode.position_updated_at == ""


def test_clearing_a_position_that_was_not_set_says_so() -> None:
    assert forget_position(_episode()) is False
