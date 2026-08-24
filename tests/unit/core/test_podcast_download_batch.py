"""The counting behind a bounded Download All.

The sentence is the feature here as much as the cap is: a bulk action that
says one number hides what happened to everything else, so each case below
asserts on the words a listener actually hears.
"""

from __future__ import annotations

from quill.core.podcasts.download_batch import BATCH_CAP, plan_download_all
from quill.core.podcasts.models import PodcastEpisode


def _episode(guid: str, *, downloaded: bool = False) -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title=f"Episode {guid}",
        audio_url=f"https://example.com/{guid}.mp3",
        published="2026-08-01T00:00:00",
        downloaded_path=f"C:/downloads/{guid}.mp3" if downloaded else "",
    )


def _have(episode: PodcastEpisode) -> bool:
    return bool(episode.downloaded_path)


def test_everything_eligible_starts_when_under_the_cap() -> None:
    batch = plan_download_all([_episode("a"), _episode("b")], already_have=_have)
    assert [e.guid for e in batch.started] == ["a", "b"]
    assert (batch.skipped, batch.deferred, batch.eligible) == (0, 0, 2)
    assert batch.sentence("My Show") == "Download All for My Show: 2 eligible, 2 started."


def test_over_the_cap_defers_the_remainder_in_feed_order() -> None:
    episodes = [_episode(f"e{n}") for n in range(BATCH_CAP + 3)]
    batch = plan_download_all(episodes, already_have=_have)
    assert len(batch.started) == BATCH_CAP
    assert batch.started[0].guid == "e0"
    assert batch.deferred == 3
    assert "3 deferred" in batch.sentence("My Show")


def test_already_downloaded_or_queued_episodes_are_counted_as_skipped() -> None:
    episodes = [_episode("a", downloaded=True), _episode("b"), _episode("c", downloaded=True)]
    batch = plan_download_all(episodes, already_have=_have)
    assert [e.guid for e in batch.started] == ["b"]
    assert batch.skipped == 2
    assert "2 skipped as already downloaded or in progress" in batch.sentence("My Show")


def test_nothing_eligible_says_why_rather_than_saying_a_zero() -> None:
    batch = plan_download_all([_episode("a", downloaded=True)], already_have=_have)
    assert batch.sentence("My Show") == (
        "Nothing to download for My Show: all 1 episode(s) are already downloaded or in progress."
    )


def test_a_show_with_no_episodes_says_so() -> None:
    batch = plan_download_all([], already_have=_have)
    assert batch.sentence("") == "Nothing to download for this show: it has no episodes yet."


def test_the_cap_is_configurable_for_a_caller_that_needs_a_smaller_batch() -> None:
    batch = plan_download_all([_episode(f"e{n}") for n in range(5)], already_have=_have, cap=2)
    assert (len(batch.started), batch.deferred) == (2, 3)
