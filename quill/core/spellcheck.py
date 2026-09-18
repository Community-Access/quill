"""Spell-check engine for Quill.

Three-tier strategy, transparently selected at runtime:

1. **Native (pyenchant + Hunspell)** if `enchant` is installed. Best quality,
   includes morphological suggestions. Optional dependency.
2. **Bundled English wordlist** (`quill/data/words_alpha.txt`, ~370k words,
   public domain). Used to validate words; suggestions come from
   `difflib.get_close_matches` over a precomputed bucket of length-similar
   candidates so the cost stays bounded.
3. **Tiny built-in stub** (a few dozen words). Last-resort fallback so the
   feature never crashes in safe-mode tests or stripped-down environments.

The user-managed personal / document / project dictionaries layer on top of
whichever tier is active. They are always merged into both the validation
set and the suggestion corpus.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from collections import defaultdict
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path

from quill.core.file_lock import guarded_write
from quill.core.paths import app_data_dir

# The language catalogue lives in spell_languages (a GATE-11 extraction). The
# re-exports keep every existing caller -- and the tests that monkeypatch these
# names as attributes of *this* module -- working unchanged.
from quill.core.spell_languages import (
    DEFAULT_LANGUAGE as _DEFAULT_LANGUAGE,
)
from quill.core.spell_languages import (
    downloaded_languages as downloaded_languages,
)
from quill.core.spell_languages import (
    installable_languages as installable_languages,
)
from quill.core.spell_languages import (
    installed_languages as installed_languages,
)
from quill.core.spell_languages import (
    language_display_name,
    managed_hunspell_dir,
    managed_spell_dir,
)
from quill.core.storage import read_json, write_json_atomic

logger = logging.getLogger(__name__)

# ``(?<![0-9])`` is the ordinal guard, and it is a bug fix rather than a
# refinement. Without it "the 13th of May" reports **"th"** as a misspelling --
# at an offset inside a number, for a word the user did not type -- because the
# pattern starts at the first letter it finds and the digits before it are
# invisible to it. "1st" and "23rd" escaped only by luck: "st" and "rd" happen
# to be in the wordlist and "th" does not.
#
# The same guard covers every other letters-after-digits shape a document is
# full of and no dictionary contains: 3D, 2x, MP3's siblings, 1080p, v2beta,
# and the units in "500ml" and "12pt". Each was a spoken interruption for a
# screen-reader user and none of them was ever a spelling mistake.
#: A word, in any language the document might be in (bad.md S4).
#:
#: It was ``[A-Za-z][A-Za-z']*``, and the walk-left beside it used
#: ``str.isalpha()`` -- so the two halves of one checker disagreed about
#: what a word is: `caf\u00e9` was flagged as `caf`, `na\u00efve` as `na` and `ve`,
#: and a curly apostrophe split `don\u2019t` in two. The same word was silent
#: on one path and flagged on another, which reads as a checker that cannot
#: make up its mind.
#:
#: ``\\w`` under Python's default Unicode rules is the letters, and the two
#: apostrophes are added explicitly: the typographic one is what every word
#: processor inserts for you, including this one. Digits stay excluded from
#: the *first* character, which is the ordinal guard the comment above
#: describes, and the lookbehind still refuses letters that follow digits.
_APOSTROPHES = "'\u2019"
_WORD_PATTERN = re.compile(r"(?<![0-9])[^\W\d_][\w" + _APOSTROPHES + r"]*")

# Tiny last-resort corpus. Real validation comes from the bundled wordlist
# or pyenchant; this only exists so the module never raises if data is
# missing (e.g. a development checkout where data files were deleted).
_STUB_WORDS: frozenset[str] = frozenset({
    "a",
    "about",
    "after",
    "all",
    "alpha",
    "an",
    "and",
    "any",
    "appears",
    "as",
    "at",
    "be",
    "beta",
    "by",
    "can",
    "check",
    "command",
    "content",
    "document",
    "editor",
    "feature",
    "file",
    "for",
    "from",
    "go",
    "have",
    "in",
    "is",
    "it",
    "line",
    "mode",
    "navigation",
    "navigator",
    "new",
    "next",
    "no",
    "not",
    "of",
    "on",
    "open",
    "or",
    "project",
    "quill",
    "save",
    "settings",
    "spell",
    "text",
    "that",
    "the",
    "this",
    "to",
    "toggle",
    "tools",
    "undo",
    "up",
    "with",
    "word",
    "you",
})

# Backwards-compatibility alias used by older tests/imports.
_DEFAULT_WORDS = _STUB_WORDS

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_WORDLIST_PATH = _DATA_DIR / "words_alpha.txt"

_BACKEND_LOCK = threading.Lock()
_WORDLIST_CACHE: frozenset[str] | None = None
_ENCHANT_DICT: object | None = None
_ENCHANT_TRIED: bool = False

# The active Hunspell language; the default and the catalogue live in
# spell_languages, re-exported above.
_ACTIVE_LANGUAGE = _DEFAULT_LANGUAGE


def active_language() -> str:
    """The Hunspell language tag the backend currently validates against."""
    return _ACTIVE_LANGUAGE


def set_active_language(lang: str | None) -> None:
    """Set the spell-check language (e.g. ``"en_US"``, ``"fr_FR"``).

    A blank/None value resets to the default. Drops the cached enchant dict so the
    next check resolves the new language (the next :func:`_try_enchant` rebuilds a
    fresh broker, which also picks up a just-downloaded dictionary).
    """
    global _ACTIVE_LANGUAGE
    new = (lang or _DEFAULT_LANGUAGE).strip() or _DEFAULT_LANGUAGE
    if new == _ACTIVE_LANGUAGE:
        return
    _ACTIVE_LANGUAGE = new
    reset_caches()


# #316: length-bucketed wordlist caches, keyed on the wordlist frozenset
# id so a reload of the bundled wordlist (reset_caches) automatically
# rebuilds the buckets on next access.  This avoids the O(W) scan of the
# ~370k-word bundled corpus on every call to ``suggest_words``.
_LENGTH_BUCKETS_LOCK = threading.Lock()
_LENGTH_BUCKETS_BY_WORDLIST_ID: dict[int, dict[int, list[str]]] = {}

# #315: memoization cache for ``list_misspellings`` keyed on
# (text, frozenset(dictionary)).  ``list_misspellings`` runs over every
# word in the document on each call; spell-check-as-you-type and the
# Spell Check dialog can fire it many times per second, so caching the
# result for an unchanged text+dictionary pair keeps the hot path
# cheap.  The key includes the dictionary's frozenset identity so a
# user edit to the personal/document/project dictionaries invalidates
# the cache automatically.
_MISSPELLINGS_CACHE: dict[tuple[str, int], list[Misspelling]] = {}


@dataclass(frozen=True, slots=True)
class BackendInfo:
    """Describe which spell-check tier is active."""

    name: str  # "enchant", "wordlist", or "stub"
    detail: str  # human-readable detail (language, word count, etc.)
    word_count: int  # 0 for enchant (size unknown)


def _load_wordlist() -> frozenset[str]:
    global _WORDLIST_CACHE
    if _WORDLIST_CACHE is not None:
        return _WORDLIST_CACHE
    with _BACKEND_LOCK:
        if _WORDLIST_CACHE is not None:
            return _WORDLIST_CACHE
        if not _WORDLIST_PATH.is_file():
            _WORDLIST_CACHE = frozenset()
            return _WORDLIST_CACHE
        try:
            text = _WORDLIST_PATH.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            _WORDLIST_CACHE = frozenset()
            return _WORDLIST_CACHE
        words = {line.strip().lower() for line in text.splitlines() if line.strip()}
        _WORDLIST_CACHE = frozenset(words)
        return _WORDLIST_CACHE


def _try_enchant() -> object | None:
    global _ENCHANT_DICT, _ENCHANT_TRIED
    if _ENCHANT_TRIED:
        return _ENCHANT_DICT
    with _BACKEND_LOCK:
        if _ENCHANT_TRIED:
            return _ENCHANT_DICT
        # Resolve the dictionary into a local first and only publish
        # _ENCHANT_TRIED once _ENCHANT_DICT holds its final value. The fast-path
        # check above is intentionally lock-free, so flipping the flag early
        # would let a concurrent thread observe a not-yet-assigned dict and fall
        # back to the wordlist backend (a backend-selection race).
        resolved: object | None = None
        try:
            # Point enchant at our managed dir so downloaded dictionaries are
            # discoverable, then import. ENCHANT_CONFIG_DIR is read when a broker
            # is constructed, so it must be set before the first broker is built;
            # an empty managed dir is harmless (bundled en_US still resolves).
            os.environ["ENCHANT_CONFIG_DIR"] = str(managed_spell_dir())
            managed_hunspell_dir().mkdir(parents=True, exist_ok=True)
            import enchant  # type: ignore[import-not-found]
        except Exception:
            resolved = None
        else:
            try:
                # A *fresh* broker rescans providers, so a dictionary downloaded
                # earlier this session is picked up without a restart. Resolve the
                # active language, then en_US, then the first English variant.
                broker = enchant.Broker()
                for lang in (_ACTIVE_LANGUAGE, "en_US"):
                    if lang and broker.dict_exists(lang):
                        resolved = broker.request_dict(lang)
                        break
                else:
                    for lang in broker.list_languages():
                        if lang.lower().startswith("en"):
                            resolved = broker.request_dict(lang)
                            break
            except Exception:
                resolved = None
        _ENCHANT_DICT = resolved
        _ENCHANT_TRIED = True
        return _ENCHANT_DICT


def preload() -> None:
    """Warm the spell-check backend *and* the suggestion index so first F7 is warm.

    Resolves the validation tier (pyenchant if present, otherwise the bundled
    wordlist) and — the other half of the warm-up (#527) — builds the
    length-bucketed candidate index over the bundled corpus that
    :func:`suggest_words` falls back on. That bucket build over the ~370k-word
    corpus is the dominant one-time cost on the first spell review; doing it here
    on the startup daemon thread keeps the first F7 from stalling even when
    enchant is the active validator (its suggestions can still miss and fall
    through to the corpus). Safe to call from a background thread; every loader is
    idempotent and lock-guarded, so repeat calls are cheap no-ops once warm.
    """
    _try_enchant()  # resolve (and cache) the validation backend, if available
    wordlist = _load_wordlist()  # the suggestion fallback corpus
    if wordlist:
        _length_buckets(wordlist)  # #527: prebuild the bucketed suggestion index


def reset_caches() -> None:
    """Drop the spell-check module caches so callers can re-measure cold start.

    N-6: the perf-budget tests previously poked the private
    ``_WORDLIST_CACHE`` / ``_ENCHANT_DICT`` / ``_ENCHANT_TRIED`` globals by
    hand, which is fragile if any of those names change. This public helper
    is the supported entry point for "make spellcheck cold again".

    Also drops the #315 misspellings memoization cache and the #316
    length-bucketed wordlist caches so a perf-budget test exercising
    the cold path stays reliable.
    """
    global _WORDLIST_CACHE, _ENCHANT_DICT, _ENCHANT_TRIED
    with _BACKEND_LOCK:
        _WORDLIST_CACHE = None
        _ENCHANT_DICT = None
        _ENCHANT_TRIED = False
    with _LENGTH_BUCKETS_LOCK:
        _LENGTH_BUCKETS_BY_WORDLIST_ID.clear()
    _MISSPELLINGS_CACHE.clear()


def backend_info() -> BackendInfo:
    """Return information about the currently active spell-check backend."""
    enchant_dict = _try_enchant()
    if enchant_dict is not None:
        tag = getattr(enchant_dict, "tag", "en")
        provider = getattr(getattr(enchant_dict, "provider", None), "name", "enchant")
        return BackendInfo(name="enchant", detail=f"{tag} ({provider})", word_count=0)
    wordlist = _load_wordlist()
    if wordlist:
        return BackendInfo(
            name="wordlist",
            detail=f"bundled English wordlist ({len(wordlist):,} words)",
            word_count=len(wordlist),
        )
    return BackendInfo(
        name="stub",
        detail=f"built-in stub ({len(_STUB_WORDS)} words) — full data missing",
        word_count=len(_STUB_WORDS),
    )


def install_language(
    lang: str,
    progress: object | None = None,
    *,
    should_cancel: object | None = None,
) -> Path:
    """Download + verify + unpack the Hunspell dictionary for *lang* on demand.

    Routes through :mod:`quill.core.release_assets` (pinned, SHA-256-verified,
    Safe-Mode gated). On success the dictionary lands in
    :func:`managed_hunspell_dir` and the backend cache is dropped so the new
    language is usable without a restart. Raises ``release_assets.ReleaseAssetError``
    (or ``DownloadCancelled``) on failure so the caller can degrade cleanly.
    """
    from quill.core import release_assets

    target = release_assets.fetch_component(
        f"spell-{lang}",
        managed_hunspell_dir(),
        progress=progress,  # type: ignore[arg-type]
        should_cancel=should_cancel,  # type: ignore[arg-type]
        label=f"Downloading {language_display_name(lang)} dictionary...",
    )
    reset_caches()
    return target


def is_known_word(token: str, extra: set[str] | frozenset[str] | None = None) -> bool:
    """Check whether *token* is spelled correctly.

    *extra* is the union of personal/document/project dictionaries.
    """
    if not token:
        return True
    lowered = token.lower()
    if extra and lowered in {item.lower() for item in extra}:
        return True
    enchant_dict = _try_enchant()
    if enchant_dict is not None:
        try:
            # enchant.check is case-sensitive for proper nouns; accept either the
            # original casing (proper nouns) or the lowercase form (sentence
            # starts). When a real dictionary (hunspell) answers cleanly its
            # verdict is authoritative: a False means the word is misspelled.
            # Do NOT fall through to the bundled wordlist here -- that ~370k-word
            # dump contains junk entries (e.g. "teest") that would otherwise
            # un-flag genuine typos. The wordlist is only a fallback for when
            # enchant is absent or errors (handled below).
            return bool(
                enchant_dict.check(token)  # type: ignore[attr-defined]
                or enchant_dict.check(lowered)  # type: ignore[attr-defined]
            )
        except Exception:
            pass  # enchant errored; fall back to the bundled wordlist below
    wordlist = _load_wordlist()
    if wordlist:
        return lowered in wordlist
    return lowered in _STUB_WORDS


@dataclass(frozen=True, slots=True)
class Misspelling:
    word: str
    start: int
    end: int


def list_misspellings(text: str, dictionary: set[str]) -> list[Misspelling]:
    """Return every misspelling in *text*, honouring *dictionary*.

    #315: the result is memoized on the ``(text, frozenset(dictionary))``
    key so repeated calls during spell-check-as-you-type and the Spell
    Check dialog are cheap when neither input has changed. The
    frozenset identity changes when a user edits their personal,
    document, or project dictionary, so cache invalidation is
    automatic; ``reset_caches()`` also clears the cache for perf
    benchmarks.
    """
    dictionary_key = frozenset(item.lower() for item in dictionary)
    cache_key = (text, hash(dictionary_key))
    cached = _MISSPELLINGS_CACHE.get(cache_key)
    if cached is not None:
        return list(cached)
    misspellings: list[Misspelling] = []
    for match in _WORD_PATTERN.finditer(text):
        token = match.group(0)
        if not is_known_word(token, dictionary_key):
            misspellings.append(Misspelling(word=token, start=match.start(), end=match.end()))
    _MISSPELLINGS_CACHE[cache_key] = misspellings
    return list(misspellings)


def rank_misspellings_by_frequency(misspellings: list[Misspelling]) -> list[Misspelling]:
    """Reorder *misspellings* by how often each word occurs, most frequent first.

    Kurzweil-1000-style "ranked spelling" (community feature request): instead
    of reviewing errors in document order, review the word that recurs the
    most first -- a single OCR misread or a repeated typo like "teh" for "the"
    is usually the fastest way to clear the bulk of a list, since fixing one
    entry via "Add to Dictionary" or a mental correction resolves every
    occurrence at once.

    Case-insensitive grouping (``Teh``/``teh`` count together), ties broken by
    first-occurrence position so the ranking is stable and reproducible. Pure
    reordering -- does not deduplicate; every occurrence is still present in
    the result, just grouped and sorted by its word's total count.
    """
    counts: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    for item in misspellings:
        key = item.word.lower()
        counts[key] = counts.get(key, 0) + 1
        if key not in first_seen:
            first_seen[key] = item.start
    return sorted(
        misspellings,
        key=lambda item: (-counts[item.word.lower()], first_seen[item.word.lower()], item.start),
    )


def misspelling_at(text: str, position: int, dictionary: set[str]) -> Misspelling | None:
    """The misspelled word starting exactly at *position*, or None.

    The bounded form of :func:`next_misspelling` for the as-you-type hint
    (#1346 round 3). The hint only ever accepts a word beginning at the caret,
    but ``next_misspelling`` keeps scanning past every correctly-spelled word
    until it finds *a* misspelling somewhere -- so on a clean document it
    spell-checked everything from the caret to the end, per pause in typing,
    to produce an answer the caller then discarded. This inspects exactly one
    word: the first at or after *position*, rejected without further scanning
    when it does not start there.

    The scan begins one character early for the same reason
    :func:`next_misspelling` starts at the cursor itself: a regex scan started
    mid-word matches a tail fragment. When ``text[position - 1]`` is a word
    character, the fragment starting there is skipped and the following whole
    word cannot start at *position* -- exactly the answer the unbounded scan
    gave for that shape.
    """
    for match in _WORD_PATTERN.finditer(text, max(0, position - 1)):
        if match.start() < position:
            continue  # tail fragment of a straddling word, or an earlier word
        if match.start() != position:
            return None
        token = match.group(0)
        if is_known_word(token, dictionary):
            return None
        return Misspelling(word=token, start=match.start(), end=match.end())
    return None


def misspelling_behind(
    text: str, cursor: int, dictionary: set[str], *, require_terminator: bool = True
) -> Misspelling | None:
    """The misspelled word you have just *finished*, or None.

    The question spell-check-as-you-type actually has, and until 2026-09-10 no
    function in this module answered it. Both editors asked
    :func:`misspelling_at` instead, which by construction matches only a word
    **beginning exactly at the caret** -- it is the bounded helper written for a
    different question. Typing left to right the caret is always at or past the
    *end* of the word just completed, so the condition was never true and the
    whole as-you-type alert was unreachable: no earcon, no status line, nothing,
    unless you happened to arrow back onto the first letter of a bad word. The
    feature shipped, was documented, had settings, and had never once fired.

    "Finished" means there is a terminator between the word and the caret -- a
    space, a comma, a newline, anything that is not part of a word. That rule is
    what stops the checker judging "recie" while somebody is still typing
    "receive", which is the failure mode that makes a live checker intolerable:
    it cries wolf on the way to every long word. *require_terminator* exists for
    a caller that has some other reason to believe the word is complete.

    Cheap by construction: it walks left over at most a handful of characters
    and matches one word, so it can sit in the typing path. Nothing here scans
    the document.
    """
    if cursor <= 0:
        return None
    end = min(cursor, len(text))
    # Step back over whatever terminated the word -- usually one space, but a
    # sentence can end ". " and a list item ", ".
    while end > 0 and not _is_word_character(text[end - 1]):
        end -= 1
    if end == min(cursor, len(text)) and require_terminator:
        return None  # the caret is still inside the word; it may be unfinished
    if end <= 0:
        return None
    start = end
    while start > 0 and _is_word_character(text[start - 1]):
        start -= 1
    match = _WORD_PATTERN.match(text, start)
    if match is None or match.end() != end:
        # The run of word characters is not a word this checker recognises as
        # one -- a bare apostrophe, or letters immediately after digits, which
        # the ordinal guard in _WORD_PATTERN deliberately refuses. Both are
        # silence rather than a report.
        return None
    token = match.group(0)
    if is_known_word(token, dictionary):
        return None
    return Misspelling(word=token, start=match.start(), end=match.end())


def next_misspelling(text: str, cursor: int, dictionary: set[str]) -> Misspelling | None:
    # Start the regex scan at the cursor position itself so the engine matches
    # whole words (a mid-word cursor would otherwise match a tail fragment).
    # Then skip any whole-word match that doesn't begin strictly after the
    # cursor. This is O(distance-to-next-mistake) rather than O(N).
    scan_from = max(0, cursor)
    for match in _WORD_PATTERN.finditer(text, scan_from):
        if match.start() <= cursor:
            continue
        token = match.group(0)
        if not is_known_word(token, dictionary):
            return Misspelling(word=token, start=match.start(), end=match.end())
    return None


def previous_misspelling(text: str, cursor: int, dictionary: set[str]) -> Misspelling | None:
    previous: Misspelling | None = None
    scan_until = max(0, cursor)
    for match in _WORD_PATTERN.finditer(text, 0, scan_until):
        if match.end() > cursor:
            break
        token = match.group(0)
        if not is_known_word(token, dictionary):
            previous = Misspelling(word=token, start=match.start(), end=match.end())
    return previous


def no_misspelling_message(text: str, cursor: int, dictionary: set[str], *, ahead: bool) -> str:
    """What to say when there is no misspelling in the direction asked for.

    Ctrl+F7 and Ctrl+Shift+F7 search forward and backward from the caret and do
    not wrap, so right after typing a misspelling the caret sits past it and
    there is no *next* one. A bare "No further misspellings" is then both
    misleading -- it reads as "your document is clean" -- and a dead end, since
    it does not say that turning round would find seven.

    QUILL has answered this way since #9; QuillLite said the bare sentence with
    no count at all (bad.md S9). Shared here rather than copied, because two
    editors describing the same silence in two different ways is exactly the
    divergence the family plan exists to remove.
    """
    direction = "ahead" if ahead else "behind"
    other_key = "behind" if ahead else "ahead"
    other = (
        previous_misspelling(text, cursor, dictionary)
        if ahead
        else next_misspelling(text, cursor, dictionary)
    )
    if other is None:
        return "No misspellings found"
    count = sum(1 for m in list_misspellings(text, dictionary) if (m.end <= cursor) == ahead)
    plural = "" if count == 1 else "s"
    return f"No misspellings {direction}; {count} misspelling{plural} {other_key}"


def misspelling_at_position(text: str, position: int, dictionary: set[str]) -> Misspelling | None:
    """The misspelling at *position*, or the one that ends there (bad.md S5).

    A caret sits at the *end* of the word you have just typed, and this needed
    ``start <= position < end``, so the answer for the word under the cursor
    was "there is no word" at the one moment somebody most often asks. Two
    context menus worked around it by retrying at ``position - 1``; the four
    keyboard commands did not, so the same question got two answers depending
    on how it was asked. The retry belongs here, once.
    """
    if position < 0 or position > len(text):
        return None
    found = _misspelling_covering(text, position, dictionary)
    if found is not None:
        return found
    if position > 0 and _is_word_character(text[position - 1]):
        # The caret is just past the last letter: the word ending here is the
        # word being asked about.
        return _misspelling_covering(text, position - 1, dictionary)
    return None


def _misspelling_covering(text: str, position: int, dictionary: set[str]) -> Misspelling | None:
    # Find the word boundary around `position` directly rather than scanning
    # every word in the document. Walk left to the start of the current word,
    # then match forward once.
    if position < 0 or position > len(text):
        return None
    left = position
    while left > 0 and _is_word_character(text[left - 1]):
        left -= 1
    match = _WORD_PATTERN.match(text, left)
    if match is None:
        return None
    if not (match.start() <= position < match.end()):
        return None
    token = match.group(0)
    if is_known_word(token, dictionary):
        return None
    return Misspelling(word=token, start=match.start(), end=match.end())


def _is_word_character(character: str) -> bool:
    """One definition of "inside a word", shared with :data:`_WORD_PATTERN`.

    The pair used to disagree -- the pattern was ASCII and this was Unicode --
    which is how the same word came to be silent on one path and flagged on
    another (bad.md S4).
    """
    return character.isalpha() or character in _APOSTROPHES


def suggest_words(word: str, dictionary: set[str], limit: int = 8) -> list[str]:
    if not word.strip():
        return []
    cleaned = word.strip()
    extras = {item.lower() for item in dictionary}
    enchant_dict = _try_enchant()
    if enchant_dict is not None:
        try:
            suggestions = list(enchant_dict.suggest(cleaned))  # type: ignore[attr-defined]
            seen: set[str] = set()
            ordered: list[str] = []
            for candidate in suggestions:
                key = candidate.lower()
                if key in seen:
                    continue
                seen.add(key)
                ordered.append(candidate)
                if len(ordered) >= limit:
                    break
            if ordered:
                return ordered
        except Exception:
            pass
    lowered = cleaned.lower()
    wordlist = _load_wordlist()
    base = wordlist if wordlist else _STUB_WORDS
    # Narrow the candidate pool by length to keep get_close_matches fast.
    # difflib over 370k strings is slow; constraining to +/- 2 characters
    # collapses that to a few thousand candidates without losing quality.
    target_len = len(lowered)
    # #316: length-bucketed candidate pool, see _length_buckets().
    buckets = _length_buckets(base)
    pool: list[str] = []
    bucket_seen: set[str] = set()
    for delta in (0, -1, 1, -2, 2):
        for candidate in buckets.get(target_len + delta, ()):
            if candidate in bucket_seen:
                continue
            bucket_seen.add(candidate)
            pool.append(candidate)
    pool.extend(extras - bucket_seen)
    matches = get_close_matches(lowered, pool, n=max(1, limit), cutoff=0.6)
    return matches[:limit]


def _length_buckets(wordlist: frozenset[str]) -> dict[int, list[str]]:
    """Return a ``{length: [words...]}`` view of *wordlist* (#316).

    The buckets are cached on ``id(wordlist)`` so a reload of the
    bundled wordlist (``reset_caches``) automatically rebuilds them
    next time. Frozen inputs (``frozenset`` and the bundled
    ``_STUB_WORDS``) keep stable ``id`` values for the life of the
    process so the cache hit rate stays high in normal use.
    """
    key = id(wordlist)
    cached = _LENGTH_BUCKETS_BY_WORDLIST_ID.get(key)
    if cached is not None:
        return cached
    with _LENGTH_BUCKETS_LOCK:
        cached = _LENGTH_BUCKETS_BY_WORDLIST_ID.get(key)
        if cached is not None:
            return cached
        buckets: dict[int, list[str]] = defaultdict(list)
        for word in wordlist:
            buckets[len(word)].append(word)
        frozen: dict[int, list[str]] = dict(buckets)
        _LENGTH_BUCKETS_BY_WORDLIST_ID[key] = frozen
        return frozen


def personal_dictionary_revision(personal_dir: Path | None = None) -> tuple[int, int]:
    """``(mtime_ns, size)`` of the personal dictionary; ``(0, 0)`` if absent.

    What a caller compares against to find out whether the shared list has
    changed under it. Each app used to load the dictionary once and keep the
    set, so a word taught in QuillLite stayed underlined in QUILL until QUILL
    was restarted -- which makes a *shared* dictionary look broken rather than
    shared (bad.md S10).
    """
    path = _dictionary_path("personal", None, None, personal_dir)
    if path is None:
        return (0, 0)
    try:
        stat = path.stat()
    except OSError:
        return (0, 0)
    return (int(stat.st_mtime_ns), int(stat.st_size))


def add_word_to_scope(
    word: str,
    scope: str,
    document_path: Path | None,
    project_root: Path | None,
    personal_dir: Path | None = None,
) -> bool:
    """Teach *word* in *scope*. ``False`` when there was nowhere to write it.

    The return value is bad.md S3. The "this document only" and "this project"
    dictionaries are files *beside* the document, so an unsaved buffer has no
    such file and nothing is written -- and the caller went on announcing
    ``Added "word" to this document only`` regardless. The word stayed
    underlined, and the only way to learn that was to try again and hear the
    same sentence a second time. Callers must now say which of the two
    happened.
    """
    token = word.strip().lower()
    if not token:
        return False
    path = _dictionary_path(scope, document_path, project_root, personal_dir)
    if path is None:
        return False
    # Read and write inside the lock, not either side of it: the point is that
    # nothing else rewrites the file between the two (bad.md S10).
    # The lock is quill/core/file_lock.py: every shared read-modify-write in
    # the product has the same race and deserves the same answer, not a second
    # implementation of it (bad.md S10).
    with guarded_write(path):
        existing = load_scope_dictionary(scope, document_path, project_root, personal_dir)
        existing.add(token)
        write_json_atomic(path, sorted(existing))
    return True


def load_combined_dictionary(
    document_path: Path | None,
    project_root: Path | None,
    personal_dir: Path | None = None,
) -> set[str]:
    personal = load_scope_dictionary("personal", document_path, project_root, personal_dir)
    document = load_scope_dictionary("document", document_path, project_root, personal_dir)
    project = load_scope_dictionary("project", document_path, project_root, personal_dir)
    return personal | document | project


def load_scope_dictionary(
    scope: str,
    document_path: Path | None,
    project_root: Path | None,
    personal_dir: Path | None = None,
) -> set[str]:
    path = _dictionary_path(scope, document_path, project_root, personal_dir)
    if path is None:
        return set()
    raw = read_json(path, default=None)
    if isinstance(raw, list):
        return {item.strip().lower() for item in raw if isinstance(item, str) and item.strip()}
    # EdSharp standard (magic2, 2026-08-27): a taught dictionary is an asset
    # the user may open and edit by hand. A hand edit that breaks the JSON
    # must not silently wipe two hundred taught words -- so a file that does
    # not parse as JSON is read as a plain word list, one per line (which is
    # also what a hand-authored file naturally looks like). Commas, brackets
    # and quotes left over from JSON editing are stripped per line.
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    words: set[str] = set()
    for line in text.splitlines():
        token = line.strip().strip("[],").strip().strip('"').strip("'").strip().lower()
        if token and all(ch.isalpha() or ch in "-'" for ch in token):
            words.add(token)
    if words:
        logger.warning(
            "Scope dictionary %s is not valid JSON; recovered %d words from it "
            "as a plain word list",
            path,
            len(words),
        )
        return words
    if text.strip():
        logger.warning("Scope dictionary %s is malformed; falling back to empty set", path)
    return set()


def _dictionary_path(
    scope: str,
    document_path: Path | None,
    project_root: Path | None,
    personal_dir: Path | None = None,
) -> Path | None:
    """Where a scope's taught words live.

    ``personal_dir`` overrides the data folder the personal dictionary is kept
    in, and exists for the sibling apps: QuillLite keeps its own dictionary in
    its own folder, because a machine that has never had QUILL installed must
    not grow a Quill data folder because somebody taught a text editor a word.
    QUILL passes nothing and gets ``app_data_dir()``, exactly as before.
    """
    if scope == "personal":
        root = personal_dir if personal_dir is not None else app_data_dir()
        return root / "dictionaries" / "personal.json"
    if scope == "document":
        if document_path is None:
            return None
        return document_path.with_suffix(document_path.suffix + ".quill-dict.json")
    if scope == "project":
        if project_root is None:
            return None
        return project_root / ".quill-dictionary.json"
    return None
