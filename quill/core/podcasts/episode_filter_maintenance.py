"""Episode Filters against the library: scopes, exemptions, refresh, and reach-back.

:mod:`quill.core.podcasts.models_filters` is the shape,
:mod:`quill.core.podcasts.episode_filters` is the decision, and this is the
part that knows about a *library*: where a podcast's rules are kept, which of
its surfaces honour them, which single episodes are exempt, what a refresh
does, and the one runtime warning the feature can raise.

**A filter is asked, not remembered.** The verdict is computed wherever it is
needed -- the Inbox, the episode list, New Episodes, a smart playlist, Search
Everywhere -- rather than stamped onto an episode when it arrived. That is the
whole reason the scopes work: untick "hide them from the episode list" and the
episodes are back in the list on the next redraw, with no migration, no
sweep, and nothing to undo. A decision written down at ingest could not do
that, and the first cut of this feature -- which did exactly that, for the
Inbox alone -- is what showed why.

Two things *are* written down, because they are events rather than opinions:

* a **Play Queue** slot removed by the explicit apply-to-existing pass (a
  queue is an ordered list somebody built, and rebuilding it silently on every
  rule change would be worse than not offering the pass at all);
* the **Needs review** warning, because the refresh that raised it may have run
  while nobody was listening.

And one escape hatch, per episode: an **exemption**, which is the listener
saying "not this one" and outranks every rule in every scope.

Four promises hold across all of it:

* **Nothing is deleted, ever.** Played state, resume position, downloaded
  file, notes, bookmarks and the episode's place in its podcast's list are
  untouched by everything in this module.
* **The listener outranks the rule** -- an exemption, and the episode playing
  right now, which is never pulled out from under the player.
* **Failure is open.** No configuration, an unreadable one, no usable rule, or
  no scope: all mean the podcast behaves exactly as it did before the feature
  existed.
* **Nothing hidden is unreachable.** Wherever a hiding scope is in force, the
  episode list's own "Filtered out" view shows what it hid.

wx-free, strict-typed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from quill.core.podcasts import episode_filters
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.models_filters import (
    MODE_KEEP_MATCHING,
    SCOPE_NOTIFY,
    SCOPE_QUEUE,
    EpisodeFilterConfiguration,
)
from quill.core.podcasts.subscriptions import PodcastLibrary

# -- where the rules live ----------------------------------------------------


def filter_for(library: PodcastLibrary, show: PodcastShow) -> EpisodeFilterConfiguration | None:
    """This podcast's stored rule set, or ``None`` when it has none."""
    return library.episode_filters.get(show.id)


def set_filter(
    library: PodcastLibrary, show: PodcastShow, config: EpisodeFilterConfiguration | None
) -> None:
    """Store (or remove) this podcast's rule set.

    A ``None`` config, or one that is switched off with no rules at all, is
    removed rather than stored as an empty record -- so a library file only
    ever carries filters somebody actually wrote, and "has this podcast got a
    filter?" has one answer instead of two that look the same.
    """
    if config is None or (not config.enabled and not config.rules):
        library.episode_filters.pop(show.id, None)
        return
    library.episode_filters[show.id] = config


def clear_filter(library: PodcastLibrary, show: PodcastShow) -> bool:
    """Forget this podcast's rules entirely; True when there were any.

    Everything the filter was hiding is visible again immediately, because
    nothing was ever hidden by a stored mark -- the lists simply stop asking.
    Per-episode exemptions go too: an exemption is an exception to a rule, and
    with no rule it has nothing to except.
    """
    library.episode_filter_reviews.pop(show.id, None)
    library.episode_filter_exceptions.pop(show.id, None)
    return library.episode_filters.pop(show.id, None) is not None


def is_active(library: PodcastLibrary, show: PodcastShow) -> bool:
    """Whether this podcast's stored rules currently change anything."""
    config = filter_for(library, show)
    return config is not None and config.is_active


# -- per-episode exemptions --------------------------------------------------


def exemptions(library: PodcastLibrary, show: PodcastShow) -> set[str]:
    """The guids of this podcast's episodes the filter is told to skip."""
    return set(library.episode_filter_exceptions.get(show.id, ()))


def is_exempt(library: PodcastLibrary, show: PodcastShow, episode: PodcastEpisode) -> bool:
    """Whether this one episode is exempt from its podcast's filter."""
    return episode.guid in library.episode_filter_exceptions.get(show.id, [])


def set_exempt(
    library: PodcastLibrary, show: PodcastShow, episode: PodcastEpisode, exempt: bool
) -> bool:
    """Exempt (or un-exempt) one episode; True when anything changed.

    The escape hatch that makes hiding safe to offer at all. A rule is a guess
    about a pattern; this is the listener being specific, and specific always
    wins. It is per episode and permanent until they say otherwise -- an
    exemption survives editing the rules, because the thing it records is "I
    have looked at this one and I want it", which no later rule change makes
    untrue.
    """
    current = list(library.episode_filter_exceptions.get(show.id, []))
    if exempt and episode.guid not in current:
        current.append(episode.guid)
    elif not exempt and episode.guid in current:
        current.remove(episode.guid)
    else:
        return False
    if current:
        library.episode_filter_exceptions[show.id] = current
    else:
        library.episode_filter_exceptions.pop(show.id, None)
    return True


# -- the question every surface asks -----------------------------------------


def hide_predicate(
    library: PodcastLibrary, show: PodcastShow, scope: str
) -> Callable[[PodcastEpisode], bool] | None:
    """A "is this episode hidden here?" test, or ``None`` when none can be.

    ``None`` rather than a function that always answers False, so the hot
    loops -- the Inbox over a 1,300-show library, a smart playlist over every
    episode of every show -- can skip the whole question with one branch for
    the overwhelmingly common case of a podcast with no filter. Only the shows
    somebody actually wrote a rule for pay for the rule.
    """
    config = filter_for(library, show)
    if config is None or not config.governs(scope):
        return None
    exempt = exemptions(library, show)

    def _hidden(episode: PodcastEpisode) -> bool:
        if episode.guid in exempt:
            return False
        return not episode_filters.keeps(config, episode)

    return _hidden


def hidden_from(
    library: PodcastLibrary, show: PodcastShow, episode: PodcastEpisode, scope: str
) -> bool:
    """Whether this podcast's filter hides *episode* from *scope*."""
    predicate = hide_predicate(library, show, scope)
    return predicate is not None and predicate(episode)


def visible(
    library: PodcastLibrary, show: PodcastShow, episodes: list[PodcastEpisode], scope: str
) -> list[PodcastEpisode]:
    """*episodes*, minus whatever this podcast's filter hides from *scope*."""
    predicate = hide_predicate(library, show, scope)
    if predicate is None:
        return list(episodes)
    return [episode for episode in episodes if not predicate(episode)]


def hidden(
    library: PodcastLibrary, show: PodcastShow, episodes: list[PodcastEpisode], scope: str
) -> list[PodcastEpisode]:
    """The other half of :func:`visible` -- what the filter is holding back.

    What the episode list's **Filtered out** view shows, and the reason a
    hiding scope is safe to offer: nothing this feature hides is unreachable.
    """
    predicate = hide_predicate(library, show, scope)
    if predicate is None:
        return []
    return [episode for episode in episodes if predicate(episode)]


def visible_pairs(
    library: PodcastLibrary, pairs: list[tuple[PodcastShow, PodcastEpisode]], scope: str
) -> list[tuple[PodcastShow, PodcastEpisode]]:
    """The cross-show form: ``(show, episode)`` pairs the filters allow here.

    One predicate per show rather than per pair, because a cross-show view
    over a large library asks this question tens of thousands of times and the
    answer only changes when the show does.
    """
    cache: dict[str, Callable[[PodcastEpisode], bool] | None] = {}
    result: list[tuple[PodcastShow, PodcastEpisode]] = []
    for show, episode in pairs:
        if show.id not in cache:
            cache[show.id] = hide_predicate(library, show, scope)
        predicate = cache[show.id]
        if predicate is not None and predicate(episode):
            continue
        result.append((show, episode))
    return result


# -- the runtime safety warning ----------------------------------------------


def needs_review(library: PodcastLibrary, show: PodcastShow) -> bool:
    """Whether a refresh found this podcast's rules rejecting *everything*."""
    return show.id in library.episode_filter_reviews


def review_stamp(library: PodcastLibrary, show: PodcastShow) -> str:
    """When that happened (ISO-8601 UTC), or ``""``."""
    return library.episode_filter_reviews.get(show.id, "")


def mark_needs_review(
    library: PodcastLibrary, show: PodcastShow, *, when: datetime | None = None
) -> None:
    """Record that a whole refresh was rejected by Keep matching.

    Raised only by :func:`route_refresh`, and only for Keep matching, because
    that is the mode in which a plausible-looking rule can quietly mean
    "nothing". Under Filter matching, rejecting every new episode is a
    perfectly ordinary result of a rule that says so.

    Stored per podcast in the library rather than announced and forgotten: the
    refresh that raised it may have been a background check that ran while
    nobody was listening, and a warning nobody heard is a warning that never
    happened.
    """
    moment = when or datetime.now(UTC)
    library.episode_filter_reviews[show.id] = moment.isoformat()


def clear_needs_review(library: PodcastLibrary, show: PodcastShow) -> bool:
    """Mark the warning as seen; True when there was one.

    Cleared by *reviewing and saving* the filter, not by opening the window:
    opening it proves somebody looked at the title bar, and saving proves they
    made a decision about the rules.
    """
    return library.episode_filter_reviews.pop(show.id, None) is not None


# -- what a refresh does -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class IngestOutcome:
    """What a filter said about one refresh's genuinely new episodes."""

    #: Everything that arrived, whatever the filter thought of it. Every one
    #: of these is in the podcast's episode list; the filter decides only
    #: where else it appears.
    arrived: list[PodcastEpisode] = field(default_factory=list)
    #: The ones no rule rejected.
    kept: list[PodcastEpisode] = field(default_factory=list)
    #: The ones a rule rejected. Not deleted, not marked, not moved.
    filtered: list[PodcastEpisode] = field(default_factory=list)
    #: True when Keep matching rejected every new candidate in this refresh.
    raised_review: bool = False
    #: The **hiding** scopes this podcast's filter carries, ready to be
    #: spoken -- empty when it only declines to route. Carried on the outcome
    #: rather than recomputed by the announcer so the sentence and the verdict
    #: come from the same read of the configuration.
    hidden_from: str = ""

    @property
    def any_filtered(self) -> bool:
        return bool(self.filtered)

    def for_scope(self, scope: str, governs: bool) -> list[PodcastEpisode]:
        """The episodes a given scope should act on.

        ``governs`` is the filter's own answer for that scope, passed in
        rather than recomputed so the caller's branch and this one can never
        disagree: a scope that is off gets everything that arrived, exactly as
        it would have with no filter at all.
        """
        return self.kept if governs else self.arrived


def route_refresh(
    library: PodcastLibrary, show: PodcastShow, new_episodes: list[PodcastEpisode]
) -> IngestOutcome:
    """Ask this podcast's filter about the episodes a refresh just found.

    Called with exactly the episodes ``merge_episodes`` reported as genuinely
    new, **before** anything routes them: before Auto-Queue, before the
    per-show announcement, before the auto-download pass. That ordering is the
    feature -- a filter consulted after auto-download would have saved the
    triage and none of the disk.

    It **changes nothing**. It returns a verdict, and the caller routes: the
    Inbox and every list ask the same question for themselves whenever they
    are drawn, which is what lets a scope be unticked later and take effect at
    once.

    Unlike Earshot, which had to cap how many items one refresh could insert to
    protect a large relational store, Cast merges the whole of what a feed
    offers and always did. There is no "kept versus filtered insertion budget"
    here and no ceiling for a filtered episode to consume: everything the feed
    published is in the podcast's list either way.
    """
    config = filter_for(library, show)
    if config is None or not config.is_active or not new_episodes:
        return IngestOutcome(arrived=list(new_episodes), kept=list(new_episodes))
    exempt = exemptions(library, show)
    kept: list[PodcastEpisode] = []
    filtered: list[PodcastEpisode] = []
    for episode in new_episodes:
        allowed = episode.guid in exempt or episode_filters.keeps(config, episode)
        (kept if allowed else filtered).append(episode)
    raised = bool(filtered) and not kept and config.mode == MODE_KEEP_MATCHING
    if raised:
        mark_needs_review(library, show)
    return IngestOutcome(
        arrived=list(new_episodes),
        kept=kept,
        filtered=filtered,
        raised_review=raised,
        hidden_from=episode_filters.describe_hiding_scopes(config),
    )


def governs(library: PodcastLibrary, show: PodcastShow, scope: str) -> bool:
    """Whether this podcast's filter is honoured in *scope* right now."""
    config = filter_for(library, show)
    return config is not None and config.governs(scope)


def queue_candidates(
    library: PodcastLibrary, show: PodcastShow, outcome: IngestOutcome
) -> list[PodcastEpisode]:
    """Which new episodes Auto-Queue may take."""
    return outcome.for_scope(SCOPE_QUEUE, governs(library, show, SCOPE_QUEUE))


def announce_candidates(
    library: PodcastLibrary, show: PodcastShow, outcome: IngestOutcome
) -> list[PodcastEpisode]:
    """Which new episodes the refresh counts and names out loud."""
    return outcome.for_scope(SCOPE_NOTIFY, governs(library, show, SCOPE_NOTIFY))


# -- applying a rule set to the Play Queue -----------------------------------


@dataclass(frozen=True, slots=True)
class ApplyOutcome:
    """What the one-time apply-to-existing pass actually did."""

    considered: int = 0
    queue_removed: int = 0
    #: True when the episode playing right now would have been removed from
    #: the Play Queue and was deliberately left there.
    playing_kept: bool = False


def _queue_index(library: PodcastLibrary, show_id: str, guid: str) -> int:
    for index, item in enumerate(library.queue):
        if item.show_id == show_id and item.episode_guid == guid:
            return index
    return -1


def apply_to_existing(
    library: PodcastLibrary,
    show: PodcastShow,
    config: EpisodeFilterConfiguration | None = None,
    *,
    playing: tuple[str, str] | None = None,
) -> ApplyOutcome:
    """Take this podcast's already-queued rejects out of the Play Queue.

    Offered at the moment a filter is saved, and only then. Every *other*
    surface needs no such pass: the Inbox, the episode list, New Episodes, the
    playlists and the search all ask the filter as they are drawn, so a saved
    rule is already in force there before this function is reached.

    The **Play Queue is the exception on purpose.** It is an ordered list
    somebody assembled by hand, and a queue that silently rearranged itself
    every time a rule was edited would be a queue nobody could trust. So it is
    changed once, when asked, and never again by itself.

    * A queued episode the filter rejects loses its slot, and the slots after
      it close up.
    * **The episode playing now keeps its slot**, and the result says so.
    * Played state, resume position, download, notes, bookmarks and the
      episode's place in its podcast's list are untouched.
    * An exempted episode is not touched at all.

    There is no bulk undo in V1; a single episode comes back through its own
    Quick Actions (Play Next, Add to End of Queue).
    """
    rules = config if config is not None else filter_for(library, show)
    if rules is None or not rules.is_active or not rules.governs(SCOPE_QUEUE):
        return ApplyOutcome()
    exempt = exemptions(library, show)
    queued_guids = [item.episode_guid for item in library.queue if item.show_id == show.id]
    candidates = [episode for episode in show.episodes if episode.guid in set(queued_guids)]

    queue_removed = 0
    playing_kept = False
    for episode in candidates:
        if episode.guid in exempt or episode_filters.keeps(rules, episode):
            continue
        if playing is not None and playing == (show.id, episode.guid):
            playing_kept = True
            continue
        index = _queue_index(library, show.id, episode.guid)
        if index >= 0:
            del library.queue[index]
            queue_removed += 1
    return ApplyOutcome(
        considered=len(candidates),
        queue_removed=queue_removed,
        playing_kept=playing_kept,
    )


__all__ = [
    "ApplyOutcome",
    "IngestOutcome",
    "announce_candidates",
    "apply_to_existing",
    "clear_filter",
    "clear_needs_review",
    "exemptions",
    "filter_for",
    "governs",
    "hidden",
    "hidden_from",
    "hide_predicate",
    "is_active",
    "is_exempt",
    "mark_needs_review",
    "needs_review",
    "queue_candidates",
    "review_stamp",
    "route_refresh",
    "set_exempt",
    "set_filter",
    "visible",
    "visible_pairs",
]
