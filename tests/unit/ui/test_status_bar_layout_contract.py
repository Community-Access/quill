from __future__ import annotations

from pathlib import Path

# open_status_bar_settings was extracted into the StatusBarMixin (GATE-11 #521),
# so this contract is checked against main_frame_statusbar.py where it now lives.
SOURCE = (
    Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_statusbar.py"
).read_text(encoding="utf-8")


def test_status_bar_layout_dialog_parents_controls_to_dialog() -> None:
    # Regression: the Status Bar Layout dialog could not be dismissed. Controls
    # were parented to an inner wx.Panel while dialog.CreateButtonSizer()'s
    # OK/Cancel buttons (children of the dialog) were added to the panel's
    # sizer. That parent/sizer mismatch mislaid the buttons, and because
    # SetEscapeId(wx.ID_CANCEL) needs a realized Cancel button, neither the
    # buttons nor Escape could exit the dialog. The fix parents every control
    # directly to the dialog in a single sizer (the working #119 pattern).
    start = SOURCE.index("def open_status_bar_settings")
    body = SOURCE[start:]

    assert 'wx.Dialog(self.frame, title="Status Bar Layout"' in body
    # No inner panel: controls share the dialog's sizer tree.
    assert "wx.Panel(dialog)" not in body
    assert "panel.SetSizer(root)" not in body
    assert "SetSizerAndFit(outer)" not in body
    # Controls and buttons are all children of the dialog.
    assert "wx.CheckListBox(" in body  # parented to dialog (A11Y-SR-1-OK exemption present)
    assert "\n            dialog," in body
    assert 'wx.Button(dialog, label="Move Up")' in body
    assert "buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)" in body
    assert "dialog.SetSizer(root)" in body
    # Explicit default action and Escape mapping for predictable dismissal.
    assert "ok_button.SetDefault()" in body
    assert "apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)" in body


def test_status_bar_dialog_exposes_shown_hidden_state() -> None:
    # Accessibility: a CheckListBox checkbox state is not always voiced, so the
    # shown/hidden state must also live in each item's visible label, and a
    # Spacebar toggle (EVT_CHECKLISTBOX) must keep that label and an
    # announcement in sync.
    start = SOURCE.index("def open_status_bar_settings")
    body = SOURCE[start:]

    # Item labels carry an explicit (shown)/(hidden) suffix.
    assert "def state_label(" in body
    assert "(shown)" in body
    assert "(hidden)" in body
    # Spacebar toggling is wired and refreshes label text + announces state.
    assert "chooser.Bind(wx.EVT_CHECKLISTBOX, on_toggle)" in body
    assert "def on_toggle(" in body
    assert "def refresh_label(" in body
    assert "def announce_state(" in body
    # Context-menu toggle uses a programmatic path because Check() does not
    # fire EVT_CHECKLISTBOX.
    assert "def toggle_item(" in body
