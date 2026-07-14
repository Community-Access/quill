"""Live boot matrix: construct the real MainFrame in several startup states.

This is the layer that would have caught the first-run startup crash
(`_apply_soft_wrap` reading `self.editor` before it existed): it actually builds
the frame, including the wizard-pending path, and exercises a basic edit/save/
reopen round-trip.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.live_ui


def test_boot_safe_mode(build_frame) -> None:
    frame = build_frame(safe_mode=True)
    assert frame.frame is not None
    assert len(list(frame.commands.list())) > 0


def test_boot_normal_profile(build_frame) -> None:
    # A profile that has already completed setup: the normal startup path.
    frame = build_frame(safe_mode=False, settings={"setup_wizard_completed": True})
    assert frame.frame is not None
    assert frame.editor is not None  # a document tab exists on the normal path


def test_boot_first_run_wizard_pending(build_frame) -> None:
    # Regression for the first-run crash: setup not completed -> __init__ takes
    # the wizard-pending branch that skips the document tab, then _bind_events
    # runs _apply_soft_wrap before the editor exists. Must not raise.
    frame = build_frame(safe_mode=False, settings={"setup_wizard_completed": False})
    assert frame.frame is not None


@pytest.mark.parametrize("soft_wrap", [True, False])
def test_boot_respects_soft_wrap_setting(build_frame, soft_wrap: bool) -> None:
    frame = build_frame(
        safe_mode=True,
        settings={"setup_wizard_completed": True, "soft_wrap": soft_wrap},
    )
    assert frame.frame is not None
    assert bool(frame.settings.soft_wrap) is soft_wrap


def test_open_edit_save_reopen_round_trip(build_frame, tmp_path: Path) -> None:
    frame = build_frame(safe_mode=True, settings={"setup_wizard_completed": True})
    target = tmp_path / "note.txt"
    target.write_text("first line\nsecond line\n", encoding="utf-8", newline="")

    import wx

    frame.open_file(path=target, record_recent=False)
    for _ in range(5):
        wx.SafeYield()
    assert "first line" in frame.editor.GetValue()

    frame.editor.SetValue("first line\nsecond line\nthird line\n")
    frame.document.set_text(frame.editor.GetValue())
    frame.save_file()

    reread = target.read_text(encoding="utf-8")
    assert "third line" in reread
