"""Source-contract tests for two Quill Radio feature requests:

- #1213: Schedule Recording sets duration as hours + minutes (not minutes only).
- #1214: a Volume slider sits in the main-window Tab order, so the volume can be
  adjusted by arrowing a focused control while listening.

wx surfaces are asserted at the source level (the house pattern for these
dialogs/frames) rather than by driving real widgets.
"""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def _read(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_schedule_recording_offers_hours_and_minutes() -> None:
    src = _read("quill/ui/radio/schedule_recording_dialog.py")
    assert "self._hours_ctrl" in src
    assert "self._minutes_ctrl" in src
    # The total stored is hours*60 + minutes.
    assert "self._hours_ctrl.GetValue() * 60 + self._minutes_ctrl.GetValue()" in src
    # Editing an existing entry splits the stored minutes back into H and M.
    assert "entry.duration_minutes // 60" in src
    assert "entry.duration_minutes % 60" in src
    # The old minutes-only spin is gone.
    assert "_duration_ctrl" not in src


def test_volume_slider_is_in_the_main_window_tab_order() -> None:
    src = _read("quill/apps/radio.py")
    assert "self._volume_slider = wx.Slider(" in src
    assert 'set_accessible_name(self._volume_slider, "Volume, percent")' in src
    assert "def _on_volume_slider(" in src
    # The handler sets the real volume and announces it.
    assert "controller.set_volume(percent)" in src
    # The slider is kept in step with Ctrl+Up/Down and per-station memory.
    assert "def _sync_volume_slider(" in src
    assert "self._sync_volume_slider()" in src
