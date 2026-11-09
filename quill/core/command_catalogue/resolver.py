"""Tiers 1 and 2: matching a sentence to this window's commands (command-key.md 6).

The resolver is given the candidate list -- the rows this window has, enabled
right now, never NEVER -- and nothing else. It cannot name a command outside
that list, because it only ever ranks the list it was handed; the policy checks
that again anyway (section 6.2).

- **Tier 1, exact.** The whole sentence, without filler, is a command's title,
  an alias or an example, or "press <its key>". Free, instant, certain.
- **Tier 2, fuzzy.** Every candidate is scored on how many of its words the
  sentence has (recall) and how many of the sentence's words it explains
  (precision), with stemming, a synonym table and one typo allowed in long
  words. It acts only with a clear margin over the runner-up.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import lru_cache

from quill.core.command_catalogue.args import ReadArgs, read_args
from quill.core.command_catalogue.spec import ArgKind, CommandSpec
from quill.core.command_catalogue.words import content_words, normalize, similar

__all__ = [
    "ACT_MARGIN",
    "ACT_SCORE",
    "ASK_SCORE",
    "Candidate",
    "Ranked",
    "Resolution",
    "rank",
    "resolve",
]

#: Tier 2 acts without asking at or above this score...
ACT_SCORE = 0.74
#: ...and only this far ahead of the next command.
ACT_MARGIN = 0.15
#: Below this, nothing is close enough even to offer as "Did you mean".
ASK_SCORE = 0.55
#: A tier 1 hit on meaningful words only, below a word-for-word one.
EXACT_LOOSE = 0.995


@dataclass(frozen=True, slots=True)
class Candidate:
    """One command this window can run now, with the key it answers to here."""

    spec: CommandSpec
    key: str = ""


@dataclass(frozen=True, slots=True)
class Ranked:
    candidate: Candidate
    score: float
    tier: int

    @property
    def id(self) -> str:
        return self.candidate.spec.id


@dataclass(frozen=True, slots=True)
class Resolution:
    """What tiers 1 and 2 made of a sentence."""

    #: Best first. Empty when nothing scored at all.
    ranked: tuple[Ranked, ...]
    args: ReadArgs
    #: The top candidate is confident enough to act on (or to confirm, if CONFIRM).
    confident: bool = False
    #: The commands worth offering as "Did you mean", best first.
    close: tuple[Ranked, ...] = field(default_factory=tuple)

    @property
    def best(self) -> Ranked | None:
        return self.ranked[0] if self.ranked else None


def _key_words(key: str) -> str:
    """A chord as a person says it: "Ctrl+Shift+S" -> "control shift s"."""
    spoken = key.lower().replace("ctrl", "control").replace("+", " ").replace(",", " ")
    return normalize(spoken)


@lru_cache(maxsize=8192)
def _phrases(spec: CommandSpec) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Each phrase of *spec*, normalised and as its meaningful words. Cached:
    the rows are frozen, and this is most of a request's work."""
    texts = (spec.title, *spec.aliases, *spec.examples)
    return tuple((normalize(text), content_words(text)) for text in texts if text)


def _exact(text: str, words: tuple[str, ...], candidate: Candidate) -> float:
    """1.0 when the sentence is a phrase word for word (or "press" its key),
    0.995 when only its meaningful words are, and 0.0 otherwise.

    The two strengths matter when two rows share their meaningful words: "make
    this a favourite" and "favourite" are both just "favourite" without filler,
    but only one row was written as the whole sentence.
    """
    if candidate.key:
        said = text.removeprefix("press ").removeprefix("hit ")
        if text != said and said == _key_words(candidate.key):
            return 1.0
    loose = 0.0
    for normal, meaning in _phrases(candidate.spec):
        if normal == text:
            return 1.0
        if words and meaning == words:
            loose = EXACT_LOOSE
    return loose


def _phrase_score(words: tuple[str, ...], phrase: tuple[str, ...]) -> float:
    if not words or not phrase:
        return 0.0
    phrase_hits = sum(1 for word in phrase if any(similar(word, said) for said in words))
    said_hits = sum(1 for said in words if any(similar(said, word) for word in phrase))
    recall = phrase_hits / len(phrase)
    precision = said_hits / len(words)
    if not phrase_hits:
        return 0.0
    return 2 * recall * precision / (recall + precision)


def _fuzzy(words: tuple[str, ...], spec: CommandSpec) -> float:
    best = 0.0
    for _normal, meaning in _phrases(spec):
        best = max(best, _phrase_score(words, meaning))
    return best


def rank(text: str, candidates: Sequence[Candidate]) -> tuple[tuple[Ranked, ...], ReadArgs]:
    """Every candidate that scores at all, best first, and the arguments read."""
    normal = normalize(text)
    args = read_args(normal)
    remainder_words = content_words(args.remainder)
    whole_words = content_words(normal)
    ranked: list[Ranked] = []
    for candidate in candidates:
        strength = _exact(normal, whole_words, candidate)
        if args.remainder != normal:
            strength = max(strength, _exact(args.remainder, remainder_words, candidate))
        if strength:
            ranked.append(Ranked(candidate, strength, 1))
            continue
        score = max(_fuzzy(remainder_words, candidate.spec), _fuzzy(whole_words, candidate.spec))
        if score > 0:
            ranked.append(Ranked(candidate, min(score, 0.99), 2))
    ranked.sort(key=lambda item: (-item.score, item.tier, item.candidate.spec.title.lower()))
    return tuple(ranked), args


def _first(ranked: tuple[Ranked, ...], chosen: Ranked) -> tuple[Ranked, ...]:
    return (chosen, *(item for item in ranked if item is not chosen))


def _takes(spec: CommandSpec, args: ReadArgs) -> bool:
    kinds = {arg.kind for arg in spec.args}
    if args.number is not None and ArgKind.NUMBER in kinds:
        return True
    return args.seconds is not None and ArgKind.DURATION in kinds


def resolve(text: str, candidates: Sequence[Candidate]) -> Resolution:
    """Rank *text* against *candidates* and say whether the best is confident."""
    ranked, args = rank(text, candidates)
    if not ranked:
        return Resolution((), args)
    top = ranked[0]
    runner = ranked[1].score if len(ranked) > 1 else 0.0
    exact_hits = [item for item in ranked if item.tier == 1]
    if len(exact_hits) == 1:
        return Resolution(ranked, args, confident=True, close=(top,))
    whole = [item for item in exact_hits if item.score == 1.0]
    if len(exact_hits) > 1 and len(whole) == 1:
        return Resolution(_first(ranked, whole[0]), args, confident=True, close=(whole[0],))
    if len(exact_hits) > 1:
        # "favourite 2" is both Play a Favourite and Favourite This Station by
        # its words, but only one of them takes a number.
        fitting = [item for item in exact_hits if _takes(item.candidate.spec, args)]
        if len(fitting) == 1:
            return Resolution(_first(ranked, fitting[0]), args, confident=True, close=(fitting[0],))
        return Resolution(ranked, args, close=tuple(exact_hits[:3]))
    confident = top.score >= ACT_SCORE and top.score - runner >= ACT_MARGIN
    close = tuple(
        item for item in ranked[:3] if item.score >= ASK_SCORE and top.score - item.score < 0.25
    )
    return Resolution(ranked, args, confident=confident, close=close)
