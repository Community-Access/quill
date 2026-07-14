"""Render the braille status-bar cell text from a document and resolver.

This module keeps the cell-text builder pure so it can be unit-tested
without importing :mod:`quill.ui.main_frame`. The UI layer pulls the
``BRFDocument`` and the current caret offset off the active document
and passes them in; everything else is string assembly.

The cell format is::

    "BRF Pg 12/87 | Ln 14/25 | Cell 31/40 | Print 7"

When the print page is unknown the trailing ``| Print 7`` segment is
replaced with ``| Print ?"``; for an implied print page we render
``| Print ~8`` (the tilde means "implied" to a screen-reader user).
"""

from __future__ import annotations

from quill.core.braille_position import BraillePosition, BraillePositionResolver
from quill.core.braille_status import PrintPageInfo


def _print_page_marker(print_page: PrintPageInfo) -> str:
    if print_page.number is None and not print_page.is_implied:
        return "Print ?"
    if print_page.is_implied and print_page.number is not None:
        return f"Print ~{print_page.number}"
    number = print_page.number if print_page.number is not None else 0
    return f"Print {number}"


def short_form(
    position: BraillePosition,
    print_page: PrintPageInfo | None = None,
) -> str:
    """Return the short-form braille cell text for the status bar.

    Example::

        "BRF Pg 12/87 | Ln 14/25 | Cell 31/40 | Print 7"
    """
    print_page = print_page if print_page is not None else PrintPageInfo()
    return (
        f"BRF Pg {position.page}/{position.page_count} | "
        f"Ln {position.line}/{position.line_count_in_page} | "
        f"Cell {position.cell}/{position.cell_width} | "
        f"{_print_page_marker(print_page)}"
    )


def short_form_from_resolver(
    resolver: BraillePositionResolver,
    char_offset: int,
    print_page: PrintPageInfo | None = None,
) -> str:
    """Resolve ``char_offset`` through ``resolver`` and return ``short_form``."""
    return short_form(resolver.resolve(char_offset), print_page)


__all__ = ["short_form", "short_form_from_resolver"]
