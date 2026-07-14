from __future__ import annotations

from quill.core.brf_progress import format_open_announcement, restore_offset
from quill.core.brf_sidecar import BRFSidecar, SidecarPosition


def _sidecar(offset: int) -> BRFSidecar:
    return BRFSidecar(position=SidecarPosition(last_offset=offset))


def test_restore_offset_returns_saved_offset() -> None:
    assert (
        restore_offset(_sidecar(1234), save_sidecar_enabled=True, safe_mode=False, text_length=5000)
        == 1234
    )


def test_restore_offset_none_for_missing_sidecar() -> None:
    assert (
        restore_offset(None, save_sidecar_enabled=True, safe_mode=False, text_length=5000) is None
    )


def test_restore_offset_skipped_in_safe_mode() -> None:
    assert (
        restore_offset(_sidecar(1234), save_sidecar_enabled=True, safe_mode=True, text_length=5000)
        is None
    )


def test_restore_offset_skipped_when_disabled() -> None:
    result = restore_offset(
        _sidecar(1234), save_sidecar_enabled=False, safe_mode=False, text_length=5000
    )
    assert result is None


def test_restore_offset_none_at_document_start() -> None:
    assert (
        restore_offset(_sidecar(0), save_sidecar_enabled=True, safe_mode=False, text_length=5000)
        is None
    )


def test_restore_offset_clamps_stale_offset_to_text_length() -> None:
    # The file was edited shorter since the position was saved.
    assert (
        restore_offset(_sidecar(9999), save_sidecar_enabled=True, safe_mode=False, text_length=100)
        == 100
    )


def test_format_announcement_with_restore_and_print_page() -> None:
    msg = format_open_announcement(
        page_count=87, restored=True, braille_page=12, line=14, cell=31, print_page="7"
    )
    assert msg == (
        "BRF file opened. 87 braille pages detected. "
        "Last position: braille page 12, line 14, cell 31, print page 7."
    )


def test_format_announcement_without_restore() -> None:
    msg = format_open_announcement(
        page_count=1, restored=False, braille_page=0, line=0, cell=0, print_page=""
    )
    assert msg == "BRF file opened. 1 braille page detected."


def test_format_announcement_omits_unknown_page_count() -> None:
    msg = format_open_announcement(
        page_count=0, restored=True, braille_page=3, line=2, cell=5, print_page=""
    )
    assert msg == "BRF file opened. Last position: braille page 3, line 2, cell 5."
