"""Starting the next episode when one finishes, and saying so either way.

When an episode ends, Cast moves on to the next one in the queue (or the next
in the show). If that one has nothing to play yet -- not downloaded, not
cached, no address -- starting it fails, and saying "Up next" anyway is the
silence a listener reported (Chris Nova, 2026-11-17): the queue stopped and
nothing said why. This says which happened.
"""

from __future__ import annotations

from collections.abc import Callable


def start_next(host: object, show: object, episode: object, up_next: str) -> bool:
    """Start *episode* for the podcasts *host*; say *up_next* if it started, why if not.

    *host* is the PodcastsMixin: its ``_podcast_controller``,
    ``_podcast_library`` and ``_announce``.
    """
    from quill.ui.podcasts.show_actions import start_episode_playback

    announce: Callable[[str], None] = getattr(host, "_announce")  # noqa: B009
    started = start_episode_playback(
        getattr(host, "_podcast_controller"),  # noqa: B009
        getattr(host, "_podcast_library"),  # noqa: B009
        show,
        episode,
    )
    title = getattr(episode, "title", "")
    if started is False:
        announce(
            f"Could not start the next episode, {title}. "
            "It has nothing to play yet; download it or check its address."
        )
        return False
    announce(up_next)
    return True
