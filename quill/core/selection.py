from __future__ import annotations

import re


def word_span(text: str, cursor: int) -> tuple[int, int]:
    position = max(0, min(cursor, len(text)))
    length = len(text)
    if not text:
        return 0, 0
    word_char = re.compile(r"\w")
    on_word = position < length and bool(word_char.match(text[position]))
    after_word = position > 0 and bool(word_char.match(text[position - 1]))
    if not on_word and not after_word:
        # Whitespace or boundary: select the single character under the cursor so
        # expansion still has a sensible innermost step.
        if position < length:
            return position, position + 1
        if position > 0:
            return position - 1, position
        return position, position
    anchor = position if on_word else position - 1
    start = anchor
    while start > 0 and word_char.match(text[start - 1]):
        start -= 1
    end = anchor
    while end < length and word_char.match(text[end]):
        end += 1
    return start, end


def line_span(text: str, cursor: int) -> tuple[int, int]:
    position = max(0, min(cursor, len(text)))
    start = text.rfind("\n", 0, position) + 1
    end = text.find("\n", position)
    if end == -1:
        end = len(text)
    return start, end


def paragraph_span(text: str, cursor: int) -> tuple[int, int]:
    position = max(0, min(cursor, len(text)))
    if not text:
        return 0, 0

    previous_break = text.rfind("\n\n", 0, position)
    start = previous_break + 2 if previous_break >= 0 else 0

    next_break = text.find("\n\n", position)
    end = next_break if next_break >= 0 else len(text)
    return start, end


def sentence_span(text: str, cursor: int) -> tuple[int, int]:
    position = max(0, min(cursor, len(text)))
    if not text:
        return 0, 0

    start = 0
    for match in re.finditer(r"[.!?](?:[\]\)\"']+)?\s+", text):
        boundary = match.end()
        if boundary > position:
            break
        start = boundary

    end = len(text)
    for match in re.finditer(r"[.!?](?:[\]\)\"']+)?\s+", text[position:]):
        end = position + match.end()
        break

    return start, end


def block_span(text: str, cursor: int) -> tuple[int, int]:
    position = max(0, min(cursor, len(text)))
    if not text:
        return 0, 0

    start = text.rfind("\n", 0, position) + 1
    end = text.find("\n", position)
    if end == -1:
        end = len(text)

    while start > 0:
        previous_break = text.rfind("\n", 0, start - 1)
        previous_line_start = previous_break + 1
        previous_line = text[previous_line_start : start - 1]
        if not previous_line.strip():
            break
        start = previous_line_start

    text_length = len(text)
    while end < text_length:
        next_break = text.find("\n", end + 1)
        if next_break == -1:
            next_break = text_length
        next_line_start = end + 1
        next_line = text[next_line_start:next_break]
        if not next_line.strip():
            break
        end = next_break

    return start, end


# Ordered innermost-to-outermost structural levels used by expand_selection.
# Each entry pairs a scope label with the span function that computes it.
_EXPANSION_LEVELS: tuple[tuple[str, object], ...] = (
    ("word", word_span),
    ("line", line_span),
    ("sentence", sentence_span),
    ("paragraph", paragraph_span),
    ("block", block_span),
)


def expand_selection(text: str, start: int, end: int) -> tuple[int, int, str] | None:
    """Return the next-larger structural span enclosing the current selection.

    Walks word -> line -> sentence -> paragraph -> block -> document and returns
    the first level whose span strictly contains the current ``(start, end)``
    selection, as ``(new_start, new_end, scope_label)``. Returns ``None`` when the
    selection already spans the whole document.
    """
    length = len(text)
    start = max(0, min(start, length))
    end = max(0, min(end, length))
    if start > end:
        start, end = end, start
    cursor = start
    for label, span_fn in _EXPANSION_LEVELS:
        span_start, span_end = span_fn(text, cursor)  # type: ignore[operator]
        if span_start <= start and span_end >= end and (span_end - span_start) > (end - start):
            return span_start, span_end, label
    if start > 0 or end < length:
        return 0, length, "document"
    return None


def shrink_selection(text: str, start: int, end: int) -> tuple[int, int, str] | None:
    """Return the next-*smaller* structural span inside the current selection.

    The computed inverse of :func:`expand_selection`: it walks the same ladder
    from the outside in and returns the first level strictly smaller than what
    is selected now, as ``(new_start, new_end, scope_label)``. ``None`` when the
    selection is already a single word or is empty -- there is nothing smaller
    to go to that is still a structure.

    Computed rather than remembered, and that is the point. Undoing an
    expansion from a stack works only if you arrived by expanding: select a
    paragraph outright and ask to shrink, and a stack has nothing to say, even
    though "the line the cursor is on" is an obvious and useful answer. A
    listener who cannot see the highlight has no way to tell those two
    situations apart, so "nothing to shrink" reads as a bug rather than as a
    boundary.

    Anchored on ``start`` so repeated shrinking converges on the beginning of
    the selection rather than wandering.
    """
    length = len(text)
    start = max(0, min(start, length))
    end = max(0, min(end, length))
    if start > end:
        start, end = end, start
    if end <= start:
        return None
    current = end - start
    for label, span_fn in reversed(_EXPANSION_LEVELS):
        span_start, span_end = span_fn(text, start)  # type: ignore[operator]
        if (span_end - span_start) < current and span_end > span_start:
            return span_start, span_end, label
    return None


def selection_scope(text: str, start: int, end: int) -> str:
    """Classify the current selection by its structural scope.

    Returns one of ``"none"`` (empty selection), ``"word"``, ``"line"``,
    ``"sentence"``, ``"paragraph"``, ``"block"``, ``"document"`` (the whole
    text), ``"lines"`` (a multi-line span that is not one of the named
    structures), or ``"span"`` (an arbitrary single-line span). The label is
    used to offer scope-aware selection actions (SEL-3).
    """
    length = len(text)
    start = max(0, min(start, length))
    end = max(0, min(end, length))
    if start > end:
        start, end = end, start
    if start == end:
        return "none"
    if start == 0 and end == length:
        return "document"
    cursor = start
    for label, span_fn in _EXPANSION_LEVELS:
        span_start, span_end = span_fn(text, cursor)  # type: ignore[operator]
        if span_start == start and span_end == end:
            return label
    if "\n" in text[start:end]:
        return "lines"
    return "span"


#: The scope names a listener should never hear, because they describe the
#: classifier rather than the document. "Selected span, 4 words" tells nobody
#: anything; the count already said how much.
_UNSPOKEN_SCOPES = frozenset({"none", "span", "lines"})


def describe_selection(
    text: str,
    start: int,
    end: int,
    *,
    prefix: str = "Selected",
    scope: str | None = None,
    with_line_range: bool = False,
) -> str:
    """The one sentence both editors say when a selection changes (bad.md L14).

    Scope, then words, and the line range only when asked for -- which is F8
    completing, the one case where the span is arbitrary and the person has no
    other way to know how far it reached.

    The two editors had two shapes for one event: QUILL said "Selected
    paragraph, 41 words" and QuillLite said "Selected paragraph, 412
    characters, 41 words", and F8 completion differed again. Neither was wrong;
    having two was, because a person who uses both hears the same key report the
    same thing two ways and has to learn which product they are in before they
    can parse the answer.

    **Words rather than characters** is QUILL's choice and the right one: a word
    count is a size somebody can picture, and 412 characters is a number they
    then have to divide. The character count survives only where it is the
    actual subject -- Duplicate Selection, the review buffer -- and not as the
    routine report on a selection.

    *scope* may be passed by a caller that already knows what it selected (Select
    Paragraph knows); otherwise it is classified from the text, and a scope that
    only names the classifier is left out rather than spoken.
    """
    length = len(text)
    start = max(0, min(start, length))
    end = max(0, min(end, length))
    if end < start:
        start, end = end, start
    if end == start:
        return f"{prefix} nothing"
    selected = text[start:end]
    words = len(selected.split())
    named = scope if scope is not None else selection_scope(text, start, end)
    parts = [prefix]
    if named and named not in _UNSPOKEN_SCOPES:
        parts.append(f"{named},")
    parts.append(f"{words} {'word' if words == 1 else 'words'}")
    sentence = " ".join(parts)
    if not with_line_range:
        return sentence
    first = text.count("\n", 0, start) + 1
    last = text.count("\n", 0, end) + 1
    if first == last:
        return f"{sentence}, line {first}"
    return f"{sentence}, lines {first} to {last}"


def changed_span(before: str, after: str) -> tuple[int, int, str]:
    """The narrowest ``(start, end, replacement)`` turning *before* into *after*.

    Trims the common prefix and the common suffix, so replacing one line in a
    document rewrites one line. Both editors had a helper that replaced the
    **whole document** for any change at all, and on a rich surface that is not
    merely wasteful -- it is destructive:

    Writing over a selection makes the new text adopt the format at the
    selection's start, so selecting all and writing turns every run in the
    document into whatever position 0 was. Confirmed live on 2026-09-17
    (``scripts/probe_rich_edits.py``): a document with one Heading 1 and two
    body lines came back with ``all_headings()`` reporting **five** headings --
    every line promoted. bad.md C2/N3 predicted the formatting would be lost;
    what actually happens is that it *spreads*, which is worse, and which is
    why the obvious check ("is my heading still there?") answers yes and misses
    it entirely.

    Returns an empty replacement over an empty span when the two are equal, so
    a caller can tell "nothing changed" from "changed to nothing" -- the
    distinction every no-op announcement depends on.
    """
    if before == after:
        return (0, 0, "")
    limit = min(len(before), len(after))
    start = 0
    while start < limit and before[start] == after[start]:
        start += 1
    # The suffix must not run back past the prefix in either string.
    tail = 0
    while tail < (limit - start) and before[len(before) - 1 - tail] == after[len(after) - 1 - tail]:
        tail += 1
    return (start, len(before) - tail, after[start : len(after) - tail])
