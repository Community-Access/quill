"""Up means more on a horizontal slider.

A Windows trackbar answers Up and Page Up with *less* and Down and Page Down
with *more*: to the control, Up is "towards the start", and on a horizontal
bar the start is the left end. On a volume slider that is backwards to every
listener -- a user of Quill Radio wrote (2026-09-28) "when you turn it up it's
down arrow, when you turn it down it's up arrow" -- and it contradicts the
Windows volume mixer, which a screen-reader user hears as Up-is-louder every
day. Left and Right are already right and are left alone.

:func:`bind_up_means_more` takes the four vertical keys away from the
trackbar, moves the value the way a person expects, and fires the slider's
own ``EVT_SLIDER`` so whatever the slider is wired to hears the change exactly
as it does for Left, Right, the mouse or Home and End. Shift, Ctrl and Alt
chords are left to the frame, so Ctrl+Up and Ctrl+Down still reach the app's
Volume Up and Volume Down commands from the slider as from anywhere else.

Home and End go with Up and Down: in the default layout Home is the top (100
percent on a volume) and End the bottom, the way a listener who has just been
told Up is louder expects. The family can choose the trackbar's own keys
instead (:mod:`quill.core.slider_key_layout`, chosen in each app's
Preferences); the choice is read at each key press, so it applies at once.

Because the keys move the slider through ``SetValue``, which Windows does not
report to a screen reader as a value change, each move raises
``EVENT_OBJECT_VALUECHANGE`` itself, so the reader speaks the new value rather
than an old one.
"""

from __future__ import annotations

import ctypes
from typing import Any

import wx

from quill.core import slider_key_layout

#: Up/Down move by the slider's line size, Page Up/Page Down by its page size,
#: exactly as the trackbar does -- only the direction changes.
_KEY_STEPS: dict[int, tuple[str, int]] = {
    wx.WXK_UP: ("line", +1),
    wx.WXK_NUMPAD_UP: ("line", +1),
    wx.WXK_DOWN: ("line", -1),
    wx.WXK_NUMPAD_DOWN: ("line", -1),
    wx.WXK_PAGEUP: ("page", +1),
    wx.WXK_NUMPAD_PAGEUP: ("page", +1),
    wx.WXK_PAGEDOWN: ("page", -1),
    wx.WXK_NUMPAD_PAGEDOWN: ("page", -1),
    wx.WXK_HOME: ("end", +1),
    wx.WXK_NUMPAD_HOME: ("end", +1),
    wx.WXK_END: ("end", -1),
    wx.WXK_NUMPAD_END: ("end", -1),
}


def step_for_key(
    key_code: int,
    line_size: int,
    page_size: int,
    *,
    span: int = 0,
    layout: str = slider_key_layout.UP_IS_MORE,
) -> int | None:
    """The signed change a vertical key makes, or None for any other key.

    Pure, so the direction rule is testable without a window. In the default
    layout Up, Page Up and Home are positive and Down, Page Down and End
    negative; :data:`~quill.core.slider_key_layout.WINDOWS` turns all six
    round. Home and End move the whole *span* (the slider's max minus min),
    which the caller clamps to an end; with no span they are left alone.
    """
    entry = _KEY_STEPS.get(key_code)
    if entry is None:
        return None
    kind, sign = entry
    if kind == "end":
        if span <= 0:
            return None
        size = span
    else:
        size = max(1, line_size if kind == "line" else page_size)
    if layout == slider_key_layout.WINDOWS:
        sign = -sign
    return sign * size


def bind_up_means_more(slider: Any) -> None:
    """Make Up, Page Up and Home raise ``slider`` and Down, Page Down and End
    lower it -- or the other way round, when the family chose the Windows keys."""

    def on_key(event: Any) -> None:
        if event.ControlDown() or event.ShiftDown() or event.AltDown():
            event.Skip()
            return
        delta = step_for_key(
            event.GetKeyCode(),
            slider.GetLineSize(),
            slider.GetPageSize(),
            span=slider.GetMax() - slider.GetMin(),
            layout=_layout(),
        )
        if delta is None:
            event.Skip()
            return
        before = slider.GetValue()
        after = max(slider.GetMin(), min(slider.GetMax(), before + delta))
        if after == before:
            return  # at an end already; nothing to say and nothing to fire
        slider.SetValue(after)
        changed = wx.CommandEvent(wx.wxEVT_SLIDER, slider.GetId())
        changed.SetInt(after)
        changed.SetEventObject(slider)
        slider.GetEventHandler().ProcessEvent(changed)
        notify_value_changed(slider)

    slider.Bind(wx.EVT_KEY_DOWN, on_key)
    # Reachable for tests, which drive it with a stand-in event: a real
    # keystroke needs focus, and focus needs a screen.
    slider._quill_up_means_more = on_key


_EVENT_OBJECT_VALUECHANGE = 0x800E
_OBJID_CLIENT = -4


def notify_value_changed(slider: Any) -> None:
    """Tell the screen reader the slider's value changed. Windows only; never raises."""
    if not hasattr(ctypes, "windll"):
        return
    try:
        ctypes.windll.user32.NotifyWinEvent(  # type: ignore[attr-defined]
            _EVENT_OBJECT_VALUECHANGE, int(slider.GetHandle()), _OBJID_CLIENT, 0
        )
    except Exception:  # noqa: BLE001 - a reader that misses one value is no crash
        return


def _data_dir() -> Any:
    from quill.core.paths import app_data_dir

    return app_data_dir()


def _layout() -> str:
    try:
        return slider_key_layout.current(_data_dir())
    except Exception:  # noqa: BLE001 - an unreadable choice is the default
        return slider_key_layout.UP_IS_MORE


#: The Preferences button, the same in every app with a slider. No access key,
#: as App Sounds Play On: it joins windows whose letters are spent (GATE-14).
BUTTON_LABEL = "Slider Keys..."
BUTTON_HELP = (
    "Which way the arrow keys move a volume slider, in every Quill app at once. "
    "Up is more, the default: Up, Page Up and Home raise it, Home being 100 "
    "percent. Or the Windows slider keys: Down, Page Down and End raise it. "
    "Right is always more and Left less. Ctrl+Up and Ctrl+Down, the volume keys "
    "that work from anywhere, are not changed."
)
SETTING_KEY = "app.slider_keys"


def preference_action(host: Any, *, key: str = SETTING_KEY) -> Any:
    """The Slider Keys button for an app's Preferences window."""
    from quill.ui.app_preferences_dialog import PreferenceAction

    return PreferenceAction(BUTTON_LABEL, BUTTON_HELP, lambda: choose(host), key=key)


def choose(host: Any) -> None:
    """Ask which way the slider keys go, for the whole family, and say so."""
    from quill.ui import modal_stack

    labels = [label for _value, label in slider_key_layout.CHOICES]
    values = [value for value, _label in slider_key_layout.CHOICES]
    saved = _layout()
    parent = getattr(host, "frame", None) or host
    with wx.SingleChoiceDialog(
        modal_stack.parent_window(parent),
        "Which way should the arrow keys move a slider, in every Quill app?",
        "Slider Keys",
        labels,
    ) as dialog:
        dialog.SetSelection(values.index(saved) if saved in values else 0)
        if dialog.ShowModal() != wx.ID_OK:
            return
        chosen = values[dialog.GetSelection()]
    announce = getattr(host, "_announce", None) or (lambda _text: None)
    if chosen == saved:
        announce("Slider keys unchanged.")
        return
    try:
        slider_key_layout.save(_data_dir(), chosen)
    except OSError as exc:
        announce(f"Could not save the slider keys: {exc}")
        return
    announce(slider_key_layout.describe(chosen))
