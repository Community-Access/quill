"""Write an Episode Filter rule from one episode: "Filter Episodes Like This".

Writing a rule from nothing means knowing, before you start, what the episodes
you do not want have in common -- and the listener usually does not know that
in words. What they know is *this one*. So the episode's own menu offers to
draft the rule, and this module guesses what "like this" means, in the order a
person would:

1. **The publisher already said.** An episode marked ``trailer`` or ``bonus``
   in ``itunes:episodeType`` is matched on exactly that -- the publisher's own
   vocabulary beats any guess at a title pattern.
2. **A series name in the title.** "Daily Briefing: Tuesday" shares
   "Daily Briefing:" with its siblings; "Interview | Jane Doe" shares
   "Interview |". The text before (or after) a separator, or the opening words,
   when several other episodes start the same way.
3. **Much shorter than the rest.** A two-minute segment in a feed of hour-long
   episodes is a length rule, with a ceiling just above it.
4. **Only this one.** If nothing above holds, the rule matches this exact title,
   which is still a rule the listener can widen in the editor.

Every guess is *checked* against the podcast's own newest episodes before it is
offered, and the count is said: a suggestion that matches every episode of the
podcast is no suggestion at all, and one that matches only itself is said to.

Nothing is saved here. The suggestion is a draft the rule editor opens on.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from statistics import median
from typing import Any

from quill.core.podcasts.filter_conditions import (
    FIELD_DURATION,
    FIELD_TITLE,
    FIELD_TYPE,
    OP_AT_MOST,
    OP_ENDS,
    OP_IS,
    OP_STARTS,
    FilterCondition,
    condition_matches,
)
from quill.core.podcasts.models_filters import PATTERN_NONE, EpisodeFilterRule

#: How many of the newest episodes a suggestion is checked against -- the same
#: sample the filter's own Preview uses.
SAMPLE_LIMIT = 50

#: Separators a publisher puts between a series name and an episode's own name.
_SEPARATORS = (": ", " | ", " - ", " – ", " — ", " #")

#: Shorter than this fraction of the podcast's median length counts as "much
#: shorter" -- a two-minute segment in a feed of half-hours, not a 40-minute
#: episode in a feed of 45s.
_SHORT_FRACTION = 0.4


@dataclass(frozen=True, slots=True)
class FilterSuggestion:
    """A drafted rule, why it was chosen, and how much it catches."""

    rule: EpisodeFilterRule
    reason: str
    matches: int
    sample: int


@dataclass(frozen=True, slots=True)
class _Candidate:
    name: str
    condition: FilterCondition
    explanation: str


def _count(condition: FilterCondition, episodes: Sequence[Any]) -> int:
    return sum(1 for episode in episodes if condition_matches(condition, episode))


def _title_candidates(title: str) -> list[_Candidate]:
    """Series-name guesses from one title, most specific first."""
    found: list[_Candidate] = []
    for separator in _SEPARATORS:
        head, sep, tail = title.partition(separator)
        if sep and head.strip() and tail.strip():
            prefix = head + sep.rstrip()
            found.append(
                _Candidate(
                    f'Starts with "{prefix}"',
                    FilterCondition(FIELD_TITLE, OP_STARTS, prefix),
                    f'its title starts with "{prefix}"',
                )
            )
        head, sep, tail = title.rpartition(separator)
        if sep and head.strip() and tail.strip():
            suffix = sep.lstrip() + tail
            found.append(
                _Candidate(
                    f'Ends with "{suffix}"',
                    FilterCondition(FIELD_TITLE, OP_ENDS, suffix),
                    f'its title ends with "{suffix}"',
                )
            )
    words = title.split()
    for size in range(min(4, len(words) - 1), 1, -1):
        prefix = " ".join(words[:size])
        found.append(
            _Candidate(
                f'Starts with "{prefix}"',
                FilterCondition(FIELD_TITLE, OP_STARTS, prefix),
                f'its title starts with "{prefix}"',
            )
        )
    return found


def _short_candidate(episode: Any, sample: Sequence[Any]) -> _Candidate | None:
    seconds = int(getattr(episode, "duration_seconds", 0) or 0)
    lengths = [int(e.duration_seconds) for e in sample if int(e.duration_seconds or 0) > 0]
    if seconds <= 0 or len(lengths) < 3:
        return None
    if seconds >= median(lengths) * _SHORT_FRACTION:
        return None
    minutes = seconds // 60
    ceiling = max(minutes + 2, round(minutes * 1.5))
    return _Candidate(
        f"{ceiling} minutes or shorter",
        FilterCondition(FIELD_DURATION, OP_AT_MOST, str(ceiling)),
        f"it is much shorter than this podcast's usual length, so the rule takes "
        f"anything {ceiling} minutes or shorter",
    )


def suggest_rule(
    episode: Any,
    episodes: Sequence[Any],
    *,
    newest: Callable[[Sequence[Any]], list[Any]] | None = None,
) -> FilterSuggestion:
    """The rule "episodes like *episode*" most plausibly means, already checked.

    *episodes* is the podcast's own episode list; the suggestion is judged
    against its newest :data:`SAMPLE_LIMIT`. *newest* is the ordering the
    filter's Preview uses, passed in so both agree on what "newest" means.
    """
    if newest is not None:
        sample = list(newest(episodes))
    else:
        sample = list(episodes)[:SAMPLE_LIMIT]
    if episode not in sample:
        sample.append(episode)
    total = len(sample)

    kind = str(getattr(episode, "episode_type", "") or "").strip().lower()
    if kind in ("trailer", "bonus"):
        condition = FilterCondition(FIELD_TYPE, OP_IS, kind)
        count = _count(condition, sample)
        name = "Trailers" if kind == "trailer" else "Bonus episodes"
        return FilterSuggestion(
            _rule(name, condition),
            f"The publisher marks this episode as a {kind}, so the rule takes "
            f"every episode they mark that way: {count} of the {total} newest.",
            count,
            total,
        )

    title = str(getattr(episode, "title", "") or "")
    best: tuple[int, _Candidate] | None = None
    for candidate in _title_candidates(title):
        count = _count(candidate.condition, sample)
        # Two or more (this one and at least one sibling), and not everything:
        # a rule that matches every episode of the podcast filters the podcast.
        if 2 <= count < total and (best is None or count > best[0]):
            best = (count, candidate)
    if best is None:
        short = _short_candidate(episode, sample)
        if short is not None:
            count = _count(short.condition, sample)
            if count < total:
                best = (count, short)
    if best is not None:
        count, chosen = best
        return FilterSuggestion(
            _rule(chosen.name, chosen.condition),
            f"Like this one because {chosen.explanation}: {count} of the {total} newest "
            "episodes match.",
            count,
            total,
        )
    only = FilterCondition(FIELD_TITLE, OP_IS, title)
    return FilterSuggestion(
        _rule(f'Exactly "{title}"', only),
        "No other recent episode shares a series name, a type or an unusual length "
        "with this one, so the rule matches this title only. Widen it in the editor "
        "-- a wildcard or a regular expression -- if you meant more.",
        _count(only, sample),
        total,
    )


def _rule(name: str, condition: FilterCondition) -> EpisodeFilterRule:
    return EpisodeFilterRule(name=name, pattern_kind=PATTERN_NONE, conditions=[condition])


def describe_trial(
    rule: EpisodeFilterRule,
    episodes: Sequence[Any],
    matcher: Callable[[EpisodeFilterRule, Any], bool],
    *,
    names: int = 5,
) -> str:
    """What a rule would catch among *episodes*, said before it is saved.

    "Try It" in the rule editor: the count, then up to *names* titles, so a
    pattern can be adjusted by ear until it catches what was meant. An
    unusable rule says why instead of saying "0".
    """
    if not rule.is_usable:
        return "This rule cannot match anything yet: " + (
            rule.pattern_error or "it has no test. Add a title pattern, a length or a test."
        )
    total = len(episodes)
    if not total:
        return "This podcast has no episodes to try the rule on yet."
    hits = [episode for episode in episodes if matcher(rule, episode)]
    if not hits:
        return f"Matches none of the {total} newest episodes."
    if len(hits) == total:
        head = f"Matches all {total} of the newest episodes -- every one."
    else:
        head = f"Matches {len(hits)} of the {total} newest episodes."
    shown = [str(getattr(episode, "title", "") or "Untitled") for episode in hits[:names]]
    more = len(hits) - len(shown)
    tail = "; ".join(shown) + (f"; and {more} more" if more else "")
    return f"{head} {tail}."


__all__ = ["SAMPLE_LIMIT", "FilterSuggestion", "describe_trial", "suggest_rule"]
