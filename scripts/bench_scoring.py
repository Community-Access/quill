"""The benchmark's scoring pipeline (dict.md section 8, "Scoring pipeline").

Used by ``scripts/dictbench.py``; pure Python, no audio, no network.

1. **Normalize both sides** with one documented normalizer. The default is
   QUILL's own (``basic``): lower case, no punctuation, hyphens and
   apostrophes kept inside words, plus the Gutenberg pre-pass (hyphenated line
   breaks joined, lines unwrapped). Spanish also matches without accents, as
   ``dictbench`` always has. When Whisper's ``EnglishTextNormalizer`` is
   importable (the ``whisper_normalizer`` package, MIT) English uses it, and
   the result says which normalizer ran. Vendoring it under ``scripts/`` is
   still to do (design record section 26).
2. **Word errors** -- ``dictbench.word_errors`` on the normalized words.
3. **Punctuation and capitals**, on the *unnormalized* text: the words of the
   reference and of the output are aligned (difflib), and for every pair of
   words that matched, the mark after each is compared. Per-mark precision,
   recall and F1 for the full stop (``!`` counts as one), the comma, the
   question mark and the new paragraph; and the share of sentences the output
   starts with a capital. Quote marks are never scored; a reference that is
   mostly inside quotes is a *dialogue* segment and is reported apart.
4. **Limits**, said in every report: :data:`LIMITS`.
5. **Grouped**, never one average: :func:`grouped`.

``command_outcome`` is B-1c's measure: a spoken command either parsed as the
command, or -- the failure that matters -- was typed as words.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "LIMITS",
    "SCORED_MARKS",
    "MarkScore",
    "capital_rate",
    "command_outcome",
    "gutenberg_prepass",
    "is_dialogue",
    "normalizer",
    "punctuation_scores",
    "tokens",
]

#: The marks scored, by name. "!" is scored as a full stop; quote marks never.
SCORED_MARKS = ("period", "comma", "question", "paragraph")
_MARK_OF = {".": "period", "!": "period", ",": "comma", "?": "question"}
_QUOTES = '"“”«»„'
_WORD = re.compile(r"[\w][\w'’-]*", re.UNICODE)
_SENTENCE_END = re.compile(r"[.?!]+[\"”’)»]*\s+")

LIMITS = (
    "An author's punctuation is one reference, not the only correct one: commas, "
    "semicolons and dashes vary legitimately. Quote marks are not scored, and "
    "segments that are mostly dialogue are reported apart. Synthetic speech "
    "(B-1c) measures parsing and robustness only; its word errors are never "
    "accuracy."
)


def gutenberg_prepass(text: str) -> str:
    """Join words hyphenated across a line break, and unwrap lines into
    paragraphs (a blank line still separates two)."""
    text = re.sub(r"(\w)-\n\s*(\w)", r"\1\2", text.replace("\r\n", "\n"))
    paragraphs = re.split(r"\n\s*\n", text)
    return "\n\n".join(" ".join(p.split()) for p in paragraphs if p.strip())


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def basic_normalize(text: str, *, accents: bool = True) -> list[str]:
    text = text.lower().replace("’", "'")
    if not accents:
        text = _fold(text)
    return [w.strip("'-") for w in _WORD.findall(text.replace("_", " ")) if w.strip("'-")]


def normalizer(language: str = "en") -> tuple[str, Callable[[str], list[str]]]:
    """``(name, function)``: Whisper's English normalizer when installed,
    QUILL's basic one otherwise. Spanish is always basic, without accents."""
    if language.startswith("es"):
        return "basic, accents ignored", lambda text: basic_normalize(text, accents=False)
    try:
        from whisper_normalizer.english import (  # type: ignore[import-not-found]
            EnglishTextNormalizer,
        )
    except ImportError:
        return "basic", basic_normalize
    whisper = EnglishTextNormalizer()
    return "whisper-english", lambda text: whisper(text).split()


@dataclass(frozen=True, slots=True)
class Token:
    word: str  # normalized
    marks: frozenset[str]  # the scored marks right after it
    capital: bool  # it begins with an upper-case letter


def tokens(text: str) -> list[Token]:
    """*text*'s words, each with the scored marks that follow it."""
    found: list[Token] = []
    matches = list(_WORD.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        gap = text[match.end() : end]
        marks = {_MARK_OF[c] for c in gap if c in _MARK_OF}
        if "\n" in gap:  # unwrapped text: any line break is a paragraph
            marks.add("paragraph")
        word = _fold(match.group().lower().replace("’", "'")).strip("'-")
        if word:
            found.append(Token(word, frozenset(marks), match.group()[:1].isupper()))
    return found


@dataclass
class MarkScore:
    hits: int = 0  # the mark is in both, after the same word
    extra: int = 0  # written, but not in the reference there
    missed: int = 0  # in the reference, not written

    def add(self, other: MarkScore) -> None:
        self.hits += other.hits
        self.extra += other.extra
        self.missed += other.missed

    @property
    def precision(self) -> float | None:
        written = self.hits + self.extra
        return round(self.hits / written, 3) if written else None

    @property
    def recall(self) -> float | None:
        expected = self.hits + self.missed
        return round(self.hits / expected, 3) if expected else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if p is None or r is None or p + r == 0:
            return None if (p is None or r is None) else 0.0
        return round(2 * p * r / (p + r), 3)

    def as_dict(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "extra": self.extra,
            "missed": self.missed,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


def punctuation_scores(reference: str, heard: str) -> dict[str, MarkScore]:
    """Per-mark hits, extras and misses over the words both texts share."""
    ref, out = tokens(reference), tokens(heard)
    scores = {mark: MarkScore() for mark in SCORED_MARKS}
    matcher = difflib.SequenceMatcher(
        a=[t.word for t in ref], b=[t.word for t in out], autojunk=False
    )
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            said, wrote = ref[block.a + offset], out[block.b + offset]
            last_of_both = block.a + offset == len(ref) - 1 and block.b + offset == len(out) - 1
            for mark in SCORED_MARKS:
                if mark == "paragraph" and last_of_both:
                    continue  # a segment's end is not a paragraph decision
                in_ref, in_out = mark in said.marks, mark in wrote.marks
                if in_ref and in_out:
                    scores[mark].hits += 1
                elif in_out:
                    scores[mark].extra += 1
                elif in_ref:
                    scores[mark].missed += 1
    return scores


def capital_rate(text: str) -> tuple[int, int]:
    """``(sentences starting with a capital, sentences)`` in *text*."""
    sentences = [s.strip().lstrip('"“«¿¡(') for s in _SENTENCE_END.split(text) if s.strip()]
    starts = [s for s in sentences if s[:1].isalpha()]
    return sum(1 for s in starts if s[:1].isupper()), len(starts)


def is_dialogue(reference: str) -> bool:
    """Mostly inside quote marks: punctuation there is noisy, so reported apart."""
    inside = 0
    quoted = False
    words = 0
    for piece in re.split(f"([{_QUOTES}])", reference):
        if piece and piece in _QUOTES:
            quoted = not quoted
            continue
        count = len(_WORD.findall(piece))
        words += count
        inside += count if quoted else 0
    return words > 0 and inside / words > 0.5


@dataclass
class Totals:
    """Punctuation and capitals summed over many files."""

    marks: dict[str, MarkScore] = field(
        default_factory=lambda: {m: MarkScore() for m in SCORED_MARKS}
    )
    capitals: int = 0
    sentences: int = 0

    def add(self, reference: str, heard: str) -> None:
        for mark, score in punctuation_scores(reference, heard).items():
            self.marks[mark].add(score)
        capitals, sentences = capital_rate(heard)
        self.capitals += capitals
        self.sentences += sentences

    def as_dict(self) -> dict[str, Any]:
        return {
            "marks": {mark: score.as_dict() for mark, score in self.marks.items()},
            "sentences_starting_with_a_capital": (
                round(self.capitals / self.sentences, 3) if self.sentences else None
            ),
        }


def command_outcome(
    reference: str, heard: str, language: str = "en", command_word: str = "quill"
) -> str:
    """For a spoken command or layout word (a reference written ``!scratch that``
    or ``!new paragraph``):

    * ``"parsed"`` -- QUILL's parser read the output as the same command, or
      the same marks with no words;
    * ``"other command"`` -- as a different command or different marks;
    * ``"typed"`` -- with words to write: the command would have been typed;
    * ``"nothing"`` -- the engine wrote nothing.

    A reference that opens with the D-1 *command_word* needs the output to
    open with it too (the controller takes the word off before parsing).
    """
    from quill.core.windows_dictation.parser import RecognizedPhrase, parse, words_from_text
    from quill.core.windows_dictation.targets import number_from
    from quill.core.windows_dictation.vocabulary import Command, vocabulary_for

    if not basic_normalize(heard):
        return "nothing"
    said = basic_normalize(reference)
    if said[:1] == [command_word]:
        got_words = basic_normalize(heard)
        if got_words[:1] != [command_word]:
            return "typed"
        reference, heard = " ".join(said[1:]), " ".join(got_words[1:])
    vocabulary = vocabulary_for(language)

    def meaning(text: str) -> tuple[str, Any]:
        parsed = parse(RecognizedPhrase(words_from_text(text)), vocabulary=vocabulary)
        if parsed.command is Command.PASTE_SLOT:
            # QUILL reads the slot through number_from, which takes "three"
            # and "3" alike: an engine that writes the digit has not failed.
            return "command", (parsed.command, number_from(parsed.argument))
        if parsed.command is not None:
            return "command", (parsed.command, tuple(parsed.argument))
        if any(piece.mark is None for piece in parsed.pieces):
            return "words", None
        return "marks", tuple(piece.text for piece in parsed.pieces)

    wanted, got = meaning(reference), meaning(heard)
    if got == wanted:
        return "parsed"
    return "typed" if got[0] == "words" else "other command"


def model_family(model_id: str) -> str:
    """The family a catalogue id belongs to, for cutoffs and contamination:
    ``distil_small_en`` and ``whisper_turbo`` are both ``whisper``."""
    head = model_id.lower().split("_")[0].split("-")[0]
    return "whisper" if head == "distil" else head


def grouped(
    results: Iterable[Any], key: Callable[[Any], str], summarise: Callable[[list[Any]], Any]
) -> dict[str, Any]:
    """One summary per group (speaker, accent, language, gender, group) --
    dict.md asks for "never one average"."""
    groups: dict[str, list[Any]] = {}
    for result in results:
        groups.setdefault(key(result) or "(not given)", []).append(result)
    return {name: summarise(members) for name, members in sorted(groups.items())}
