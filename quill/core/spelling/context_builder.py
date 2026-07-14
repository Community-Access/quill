"""Extract readable sentence context around a misspelled word."""

from __future__ import annotations

import re

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def build_context(
    text: str,
    word_start: int,
    word_end: int,
    max_chars: int = 900,
) -> tuple[str, int, int]:
    """Return (context_text, word_start_in_ctx, word_end_in_ctx).

    Extracts the sentence containing the word plus one adjacent sentence on
    each side, capped at *max_chars*. Falls back to a character window when
    sentence boundaries cannot be detected.
    """
    if not text:
        return ("", 0, 0)

    # Find sentence boundaries in a broad window first.
    window_radius = max_chars
    raw_start = max(0, word_start - window_radius)
    raw_end = min(len(text), word_end + window_radius)
    window = text[raw_start:raw_end]

    # Split window into sentences.
    sentences = _SENTENCE_END.split(window)
    if not sentences:
        return _character_window(text, word_start, word_end, max_chars)

    # Locate which sentence(s) contain the word (adjusted for window offset).
    adj_start = word_start - raw_start
    adj_end = word_end - raw_start

    sent_ranges: list[tuple[int, int]] = []
    offset = 0
    for sent in sentences:
        sent_ranges.append((offset, offset + len(sent)))
        offset += len(sent) + 1  # +1 for the space consumed by split

    containing: list[int] = []
    for i, (s, e) in enumerate(sent_ranges):
        if s <= adj_start < e or (adj_start < s < adj_end):
            containing.append(i)

    if not containing:
        return _character_window(text, word_start, word_end, max_chars)

    # Include one sentence before and after the containing range.
    first_idx = max(0, containing[0] - 1)
    last_idx = min(len(sent_ranges) - 1, containing[-1] + 1)

    ctx_start_in_window = sent_ranges[first_idx][0]
    ctx_end_in_window = sent_ranges[last_idx][1]
    context = window[ctx_start_in_window:ctx_end_in_window].strip()

    # Map word offsets into context.
    ctx_abs_start = raw_start + ctx_start_in_window
    ctx_word_start = word_start - ctx_abs_start
    ctx_word_end = word_end - ctx_abs_start

    # Trim to max_chars, keeping the word visible.
    if len(context) > max_chars:
        context, ctx_word_start, ctx_word_end = _trim_to_budget(
            context, ctx_word_start, ctx_word_end, max_chars
        )

    # Clamp offsets defensively.
    ctx_word_start = max(0, min(ctx_word_start, len(context)))
    ctx_word_end = max(ctx_word_start, min(ctx_word_end, len(context)))

    return (context, ctx_word_start, ctx_word_end)


def _character_window(
    text: str, word_start: int, word_end: int, max_chars: int
) -> tuple[str, int, int]:
    half = max_chars // 2
    c_start = max(0, word_start - half)
    c_end = min(len(text), word_end + half)
    context = text[c_start:c_end]
    return (context, word_start - c_start, word_end - c_start)


def _trim_to_budget(context: str, ws: int, we: int, budget: int) -> tuple[str, int, int]:
    if we <= budget:
        return (context[:budget], ws, we)
    # Centre the window around the word.
    half = budget // 2
    trim_start = max(0, ws - half)
    trim_end = trim_start + budget
    if trim_end > len(context):
        trim_end = len(context)
        trim_start = max(0, trim_end - budget)
    return (
        context[trim_start:trim_end],
        ws - trim_start,
        we - trim_start,
    )
