"""Record Key: press a key combination and get it written out.

Beside the box where a system-wide key is typed -- every app's Show and Hide
Key, QUILL Transcribe's Start and Stop Key and its setup window -- so a key can
be pressed instead of spelled (owner, 2026-10-12). Typing stays: a key another
program has already registered system-wide never reaches this window, so the
prompt says to type such a key instead, and Escape or Cancel leave the box as
it was.

One window, waiting for one combination. A bare Ctrl, Alt or Shift is part of
the combination being held, not the answer; Escape cancels, so Escape itself
cannot be recorded (no system-wide key should be Escape anyway).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["chord_from_key_event", "record_key"]

_TITLE = "Record Key"
#: The window's title carries the instruction: every screen reader says a
#: dialog's title, and not every one reads the text inside a wx.Dialog
#: (NVDA and Narrator may say only "Cancel button"). It also says Escape,
#: because Space and Enter on Cancel are recorded as keys, not presses.
_SPOKEN_TITLE = "Record Key: press the key combination, or Escape to cancel"

#: Windows virtual-key codes for the punctuation keys, by what they type on a
#: US layout -- the names the family's keymap reads (normalise_chord).
_OEM_KEYS = {
    0xBA: ";",
    0xBB: "=",
    0xBC: ",",
    0xBD: "-",
    0xBE: ".",
    0xBF: "/",
    0xC0: "`",
    0xDB: "[",
    0xDC: "\\",
    0xDD: "]",
    0xDE: "'",
}


def _named_keys(wx: Any) -> dict[int, str]:
    named = {
        getattr(wx, "WXK_RETURN", 13): "Enter",
        getattr(wx, "WXK_TAB", 9): "Tab",
        getattr(wx, "WXK_SPACE", 32): "Space",
        getattr(wx, "WXK_DELETE", 127): "Delete",
        getattr(wx, "WXK_BACK", 8): "Backspace",
        getattr(wx, "WXK_INSERT", 322): "Insert",
        getattr(wx, "WXK_HOME", 313): "Home",
        getattr(wx, "WXK_END", 312): "End",
        getattr(wx, "WXK_PAGEUP", 366): "PageUp",
        getattr(wx, "WXK_PAGEDOWN", 367): "PageDown",
        getattr(wx, "WXK_LEFT", 314): "Left",
        getattr(wx, "WXK_RIGHT", 316): "Right",
        getattr(wx, "WXK_UP", 315): "Up",
        getattr(wx, "WXK_DOWN", 317): "Down",
        getattr(wx, "WXK_PAUSE", 310): "Pause",
    }
    for index in range(1, 25):
        named[getattr(wx, f"WXK_F{index}", 339 + index)] = f"F{index}"
    for digit in range(10):
        named[getattr(wx, f"WXK_NUMPAD{digit}", 324 + digit)] = f"Num{digit}"
    return named


def _is_modifier(wx: Any, key_code: int) -> bool:
    names = ("WXK_CONTROL", "WXK_ALT", "WXK_SHIFT", "WXK_WINDOWS_LEFT", "WXK_WINDOWS_RIGHT")
    return key_code in {getattr(wx, name, -1) for name in names} or key_code in {
        306,
        307,
        308,
        393,
        394,
    }


def chord_from_key_event(wx: Any, event: Any) -> str | None:
    """The combination a key-down *event* is, as the family writes it
    (``Ctrl+Alt+Shift+Key``), or None for a lone modifier or a key with no name."""
    key_code = int(event.GetKeyCode())
    if _is_modifier(wx, key_code):
        return None
    raw = getattr(event, "GetRawKeyCode", None)
    vk = int(raw()) if callable(raw) else 0
    token = _OEM_KEYS.get(vk) or _named_keys(wx).get(key_code)
    if token is None and 32 < key_code < 127:
        token = chr(key_code).upper()
    if token is None:
        return None
    mods = [
        name
        for name, down in (
            ("Ctrl", event.ControlDown()),
            ("Alt", event.AltDown()),
            ("Shift", event.ShiftDown()),
        )
        if down
    ]
    return "+".join([*mods, token])


def record_key(parent: Any, wx: Any, show_modal: Callable[[Any, str], int]) -> str | None:
    """Open the Record Key window; the combination pressed, or None if cancelled.

    *show_modal* is the host's ``_show_modal_dialog``, so the window goes
    through the same modal contract as every other.
    """
    from quill.ui.dialog_contract import apply_modal_ids

    dialog = wx.Dialog(parent, title=_SPOKEN_TITLE)
    captured: dict[str, str] = {}
    root = wx.BoxSizer(wx.VERTICAL)
    prompt = wx.StaticText(
        dialog,
        label=(
            "Press the key combination you want, for example Alt+Shift+Backslash. "
            "It is written into the box for you. Press Escape, or choose Cancel, to "
            "leave the box as it was. If a key does something else instead, another "
            "program already uses it: type it in the box, or choose another. Keys "
            "with your screen reader key (Insert or Caps Lock) and the Windows key "
            "never arrive here."
        ),
    )
    prompt.Wrap(400)
    root.Add(prompt, 1, wx.ALL | wx.EXPAND, 12)
    cancel = wx.Button(dialog, id=wx.ID_CANCEL, label="Cancel")
    cancel.SetHelpText(
        "Press Escape to close without recording; the box keeps what it had. Space "
        "and Enter are recorded as keys here, not as presses of this button."
    )
    buttons = wx.StdDialogButtonSizer()
    buttons.AddButton(cancel)
    buttons.Realize()
    root.Add(buttons, 0, wx.ALL | wx.EXPAND, 8)
    dialog.SetSizerAndFit(root)

    def on_key(event: Any) -> None:
        repeat = getattr(event, "IsAutoRepeat", None)
        if callable(repeat) and repeat():
            return  # the access key that opened this window, still held down
        if event.GetKeyCode() == getattr(wx, "WXK_ESCAPE", 27):
            dialog.EndModal(wx.ID_CANCEL)
            return
        chord = chord_from_key_event(wx, event)
        if chord is None:
            return  # a modifier on its own: still waiting for the key
        captured["chord"] = chord
        dialog.EndModal(wx.ID_OK)

    cancel.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CANCEL))
    dialog.Bind(wx.EVT_CHAR_HOOK, on_key)
    # Cancel carries both ids: Enter is recorded as a key, and Escape closes
    # through the same button -- never a trap.
    apply_modal_ids(dialog, affirmative_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
    try:
        result = show_modal(dialog, _TITLE)
    finally:
        dialog.Destroy()
    return captured.get("chord") if result == wx.ID_OK else None
