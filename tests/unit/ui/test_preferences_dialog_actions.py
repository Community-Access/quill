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
    PreferenceText,
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


def test_text_field_starts_with_its_value_and_is_named(wx_app) -> None:
    dialog = _dialog(
        wx_app,
        texts=[PreferenceText("&Template:", "The announcement template", "{title}")],
    )
    assert len(dialog._text_controls) == 1
    assert dialog._text_controls[0].GetValue() == "{title}"
    assert dialog._text_controls[0].GetName() == "The announcement template"
    dialog.dialog.Destroy()


def test_save_returns_text_values_as_the_third_element(wx_app) -> None:
    # Save now yields (checkbox_values, choice_indices, text_values); an edited
    # text field must come back in text_values.
    dialog = _dialog(
        wx_app,
        texts=[PreferenceText("&Template:", "The announcement template", "{title}")],
    )
    dialog._text_controls[0].SetValue("{artist}: {title}")
    dialog._capture_result()
    checkbox_values, choice_indices, text_values = dialog._result
    assert text_values == ["{artist}: {title}"]
    assert checkbox_values == [True]  # the one checkbox _dialog always adds
    assert choice_indices == []
    dialog.dialog.Destroy()


def test_result_is_a_three_tuple_even_without_text_fields(wx_app) -> None:
    dialog = _dialog(wx_app)
    dialog._capture_result()
    checkbox_values, choice_indices, text_values = dialog._result
    assert text_values == []
    dialog.dialog.Destroy()


class _Key:
    def __init__(self, code: int, modifiers: bool = False) -> None:
        self.code = code
        self.modifiers = modifiers
        self.skipped = False

    def GetKeyCode(self) -> int:  # noqa: N802
        return self.code

    def HasAnyModifiers(self) -> bool:  # noqa: N802
        return self.modifiers

    def Skip(self, skip: bool = True) -> None:  # noqa: N802
        self.skipped = skip


def test_enter_on_a_dropdown_is_ok(wx_app, monkeypatch) -> None:
    """Jeff (2026-09-29): Enter after changing a Preferences dropdown did nothing."""
    from quill.ui.app_preferences_dialog import PreferenceChoice

    dialog = _dialog(
        wx_app, choices=[PreferenceChoice("Playback &engine:", "engine", ["Auto", "wx"], 0)]
    )
    ended: list[int] = []
    monkeypatch.setattr(dialog.dialog, "EndModal", ended.append)
    choice = dialog._choice_controls[0]
    choice.SetSelection(1)
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: choice))
    key = _Key(wx.WXK_RETURN)
    dialog._on_char_hook(key)
    assert ended == [wx.ID_OK]
    assert key.skipped is False
    assert dialog._result[1] == [1]  # the changed dropdown was captured
    dialog.dialog.Destroy()


def test_enter_on_a_button_or_a_multiline_box_is_left_alone(wx_app, monkeypatch) -> None:
    dialog = _dialog(wx_app)
    ended: list[int] = []
    monkeypatch.setattr(dialog.dialog, "EndModal", ended.append)
    button = wx.Button(dialog.dialog, label="Cancel")
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: button))
    key = _Key(wx.WXK_RETURN)
    dialog._on_char_hook(key)
    assert ended == [] and key.skipped is True
    box = wx.TextCtrl(dialog.dialog, style=wx.TE_MULTILINE)
    monkeypatch.setattr(wx.Window, "FindFocus", staticmethod(lambda: box))
    key = _Key(wx.WXK_NUMPAD_ENTER)
    dialog._on_char_hook(key)
    assert ended == [] and key.skipped is True
    key = _Key(wx.WXK_RETURN, modifiers=True)
    dialog._on_char_hook(key)
    assert ended == [] and key.skipped is True
    dialog.dialog.Destroy()
