"""ear.md R8: a listener's name for a podcast or an episode survives a refresh."""

from __future__ import annotations

from quill.core.podcasts.custom_names import rename
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.subscriptions import merge_episodes


def _episode(title: str) -> PodcastEpisode:
    return PodcastEpisode(guid="g", title=title, audio_url="https://x.invalid/a.mp3")


def test_an_episode_rename_survives_the_next_refresh() -> None:
    show = PodcastShow(id="s", title="Show", feed_url="https://x.invalid/f")
    show.episodes.append(_episode("Ep 412: Untitled"))
    said = rename(show.episodes[0], "The one about braille")
    assert said.startswith("Renamed to The one about braille.")
    merge_episodes(show, [_episode("Ep 412: A Better Title")])
    episode = show.episodes[0]
    assert episode.title == "The one about braille"
    assert episode.feed_title == "Ep 412: A Better Title"


def test_clearing_the_name_puts_the_feeds_back() -> None:
    show = PodcastShow(id="s", title="The Daily Pod", feed_url="")
    rename(show, "News")
    assert (show.title, show.feed_title) == ("News", "The Daily Pod")
    assert rename(show, "") == "Back to the feed's own name, The Daily Pod."
    assert (show.title, show.feed_title) == ("The Daily Pod", "")
    assert rename(show, "") == ""


def test_the_feed_name_round_trips_through_the_library_file() -> None:
    show = PodcastShow(id="s", title="News", feed_title="The Daily Pod", feed_url="")
    again = PodcastShow.from_dict(show.to_dict())
    assert again is not None and again.feed_title == "The Daily Pod"
    plain = PodcastShow(id="s", title="News", feed_url="")
    assert "feed_title" not in plain.to_dict()
