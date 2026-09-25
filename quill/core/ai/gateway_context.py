"""What gets sent, decided on this computer before any request exists.

The cheapest token is the one never sent, and everything expensive about hosted
AI is decided here rather than on the server. Three jobs, all pure and all
wx-free:

**Resolve what the command acts on.** The selection if there is one, otherwise
the paragraph the cursor is in, otherwise -- in a document with headings -- the
section under the nearest heading above. **Never the whole document.** That is
a cost rule and a correctness rule at once: a summary of a whole file is rarely
what somebody pressing Summarize on a paragraph wanted.

**Find the parts of a document that answer a question.** Plain keyword overlap,
scored locally. No embeddings, no model call, no extra dependency, no second
round trip. It is not as good as a real retriever and it does not need to be:
the job is to pick three passages out of a document somebody has open, and the
person asking already knows roughly where the answer is.

**Refuse too much before it costs anything.** The server enforces the real
boundary -- this is a courtesy that saves a round trip and, more importantly,
lets the refusal name a *number of words* rather than a number of tokens.

Nobody thinks in tokens, so nothing in this module reports them to a person.
:func:`words_in` and the ``*_words`` fields are what the messages use.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

__all__ = [
    "Excerpt",
    "MAX_SCAN_CHARS",
    "Retrieval",
    "Scope",
    "SCOPE_LABELS",
    "chunk_document",
    "estimate_tokens",
    "pick_excerpts",
    "resolve_scope",
    "scopes_available",
    "words_for_tokens",
    "words_in",
]

#: Four characters to a token, which is the provider's own rule of thumb for
#: English prose and deliberately an over-estimate. Being conservative here can
#: only ever refuse a borderline passage slightly early; the opposite error
#: sends something too big and wastes the round trip.
_CHARS_PER_TOKEN = 4

#: Tokens to words. Only ever used to *say* a limit out loud.
_WORDS_PER_TOKEN = 0.75

#: A paragraph break. Two newlines, or one newline in a document that uses
#: single-spaced paragraphs -- both shapes appear in plain text files.
_PARA_BREAK = re.compile(r"\n\s*\n")

#: Markdown and plain-text heading shapes. QUILL Lite documents are plain text,
#: Markdown or RTF; this catches the first two, and an RTF document's headings
#: arrive already split by the caller.
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$|^(.+)\n([=-]{3,})$", re.M)

_WORD = re.compile(r"[A-Za-z0-9']+")

#: Spelled as constants because the generator that joins with them is
#: written into this file by tooling often enough that an escaped "\n"
#: has collapsed into a real newline in it before now.
NEWLINE = chr(10)
NEWLINES = NEWLINE * 2

#: Words too common to tell two passages apart. Deliberately short: a long stop
#: list starts throwing away the words that carry a question's meaning ("how
#: many", "who", "not"), and a question is usually eight words of which six are
#: doing work.
_STOPWORDS = frozenset({
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "his",
    "i",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "our",
    "she",
    "that",
    "the",
    "their",
    "them",
    "there",
    "these",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "will",
    "with",
    "you",
    "your",
})

#: The three things a command can act on, cheapest first.
Scope = str
SCOPE_SELECTION: Scope = "selection"
SCOPE_PARAGRAPH: Scope = "paragraph"
SCOPE_SECTION: Scope = "section"

#: What each scope is called in a control a person reads. Written once here so
#: the pad's chooser, its summary line and any message about size all say the
#: same words.
SCOPE_LABELS: dict[Scope, str] = {
    SCOPE_SELECTION: "What I have selected",
    SCOPE_PARAGRAPH: "This paragraph",
    SCOPE_SECTION: "This section",
}


def words_in(text: str) -> int:
    """How many words *text* has, counted the way QUILL counts them."""
    return len(text.split())


def estimate_tokens(text: str) -> int:
    """A conservative token estimate. Never shown to a person."""
    return max(1, len(text) // _CHARS_PER_TOKEN)


def words_for_tokens(tokens: int) -> int:
    """Roughly how many words a token limit is, rounded to something speakable.

    The number a refusal message quotes. "About 1,100 words" is a sentence
    somebody can act on; "1,500 tokens" is a sentence they have to look up.
    """
    words = tokens * _WORDS_PER_TOKEN
    return int(round(words / 50.0) * 50) if words >= 100 else int(round(words / 10.0) * 10)


# --------------------------------------------------------------------------- #
# What the command acts on
# --------------------------------------------------------------------------- #


def _paragraph_at(text: str, position: int) -> str:
    """The paragraph containing *position*.

    Falls back to the whole of a document that has no paragraph breaks in it --
    a one-paragraph file is still one paragraph, and the size check downstream
    is what stops a very long one.
    """
    if not text:
        return ""
    position = max(0, min(position, len(text)))
    starts = [0]
    for match in _PARA_BREAK.finditer(text):
        starts.append(match.end())
    starts.append(len(text) + 1)

    for index in range(len(starts) - 1):
        if starts[index] <= position < starts[index + 1]:
            chunk = text[starts[index] : starts[index + 1] - 1]
            return chunk.strip()
    return text.strip()


def _heading_positions(text: str) -> list[int]:
    return sorted({match.start() for match in _HEADING.finditer(text)})


def _section_at(text: str, position: int) -> str:
    """From the nearest heading at or above *position* to the next one.

    Returns "" when the document has no headings, which is how
    :func:`scopes_available` knows not to offer the choice.
    """
    positions = _heading_positions(text)
    if not positions:
        return ""
    position = max(0, min(position, len(text)))
    start = 0
    for heading_start in positions:
        if heading_start <= position:
            start = heading_start
        else:
            break
    end = len(text)
    for heading_start in positions:
        if heading_start > start:
            end = heading_start
            break
    return text[start:end].strip()


def scopes_available(text: str, selection: str, position: int) -> list[Scope]:
    """Which scopes this document and cursor actually offer, best first.

    The pad shows a chooser only when there is more than one. A control that
    always contains a single option is a stop on every Tab cycle forever, for
    a choice that was never a choice.
    """
    available: list[Scope] = []
    if selection.strip():
        available.append(SCOPE_SELECTION)
    if _paragraph_at(text, position):
        available.append(SCOPE_PARAGRAPH)
    if _section_at(text, position):
        available.append(SCOPE_SECTION)
    return available


def resolve_scope(text: str, selection: str, position: int, scope: Scope = "") -> tuple[Scope, str]:
    """What to send, and which scope it came from.

    With *scope* empty this picks the best available -- selection, else
    paragraph, else section. With *scope* named it honours the choice, falling
    back if that scope turns out to be empty, so a stale chooser can never send
    nothing at all.
    """
    available = scopes_available(text, selection, position)
    if not available:
        return "", ""

    chosen = scope if scope in available else available[0]
    if chosen == SCOPE_SELECTION:
        return chosen, selection.strip()
    if chosen == SCOPE_PARAGRAPH:
        return chosen, _paragraph_at(text, position)
    return chosen, _section_at(text, position)


# --------------------------------------------------------------------------- #
# Finding the parts of a document that answer a question
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class Excerpt:
    """One passage chosen to answer a question, and where it came from.

    ``heading`` is what the pad shows above it. Showing the excerpts before
    sending is not a debug affordance: it is the only way somebody can tell
    "the AI got it wrong" apart from "it never saw the right paragraph", and
    that distinction decides whether they rephrase the question or give up on
    the feature.
    """

    heading: str
    text: str
    score: float = 0.0

    @property
    def words(self) -> int:
        return words_in(self.text)


@dataclass(frozen=True, slots=True)
class Retrieval:
    """What was found, and how much of the document was looked at.

    The second half exists because of :data:`MAX_SCAN_CHARS`. A cap that is not
    reported is a silent truncation, and a silent truncation here reads as "the
    AI could not find it" when the truth is "nobody looked there" -- which sends
    somebody rewording a question that was fine.
    """

    excerpts: list[Excerpt]
    scanned_chars: int = 0
    total_chars: int = 0

    @property
    def scanned_all(self) -> bool:
        return self.scanned_chars >= self.total_chars

    def note(self) -> str:
        """A sentence for the pad when only part of the document was searched."""
        if self.scanned_all:
            return ""
        return (
            f"This document is very long, so QUILL Lite searched the first "
            f"{words_for_tokens(self.scanned_chars // _CHARS_PER_TOKEN):,} words "
            "of it. Put the cursor nearer what you are asking about, or ask about "
            "a selection instead."
        )


#: How much of a document retrieval will read. Generous enough that ordinary
#: documents are never touched by it -- roughly a 400-page book -- and bounded
#: because the alternative is a freeze.
#:
#: This is not a guess. Scoring a 1 MB document by materialising every chunk
#: took **three seconds on the UI thread**, on every refresh of the pad's
#: preview, in an editor whose whole promise is that it never stops accepting
#: keystrokes. QUILL Lite opens files far larger than that.
MAX_SCAN_CHARS = 2_000_000


def _terms(text: str) -> list[str]:
    return [word for word in _WORD.findall(text.lower()) if word not in _STOPWORDS]


def _iter_chunks(text: str, target_words: int = 180) -> Iterator[tuple[str, str]]:
    """Yield ``(heading, chunk_text)`` without building a list of all of them.

    A generator rather than a list, and that is the whole point: a 1 MB document
    is twenty thousand chunks, and twenty thousand dataclasses is where the
    three seconds went.
    """
    heading_positions = set(_heading_positions(text))
    current: list[str] = []
    current_words = 0
    current_heading = ""

    cursor = 0
    for block in _PARA_BREAK.split(text):
        stripped = block.strip()
        block_start = text.find(block, cursor)
        cursor = block_start + len(block) if block_start >= 0 else cursor
        if not stripped:
            continue

        if block_start in heading_positions or _HEADING.match(stripped):
            if current:
                yield current_heading, NEWLINES.join(current)
                current, current_words = [], 0
            current_heading = stripped.lstrip("#").strip().split(NEWLINE)[0]

        current.append(stripped)
        current_words += words_in(stripped)
        if current_words >= target_words:
            yield current_heading, NEWLINES.join(current)
            current, current_words = [], 0

    if current:
        yield current_heading, NEWLINES.join(current)


def chunk_document(text: str, *, target_words: int = 180) -> list[Excerpt]:
    """Split *text* into passages, keeping the heading each one sits under.

    Paragraphs are the unit, gathered up to roughly *target_words* so a chunk is
    big enough to contain an answer and small enough that three of them fit
    inside the size limit. Headings are carried rather than discarded: an
    excerpt that announces which section it came from is one a person can place
    in their own document.

    Materialises everything, so it is for tests and small documents.
    :func:`pick_excerpts` streams instead.
    """
    if not text.strip():
        return []
    return [Excerpt(heading, body) for heading, body in _iter_chunks(text, target_words)]


def pick_excerpts(text: str, question: str, *, limit: int = 3) -> Retrieval:
    """The *limit* passages of *text* most likely to answer *question*.

    Keyword overlap, weighted so a term appearing in many passages counts for
    less than one appearing in a few -- the useful half of what a real ranker
    does, in one pass and no dependency.

    **One pass, bounded memory.** Only passages that share a word with the
    question are kept, which on a real document is a handful; the rest are
    scored and discarded as they go. The earlier version built an ``Excerpt``
    for every chunk in the document first, which cost three seconds on a 1 MB
    file -- on the UI thread, on every keystroke in the question box.

    A question with no meaningful words left after stop-words (somebody typed
    "what is it") keeps the opening passages instead. That is the right
    fallback: the top of a document is a better guess than nothing, and the pad
    shows what was chosen before anything is sent.
    """
    total = len(text)
    scanned = min(total, MAX_SCAN_CHARS)
    window = text[:scanned]
    if not window.strip():
        return Retrieval([], scanned, total)

    wanted = set(_terms(question))
    opening: list[Excerpt] = []
    candidates: list[tuple[str, str, set[str]]] = []
    spread: dict[str, int] = {}

    for heading, body in _iter_chunks(window):
        if len(opening) < limit:
            opening.append(Excerpt(heading, body))
        if not wanted:
            if len(opening) >= limit:
                break
            continue
        terms = set(_terms(heading + " " + body))
        hit = terms & wanted
        if not hit:
            continue
        for term in hit:
            spread[term] = spread.get(term, 0) + 1
        candidates.append((heading, body, terms))

    if not wanted or not candidates:
        return Retrieval(opening[:limit], scanned, total)

    scored: list[Excerpt] = []
    for heading, body, terms in candidates:
        score = sum(1.0 / spread[term] for term in terms & wanted)
        # A heading that matches is worth more than a body word that matches:
        # it is the author's own label for what this passage is about.
        if wanted & set(_terms(heading)):
            score += 0.5
        scored.append(Excerpt(heading, body, score))

    scored.sort(key=lambda item: item.score, reverse=True)
    return Retrieval(scored[:limit], scanned, total)


# --------------------------------------------------------------------------- #
# Refusing too much, before it costs anything
# --------------------------------------------------------------------------- #


def too_large(text: str, max_input_tokens: int) -> tuple[bool, int, int]:
    """``(is_too_large, words_here, words_allowed)``.

    The server checks this again and authoritatively -- that boundary is the
    real one and holds whatever the client does. This exists so the refusal can
    happen without a round trip, and so it can be phrased in words.
    """
    tokens = estimate_tokens(text)
    return tokens > max_input_tokens, words_in(text), words_for_tokens(max_input_tokens)
