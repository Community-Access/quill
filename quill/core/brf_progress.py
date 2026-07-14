"""Restore-on-open for braille files (BR-016, #239).

Pure, wx-free helpers that decide where to put the caret when a braille file is
reopened and format the spoken open announcement. The sidecar (BR-015) is the
source of the saved position. The UI wiring — reading the sidecar, moving the
caret, resolving page/line/cell, and announcing — lives in the braille mixin;
this module stays unit-testable.
"""

from __future__ import annotations

from quill.core.brf_sidecar import BRFSidecar


def restore_offset(
    sidecar: BRFSidecar | None,
    *,
    save_sidecar_enabled: bool,
    safe_mode: bool,
    text_length: int,
) -> int | None:
    """Return the caret offset to restore, or ``None``.

    ``None`` when there is no sidecar, sidecar saving is disabled, safe mode is
    on, or the saved offset is at the very start (nothing to restore). A stale
    offset past the end of a (possibly edited) file is clamped to ``text_length``
    so restore never lands out of bounds.
    """
    if safe_mode or not save_sidecar_enabled or sidecar is None:
        return None
    offset = sidecar.position.last_offset
    if offset <= 0:
        return None
    return min(offset, max(0, text_length))


def format_open_announcement(
    *,
    page_count: int,
    restored: bool,
    braille_page: int,
    line: int,
    cell: int,
    print_page: str,
) -> str:
    """Build the spoken message for opening a braille file (BR-016)."""
    parts = ["BRF file opened."]
    if page_count > 0:
        parts.append(f"{page_count} braille page{'s' if page_count != 1 else ''} detected.")
    if restored:
        location = f"Last position: braille page {braille_page}, line {line}, cell {cell}"
        if print_page:
            location += f", print page {print_page}"
        parts.append(location + ".")
    return " ".join(parts)
