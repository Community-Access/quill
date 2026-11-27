"""FUX-05: a QUILL Lite restore that fails speaks of the work, not the exception."""

from __future__ import annotations

from pathlib import Path

from quill.core.lite.recovery import RecoverySlot


def test_a_failed_restore_names_the_work_and_what_happens_to_it(
    lite_window, tmp_path: Path
) -> None:
    win = lite_window("")
    missing = tmp_path / "gone" / "slot.txt"
    slot = RecoverySlot(
        slot_id="slot",
        mode="plain",
        original_path=str(tmp_path / "chapter3.md"),
        content_path=missing,
        meta_path=tmp_path / "gone" / "slot.json",
    )

    win._load_recovery(slot)

    assert len(win.failures) == 1
    caption, message = win.failures[0]
    assert caption == "Recovery failed"
    assert message == (
        "Could not restore your unsaved work in chapter3.md: its saved-aside copy "
        "could not be read. It stays saved aside and is offered again next time."
    )
    assert "Errno" not in message and str(missing) not in message
    assert win._slot is not slot, "a failed restore claims nothing"
