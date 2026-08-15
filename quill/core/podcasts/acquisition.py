"""Auto-download: the acquisition policy (1.1.0).

Through 1.0.x Cast had a retention policy and no acquisition policy. It knew
what to throw away and nothing about what to fetch, so an episode arrived on
disk only because somebody asked for it -- or, with Always Sync, because
*everything* did. There was no "keep the newest three ready".

That gap sits under several others. An auto-queued show wants its episodes
downloaded; a queue-expiration limit is only meaningful if things arrive
without being asked for; "subscribe and press play" is the difference between
a podcast app and a feed reader.

This module decides *which* episodes should be on disk. It never downloads
anything itself -- it returns the episodes a caller should enqueue, so the
policy is testable without a network, a thread, or a file.

wx-free, strict-typed.
"""

from __future__ import annotations

import heapq

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary


def _newest(episodes: list[PodcastEpisode], count: int) -> list[PodcastEpisode]:
    """The *count* newest episodes (``count < 0`` = all of them), newest first.

    ``published`` is the feed's own ISO-ish string; ordering it as text is
    right for ISO 8601 and harmless for anything else, since a feed with
    unsortable dates has no better ordering to offer anyway.

    ``nlargest`` rather than a full sort for the usual "newest three" case:
    this runs for every show on every refresh, and over a very large library
    that is the difference between a linear pass and sorting a few hundred
    thousand episodes to look at nine of them. (Earshot hit exactly this --
    resolving every episode of every imported show just to pick the few most
    recent ones was one of the memory spikes that made large OPML imports
    unusable there.)
    """
    key = lambda episode: (episode.published, episode.title)  # noqa: E731
    if count < 0 or count >= len(episodes):
        return sorted(episodes, key=key, reverse=True)
    return heapq.nlargest(count, episodes, key=key)


def episodes_to_auto_download(
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    queued_guids: frozenset[str] = frozenset(),
    inbox_guids: frozenset[str] = frozenset(),
) -> list[PodcastEpisode]:
    """Which of *show*'s episodes the auto-download policy wants on disk.

    Newest ``auto_download_count`` episodes (``-1`` = the whole catalog,
    ``0`` = none), plus -- whatever that count is -- anything queued or in the
    Inbox when the matching toggle is on. Already-downloaded episodes and
    stream-only overrides are excluded, so this is safe to call on every
    refresh: it returns work, not intentions.

    Callers pass the guids already in the Play Queue / Inbox rather than
    having this module recompute them, because the caller usually just built
    those sets for its own reasons.
    """
    settings = library.effective_settings(show)
    if settings.playback_mode != "download" and not show.is_local:
        # A stream-by-default show still honours a per-episode download
        # override, but nothing auto-downloads for it: the listener asked for
        # streaming, and filling their disk anyway would be a surprise.
        return []
    count = settings.effective_auto_download_count
    wanted: list[PodcastEpisode] = []
    if count != 0:
        wanted.extend(_newest(show.episodes, count))
    if settings.auto_download_queued and queued_guids:
        wanted.extend(e for e in show.episodes if e.guid in queued_guids)
    # Inbox membership is a mode, not a flag: under opt-out, an unmarked show
    # *is* in the Inbox. Asked of one helper so auto-download can never
    # disagree with what the Inbox itself shows.
    from quill.core.podcasts.inbox import in_inbox

    if settings.auto_download_inbox and inbox_guids and in_inbox(library, show):
        wanted.extend(e for e in show.episodes if e.guid in inbox_guids)
    seen: set[str] = set()
    result: list[PodcastEpisode] = []
    for episode in wanted:
        if episode.guid in seen:
            continue
        seen.add(episode.guid)
        if episode.downloaded_path or episode.mode_override == "stream":
            continue
        if not episode.audio_url:
            continue
        result.append(episode)
    return result


def route_new_episodes(
    library: PodcastLibrary, show: PodcastShow, new_episodes: list[PodcastEpisode]
) -> int:
    """Auto-Queue: put a show's brand-new episodes into the Play Queue.

    Returns how many were queued. Called with exactly the episodes a refresh
    reported as new, so a show that has been auto-queueing for a year never
    re-queues its back catalog. An episode already queued (or already played)
    is skipped.
    """
    if not show.auto_queue:
        return 0
    queued = 0
    for episode in new_episodes:
        if episode.played:
            continue
        if library.queue_episode(show.id, episode.guid):
            queued += 1
    return queued


__all__ = ["episodes_to_auto_download", "route_new_episodes"]
