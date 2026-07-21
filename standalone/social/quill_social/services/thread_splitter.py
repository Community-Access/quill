"""Intelligent long-post splitting (PRD 16.1).

Splits a long composition into an ordered list of segments, each within a
network's character limit, following the PRD's boundary preferences:

- Prefer paragraph boundaries, then sentence boundaries, then word boundaries.
- Never break inside a link, @mention, #hashtag, Markdown link, or inline code.
- Support numbering such as ``1/5`` (reserved out of the limit so a numbered
  segment never overflows).
- Recalculate on demand -- the function is pure, so re-running is the recompute.
- Expose every segment plus whether any segment had to exceed the limit because
  a single atomic token (a long URL) could not be broken.

The character counter is pluggable: Mastodon counts every URL as 23 characters
and a ``@user@domain`` mention as just ``@user`` (PRD 22), so an adapter can
pass its own counter. The default counts Unicode code points.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

Counter = Callable[[str], int]

# Spans that must never be split internally and must not contain a break point.
# Order matters: Markdown links before bare URLs so the whole [text](url) is one
# atom.
_PROTECTED = re.compile(
    r"""
    (\[[^\]]+\]\([^)]+\))          # [markdown](link)
    | (`[^`]+`)                    # `inline code`
    | (https?://\S+)               # http(s) URL
    | (www\.\S+)                   # bare www URL
    | (@[\w.]+(?:@[\w.]+)?)        # @mention or @user@domain
    | (\#[^\s#]+)                  # #hashtag
    """,
    re.VERBOSE,
)

# Priority of a candidate cut point; higher wins when several fit.
_P_PARAGRAPH = 4
_P_SENTENCE = 3
_P_NEWLINE = 2
_P_WORD = 1
_P_TOKEN = 0  # a safe cut immediately after a protected token


@dataclass
class Segment:
    text: str
    index: int  # 1-based
    length: int
    over_limit: bool = False


@dataclass
class ThreadSplit:
    segments: list[Segment] = field(default_factory=list)
    limit: int = 0
    numbered: bool = False
    any_over_limit: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.segments)

    def texts(self) -> list[str]:
        return [s.text for s in self.segments]


def _protected_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _PROTECTED.finditer(text)]


def _inside_protected(pos: int, spans: list[tuple[int, int]]) -> bool:
    for a, b in spans:
        if a < pos < b:
            return True
    return False


def _candidate_cuts(text: str, spans: list[tuple[int, int]]) -> dict[int, int]:
    """Map a cut position -> priority. A cut at ``i`` splits before ``text[i]``.

    Cuts never land inside a protected span. Whitespace runs collapse to a
    single cut at the start of the whitespace so trailing spaces are stripped
    from segments by the packer.
    """
    cuts: dict[int, int] = {}

    def offer(pos: int, prio: int) -> None:
        if pos <= 0 or pos >= len(text):
            return
        if _inside_protected(pos, spans):
            return
        cuts[pos] = max(cuts.get(pos, -1), prio)

    # Paragraph and newline boundaries.
    for m in re.finditer(r"\n[ \t]*\n", text):
        offer(m.start(), _P_PARAGRAPH)
    for m in re.finditer(r"\n", text):
        offer(m.start(), _P_NEWLINE)
    # Sentence boundaries: end punctuation followed by whitespace.
    for m in re.finditer(r"[.!?][\"')\]]*\s", text):
        offer(m.end() - 1, _P_SENTENCE)  # cut at the whitespace after the sentence
    # Word boundaries: any run of whitespace.
    for m in re.finditer(r"\s+", text):
        offer(m.start(), _P_WORD)
    # Safe cut right after a protected token (usually already a word boundary).
    for _a, b in spans:
        offer(b, _P_TOKEN)
    return cuts


def _pack(text: str, limit: int, counter: Counter) -> tuple[list[str], bool]:
    """Greedy pack ``text`` into <= ``limit`` chunks. Returns (chunks, over_flag)."""
    text = text.strip()
    if not text:
        return [], False
    spans = _protected_spans(text)
    cuts = _candidate_cuts(text, spans)
    sorted_positions = sorted(cuts)

    segments: list[str] = []
    any_over = False
    start = 0
    n = len(text)

    while start < n:
        # Skip leading whitespace so a segment never begins mid-space.
        while start < n and text[start].isspace():
            start += 1
        if start >= n:
            break
        remaining = text[start:].rstrip()
        if counter(remaining) <= limit:
            segments.append(remaining)
            break

        # Candidate cut positions strictly after start.
        window = [p for p in sorted_positions if p > start]
        best_fit: int | None = None
        best_prio = -1
        fallback: int | None = None  # first cut > start, used if nothing fits
        for pos in window:
            chunk = text[start:pos].rstrip()
            if fallback is None:
                fallback = pos
            if counter(chunk) <= limit:
                prio = cuts[pos]
                # Prefer higher priority; among equal priority prefer the
                # farthest position (pack fuller segments).
                if prio > best_prio or (prio == best_prio and best_fit is not None
                                        and pos > best_fit):
                    best_prio = prio
                    best_fit = pos
            else:
                # Positions only get longer; once we overflow we can stop
                # searching for a *fitting* cut, but we already captured the
                # best so far.
                break

        if best_fit is not None:
            chunk = text[start:best_fit].rstrip()
            segments.append(chunk)
            start = best_fit
            continue

        # Nothing fits: a single atomic token (e.g. a long URL) is longer than
        # the limit. Emit up to the next safe cut and flag the overflow rather
        # than shredding the token (PRD 16.1: never break a link).
        if fallback is not None:
            chunk = text[start:fallback].rstrip()
        else:
            chunk = remaining
            fallback = n
        segments.append(chunk)
        any_over = any_over or counter(chunk) > limit
        start = fallback

    return segments, any_over


def split_thread(
    text: str,
    limit: int,
    *,
    numbering: bool = True,
    counter: Counter = len,
) -> ThreadSplit:
    """Split ``text`` into a numbered, limit-respecting thread.

    ``numbering`` reserves room for a trailing `` i/n`` marker out of the limit
    so a numbered segment never overflows. The reserve depends on the final
    count, so we iterate to a fixed point (bounded), which converges in one or
    two passes for any realistic input.
    """
    result = ThreadSplit(limit=limit, numbered=numbering)
    if limit <= 0:
        result.warnings.append("limit must be positive")
        return result
    text = text.strip()
    if not text:
        return result

    chunks: list[str] = []
    any_over = False
    guess = 1
    # Fixed-point iteration: re-pack reserving room for the trailing " i/n"
    # marker until the segment count stabilizes. Reserving len(" n/n") is the
    # worst-case width, so once the count is stable every numbered body fits.
    for _ in range(8):
        reserve = len(f" {guess}/{guess}") if numbering else 0
        effective = max(1, limit - reserve)
        chunks, any_over = _pack(text, effective, counter)
        new_guess = len(chunks)
        if not numbering or new_guess == guess:
            break
        guess = new_guess

    total = len(chunks)
    for i, chunk in enumerate(chunks, start=1):
        body = f"{chunk} {i}/{total}" if numbering and total > 1 else chunk
        over = counter(body) > limit
        result.segments.append(
            Segment(text=body, index=i, length=counter(body), over_limit=over)
        )
        result.any_over_limit = result.any_over_limit or over
    result.any_over_limit = result.any_over_limit or any_over
    if result.any_over_limit:
        result.warnings.append(
            "a segment exceeds the limit because an unbreakable token "
            "(such as a long link) is longer than the limit"
        )
    return result


def mastodon_counter(text: str) -> int:
    """Mastodon's weighting: URLs count as 23, mentions drop the domain (PRD 22)."""
    weighted = text
    weighted = re.sub(r"https?://\S+", "x" * 23, weighted)
    weighted = re.sub(r"www\.\S+", "x" * 23, weighted)
    weighted = re.sub(r"(@[\w.]+)@[\w.]+", r"\1", weighted)
    return len(weighted)
