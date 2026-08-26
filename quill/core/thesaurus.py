"""Thesaurus support backed by the LibreOffice MyThes en_US data file.

The data file lives at ``quill/data/th_en_US_v2.dat`` and uses this format:

    UTF-8
    word|N            (N meanings follow)
    (pos)|syn1|syn2|...
    (pos)|syn1|syn2|...
    next-word|N
    ...

The parser is lazy: the first lookup builds an in-memory dict keyed by
lowercase headword. The .dat is ~18 MB, so the dict is a few tens of MB at
most and load time is well under a second on a modern machine.

If the data file is missing, all lookups return an empty result and
``is_available()`` returns ``False`` so the UI can surface a friendly
"data not installed" dialog.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "th_en_US_v2.dat"

_LOAD_LOCK = threading.Lock()
_INDEX: dict[str, list[Meaning]] | None = None
_LOAD_ERROR: str | None = None


#: The four annotations MyThes puts after a sense member, and nothing else --
#: verified against the whole shipped data file, where these are the *only*
#: parentheticals that appear at all. An unmarked member is a plain synonym.
#:
#: The marker is not decoration. It is the difference between a word that can
#: replace the headword and a word that means the opposite, and dropping it (as
#: this module did until 2026-08-26) puts 13,060 antonyms across 9,667
#: headwords into the synonym list -- "heavy" offered for "light", "decrease"
#: for "increase". Nothing announces that, and a writer who takes one has
#: inverted their own sentence.
_RELATION_MARKERS = {
    "similar term": "similar",
    "generic term": "broader",
    "antonym": "antonym",
    "related term": "related",
}


@dataclass(frozen=True, slots=True)
class Meaning:
    """One sense of a word, with its part of speech and its members by relation.

    ``synonyms`` holds what can actually stand in for the headword: the
    unmarked members plus MyThes' "similar term" and "related term". The other
    two relations are real and useful but are *not* substitutes, so they are
    kept apart rather than merged into one list a caller presents as equals.

    Related terms belong with the synonyms, and the evidence for that is
    "happy": its primary sense's unmarked members are *blessed, blissful,
    bright, golden, halcyon* -- while *cheerful, glad, joyful, elated* are all
    marked "(related term)". Filing those elsewhere would delete the useful
    answer for the word.
    """

    part_of_speech: str  # e.g. "noun", "verb", "adj", "adv"
    synonyms: tuple[str, ...]
    #: Opposites. Never offer these as synonyms.
    antonyms: tuple[str, ...] = ()
    #: Hypernyms -- broader categories the headword belongs to ("city" for
    #: "The Hague"). Informative, but substituting one loses the meaning.
    broader: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ThesaurusEntry:
    word: str
    meanings: tuple[Meaning, ...]

    @property
    def all_synonyms(self) -> tuple[str, ...]:
        """Every synonym across every sense, deduplicated, in file order.

        Substitutes only -- antonyms and broader terms are reached through
        :attr:`all_antonyms` and :attr:`all_broader`. A caller wanting
        "everything about this word" wants the senses, not a longer flat list.
        """
        return self._flatten(lambda meaning: meaning.synonyms)

    @property
    def all_antonyms(self) -> tuple[str, ...]:
        """Every antonym across every sense, deduplicated, in file order."""
        return self._flatten(lambda meaning: meaning.antonyms)

    @property
    def all_broader(self) -> tuple[str, ...]:
        """Every broader (generic) term across every sense."""
        return self._flatten(lambda meaning: meaning.broader)

    def _flatten(self, pick: Callable[[Meaning], tuple[str, ...]]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for meaning in self.meanings:
            for term in pick(meaning):
                key = term.lower()
                if key in seen:
                    continue
                seen.add(key)
                ordered.append(term)
        return tuple(ordered)


#: MyThes writes four, and only four, parts of speech. Spelled out because
#: these are read aloud: "adjective" is a word, "adj" is a noise.
_POS_NAMES = {"adj": "adjective", "adv": "adverb", "noun": "noun", "verb": "verb"}

#: How many terms a sense shows in its own row before saying "N more". Long
#: enough to tell senses apart, short enough that arrowing 45 of them is not
#: wading: a row has to stay near three seconds at a normal speech rate, and
#: "big" has a sense with 87 members.
_PREVIEW_TERMS = 4


@dataclass(frozen=True, slots=True)
class SenseRow:
    """One sense, ready for a two-pane picker.

    ``label`` is the row in the sense list. ``rows`` are the ``(label, term)``
    pairs for the synonym pane when this sense is chosen -- two different
    strings on purpose, because the labels carry a prefix and replacing "light"
    with "opposite: heavy" would be a funny bug in a serious place.
    """

    label: str
    part_of_speech: str
    rows: tuple[tuple[str, str], ...]


def sense_rows(entry: ThesaurusEntry) -> tuple[SenseRow, ...]:
    """Group *entry* by sense for a picker. Pure, and wx-free so it can be tested.

    A flat list is what this replaced, and it was the wrong shape: "light" has
    46 senses and 168 members, and presenting them as one list mixes weight,
    colour and illumination with no boundary between them.

    Three rules, each earned:

    * **A sense with nothing but antonyms is dropped.** 1,191 senses corpus-wide
      are antonym-only; one of them is why "light" used to offer "heavy" as its
      own sense. Every remaining row can be acted on.
    * **The part of speech leads the row**, spelled out. Not a bracketed suffix:
      a native list box does first-character type-ahead, so with the part of
      speech first, ``n`` jumps to the noun senses and ``v`` to the verbs. A
      free filter, no control and no code.
    * **The preview falls back to broader terms** when a sense has no
      substitutes of its own, and says so. Those senses are real -- dropping
      them loses "in a new light" -- but a hypernym is not a synonym and the row
      must not imply it is.

    Position ("3 of 45") is deliberately absent: screen readers announce list
    position themselves, and putting it in the row text says it twice.
    """
    senses: list[SenseRow] = []
    for meaning in entry.meanings:
        if not meaning.synonyms and not meaning.broader:
            continue  # antonym-only: nothing here can be acted on
        pos = _POS_NAMES.get(meaning.part_of_speech, meaning.part_of_speech or "other")
        preview_from = meaning.synonyms or meaning.broader
        qualifier = "" if meaning.synonyms else " (broader)"
        shown = list(preview_from[:_PREVIEW_TERMS])
        remaining = len(preview_from) - len(shown)
        if remaining > 0:
            shown.append(f"{remaining} more")
        rows: list[tuple[str, str]] = [(term, term) for term in meaning.synonyms]
        rows.extend((f"broader: {term}", term) for term in meaning.broader)
        rows.extend((f"opposite: {term}", term) for term in meaning.antonyms)
        senses.append(
            SenseRow(
                label=f"{pos}{qualifier}: {', '.join(shown)}",
                part_of_speech=pos,
                rows=tuple(rows),
            )
        )
    return tuple(senses)


def is_available() -> bool:
    """Return True when the thesaurus data file is present on disk."""
    return _DATA_PATH.is_file()


def data_path() -> Path:
    """Return the absolute path to the expected data file (may not exist)."""
    return _DATA_PATH


def load_error() -> str | None:
    """Return the parse error message from the last load attempt, if any."""
    return _LOAD_ERROR


def _ensure_loaded() -> dict[str, list[Meaning]]:
    global _INDEX, _LOAD_ERROR
    if _INDEX is not None:
        return _INDEX
    with _LOAD_LOCK:
        if _INDEX is not None:
            return _INDEX
        if not _DATA_PATH.is_file():
            _INDEX = {}
            _LOAD_ERROR = f"Thesaurus data file not found at {_DATA_PATH}"
            return _INDEX
        try:
            text = _DATA_PATH.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            _INDEX = {}
            _LOAD_ERROR = f"Could not read thesaurus data: {error}"
            return _INDEX
        try:
            _INDEX = _parse_mythes(text)
            _LOAD_ERROR = None
        except Exception as error:  # pragma: no cover - data should be valid
            _INDEX = {}
            _LOAD_ERROR = f"Thesaurus data parse error: {error}"
        return _INDEX


def _parse_mythes(text: str) -> dict[str, list[Meaning]]:
    index: dict[str, list[Meaning]] = {}
    lines = text.splitlines()
    # First line is the encoding declaration ("UTF-8"); skip it.
    cursor = 1 if lines and lines[0].strip().lower() == "utf-8" else 0
    while cursor < len(lines):
        header = lines[cursor].strip()
        cursor += 1
        if not header or "|" not in header:
            continue
        word_part, _, count_part = header.partition("|")
        word = word_part.strip().lower()
        try:
            meaning_count = int(count_part.strip())
        except ValueError:
            continue
        meanings: list[Meaning] = []
        for _ in range(meaning_count):
            if cursor >= len(lines):
                break
            sense_line = lines[cursor].rstrip()
            cursor += 1
            parts = sense_line.split("|")
            if not parts:
                continue
            raw_pos = parts[0].strip()
            # Strip surrounding parens if present: "(noun)" -> "noun".
            if raw_pos.startswith("(") and raw_pos.endswith(")"):
                raw_pos = raw_pos[1:-1].strip()
            buckets: dict[str, list[str]] = {"synonym": [], "antonym": [], "broader": []}
            for member in parts[1:]:
                term, relation = _split_relation(member)
                if not term:
                    continue
                # "similar" and "related" can stand in for the headword;
                # "broader" and "antonym" cannot. See Meaning's docstring.
                substitutable = relation in ("", "similar", "related")
                buckets["synonym" if substitutable else relation].append(term)
            if any(buckets.values()):
                meanings.append(
                    Meaning(
                        part_of_speech=raw_pos or "",
                        synonyms=tuple(buckets["synonym"]),
                        antonyms=tuple(buckets["antonym"]),
                        broader=tuple(buckets["broader"]),
                    )
                )
        if word and meanings:
            # A headword may appear more than once across senses; merge.
            existing = index.get(word)
            if existing is None:
                index[word] = meanings
            else:
                existing.extend(meanings)
    return index


def _split_relation(raw: str) -> tuple[str, str]:
    """Split a MyThes sense member into ``(term, relation)``.

    ``"capital (generic term)"`` becomes ``("capital", "broader")``;
    ``"heavy (antonym)"`` becomes ``("heavy", "antonym")``; an unmarked member
    becomes ``(term, "")``, meaning a plain synonym.

    This replaces an earlier ``_clean_synonym`` which dropped the annotation
    entirely "so the suggestion list reads cleanly". It did read cleanly, and
    it was wrong: the annotation is the only thing distinguishing a substitute
    from its opposite, and discarding it offered "heavy" as a synonym for
    "light".

    An unrecognised parenthetical is left as part of the term rather than
    guessed at. None exists in the shipped data -- the four markers in
    :data:`_RELATION_MARKERS` are the complete vocabulary -- so this is a guard
    against a future data file rather than a live case, and the safe failure is
    a slightly odd term rather than a silently miscategorised one.
    """
    text = raw.strip()
    if not text or not text.endswith(")"):
        return text, ""
    head, sep, marker = text.rpartition("(")
    if not sep:
        return text, ""
    relation = _RELATION_MARKERS.get(marker[:-1].strip().lower())
    if relation is None:
        return text, ""
    term = head.strip()
    return (term, relation) if term else ("", "")


def preload() -> None:
    """Warm the thesaurus index so the first lookup does not stall.

    Safe to call from a background thread at startup; ``_ensure_loaded`` is
    idempotent and guarded by ``_LOAD_LOCK``, so repeat calls are cheap no-ops
    once the index is in memory.
    """
    _ensure_loaded()


def reset_caches() -> None:
    """Drop the thesaurus module caches so callers can re-measure cold start.

    N-6: the perf-budget tests previously poked ``_INDEX`` and
    ``_LOAD_ERROR`` by hand. This public helper is the supported entry
    point for "make thesaurus cold again".
    """
    global _INDEX, _LOAD_ERROR
    with _LOAD_LOCK:
        _INDEX = None
        _LOAD_ERROR = None


def lookup(word: str) -> ThesaurusEntry | None:
    """Return the thesaurus entry for *word*, or ``None`` if not found."""
    if not word or not word.strip():
        return None
    cleaned = word.strip().lower()
    index = _ensure_loaded()
    meanings = index.get(cleaned)
    if meanings is None:
        # Try a naive singularisation for plural lookups (cats -> cat).
        if cleaned.endswith("s") and len(cleaned) > 3:
            meanings = index.get(cleaned[:-1])
        if meanings is None:
            return None
    return ThesaurusEntry(word=cleaned, meanings=tuple(meanings))


def word_at(text: str, position: int) -> tuple[str, int, int] | None:
    """Return ``(word, start, end)`` for the word under *position* in *text*.

    Returns ``None`` if the position isn't inside an alphabetic word. Used by
    the UI to look up the word at the caret without requiring a selection.
    """
    if not text or position < 0 or position > len(text):
        return None
    if position == len(text) and position > 0:
        position -= 1
    if not _is_word_char(text[position]):
        # Try the character just before the caret (typical when caret sits
        # immediately after a word).
        if position > 0 and _is_word_char(text[position - 1]):
            position -= 1
        else:
            return None
    start = position
    while start > 0 and _is_word_char(text[start - 1]):
        start -= 1
    end = position
    while end < len(text) and _is_word_char(text[end]):
        end += 1
    if start == end:
        return None
    return text[start:end], start, end


def _is_word_char(char: str) -> bool:
    return char.isalpha() or char == "'"
