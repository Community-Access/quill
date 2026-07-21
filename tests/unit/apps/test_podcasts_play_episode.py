"""#1192: playing a specific episode chosen from the expandable library tree.

Enter on an episode expanded under its show must play THAT episode (not the
show's next unplayed one).
"""

from __future__ import annotations

from quill.apps.podcasts import PodcastsAppFrame
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary


def test_play_specific_episode_plays_the_chosen_one() -> None:
    library = PodcastLibrary()
    library.add_show(
        PodcastShow(
            id="s1",
            title="My Show",
            feed_url="https://f/x.xml",
            episodes=[
                PodcastEpisode(guid="g1", title="Ep One", audio_url="https://a/1.mp3"),
                PodcastEpisode(guid="g2", title="Ep Two", audio_url="https://a/2.mp3"),
            ],
        )
    )
    played: dict = {}

    class _Ctrl:
        def play_episode(self, **kwargs: object) -> None:
            played.update(kwargs)

    frame = PodcastsAppFrame.__new__(PodcastsAppFrame)
    frame._podcast_library = library
    frame._podcast_controller = _Ctrl()
    frame._announce = lambda *_a, **_k: None

    frame._play_specific_episode("s1", "g2")

    assert played.get("episode_guid") == "g2"
    assert played.get("title") == "Ep Two"
    assert played.get("show_id") == "s1"
