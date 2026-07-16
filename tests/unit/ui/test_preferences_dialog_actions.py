"""PreferencesDialog's optional action buttons (PreferenceAction).

Unlike checkboxes/choices, an action button fires its callback immediately
on click -- independent of Save/Cancel -- for utility actions like Quill
Radio's "Reset All Stations' Sound Enhancements..." that shouldn't wait on
or be bundled with unrelated Preferences edits.
"""

from __future__ import annotations

import pytest
import wx

from quill.ui.app_preferences_dialog import (
    PreferenceAction,
    PreferenceCheckbox,
    PreferencesDialog,
)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _dialog(wx_app, **kwargs) -> PreferencesDialog:
    frame = wx.Frame(None)
    return PreferencesDialog(
        frame,
        app_title="Quill Radio",
        checkboxes=[PreferenceCheckbox("&Resume Last Station", "Resume Last Station", True)],
        **kwargs,
    )


def test_no_action_buttons_without_actions(wx_app) -> None:
    dialog = _dialog(wx_app)
    assert dialog._action_buttons == []
    dialog.dialog.Destroy()


def test_action_button_created_with_given_label(wx_app) -> None:
    dialog = _dialog(
        wx_app,
        actions=[PreferenceAction("Reset &All Stations...", "Reset all stations", lambda: None)],
    )
    assert len(dialog._action_buttons) == 1
    assert dialog._action_buttons[0].GetLabel() == "Reset &All Stations..."
    dialog.dialog.Destroy()


def test_clicking_action_button_calls_its_callback_immediately(wx_app) -> None:
    calls: list[str] = []
    dialog = _dialog(
        wx_app,
        actions=[
            PreferenceAction("Reset &All...", "Reset all", lambda: calls.append("reset")),
        ],
    )

    btn = dialog._action_buttons[0]
    btn.Command(wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId()))

    assert calls == ["reset"]
    dialog.dialog.Destroy()


def test_clicking_action_button_does_not_trigger_save(wx_app) -> None:
    # Action buttons are independent of Save/Cancel -- clicking one must not
    # end the dialog or populate the checkbox/choice result.
    dialog = _dialog(
        wx_app,
        actions=[PreferenceAction("Reset &All...", "Reset all", lambda: None)],
    )

    btn = dialog._action_buttons[0]
    btn.Command(wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId()))

    assert dialog._result is None
    dialog.dialog.Destroy()


def test_two_actions_are_independent(wx_app) -> None:
    calls: list[str] = []
    dialog = _dialog(
        wx_app,
        actions=[
            PreferenceAction("&First", "First action", lambda: calls.append("first")),
            PreferenceAction("&Second", "Second action", lambda: calls.append("second")),
        ],
    )

    dialog._action_buttons[1].Command(
        wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, dialog._action_buttons[1].GetId())
    )

    assert calls == ["second"]
    dialog.dialog.Destroy()
