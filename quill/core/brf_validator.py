"""BRF layout validation (BR-018, #241).

Pure, wx-free routines that walk a BRF document and emit a list of
:class:`BRFWarning` records. The validator is **read-only** — it never modifies
the text (mixed line endings, for example, are reported but not corrected). The
UI surface (the Validation submenu and the Warnings List dialog) is BR-019 / #242.

Ten warning categories are covered:

1. ``line_too_long`` — a line longer than the cell width.
2. ``page_too_long`` — a braille page with more lines than the page height.
3. ``page_too_short`` — a braille page with very few lines (a likely stuck page).
4. ``missing_form_feeds`` — form feeds expected but the file has none and is long.
5. ``mixed_line_endings`` — CRLF and bare LF in the same file.
6. ``non_brf_ascii`` — a byte outside printable NABCC ASCII (and not braille
   Unicode, which is its own category).
7. ``page_indicator`` — a page-separator line whose page anchor is missing/malformed.
8. ``page_numbering`` — a gap or duplicate in the detected page-number sequence.
9. ``running_head`` — running heads that disagree across pages.
10. ``unicode_braille`` — the file is in Unicode braille (U+2800..U+28FF) rather
    than NABCC ASCII.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"

KIND_LINE_TOO_LONG = "line_too_long"
KIND_PAGE_TOO_LONG = "page_too_long"
KIND_PAGE_TOO_SHORT = "page_too_short"
KIND_MISSING_FORM_FEEDS = "missing_form_feeds"
KIND_MIXED_LINE_ENDINGS = "mixed_line_endings"
KIND_NON_BRF_ASCII = "non_brf_ascii"
KIND_PAGE_INDICATOR = "page_indicator"
KIND_PAGE_NUMBERING = "page_numbering"
KIND_RUNNING_HEAD = "running_head"
KIND_UNICODE_BRAILLE = "unicode_braille"

# A page-separator line: three or more dashes, optionally followed by a page
# anchor like "#12" or "#12a". A separator with dashes but no valid anchor is a
# page-indicator problem (#7).
_SEPARATOR_RE = re.compile(r"^-{3,}(?P<anchor>.*)$")
_VALID_ANCHOR_RE = re.compile(r"^#\d+[a-z]?$")
# A right-margin page number on line 1: trailing "#12" / "#12a" / bare digits.
_RIGHT_MARGIN_RE = re.compile(r"(?:#)?(?P<num>\d+)[a-z]?\s*$")


@dataclass(frozen=True, slots=True)
class BRFWarning:
    """One validation finding, addressed for navigation and speech."""

    kind: str
    message: str
    severity: str
    offset: int  # 0-based char offset where the finding begins
    line: int  # 1-based file line number
    page: int  # 1-based braille page

    def describe(self) -> str:
        """One-line, screen-reader-friendly summary."""
        return (
            f"{self.severity.capitalize()} on braille page {self.page}, "
            f"line {self.line}: {self.message}"
        )


@dataclass(slots=True)
class ValidatorOptions:
    cells_per_line: int = 40
    lines_per_page: int = 25
    min_lines_per_page: int = 5
    use_form_feeds: bool = True
    nabcc_mode: bool = True


@dataclass(frozen=True, slots=True)
class _Line:
    text: str
    offset: int
    number: int  # 1-based file line number
    page: int  # 1-based braille page
    index_in_page: int  # 0-based line index within its page


@dataclass(slots=True)
class _Page:
    number: int
    lines: list[_Line] = field(default_factory=list)


def _scan_lines(text: str) -> tuple[list[_Line], list[_Page]]:
    """Split ``text`` into pages (on form feeds) and offset-tagged lines."""
    lines: list[_Line] = []
    pages: list[_Page] = []
    offset = 0
    line_number = 1
    for page_index, chunk in enumerate(text.split("\f"), start=1):
        page = _Page(number=page_index)
        # Split the page chunk into lines on LF; normalise CR for length checks.
        for idx, raw in enumerate(chunk.split("\n")):
            clean = raw.rstrip("\r")
            entry = _Line(
                text=clean, offset=offset, number=line_number, page=page_index, index_in_page=idx
            )
            lines.append(entry)
            page.lines.append(entry)
            offset += len(raw) + 1  # + the LF
            line_number += 1
        pages.append(page)
        offset += 0  # the form feed itself is consumed by the split boundary
    return lines, pages


def validate_brf(text: str, options: ValidatorOptions | None = None) -> list[BRFWarning]:
    """Validate a BRF document and return findings (read-only)."""
    opts = options or ValidatorOptions()
    warnings: list[BRFWarning] = []
    lines, pages = _scan_lines(text)

    _check_lines(lines, opts, warnings)
    _check_pages(pages, opts, warnings)
    _check_missing_form_feeds(text, lines, opts, warnings)
    _check_mixed_line_endings(text, warnings)
    _check_separators_and_numbering(lines, warnings)
    _check_running_heads(pages, warnings)

    warnings.sort(key=lambda w: (w.offset, w.kind))
    return warnings


def _check_lines(lines: list[_Line], opts: ValidatorOptions, out: list[BRFWarning]) -> None:
    for line in lines:
        if len(line.text) > opts.cells_per_line:
            out.append(
                BRFWarning(
                    KIND_LINE_TOO_LONG,
                    f"Line is {len(line.text)} cells, over the {opts.cells_per_line}-cell width.",
                    SEVERITY_WARNING,
                    line.offset,
                    line.number,
                    line.page,
                )
            )
        _check_line_characters(line, opts, out)


def _check_line_characters(line: _Line, opts: ValidatorOptions, out: list[BRFWarning]) -> None:
    for column, char in enumerate(line.text):
        code = ord(char)
        if 0x2800 <= code <= 0x28FF:
            if opts.nabcc_mode:
                out.append(
                    BRFWarning(
                        KIND_UNICODE_BRAILLE,
                        "Unicode braille character found; this file should be NABCC ASCII.",
                        SEVERITY_ERROR,
                        line.offset + column,
                        line.number,
                        line.page,
                    )
                )
            continue
        if code > 0x7F or (code < 0x20 and char not in "\t"):
            out.append(
                BRFWarning(
                    KIND_NON_BRF_ASCII,
                    f"Character U+{code:04X} is not valid braille ASCII.",
                    SEVERITY_WARNING,
                    line.offset + column,
                    line.number,
                    line.page,
                )
            )


def _check_pages(pages: list[_Page], opts: ValidatorOptions, out: list[BRFWarning]) -> None:
    for page in pages:
        # Trailing blank line from a final LF should not count as content.
        content = [ln for ln in page.lines if ln.text != ""]
        count = len(content)
        first = page.lines[0] if page.lines else None
        if count > opts.lines_per_page:
            out.append(
                BRFWarning(
                    KIND_PAGE_TOO_LONG,
                    f"Braille page has {count} lines, over the {opts.lines_per_page}-line height.",
                    SEVERITY_WARNING,
                    first.offset if first else 0,
                    first.number if first else 1,
                    page.number,
                )
            )
        elif 0 < count < opts.min_lines_per_page and len(pages) > 1:
            out.append(
                BRFWarning(
                    KIND_PAGE_TOO_SHORT,
                    f"Braille page has only {count} line(s); it may be a stuck or short page.",
                    SEVERITY_INFO,
                    first.offset if first else 0,
                    first.number if first else 1,
                    page.number,
                )
            )


def _check_missing_form_feeds(
    text: str, lines: list[_Line], opts: ValidatorOptions, out: list[BRFWarning]
) -> None:
    if not opts.use_form_feeds:
        return
    if "\f" in text:
        return
    if len(lines) > opts.lines_per_page:
        out.append(
            BRFWarning(
                KIND_MISSING_FORM_FEEDS,
                "The file has no form feeds but spans more than one page; "
                "page breaks may be missing.",
                SEVERITY_WARNING,
                0,
                1,
                1,
            )
        )


def _check_mixed_line_endings(text: str, out: list[BRFWarning]) -> None:
    has_crlf = "\r\n" in text
    has_lone_lf = re.search(r"(?<!\r)\n", text) is not None
    if has_crlf and has_lone_lf:
        out.append(
            BRFWarning(
                KIND_MIXED_LINE_ENDINGS,
                "The file mixes CRLF and LF line endings. (Reported only; not changed.)",
                SEVERITY_WARNING,
                0,
                1,
                1,
            )
        )


def _check_separators_and_numbering(lines: list[_Line], out: list[BRFWarning]) -> None:
    numbers: list[tuple[int, _Line]] = []
    for line in lines:
        match = _SEPARATOR_RE.match(line.text)
        if match is None:
            continue
        anchor = match.group("anchor").strip()
        if anchor == "" or not _VALID_ANCHOR_RE.match(anchor):
            out.append(
                BRFWarning(
                    KIND_PAGE_INDICATOR,
                    "Page-separator line has a missing or malformed page number.",
                    SEVERITY_WARNING,
                    line.offset,
                    line.number,
                    line.page,
                )
            )
            continue
        numbers.append((int(anchor.lstrip("#").rstrip("abcdefghijklmnopqrstuvwxyz")), line))

    seen: set[int] = set()
    previous: int | None = None
    for value, line in numbers:
        if value in seen:
            out.append(
                BRFWarning(
                    KIND_PAGE_NUMBERING,
                    f"Duplicate print page number {value}.",
                    SEVERITY_WARNING,
                    line.offset,
                    line.number,
                    line.page,
                )
            )
        elif previous is not None and value > previous + 1:
            out.append(
                BRFWarning(
                    KIND_PAGE_NUMBERING,
                    f"Print page numbering jumps from {previous} to {value}.",
                    SEVERITY_INFO,
                    line.offset,
                    line.number,
                    line.page,
                )
            )
        seen.add(value)
        previous = value


def _check_running_heads(pages: list[_Page], out: list[BRFWarning]) -> None:
    heads: list[tuple[str, _Line]] = []
    for page in pages:
        if not page.lines:
            continue
        first = page.lines[0]
        head = _RIGHT_MARGIN_RE.sub("", first.text).strip()
        if head:
            heads.append((head, first))
    if len(heads) < 2:
        return
    counts: dict[str, int] = {}
    for head, _line in heads:
        counts[head] = counts.get(head, 0) + 1
    if len(counts) < 2:
        return
    majority = max(counts, key=lambda key: counts[key])
    for head, line in heads:
        if head != majority:
            out.append(
                BRFWarning(
                    KIND_RUNNING_HEAD,
                    f'Running head "{head}" differs from the usual "{majority}".',
                    SEVERITY_INFO,
                    line.offset,
                    line.number,
                    line.page,
                )
            )
