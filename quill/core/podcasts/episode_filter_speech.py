"""Episode Filters, spoken: every sentence the feature says out loud.

Split from :mod:`quill.core.podcasts.episode_filters` under GATE-11 (extract,
never rebaseline). The split is not arbitrary bookkeeping -- these two files
change for different reasons and are reviewed by different eyes. What a rule
*decides* is a correctness question with a right answer; how it *reads* is a
question about somebody arrowing down a list at 400 words a minute, and every
one of the orders below was reviewed on those grounds:

* **A rule is name, then enabled state, then criteria.** The name is how you
  find the rule you meant; the state is the single most consequential fact
  about it and belongs before the detail, not after a clause about wildcards.
  A listener has heard everything they need by the second word.
* **A preview row leads with the decision.** *Kept* or *Filtered* first, then
  the title and the length. A row that opens with the title makes somebody
  wait through a title they already know -- they subscribe to the podcast --
  to reach the one word they came for.
* **Every sentence about a filtered episode says nothing was deleted**,
  because "filtered" on its own sounds like it was.
* **Only the scopes that hide are named** in a passing announcement. Reciting
  four routing scopes turns a refresh into a paragraph, and an episode that
  was merely not queued is exactly as findable as it was.

Kept out of the dialogs so a test can assert on the word order, which is not
something you can assert about a literal buried in a sizer -- the same reason
``core/podcasts/settings_help.py`` exists.

Takes primitives rather than the records from ``episode_filters`` (a decision,
a title, a duration) so the dependency runs one way: that module imports this
one, and this one imports nothing but the stored shapes.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from quill.core.podcasts.models_filters import (
    FILTER_SCOPES,
    HIDING_SCOPES,
    MODE_LABELS,
    PATTERN_KIND_LABELS,
    SCOPE_SUMMARIES,
    EpisodeFilterConfiguration,
    EpisodeFilterRule,
)


def hiding_question(hiding: str) -> str:
    """The one confirmation a hiding scope always earns.

    Not a warning for its own sake: a scope that removes episodes from a list
    is the only part of this feature somebody could mistake for a delete, and
    the answer to that mistake is to say -- once, at the moment they choose it
    -- exactly where the episodes still are.
    """
    return (
        f"This filter will hide matching episodes from {hiding}. They are not "
        "deleted and nothing about them changes: choose Filtered out in the "
        "episode list's filter to see them, and any single episode can be "
        "exempted from its own menu. Save this filter?"
    )


# -- the words ---------------------------------------------------------------


def rule_name(rule: EpisodeFilterRule) -> str:
    """This rule's name, or a readable stand-in when it has none."""
    return rule.name.strip() or "Unnamed rule"


def format_minutes(seconds: int) -> str:
    """A duration as the preview and the rules list say it."""
    if seconds <= 0:
        return "length unknown"
    minutes = max(1, round(seconds / 60))
    return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"


def describe_criteria(rule: EpisodeFilterRule) -> str:
    """A rule's criteria, without its name or state."""
    parts: list[str] = []
    if rule.has_title_criterion:
        kind = PATTERN_KIND_LABELS.get(rule.pattern_kind, "Title")
        sensitivity = ", case sensitive" if rule.case_sensitive else ""
        parts.append(f"{kind}, {rule.pattern}{sensitivity}.")
    if rule.has_duration_criterion:
        minutes = rule.min_duration_minutes
        unit = "minute" if minutes == 1 else "minutes"
        parts.append(f"Duration at least {minutes} {unit}.")
    if not parts:
        parts.append("No criteria yet, so this rule matches nothing.")
    error = rule.pattern_error
    if error:
        parts.append(f"This pattern cannot be read, so the rule matches nothing: {error}.")
    return " ".join(parts)


def describe_rule(rule: EpisodeFilterRule) -> str:
    """One rule, spoken: **name, enabled state, then criteria**.

    The order was reviewed and it is not arbitrary. The name is how somebody
    finds the rule they meant; the state is the single most consequential fact
    about it and belongs before the detail, not after a clause about wildcards
    -- a listener arrowing down a rules list has heard everything they need by
    the second word.
    """
    state = "enabled" if rule.enabled else "disabled"
    return f"{rule_name(rule)}, {state}. {describe_criteria(rule)}"


def describe_preview_row(
    decision: str,
    title: str,
    duration_seconds: int,
    matched: tuple[str, ...] = (),
    *,
    with_reason: bool = False,
) -> str:
    """One preview line, spoken: **decision first**, then title and length.

    Leading with Kept or Filtered is what makes the list skimmable by ear. A
    row that opens with the episode title makes somebody wait through the
    title -- which they already know, because they subscribe to the podcast --
    to hear the one word they came for.

    *with_reason* appends which rule decided it. The dialog asks for it only
    when there is more than one rule to choose between: with a single rule the
    name adds a clause to every row and answers a question nobody has, and with
    five rules "which of these caught it?" is the whole reason somebody pressed
    Preview.
    """
    length = format_minutes(duration_seconds)
    line = f"{decision}, {title}, {length}."
    if with_reason and matched:
        line += f" Matched {_join(list(matched))}."
    return line


def _join(parts: list[str]) -> str:
    """``a``, ``a and b``, ``a, b and c`` -- read out loud, not printed."""
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def describe_scopes(config: EpisodeFilterConfiguration) -> str:
    """Where this filter applies, in the order the checkboxes offer it."""
    return _join([
        SCOPE_SUMMARIES[scope] for scope in FILTER_SCOPES if scope in config.active_scopes
    ])


def describe_hiding_scopes(config: EpisodeFilterConfiguration) -> str:
    """Only the scopes that take an episode *out of a list*, or ``""``.

    Asked separately from :func:`describe_scopes` because the two halves earn
    different treatment: declining to auto-download something is invisible and
    harmless, and removing it from a list is the one thing here somebody could
    mistake for a deletion.
    """
    return _join([
        SCOPE_SUMMARIES[scope]
        for scope in FILTER_SCOPES
        if scope in HIDING_SCOPES and scope in config.active_scopes
    ])


def describe_configuration(config: EpisodeFilterConfiguration | None) -> str:
    """The whole rule set in one sentence, for a status line or F1."""
    if config is None or not config.enabled:
        return "Episode filtering is off for this podcast; every new episode arrives as usual."
    if not config.usable_rules:
        return (
            "Episode filtering is switched on but no usable rule is switched on, "
            "so every new episode arrives as usual."
        )
    if not config.active_scopes:
        return (
            "Episode filtering is switched on but applies nowhere, "
            "so every new episode arrives as usual."
        )
    count = len(config.usable_rules)
    noun = "rule" if count == 1 else "rules"
    return (
        f"{MODE_LABELS.get(config.mode, config.mode)}. {count} {noun} in force, "
        f"applied to {describe_scopes(config)}."
    )


def describe_refresh_outcome(show_title: str, kept: int, filtered: int, *, hidden: str = "") -> str:
    """What a refresh says when a filter took some of what arrived.

    Names the filter as the reason, because "2 new episodes" when the feed
    published five is quiet arithmetic that reads as a bug, and says nothing
    was deleted, because "filtered" on its own sounds like it was.

    *hidden* is the **hiding** scopes only, not every scope. Listing all eight
    would make a passing announcement into a paragraph, and the four routing
    scopes are the ones nobody needs told about: an episode that was not
    queued is exactly as findable as it was. The scopes that take an episode
    *out of a list* are different -- somebody who cannot find it afterwards
    needs to have been told where to look -- so those, and only those, are
    named, with the way back.
    """
    if not filtered:
        return ""
    episodes = "episode" if filtered == 1 else "episodes"
    tail = f"{filtered} {episodes} filtered out for {show_title}; nothing was deleted."
    if hidden:
        tail += (
            f" They are hidden from {hidden}; choose Filtered out in the episode list to see them."
        )
    else:
        tail += " They are in the podcast's episode list as usual."
    return f"{kept} new, {tail}" if kept else tail


def describe_apply_result(show_title: str, queue_removed: int, playing_kept: bool) -> str:
    """What the one-time Play Queue pass says when it finishes.

    An exact count, and the currently-playing exception said out loud when it
    applied -- an episode that stayed in the queue against the rule is exactly
    the thing somebody would otherwise file as a bug.
    """
    if not queue_removed:
        message = f"Filter saved for {show_title}. Nothing in the Play Queue matched it."
    else:
        episodes = "episode" if queue_removed == 1 else "episodes"
        message = (
            f"Filter saved for {show_title}. "
            f"{queue_removed} {episodes} removed from the Play Queue."
        )
    if playing_kept:
        message += " The episode playing now was left in the queue."
    return message + " Nothing was deleted; every episode is still in the podcast's list."


def describe_needs_review(show_title: str) -> str:
    """The runtime safety warning: a whole refresh rejected, and why that matters."""
    return (
        f"Every new episode of {show_title} was filtered out by its Keep matching "
        "rules. Nothing was lost -- they are in the podcast's episode list -- but "
        "the rules may not say what you meant. Open Episode Filters for this "
        "podcast to review them."
    )


__all__ = [
    "describe_apply_result",
    "describe_configuration",
    "describe_criteria",
    "describe_hiding_scopes",
    "describe_needs_review",
    "describe_preview_row",
    "describe_refresh_outcome",
    "describe_rule",
    "describe_scopes",
    "format_minutes",
    "hiding_question",
    "rule_name",
]
