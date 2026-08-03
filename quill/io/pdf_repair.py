"""Repair heuristics for text pulled out of a PDF (extraction phase 2).

A PDF stores glyphs and positions, not sentences. Whatever an extractor hands
back is therefore a *rendering* of the page rather than the author's text: words
are broken across lines by hyphens that were never typed, every visual line is a
separate line of text, display headings arrive letter-spaced, and ligatures
often come through as private-use codepoints that a screen reader reads as
nothing at all. :func:`repair_extracted_text` undoes those four artefacts.

Every repair here is deliberately conservative: it must be safe to run over text
that is already clean, so each heuristic refuses to act unless the damage is
unambiguous, and running the pipeline twice produces the same result as running
it once. When a case is genuinely ambiguous the rule is to leave the text alone
-- a missed repair is a small annoyance, but a wrong "repair" silently changes
what the document says.

The module is pure text in / text out: no wx, no I/O, no new dependencies.
"""

from __future__ import annotations

import re

# --- private-use glyph repair -------------------------------------------------

# The Unicode Private Use Area. Codepoints here have no agreed meaning: what
# they render as depends entirely on the font the PDF embedded, so once the text
# is extracted the glyph is gone and only an unassigned codepoint remains. A
# screen reader announces nothing (or "unknown character") for these.
_PUA_FIRST = "\ue000"
_PUA_LAST = "\uf8ff"

# Ligature codepoints seen in the private-use runs of subsetted PDF fonts. Two
# layouts dominate: the Adobe/Type-1 style run that starts at U+F000, and the
# same ordering restarted at U+E000 by some LaTeX and font-subsetting toolchains.
# "th" has no Unicode codepoint at all, so a font that ligates it *must* put it
# in a private-use slot; it sits at the end of both runs.
_PUA_LIGATURES = {
    "\uf000": "ff",
    "\uf001": "fi",
    "\uf002": "fl",
    "\uf003": "ffi",
    "\uf004": "ffl",
    "\uf005": "ft",
    "\uf006": "st",
    "\uf007": "th",
    "\ue000": "ff",
    "\ue001": "fi",
    "\ue002": "fl",
    "\ue003": "ffi",
    "\ue004": "ffl",
    "\ue005": "ft",
    "\ue006": "st",
    "\ue007": "th",
}

# The real Unicode ligature block (U+FB00-U+FB06). These are legible in
# principle, but screen readers and find-in-document both handle the spelled-out
# letters far better, so they are normalized alongside the private-use ones.
_UNICODE_LIGATURES = {
    "ﬀ": "ff",
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "ﬅ": "st",  # long-s + t
    "ﬆ": "st",
}


def repair_private_use_glyphs(text: str) -> str:
    """Turn private-use ligature codepoints back into letters; drop the rest.

    The "fi" in an extracted PDF is often not U+FB01 but a private-use codepoint
    such as U+F001, which reads as silence. Known ligature slots are expanded to
    their letters (ff, fi, fl, ffi, ffl, ft, st, th); any other private-use
    character is removed, because an unmapped one carries no recoverable meaning
    and only adds noise to speech and search.
    """
    if not text:
        return text
    pieces: list[str] = []
    for character in text:
        replacement = _PUA_LIGATURES.get(character) or _UNICODE_LIGATURES.get(character)
        if replacement is not None:
            pieces.append(replacement)
        elif _PUA_FIRST <= character <= _PUA_LAST:
            continue  # unmapped private use: no meaning survived extraction
        else:
            pieces.append(character)
    return "".join(pieces)


# --- letter-spaced heading repair ---------------------------------------------

# A letter-spaced heading has to be long enough to be unmistakable. Three tokens
# ("A B testing") is still ordinary prose; four or more mostly single letters in
# a row is a typographic effect, not a sentence.
_MIN_SPACED_TOKENS = 4

# Share of whitespace-separated tokens on the line that must be a single
# character before the line is treated as letter-spaced. Below 1.0 so a stray
# word or a trailing number does not defeat the repair, but high enough that
# ordinary prose (where most tokens are whole words) never qualifies. Heuristic.
_SPACED_SINGLE_RATIO = 0.8

# Two or more spaces between letter groups is how a letter-spaced heading marks
# its word boundaries ("C H A P T E R  O N E").
_WORD_GAP = re.compile(r"\s{2,}")


def repair_spaced_headings(text: str) -> str:
    """Collapse letter-spaced display lines: "H E A D I N G" -> "HEADING".

    Designers space out display type, and the extractor faithfully reports each
    letter as its own word -- so the heading is spelled out one letter at a time
    by a screen reader and never matches a search. A line is only collapsed when
    it is overwhelmingly single characters separated by spaces, which leaves
    prose and short phrases such as "A B testing" untouched.
    """
    if not text:
        return text
    return "\n".join(_collapse_spaced_line(line) for line in text.split("\n"))


def _collapse_spaced_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return line
    tokens = stripped.split()
    if len(tokens) < _MIN_SPACED_TOKENS:
        return line
    singles = [token for token in tokens if len(token) == 1]
    if len(singles) / len(tokens) < _SPACED_SINGLE_RATIO:
        return line
    if not any(token.isalpha() for token in singles):
        return line  # spaced digits are data (a table row), not a heading
    words = ["".join(group.split()) for group in _WORD_GAP.split(stripped) if group.strip()]
    leading = line[: len(line) - len(line.lstrip())]
    return leading + " ".join(words)


# --- dehyphenation ------------------------------------------------------------

# What a PDF may leave at a line end when a word was split across lines: an
# ordinary hyphen-minus, a real Unicode hyphen, or a soft hyphen.
_LINE_END_HYPHENS = ("-", "‐", "\u00ad")


def dehyphenate(text: str) -> str:
    """Rejoin words the page layout split across lines.

    "inter-" followed by "national" becomes "international". The join only
    happens when the hyphen is almost certainly a typesetting artefact: the
    character before it is a letter, and the next line begins with a lowercase
    letter. A hyphen after a number ("2018-"), before a capitalized word
    ("Anglo-" / "Saxon"), or standing alone is meaningful punctuation, and is
    kept along with its line break.
    """
    if not text:
        return text
    lines = text.split("\n")
    joined: list[str] = []
    index = 0
    while index < len(lines):
        current = lines[index]
        while index + 1 < len(lines) and _hyphen_continues(current, lines[index + 1]):
            current = current.rstrip()[:-1] + lines[index + 1].lstrip()
            index += 1
        joined.append(current)
        index += 1
    return "\n".join(joined)


def _hyphen_continues(current: str, following: str) -> bool:
    stripped = current.rstrip()
    if not stripped.endswith(_LINE_END_HYPHENS):
        return False
    stem = stripped[:-1]
    if not stem or not stem[-1].isalpha():
        # A digit, a space, or a second hyphen before the break: real punctuation
        # (a number range, a dash, or an em dash typed as "--"), not a split word.
        return False
    continuation = following.lstrip()
    if not continuation:
        return False
    first = continuation[0]
    # An uppercase continuation means a proper compound (Anglo-Saxon), so the
    # hyphen belongs to the text and the two halves stay as they were written.
    return first.isalpha() and first.islower()


# --- paragraph reflow ---------------------------------------------------------

# Heuristic: a PDF extractor emits one line of text per line rendered on the
# page, so a paragraph arrives hard-wrapped at whatever width the page used --
# typically 60 to 90 characters at ordinary body sizes. The true wrap width is
# not recoverable from extracted text, so this is a tuned threshold rather than a
# measurement: a line that reaches it was almost certainly cut by the wrap and
# continues on the next line, while a line that stops well short of it was broken
# deliberately (a heading, a table row, an address, or the last line of a
# paragraph) and must keep its break.
_WRAP_WIDTH = 60

# Bullets and numbered markers that start a list item.
_LIST_ITEM = re.compile(r"^(?:[-*+•‣▪●·–—]\s+|\(?\d+[.)]\s+)")

# Sentence-ending punctuation, allowing for a closing quote or bracket after it.
_SENTENCE_END = re.compile("[.!?…][\"'”’)\\]]*$")


def reflow_paragraphs(text: str) -> str:
    """Rejoin hard-wrapped lines back into paragraphs.

    Each line is offered to :func:`_joins_previous_line`, which decides whether
    it continues the line above. Blank lines, list items, deliberately short
    lines, and a finished sentence followed by a capital all stop the join, so
    the document keeps its paragraph and list structure instead of melting into
    one block of text.
    """
    if not text:
        return text
    if "\f" in text:  # never join across a page boundary
        return "\f".join(reflow_paragraphs(page) for page in text.split("\f"))
    paragraphs: list[str] = []
    for line in text.split("\n"):
        if paragraphs and _joins_previous_line(paragraphs[-1], line):
            paragraphs[-1] = paragraphs[-1].rstrip() + " " + line.strip()
        else:
            paragraphs.append(line)
    return "\n".join(paragraphs)


def _joins_previous_line(previous: str, following: str) -> bool:
    """Return True when *following* is the continuation of wrapped *previous*."""
    above = previous.rstrip()
    below = following.strip()
    if not above or not below:
        return False  # a blank line always ends a paragraph
    if _LIST_ITEM.search(above) or _LIST_ITEM.search(below):
        return False  # list items are their own lines, wrapped or not
    if above.endswith(_LINE_END_HYPHENS):
        return False  # dehyphenate() deliberately kept this hyphen
    if len(above) < _WRAP_WIDTH:
        return False  # short line: the break was intentional
    if _SENTENCE_END.search(above) and below[:1].isupper():
        return False  # a finished sentence followed by a new one
    return True


# --- pipeline -----------------------------------------------------------------


def repair_extracted_text(text: str) -> str:
    """Run every PDF text repair, in the order they depend on each other.

    Glyphs are fixed first, so the later line-level tests see real letters;
    headings are collapsed before any joining, so a letter-spaced title is not
    mistaken for prose; hyphenated words are rejoined before reflow, so the wrap
    test sees whole words; reflow runs last, once the lines are trustworthy.

    Form feeds (QUILL's page separators) are hard boundaries: each page is
    repaired on its own, so nothing is ever joined across a page break.
    """
    if not text:
        return text
    if "\f" in text:
        return "\f".join(repair_extracted_text(page) for page in text.split("\f"))
    repaired = repair_private_use_glyphs(text)
    repaired = repair_spaced_headings(repaired)
    repaired = dehyphenate(repaired)
    return reflow_paragraphs(repaired)
