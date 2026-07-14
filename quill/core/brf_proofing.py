"""Proofing operations on the BRF sidecar (BR-017, #240).

Pure, wx-free functions that apply proofing actions to a :class:`BRFSidecar` and
return a screen-reader-friendly message. The UI mixin supplies the current
braille page (from the position resolver), calls these, and persists the sidecar
via :func:`quill.core.brf_sidecar.write_sidecar`. The braille file itself is
never touched — proofing state lives only in the sidecar.
"""

from __future__ import annotations

from quill.core.brf_sidecar import BRFSidecar, SidecarNote


def _sorted_unique(values: list[int]) -> list[int]:
    return sorted(set(values))


def mark_proofed(sidecar: BRFSidecar, page: int) -> str:
    """Mark ``page`` proofed: add to proofed, drop from needs-review, bump last."""
    proofing = sidecar.proofing
    proofing.proofed_pages = _sorted_unique([*proofing.proofed_pages, page])
    proofing.pages_needing_review = [p for p in proofing.pages_needing_review if p != page]
    proofing.last_proofed_braille_page = max(proofing.last_proofed_braille_page, page)
    return f"Braille page {page} marked proofed."


def mark_needs_review(sidecar: BRFSidecar, page: int) -> str:
    """Flag ``page`` as needing review and remove any proofed mark for it."""
    proofing = sidecar.proofing
    proofing.pages_needing_review = _sorted_unique([*proofing.pages_needing_review, page])
    proofing.proofed_pages = [p for p in proofing.proofed_pages if p != page]
    return f"Braille page {page} marked needs review."


def clear_proofing_mark(sidecar: BRFSidecar, page: int) -> str:
    """Remove any proofed / needs-review mark for ``page``."""
    proofing = sidecar.proofing
    had = page in proofing.proofed_pages or page in proofing.pages_needing_review
    proofing.proofed_pages = [p for p in proofing.proofed_pages if p != page]
    proofing.pages_needing_review = [p for p in proofing.pages_needing_review if p != page]
    if had:
        return f"Cleared proofing mark on braille page {page}."
    return f"Braille page {page} had no proofing mark."


def add_note(sidecar: BRFSidecar, page: int, text: str) -> str:
    """Attach a free-form note to ``page``. Blank text is ignored."""
    note = text.strip()
    if not note:
        return "No note added."
    sidecar.notes.append(SidecarNote(braille_page=page, text=note))
    return f"Note added to braille page {page}."


def progress_summary(
    sidecar: BRFSidecar,
    *,
    page_count: int,
    current_page: int,
    print_page: str = "",
) -> str:
    """Build the spoken progress summary."""
    proofing = sidecar.proofing
    proofed = len(set(proofing.proofed_pages))
    review = len(set(proofing.pages_needing_review))
    parts = [
        "Progress summary.",
        f"{page_count} braille page{'s' if page_count != 1 else ''}.",
        f"Current page {current_page}.",
        f"{proofed} page{'s' if proofed != 1 else ''} proofed.",
        f"{review} page{'s' if review != 1 else ''} need review."
        if review != 1
        else f"{review} page needs review.",
        f"Last proofed page {proofing.last_proofed_braille_page}.",
    ]
    if print_page:
        parts.append(f"Current print page {print_page}.")
    if page_count > 0:
        percent = round(proofed / page_count * 100)
        parts.append(f"Estimated completion {percent} percent.")
    return " ".join(parts)


def proofed_pages(sidecar: BRFSidecar) -> list[int]:
    """Proofed braille pages, sorted and de-duplicated."""
    return _sorted_unique(sidecar.proofing.proofed_pages)


def pages_needing_review(sidecar: BRFSidecar) -> list[int]:
    """Braille pages flagged as needing review, sorted and de-duplicated."""
    return _sorted_unique(sidecar.proofing.pages_needing_review)


def export_report(sidecar: BRFSidecar, *, document_name: str, page_count: int) -> str:
    """Build a plain-text proofing report (for save-to-.txt)."""
    proofed = proofed_pages(sidecar)
    review = pages_needing_review(sidecar)
    lines = [
        f"Proofing report for {document_name}",
        "=" * 40,
        f"Braille pages: {page_count}",
        f"Proofed pages ({len(proofed)}): {_format_page_list(proofed)}",
        f"Pages needing review ({len(review)}): {_format_page_list(review)}",
        f"Last proofed braille page: {sidecar.proofing.last_proofed_braille_page}",
    ]
    if page_count > 0:
        lines.append(f"Estimated completion: {round(len(proofed) / page_count * 100)} percent")
    if sidecar.notes:
        lines.append("")
        lines.append("Notes:")
        for note in sidecar.notes:
            lines.append(f"  Braille page {note.braille_page}: {note.text}")
    return "\n".join(lines) + "\n"


def _format_page_list(pages: list[int]) -> str:
    return ", ".join(str(p) for p in pages) if pages else "none"
