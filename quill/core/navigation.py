from __future__ import annotations

import re


def page_starts(text: str) -> list[int]:
    starts = [0]
    for index, char in enumerate(text):
        if char == "\f":
            starts.append(index + 1)
    return starts


def page_start_for_number(text: str, page_number: int) -> int | None:
    starts = page_starts(text)
    if page_number < 1 or page_number > len(starts):
        return None
    return starts[page_number - 1]


def page_position(text: str, position: int) -> tuple[int, int] | None:
    """``(page, of)`` for *position*, or ``None`` when the text has no real pages.

    Real pages are form feeds, which is how a PDF's page breaks arrive (#872).
    Both editors' status bars ask this one question, so "page 3 of 12" cannot
    mean two different things in the two products.
    """
    starts = page_starts(text)
    if len(starts) < 2:
        return None
    current = sum(1 for start in starts if start <= position)
    return max(1, min(current, len(starts))), len(starts)


def page_target(starts: list[int], position: int, *, forward: bool) -> int | None:
    """Where Next or Previous Page goes from *position*, or ``None`` at the end.

    *starts* is :func:`page_starts`. Next is the start of the page after the
    caret's; Previous is the start of the caret's own page when the caret is
    inside it, else of the page before -- the way Ctrl+Up treats paragraphs, so
    a press from mid-page goes to the top of the page being read first.
    """
    if forward:
        return next((start for start in starts if start > position), None)
    return next((start for start in reversed(starts) if start < position), None)


class PageLatch:
    """The last page somebody was told about, so it is said once, not per key.

    Arrowing through a PDF crosses a form feed now and then; the page number
    is worth hearing when that happens and is noise on every other key.
    :meth:`crossed` answers True only when the page differs from the one
    recorded -- the first reading of a document records without speaking,
    because opening a file is not a page crossing. :meth:`settle` records a
    page a command has already announced, so arriving there is not news twice.
    """

    __slots__ = ("document", "page")

    def __init__(self) -> None:
        self.page: int | None = None
        self.document: object = None

    def crossed(self, page: int | None, document: object = None) -> bool:
        if document is not self.document:
            self.document, self.page = document, page
            return False
        changed = page is not None and self.page is not None and page != self.page
        self.page = page
        return changed

    def settle(self, page: int | None, document: object = None) -> None:
        self.document, self.page = document, page


def _word_starts(text: str) -> list[int]:
    """Character offset of each word (maximal run of non-whitespace).

    Matches the token count `text.split()` would produce (used by the
    word-count status cell), so the page estimate always agrees with the
    word count shown elsewhere in the status bar.
    """
    return [match.start() for match in re.finditer(r"\S+", text)]


def estimate_page_count(text: str, words_per_page: int) -> int:
    """Estimate a page count from word count alone.

    This is an approximation for documents with no real page breaks
    (plain text, Markdown, most DOCX) -- it has no knowledge of fonts,
    margins, or paper size, and will not match a printed or exported
    page count. Always returns at least 1.
    """
    words = len(_word_starts(text))
    if words == 0:
        return 1
    return max(1, -(-words // words_per_page))  # ceiling division


def estimate_page_for_position(text: str, position: int, words_per_page: int) -> int:
    """Estimate which page `position` falls on, clamped to the total."""
    starts = _word_starts(text)
    if not starts:
        return 1
    position = max(0, min(position, len(text)))
    words_before = sum(1 for start in starts if start < position)
    page = words_before // words_per_page + 1
    total = estimate_page_count(text, words_per_page)
    return max(1, min(page, total))


def estimate_page_start_for_number(text: str, page_number: int, words_per_page: int) -> int | None:
    """Character offset where estimated `page_number` begins, or None if out of range."""
    if page_number < 1:
        return None
    starts = _word_starts(text)
    total = estimate_page_count(text, words_per_page)
    if page_number > total:
        return None
    if page_number == 1:
        return 0
    index = (page_number - 1) * words_per_page
    if index >= len(starts):
        return len(text)
    return starts[index]


def parse_line_column(value: str) -> tuple[int, int | None]:
    raw = value.strip()
    if not raw:
        raise ValueError("Line number is required")
    if "," not in raw:
        return int(raw), None
    line_raw, column_raw = (part.strip() for part in raw.split(",", 1))
    if not line_raw or not column_raw:
        raise ValueError("Line and column are required")
    return int(line_raw), int(column_raw)


def next_heading_start(text: str, cursor: int, markup_kind: str) -> int | None:
    starts = _heading_starts(text, markup_kind)
    for start in starts:
        if start > cursor:
            return start
    return None


def previous_heading_start(text: str, cursor: int, markup_kind: str) -> int | None:
    starts = _heading_starts(text, markup_kind)
    previous: int | None = None
    for start in starts:
        if start >= cursor:
            break
        previous = start
    return previous


def next_block_start(text: str, cursor: int) -> int | None:
    blocks = _block_starts(text)
    for start in blocks:
        if start > cursor:
            return start
    return None


def previous_block_start(text: str, cursor: int) -> int | None:
    blocks = _block_starts(text)
    previous: int | None = None
    for start in blocks:
        if start >= cursor:
            break
        previous = start
    return previous


def _heading_starts(text: str, markup_kind: str) -> list[int]:
    if markup_kind == "markdown":
        pattern = re.compile(r"^[ \t]{0,3}#{1,6}\s+\S", re.MULTILINE)
    elif markup_kind == "html":
        pattern = re.compile(r"^[ \t]*<h[1-6]\b[^>]*>", re.MULTILINE | re.IGNORECASE)
    else:
        return []
    return [match.start() for match in pattern.finditer(text)]


def _block_starts(text: str) -> list[int]:
    starts: list[int] = []
    lines = text.splitlines(keepends=True)
    if not lines:
        return starts
    offset = 0
    in_block = False
    for line in lines:
        if line.strip():
            if not in_block:
                starts.append(offset)
                in_block = True
        else:
            in_block = False
        offset += len(line)
    return starts
