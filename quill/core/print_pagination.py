"""Print pagination and page-set selection (#891): the pure logic behind
Print Studio's accessible preview and odd/even/reverse/skip-first-page
options.

QUILL's print pipeline draws plain text to a DC (``main_frame.py``'s
``_TextPrintout``); this module answers, without touching wx at all, how
many pages that produces and which lines land on which page, plus how to
turn a page count and a chosen page-set option into the concrete list of
page numbers to actually print, in print order.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "PageSetOption",
    "PrintPreview",
    "describe_preview",
    "margins_text",
    "paginate_lines",
    "paper_name",
    "select_pages",
]

#: wx.PaperSize ids for the common sizes worth naming; anything else (or the
#: unset id 0 / PAPER_NONE) reports generically rather than guessing.
_PAPER_NAMES: dict[int, str] = {
    1: "Letter",
    2: "Legal",
    3: "A4",
    8: "Tabloid",
    12: "A3",
    14: "A5",
}


def paper_name(paper_id: int) -> str:
    """A human paper-size name for a ``wx.PaperSize`` id, or a safe fallback."""
    return _PAPER_NAMES.get(paper_id, "the selected paper size")


def margins_text(top_left_mm: tuple[int, int], bottom_right_mm: tuple[int, int]) -> str:
    """A human margins description from ``PageSetupDialogData``'s millimetre points."""
    if top_left_mm == (0, 0) and bottom_right_mm == (0, 0):
        return "default margins"
    left, top = top_left_mm
    right, bottom = bottom_right_mm
    if left == top == right == bottom:
        return f"{left}mm margins"
    return f"margins {left}/{top}/{right}/{bottom}mm (left/top/right/bottom)"


class PageSetOption:
    ALL = "all"
    ODD = "odd"
    EVEN = "even"


@dataclass(frozen=True, slots=True)
class PrintPreview:
    page_count: int
    paper_name: str
    margins_text: str


def paginate_lines(lines: list[str], lines_per_page: int) -> list[list[str]]:
    """Split *lines* into pages of at most *lines_per_page* lines each.

    An empty document is still one page (a blank sheet prints, matching
    what every other editor does with an empty file).
    """
    if lines_per_page < 1:
        raise ValueError(f"lines_per_page must be at least 1, got {lines_per_page!r}")
    if not lines:
        return [[]]
    return [lines[i : i + lines_per_page] for i in range(0, len(lines), lines_per_page)]


def select_pages(
    page_count: int,
    *,
    page_set: str = PageSetOption.ALL,
    reverse: bool = False,
    skip_first_page: bool = False,
) -> list[int]:
    """Return the 1-based page numbers to print, in the order to print them.

    *skip_first_page* is for letterhead paper already loaded for page 1 --
    it drops page 1 from the set before odd/even filtering or reversing,
    so "odd pages, skip first" means "3, 5, 7...", not "1, 3, 5...".
    """
    pages = list(range(1, page_count + 1))
    if skip_first_page and pages:
        pages = pages[1:]
    if page_set == PageSetOption.ODD:
        pages = [p for p in pages if p % 2 == 1]
    elif page_set == PageSetOption.EVEN:
        pages = [p for p in pages if p % 2 == 0]
    if reverse:
        pages = list(reversed(pages))
    return pages


def describe_preview(preview: PrintPreview) -> str:
    """The spoken/textual accessible print preview: "N pages, Letter, 1-inch margins"."""
    noun = "page" if preview.page_count == 1 else "pages"
    return f"{preview.page_count} {noun}, {preview.paper_name}, {preview.margins_text}"
