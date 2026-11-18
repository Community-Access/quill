"""Starting the next episode when one finishes, and saying so either way.

When an episode ends, Cast moves on to the next one in the queue (or the next
in the show). If that one has nothing to play yet -- not downloaded, not
cached, no address -- starting it fails, and saying "Up next" anyway is the
silence a listener reported (Chris Nova, 2026-11-17): the queue stopped and
nothing said why. This says which happened.
"""

from __future__ import annotations

from collections.abc import Callable


def start_next(
    host: object, show: object, episode: object, up_next: str, *, from_queue: bool = False
) -> bool:
    """Start *episode* for the podcasts *host*; say *up_next* if it started, why if not.

    *host* is the PodcastsMixin: its ``_podcast_controller``,
    ``_podcast_library`` and ``_announce``. With *from_queue*, an episode that
    cannot start is passed over for the next one in the queue that can, so one
    episode with nothing to play does not stop the run (Chris Nova,
    2026-11-18); each one passed over is named, and stays in the queue.
    """
    from quill.core.podcasts.queue_steps import step_next
    from quill.ui.podcasts.show_actions import start_episode_playback

    announce: Callable[[str], None] = getattr(host, "_announce")  # noqa: B009
    library = getattr(host, "_podcast_library")  # noqa: B009
    controller = getattr(host, "_podcast_controller")  # noqa: B009
    skipped: list[str] = []
    attempts = max(1, len(getattr(library, "queue", ()))) if from_queue else 1
    for _ in range(attempts):
        if start_episode_playback(controller, library, show, episode) is not False:
            if skipped:
                up_next = (
                    f"Could not start {', '.join(skipped)}: nothing to play yet. "
                    f"Playing {getattr(episode, 'title', '')} instead."
                )
            announce(up_next)
            return True
        skipped.append(getattr(episode, "title", ""))
        if len(skipped) >= attempts:
            break
        step = step_next(library, getattr(show, "id", ""), getattr(episode, "guid", ""))
        if step.kind != "play":
            break
        show, episode = step.show, step.episode
    announce(
        f"Could not start the next episode, {', '.join(skipped)}. "
        "It has nothing to play yet; download it or check its address."
    )
    return False
