"""Custom-vocabulary correction for transcripts (names, products, jargon).

Every dictation engine mangles the words that matter most to their speaker:
"ChargeBee" arrives as "Charge B", "Quillin" as "quill in", a colleague's name
as whatever common word sounds nearest. The engines cannot know these words —
but the user can *tell us*, once, and every later dictation benefits.

This module is a pure-Python port of the matcher the Handy project
(D:\\code\\handy, ``src-tauri/src/audio_toolkit/text.rs``, MIT) runs in
production, chosen because each of its guards answers a real mis-correction:

- **Fuzzy match, two signals.** A candidate span matches a custom word when its
  spelling is close (Levenshtein distance, normalised by length) *and* — for
  near-threshold cases — it also *sounds* like it (Soundex). Spelling alone
  turns "their" into a nearby name; sound alone turns everything into
  everything.
- **N-grams, because engines split names.** "Charge B" is two tokens; matching
  single words would never see it. Spans of 1–3 words are tried, cleaned of
  case and punctuation, so "charge b" -> "chargebee".
- **A 25% length gate (minimum 2).** Without it, long n-grams collapse into
  short custom words ("openaigpt" must not become "openai") — Handy's exact
  counter-example, kept as a test here.
- **ASCII-only fallback.** The matcher tokenises on whitespace and scores by
  Soundex, both meaningless for CJK scripts; a non-ASCII custom word is simply
  never fuzzy-matched rather than wrongly matched. (Engines that accept
  vocabulary prompts natively can still receive such words upstream.)
- **The user's casing is canonical.** A match is replaced by the custom word
  exactly as the user wrote it — that is the point of the feature.

Deliberately stdlib-only (no new dependency for a text pass), wx-free, pure,
and unit-tested directly. Used by the dictation pipeline via
:func:`quill.core.speech.dictation.refine.refine_transcript`; the transcription
flows can adopt it the same way.
"""

from __future__ import annotations

import re

#: Accept a span when normalised edit distance is at or below this AND the
#: Soundex codes agree ("sounds right, spelled nearly right").
_PHONETIC_THRESHOLD = 0.34
#: Accept on spelling alone below this ("so close it cannot be another word").
_EXACTISH_THRESHOLD = 0.2
#: Longest candidate span, in words. Three covers "charge bee inc" -> one term;
#: beyond that, false merges outweigh catches (Handy shipped the same bound).
_MAX_NGRAM_WORDS = 3
#: A span longer than this is prose, not a term; never fuzzy-match it.
_MAX_CANDIDATE_CHARS = 50

_WORD_SPLIT = re.compile(r"(\s+)")


def soundex(word: str) -> str:
    """Classic American Soundex: first letter + three digits (pure).

    Adjacent same-code letters collapse; H and W are transparent between
    consonants; vowels break runs. Empty/non-alphabetic input yields "".
    """
    codes = {
        "b": "1", "f": "1", "p": "1", "v": "1",
        "c": "2", "g": "2", "j": "2", "k": "2", "q": "2", "s": "2", "x": "2", "z": "2",
        "d": "3", "t": "3",
        "l": "4",
        "m": "5", "n": "5",
        "r": "6",
    }  # fmt: skip
    letters = [c for c in word.lower() if c.isalpha()]
    if not letters:
        return ""
    head = letters[0]
    result = [head.upper()]
    previous = codes.get(head, "")
    for letter in letters[1:]:
        code = codes.get(letter, "")
        if code and code != previous:
            result.append(code)
            if len(result) == 4:
                break
        # Vowels reset the run; H/W are transparent (previous code survives).
        if letter not in "hw":
            previous = code
    return "".join(result).ljust(4, "0")


#: Cached optional accelerator: rapidfuzz's C++ Levenshtein when importable,
#: else None. Resolved once, lazily — the same optional-engine discipline as
#: sherpa-onnx/vosk: never required, never imported at module load, and the
#: pure fallback below is always the behavioural contract (identical results,
#: pinned by a parity test). ``False`` = not yet probed.
_FAST_DISTANCE: object = False


def _fast_distance() -> object:
    """rapidfuzz's distance callable, or None; probed once (see _FAST_DISTANCE)."""
    global _FAST_DISTANCE
    if _FAST_DISTANCE is False:
        try:
            from rapidfuzz.distance import Levenshtein  # type: ignore[import-not-found]

            _FAST_DISTANCE = Levenshtein.distance
        except Exception:  # noqa: BLE001 - absence or breakage both mean "use pure"
            _FAST_DISTANCE = None
    return _FAST_DISTANCE


def levenshtein(a: str, b: str) -> int:
    """Edit distance (insert/delete/substitute).

    Uses rapidfuzz when installed (the ``quill[rapidfuzz]`` extra; ~50-100x
    faster, worthwhile when batch transcription runs the corrector over long
    files); the iterative two-row DP below is the always-available pure
    fallback and the definition of correct.
    """
    fast = _fast_distance()
    if callable(fast):
        return int(fast(a, b))
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,  # delete
                    current[j - 1] + 1,  # insert
                    previous[j - 1] + (ca != cb),  # substitute
                )
            )
        previous = current
    return previous[-1]


def _match_key(word: str) -> str:
    """Lowercased alphanumerics only: the comparable core of a token."""
    return "".join(c.lower() for c in word if c.isalnum())


def _fuzzy_eligible(key: str) -> bool:
    """The ASCII gate: only keys the tokenizer and Soundex can be honest about."""
    return bool(key) and all(c.isascii() and c.isalnum() for c in key)


def _custom_word_keys(custom_words: list[str] | tuple[str, ...]) -> list[tuple[int, str]]:
    """(index, normalised key) pairs, including an "&" -> "and" spelling.

    "R&D" should match a transcript's "r and d"; both spellings map to the same
    custom word.
    """
    keys: list[tuple[int, str]] = []
    for index, word in enumerate(custom_words):
        primary = _match_key(word)
        if _fuzzy_eligible(primary):
            keys.append((index, primary))
        if "&" in word:
            expanded = _match_key(word.replace("&", " and "))
            if _fuzzy_eligible(expanded) and expanded != primary:
                keys.append((index, expanded))
    return keys


def _best_match(
    candidate: str, custom_words: list[str] | tuple[str, ...], keys: list[tuple[int, str]]
) -> str | None:
    """The custom word *candidate* should become, or None.

    Both acceptance routes and the length gate are documented in the module
    docstring; the scores are normalised edit distance in [0, 1].
    """
    if not _fuzzy_eligible(candidate) or len(candidate) > _MAX_CANDIDATE_CHARS:
        return None
    best: str | None = None
    best_score = 2.0
    for index, key in keys:
        longest = max(len(candidate), len(key))
        if longest == 0:
            continue
        # The 25%-of-length gate (minimum 2): stops long n-grams collapsing
        # into short terms ("openaigpt" vs "openai").
        if abs(len(candidate) - len(key)) > max(longest * 0.25, 2.0):
            continue
        if candidate == key:
            return custom_words[index]  # exact (case/punctuation aside): done
        score = levenshtein(candidate, key) / longest
        sounds_alike = soundex(candidate) == soundex(key) and soundex(candidate) != ""
        acceptable = score <= _EXACTISH_THRESHOLD or (sounds_alike and score <= _PHONETIC_THRESHOLD)
        if acceptable and score < best_score:
            best_score = score
            best = custom_words[index]
    return best


def apply_custom_vocabulary(text: str, custom_words: list[str] | tuple[str, ...]) -> str:
    """Replace fuzzy matches of the user's vocabulary in *text* (pure).

    Spans of 1–{_MAX_NGRAM_WORDS} words are considered longest-first, so
    "charge bee" wins before "charge" can mis-match something shorter. A
    replaced span keeps the punctuation that trailed it ("ChargeBee," stays a
    comma) and consumes its inner whitespace — the custom word is inserted
    exactly as the user wrote it.
    """
    if not text or not custom_words:
        return text
    keys = _custom_word_keys(custom_words)
    if not keys:
        return text
    # Split preserving whitespace so reassembly is loss-free.
    parts = _WORD_SPLIT.split(text)
    tokens = [p for p in parts if p and not p.isspace()]
    if not tokens:
        return text
    # Map token index -> position in `parts` for splicing.
    positions = [i for i, p in enumerate(parts) if p and not p.isspace()]

    out: list[str] = []
    consumed_until = 0  # index into `parts`
    token_index = 0
    while token_index < len(tokens):
        matched = False
        for span in range(min(_MAX_NGRAM_WORDS, len(tokens) - token_index), 0, -1):
            window = tokens[token_index : token_index + span]
            candidate = "".join(_match_key(w) for w in window)
            replacement = _best_match(candidate, custom_words, keys)
            if replacement is None:
                continue
            # Trailing punctuation of the span's last word survives the swap.
            last = window[-1]
            trailing = last[len(last.rstrip(".,;:!?)]}\"'")) :]
            start_part = positions[token_index]
            end_part = positions[token_index + span - 1]
            out.extend(parts[consumed_until:start_part])
            out.append(replacement + trailing)
            consumed_until = end_part + 1
            token_index += span
            matched = True
            break
        if not matched:
            token_index += 1
    out.extend(parts[consumed_until:])
    return "".join(out)
