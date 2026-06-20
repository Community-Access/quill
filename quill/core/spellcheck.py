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
import re
import threading
from collections import defaultdict
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

logger = logging.getLogger(__name__)

_WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z']*")

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
            import enchant  # type: ignore[import-not-found]
        except Exception:
            resolved = None
        else:
            try:
                # Prefer en_US; fall back to the first installed English variant
                # if en_US isn't available on this system.
                if enchant.dict_exists("en_US"):
                    resolved = enchant.Dict("en_US")
                else:
                    for lang in enchant.list_languages():
                        if lang.lower().startswith("en"):
                            resolved = enchant.Dict(lang)
                            break
            except Exception:
                resolved = None
        _ENCHANT_DICT = resolved
        _ENCHANT_TRIED = True
        return _ENCHANT_DICT


def preload() -> None:
    """Warm the spell-check backend so the first check does not stall.

    Resolves the active tier (pyenchant if present, otherwise the bundled
    wordlist) and forces the wordlist into memory. Safe to call from a
    background thread at startup; the underlying loaders are idempotent and
    guarded by ``_BACKEND_LOCK``, so repeat calls are cheap no-ops once warm.
    """
    if _try_enchant() is not None:
        # Enchant resolves its own dictionary lazily; touching it is enough to
        # avoid a first-use stall. The bundled wordlist is the fallback corpus.
        return
    _load_wordlist()


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
            # enchant.check is case-sensitive for proper nouns; try original
            # casing first, then lowercase, then title case for sentence
            # starts.
            if enchant_dict.check(token):  # type: ignore[attr-defined]
                return True
            if enchant_dict.check(lowered):  # type: ignore[attr-defined]
                return True
        except Exception:
            pass
        # If enchant returned False without raising, fall through to the
        # bundled wordlist as a secondary check. Enchant's installed
        # dictionary may be incomplete or minimal in some environments.
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


def misspelling_at_position(text: str, position: int, dictionary: set[str]) -> Misspelling | None:
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
    return character.isalpha() or character == "'"


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


def add_word_to_scope(
    word: str,
    scope: str,
    document_path: Path | None,
    project_root: Path | None,
) -> None:
    token = word.strip().lower()
    if not token:
        return
    path = _dictionary_path(scope, document_path, project_root)
    if path is None:
        return
    existing = load_scope_dictionary(scope, document_path, project_root)
    existing.add(token)
    write_json_atomic(path, sorted(existing))


def load_combined_dictionary(
    document_path: Path | None,
    project_root: Path | None,
) -> set[str]:
    personal = load_scope_dictionary("personal", document_path, project_root)
    document = load_scope_dictionary("document", document_path, project_root)
    project = load_scope_dictionary("project", document_path, project_root)
    return personal | document | project


def load_scope_dictionary(
    scope: str,
    document_path: Path | None,
    project_root: Path | None,
) -> set[str]:
    path = _dictionary_path(scope, document_path, project_root)
    if path is None:
        return set()
    raw = read_json(path, default=[])
    if not isinstance(raw, list):
        logger.warning("Scope dictionary %s is malformed; falling back to empty set", path)
        return set()
    return {item.strip().lower() for item in raw if isinstance(item, str) and item.strip()}


def _dictionary_path(
    scope: str,
    document_path: Path | None,
    project_root: Path | None,
) -> Path | None:
    if scope == "personal":
        return app_data_dir() / "dictionaries" / "personal.json"
    if scope == "document":
        if document_path is None:
            return None
        return document_path.with_suffix(document_path.suffix + ".quill-dict.json")
    if scope == "project":
        if project_root is None:
            return None
        return project_root / ".quill-dictionary.json"
    return None
