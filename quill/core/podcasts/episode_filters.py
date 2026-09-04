"""Episode Filters: matching, preview, and the save gate.

The stored shape is :mod:`quill.core.podcasts.models_filters`; this is what
that shape *does*. Three jobs, in the order somebody meets them:

1. **Decide.** :func:`keeps` answers, for one episode, whether the podcast's
   rules let it through. :func:`partition` answers it for a list, which is what
   a refresh needs.
2. **Preview.** :func:`preview` runs the same decision as a dry run over the
   newest :data:`PREVIEW_LIMIT` episodes already stored, mutating nothing.
3. **Gate the save.** :func:`assess_save` refuses the saves that would silently
   throw a podcast away, and asks for confirmation on the two that might.

A fourth -- **saying it** -- lives in
:mod:`quill.core.podcasts.episode_filter_speech` and is re-exported here, so
every caller has one import while the two halves stay separately reviewable:
what a rule decides has a right answer, and how it reads is a question about
somebody arrowing down a list by ear.

Two rules run through everything:

* **Fail open.** An unusable rule never matches; a configuration with no usable
  enabled rule is not active. Under Keep matching those two sentences are the
  whole safety story, because the failure they prevent -- a podcast that
  silently stops arriving -- is invisible by construction.
* **Filtering is not deleting.** Nothing in this module removes, marks, or
  reorders anything. It returns decisions; the caller routes.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# The spoken forms live next door (GATE-11: extract, never rebaseline) and are
# re-exported here, because "the filter's words" and "the filter's decisions"
# are one subject to every caller and two files only to a reviewer.
from quill.core.podcasts.episode_filter_speech import (
    describe_apply_result as describe_apply_result,
)
from quill.core.podcasts.episode_filter_speech import (
    describe_configuration as describe_configuration,
)
from quill.core.podcasts.episode_filter_speech import (
    describe_criteria as describe_criteria,
)
from quill.core.podcasts.episode_filter_speech import (
    describe_hiding_scopes,
    hiding_question,
)
from quill.core.podcasts.episode_filter_speech import (
    describe_needs_review as describe_needs_review,
)
from quill.core.podcasts.episode_filter_speech import (
    describe_preview_row as _describe_preview_line,
)
from quill.core.podcasts.episode_filter_speech import (
    describe_refresh_outcome as describe_refresh_outcome,
)
from quill.core.podcasts.episode_filter_speech import (
    describe_rule as describe_rule,
)
from quill.core.podcasts.episode_filter_speech import (
    describe_scopes as describe_scopes,
)
from quill.core.podcasts.episode_filter_speech import (
    format_minutes as format_minutes,
)
from quill.core.podcasts.episode_filter_speech import (
    rule_name as rule_name,
)
from quill.core.podcasts.models import PodcastEpisode
from quill.core.podcasts.models_filters import (
    FILTER_SCOPES,
    MODE_KEEP_MATCHING,
    PATTERN_REGEX,
    PATTERN_WILDCARD,
    EpisodeFilterConfiguration,
    EpisodeFilterRule,
    wildcard_to_regex,
)

#: How many stored episodes Preview evaluates: the newest 50.
#:
#: A number rather than "all of them" because Preview must stay instant on a
#: podcast with four thousand episodes, and because the rules people write are
#: about what a feed is publishing *now*. The same 50 are what the duration
#: save gate measures coverage over, so the sentence "none of the episodes
#: Preview looked at reports a duration" is literally true and checkable.
PREVIEW_LIMIT = 50

#: The two decisions, as the words the preview row leads with.
DECISION_KEPT = "Kept"
DECISION_FILTERED = "Filtered"


# -- matching ----------------------------------------------------------------


def _title_matches(rule: EpisodeFilterRule, title: str) -> bool:
    """Whether *title* satisfies this rule's title criterion.

    ``fullmatch``, not ``search``: a wildcard pattern reads as a shape for the
    whole title, so ``*date*`` means "has 'date' somewhere" and ``Update``
    means exactly that title and not every title containing it. A regular
    expression is held to the same rule for the same reason -- one anchoring
    convention that a person can hold in their head, rather than two that
    differ by which radio button is selected.
    """
    if not rule.has_title_criterion:
        return True  # a duration-only rule asks nothing about the title
    flags = 0 if rule.case_sensitive else re.IGNORECASE
    if rule.pattern_kind == PATTERN_WILDCARD:
        source = wildcard_to_regex(rule.pattern)
    elif rule.pattern_kind == PATTERN_REGEX:
        source = rule.pattern
    else:  # pragma: no cover - not reachable while has_title_criterion holds
        return True
    try:
        return re.fullmatch(source, title, flags) is not None
    except re.error:
        # Belt and braces: ``is_usable`` already excluded this rule, and an
        # exception escaping into a feed refresh would be far worse than a
        # rule that declines to match.
        return False


def _duration_matches(rule: EpisodeFilterRule, episode: PodcastEpisode) -> bool:
    """Whether *episode* satisfies this rule's minimum-duration criterion.

    **An episode whose feed omits a duration never matches a duration rule.**
    A missing duration is not a short episode; treating zero as "shorter than
    45 minutes" would make a duration rule quietly filter every item in a feed
    that simply does not publish ``itunes:duration``, which is a great many of
    them.
    """
    if not rule.has_duration_criterion:
        return True
    if episode.duration_seconds <= 0:
        return False
    return episode.duration_seconds >= rule.min_duration_minutes * 60


def rule_matches(rule: EpisodeFilterRule, episode: PodcastEpisode) -> bool:
    """Whether one rule matches one episode.

    Both criteria have to hold -- a rule that names a title *and* a minimum
    duration is one condition, not two. An unusable rule matches nothing at
    all, whatever mode it is in.
    """
    if not rule.is_usable:
        return False
    return _title_matches(rule, episode.title) and _duration_matches(rule, episode)


def matching_rules(
    config: EpisodeFilterConfiguration, episode: PodcastEpisode
) -> list[EpisodeFilterRule]:
    """Every usable enabled rule of *config* that matches *episode*.

    The preview's "why" -- a decision with no reason attached is a decision
    somebody has to reverse-engineer.
    """
    return [rule for rule in config.usable_rules if rule_matches(rule, episode)]


def keeps(config: EpisodeFilterConfiguration | None, episode: PodcastEpisode) -> bool:
    """Whether *episode* is allowed through by *config*.

    ``True`` for a missing or inactive configuration, which is the whole of
    the compatibility story: a podcast with no filter behaves exactly as it
    did before this feature existed, down to the code path.
    """
    if config is None or not config.is_active:
        return True
    matched = bool(matching_rules(config, episode))
    if config.mode == MODE_KEEP_MATCHING:
        return matched
    return not matched


def partition(
    config: EpisodeFilterConfiguration | None, episodes: list[PodcastEpisode]
) -> tuple[list[PodcastEpisode], list[PodcastEpisode]]:
    """``(kept, filtered)`` for *episodes*, in their given order.

    Order preserved rather than sorted: the caller passes the episodes a
    refresh just reported as new, and it wants them back in the same order to
    announce and route them.
    """
    kept: list[PodcastEpisode] = []
    filtered: list[PodcastEpisode] = []
    for episode in episodes:
        (kept if keeps(config, episode) else filtered).append(episode)
    return kept, filtered


# -- preview -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PreviewRow:
    """One line of the dry run: what would happen, and to what."""

    episode: PodcastEpisode
    kept: bool
    matched: tuple[str, ...] = ()

    @property
    def decision(self) -> str:
        return DECISION_KEPT if self.kept else DECISION_FILTERED


def describe_preview_row(row: PreviewRow, *, with_reason: bool = False) -> str:
    """One preview line, spoken -- the row form of
    :func:`quill.core.podcasts.episode_filter_speech.describe_preview_row`.

    The sentence itself lives in the speech module, which takes primitives so
    the dependency runs one way; this is the two-line adapter that keeps every
    caller passing the row it already has.
    """
    return _describe_preview_line(
        row.decision,
        row.episode.title,
        row.episode.duration_seconds,
        row.matched,
        with_reason=with_reason,
    )


def newest_episodes(
    episodes: list[PodcastEpisode], limit: int = PREVIEW_LIMIT
) -> list[PodcastEpisode]:
    """The *limit* newest stored episodes, newest first.

    Sorted on the feed's own ``published`` string, exactly as the acquisition
    policy does: right for ISO 8601, harmless for anything else, and a feed
    with unsortable dates has no better order to offer.
    """
    ordered = sorted(episodes, key=lambda e: (e.published, e.title), reverse=True)
    return ordered[: max(0, limit)]


def preview(
    config: EpisodeFilterConfiguration | None,
    episodes: list[PodcastEpisode],
    *,
    limit: int = PREVIEW_LIMIT,
) -> list[PreviewRow]:
    """A dry run of *config* over the newest stored episodes.

    **Evaluated against the draft even when the top-level switch is off.**
    That is deliberate and it is the fix device testing asked for: previewing
    before activating is the only safe way to write a Keep-matching rule, and
    a preview that reported "everything kept" whenever the switch was off was
    a preview that agreed with you right up until it mattered.

    Nothing is mutated. This function cannot route, dismiss, queue or delete;
    it reads episodes and returns rows.
    """
    draft = config
    if draft is not None and (not draft.enabled or not draft.active_scopes):
        # A copy, switched on and given every scope, so the decision function
        # sees an active configuration -- the caller's object is left exactly
        # as it was. Scopes are neutralised for the same reason the switch is:
        # Preview answers "what do these rules catch?", which is a question
        # about the rules and not about where the answer will be honoured.
        draft = draft.copy()
        draft.enabled = True
        if not draft.active_scopes:
            draft.scopes = set(FILTER_SCOPES)
    rows: list[PreviewRow] = []
    for episode in newest_episodes(episodes, limit):
        matched = matching_rules(draft, episode) if draft is not None else []
        rows.append(
            PreviewRow(
                episode=episode,
                kept=keeps(draft, episode),
                matched=tuple(rule_name(rule) for rule in matched),
            )
        )
    return rows


def preview_summary(rows: list[PreviewRow]) -> str:
    """What the Preview button says when it finishes.

    Counted, like every other list verb in Cast: "3 of 50 would be filtered"
    is an answer, where "preview complete" is a noise. Says so explicitly when
    a Keep-matching draft would take the whole sample, because that is the one
    result somebody needs to hear rather than discover.
    """
    total = len(rows)
    if not total:
        return (
            "Nothing to preview: this podcast has no stored episodes yet. "
            "Refresh the feed first, then preview."
        )
    filtered = sum(1 for row in rows if not row.kept)
    kept = total - filtered
    if filtered == total:
        return (
            f"Every one of the {total} newest episodes would be filtered out. "
            "Check the mode and the rules before saving."
        )
    return (
        f"{filtered} of the {total} newest episodes would be filtered out, "
        f"{kept} kept. Nothing has changed yet."
    )


# -- the save gate -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SaveAssessment:
    """Whether this draft may be saved, and what has to be said first."""

    #: Empty when the save may proceed; otherwise why it may not, in a
    #: sentence that names the fix.
    blocked: str = ""
    #: Empty when nothing needs asking; otherwise the exact question, with the
    #: counts that make it answerable.
    confirm: str = ""

    @property
    def ok(self) -> bool:
        return not self.blocked


def _duration_rule_active(config: EpisodeFilterConfiguration) -> bool:
    return any(rule.has_duration_criterion for rule in config.usable_rules)


def assess_save(
    config: EpisodeFilterConfiguration, episodes: list[PodcastEpisode]
) -> SaveAssessment:
    """Whether this configuration is safe to save, judged against real episodes.

    Four gates, every one of them the answer to a way this feature could take
    somebody's podcast away without telling them:

    * **On with no enabled rule** cannot be saved. Under Keep matching that
      configuration means "keep nothing"; under either mode it means the switch
      claims to be doing something it is not.
    * **An enabled rule whose regular expression does not compile** cannot be
      saved, and the compiler's own message is quoted -- "invalid pattern" with
      no reason is a dead end.
    * **A duration rule none of the sampled episodes can answer** cannot be
      saved. If not one of the newest :data:`PREVIEW_LIMIT` episodes reports a
      duration, the feed does not publish durations and the rule can only ever
      reject; the empty sample counts here too.
    * **A duration rule only some episodes can answer** needs confirmation,
      with the exact coverage count, because the rule will work and will also
      reject every episode whose duration is missing.
    * **On with every scope unticked** cannot be saved either. A filter with
      nowhere to apply is a switch that reports itself as on and does nothing,
      which is the most expensive kind of setting there is.
    * **A hiding scope** -- one that takes episodes out of a list rather than
      merely declining to route them -- needs confirmation, and the
      confirmation says where the hidden episodes can still be found.

    A configuration that is switched **off** is only checked for the things
    that would still be wrong when it is switched on later, which in practice
    means nothing at all: an inactive configuration is safe by definition, and
    refusing to save a draft you are still writing is its own kind of trap.
    """
    if not config.enabled:
        return SaveAssessment()
    if not config.enabled_rules:
        return SaveAssessment(
            blocked=(
                "Filtering is on but no rule is switched on, so this would "
                "decide nothing under Keep matching and everything under it. "
                "Add a rule, switch one on, or turn filtering off."
            )
        )
    for rule in config.enabled_rules:
        error = rule.pattern_error
        if error:
            return SaveAssessment(
                blocked=(
                    f"The rule {rule_name(rule)} has a regular expression that "
                    f"cannot be read: {error}. Fix the pattern, switch the rule "
                    "off, or change it to a wildcard."
                )
            )
    if not config.usable_rules:
        return SaveAssessment(
            blocked=(
                "Every switched-on rule is empty -- none of them asks anything "
                "about a title or a duration. Give a rule something to match, "
                "or turn filtering off."
            )
        )
    if not config.active_scopes:
        return SaveAssessment(
            blocked=(
                "Filtering is on but nothing is ticked under Where this applies, "
                "so the filter would decide nothing anywhere. Tick at least one "
                "place, or turn filtering off."
            )
        )
    hiding = describe_hiding_scopes(config)
    if not _duration_rule_active(config):
        if hiding:
            return SaveAssessment(confirm=hiding_question(hiding))
        return SaveAssessment()

    sample = newest_episodes(episodes)
    with_duration = sum(1 for episode in sample if episode.duration_seconds > 0)
    if not with_duration:
        return SaveAssessment(
            blocked=(
                "A rule uses a minimum duration, but not one of the "
                f"{len(sample)} newest episodes of this podcast reports how "
                "long it is, so the rule could only ever reject. Remove the "
                "duration from the rule, or refresh the feed and try again."
            )
        )
    if with_duration < len(sample):
        question = (
            f"Only {with_duration} of the {len(sample)} newest episodes "
            "report how long they are. A rule with a minimum duration does "
            "not match an episode whose length is missing, so those "
            f"{len(sample) - with_duration} would be treated as not matching."
        )
        if hiding:
            question += " " + hiding_question(hiding)
        else:
            question += " Save this filter anyway?"
        return SaveAssessment(confirm=question)
    if hiding:
        return SaveAssessment(confirm=hiding_question(hiding))
    return SaveAssessment()


__all__ = [
    "DECISION_FILTERED",
    "DECISION_KEPT",
    "PREVIEW_LIMIT",
    "PreviewRow",
    "SaveAssessment",
    "assess_save",
    "describe_apply_result",
    "describe_configuration",
    "describe_criteria",
    "describe_hiding_scopes",
    "describe_needs_review",
    "describe_scopes",
    "describe_preview_row",
    "describe_refresh_outcome",
    "describe_rule",
    "format_minutes",
    "keeps",
    "matching_rules",
    "newest_episodes",
    "partition",
    "preview",
    "preview_summary",
    "rule_matches",
    "rule_name",
]
