"""What one successful (or failed) feed read does to a podcast's record.

The refresh in ``quill/ui/podcasts/feed_refresh.py`` used to do all of this
inline, between a fetch and a dozen UI calls, which is why the two worst bugs
in the 2026-10-04 Downcast import test lived there unnoticed (check.md):

* **The first read of a show was treated as news** (bug 2). An imported show
  starts with no episodes, so everything in its feed counted as "arrived":
  360,316 "new" episodes for one 1,306-show file, all handed to Episode
  Filters, routing and the new-episode notice -- and "last published" was
  stamped with the time of the check, so a show that stopped in 2005 read as
  "just now" and gone-quiet could never fire.
* **An empty feed counted as healthy** (bug 3).

So the decisions live here, wx-free and tested, and the refresh routes what
this returns. Three rules:

* **A show's first read is a starting point.** When the podcast has no
  episodes yet (and its last read was not an empty feed), nothing is "new":
  no notice, no routing, no filters. What it gets instead is exactly what its
  own back-catalogue setting (``backfill_mode``) asks for -- the same one-off
  that following it through Add Podcast applies.
* **"Last published" is the newest episode's own date**, written on every
  successful read, so a library stamped from the clock by an older Cast heals
  on its next check.
* **A "not modified" answer is a success with nothing new** (bug 9).

wx-free, strict-typed.
"""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from datetime import datetime

from quill.core.podcasts import check_state, feed_problems
from quill.core.podcasts.feed_reader import FeedInfo, FetchNotes
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary, merge_episodes

__all__ = [
    "FeedRead",
    "apply_backfill",
    "notes_for",
    "record_failure",
    "record_success",
]


@dataclass(slots=True)
class FeedRead:
    """What a successful read changed, for the refresh to act on."""

    #: Episodes that are genuinely new: these are filtered, routed and
    #: announced. Empty on a first read and on a "not modified" answer.
    arrived: list[PodcastEpisode] = field(default_factory=list)
    #: Guids the publisher re-published (a later date on a known guid).
    republished: list[str] = field(default_factory=list)
    #: This was the show's first read: a starting point, not news.
    baseline: bool = False
    #: How many back-catalogue episodes the first read marked for download.
    backfilled: int = 0
    not_modified: bool = False
    #: The feed answered but holds no episodes.
    empty: bool = False


def notes_for(library: PodcastLibrary, show: PodcastShow) -> FetchNotes:
    """The fetch notes to send: this podcast's stored validators, if any."""
    etag, modified = check_state.validators(library, show)
    return FetchNotes(etag=etag, last_modified=modified)


def apply_backfill(library: PodcastLibrary, show: PodcastShow) -> int:
    """Mark what this podcast's back-catalogue setting asks for; returns how many.

    A one-off at the moment a show is first read. It marks episodes for
    download and never plays, queues or deletes anything, and a podcast whose
    setting says "nothing" (the default) gets nothing.
    """
    try:
        from quill.core.podcasts.show_policy import backfill_episodes

        wanted = backfill_episodes(library, show, show.episodes)
    except Exception:  # noqa: BLE001 - a backfill must never break a refresh
        return 0
    for episode in wanted:
        if not episode.downloaded_path and episode.mode_override != "stream":
            episode.mode_override = "download"
    return len(wanted)


def _heal_title(show: PodcastShow) -> None:
    """Undo a second layer of escaping left in an older import's title.

    Downcast escapes titles twice, so shows imported before the OPML reader
    learned that carry a literal ``We&apos;re Alive`` -- read aloud as
    "ampersand a p o s semicolon" on every row. A refresh never renames a show,
    so without this they kept it for good (check.md bug 17).
    """
    title = show.title or ""
    if "&" in title and ";" in title:
        healed = html.unescape(title).strip()
        if healed and healed != title:
            show.title = healed


def record_success(
    library: PodcastLibrary,
    show: PodcastShow,
    info: FeedInfo,
    notes: FetchNotes | None = None,
    *,
    now: datetime | None = None,
) -> FeedRead:
    """Merge *info* into *show* and write down what the read found."""
    notes = notes if notes is not None else FetchNotes()
    _heal_title(show)
    if info.not_modified:
        # Nothing changed, so nothing about the feed's shape changed either;
        # only the check itself is recorded.
        check_state.record_success(library, show, now=now)
        return FeedRead(not_modified=True, empty=check_state.is_empty(library, show))
    # The first read after Replace Feed is a starting point too: the new
    # host's feed has its own episode ids, and its back catalogue is not news.
    rebased = check_state.take_rebase(library, show)
    baseline = rebased or (not show.episodes and not check_state.is_empty(library, show))
    known = {episode.guid for episode in show.episodes}
    known_titles = {episode.title.strip().casefold() for episode in show.episodes}
    republished: list[str] = []
    if not info.tags.is_empty:
        show.tags = info.tags
    twins = set(check_state.twin_guids(library, show))
    merge_episodes(show, info.episodes, republished=republished)
    arrived = [episode for episode in show.episodes if episode.guid not in known]
    if rebased and arrived:
        # The same episodes under the new host's ids: keep the ones the show
        # already has (with their play state), not a second copy of each --
        # and remember those ids, so the next read does not add them back.
        found = {
            episode.guid for episode in arrived if episode.title.strip().casefold() in known_titles
        }
        check_state.add_twin_guids(library, show, found)
        twins |= found
    if twins and arrived:
        show.episodes = [e for e in show.episodes if e.guid in known or e.guid not in twins]
        arrived = [episode for episode in arrived if episode.guid not in twins]
    backfilled = apply_backfill(library, show) if baseline and arrived else 0
    check_state.record_success(
        library,
        show,
        new_episodes=0 if baseline else len(arrived),
        now=now,
        published=check_state.newest_episode_date(show),
    )
    empty = not info.episodes
    check_state.record_shape(
        library,
        show,
        empty=empty,
        truncated=info.truncated or notes.truncated,
        read_securely=notes.read_securely,
    )
    check_state.record_validators(library, show, notes.etag, notes.last_modified)
    check_state.record_hint(library, show, int(info.hint_minutes or 0), str(info.hint_words or ""))
    return FeedRead(
        arrived=[] if baseline else arrived,
        republished=[] if baseline else republished,
        baseline=baseline,
        backfilled=backfilled,
        empty=empty,
    )


def record_failure(
    library: PodcastLibrary,
    show: PodcastShow,
    error: BaseException,
    *,
    had_credentials: bool = False,
    now: datetime | None = None,
) -> feed_problems.Problem:
    """Write down a failed read with its plain reason; returns the problem."""
    problem = feed_problems.classify(error, had_credentials=had_credentials)
    check_state.record_failure(library, show, now=now, reason=problem.sentence, kind=problem.kind)
    return problem
