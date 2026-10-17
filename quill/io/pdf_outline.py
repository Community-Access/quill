"""A PDF's embedded outline (Adobe bookmarks): titles, pages and nesting.

Read with pypdf. Each entry is a title, the 1-based page it points to, and its
nesting level (1 for a top-level entry, 2 for its children, and so on), in
document order. The level is kept for *presentation* only -- Go To says
"level 2" beside a nested entry -- and is never turned into a heading: an
outline says where to go, not what the text there is.

Best-effort throughout: pypdf absent, no outline, a locked file the password
does not open, or an entry that will not resolve all mean fewer entries, never
a failed open. Capped at :data:`_PDF_MAX_OUTLINE_ENTRIES`.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["extract_pdf_outline", "extract_pdf_outline_entries"]

# Bound how many embedded outline (bookmark) entries we import so a pathological
# PDF with thousands of outline nodes cannot flood the bookmark store.
_PDF_MAX_OUTLINE_ENTRIES = 500


def extract_pdf_outline_entries(
    path: Path, *, password: str | None = None
) -> list[tuple[str, int, int]]:
    """``(title, page, level)`` for each outline entry, in document order."""
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return []
    try:
        reader = PdfReader(str(path))
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt(password or "")
            except Exception:  # noqa: BLE001 - decrypt API varies; treat as locked
                return []
        raw_outline = reader.outline  # property; can raise on a malformed tree
    except Exception:  # noqa: BLE001 - corrupt/unreadable -> no outline
        return []

    entries: list[tuple[str, int, int]] = []

    def _walk(items: object, level: int) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if len(entries) >= _PDF_MAX_OUTLINE_ENTRIES:
                return
            if isinstance(item, list):
                # pypdf nests an entry's children as a list right after it.
                _walk(item, level + 1)
                continue
            title = getattr(item, "title", None)
            if not title or not str(title).strip():
                continue
            try:
                page_index = reader.get_destination_page_number(item)
            except Exception:  # noqa: BLE001 - unresolvable destination -> skip
                continue
            if not isinstance(page_index, int) or page_index < 0:
                continue
            entries.append((str(title).strip(), page_index + 1, level))

    try:
        _walk(raw_outline, 1)
    except Exception:  # noqa: BLE001 - any traversal failure -> what we have so far
        pass
    return entries


def extract_pdf_outline(path: Path, *, password: str | None = None) -> list[tuple[str, int]]:
    """``(title, page)`` pairs, the shape the bookmark import and stores keep.

    The same entries as :func:`extract_pdf_outline_entries` without the level,
    so a stored ``pdf_outline`` from an older build reads exactly as before.
    """
    return [
        (title, page)
        for title, page, _level in extract_pdf_outline_entries(path, password=password)
    ]
