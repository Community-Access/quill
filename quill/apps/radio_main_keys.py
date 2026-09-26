"""The keys Quill Radio's main window answers that no menu item carries.

Every other key on the main window is a menu accelerator: the label shows it and
wx binds it, so the key and the menu cannot disagree. Three families of key had
no menu item to ride on, and so -- until 2026-09-25 -- did nothing at all on the
one window people use most, while the palette, the first-run screen and the
tutorials all taught them:

* **Alt+1 .. Alt+0**, quick-play favorites one to ten (``APP_KEYMAPS``). Ten
  menu rows for them were retired for the Play Favorite chooser, which took the
  keys' only carrier with them.
* **Stop** (``radio.stop``). The transport table gives every other window Stop
  on Ctrl+. and the main window had no Stop at all.
* **Mute on Ctrl+Shift+O**, which is what Mute is in every other window of the
  app. The main window keeps Ctrl+M on its Audio menu as well; Ctrl+Shift+O is
  honoured here too so "Mute is Ctrl+Shift+O anywhere" is simply true.

This is a char hook rather than an accelerator table on purpose: the frame's one
table belongs to the WindowManager (Ctrl+Tab, Ctrl+1..9), and ``SetAcceleratorTable``
*replaces* -- adding a second table is how window traversal was killed before.
A char hook adds; it runs before the focused control, and anything it does not
recognise is passed on untouched.

The keymap is read at press time, not at install time, so a key rebound in
Keyboard Shortcuts works at once and the old one stops.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["FAVORITE_SLOTS", "chord_of", "install", "resolve"]

#: The quick-play commands, slot 1..10, in keymap order.
FAVORITE_SLOTS: tuple[str, ...] = tuple(f"radio.play_favorite_{slot}" for slot in range(1, 11))

#: Commands dispatched through the registry by whatever key the keymap gives them.
_KEYMAP_COMMANDS: tuple[str, ...] = (*FAVORITE_SLOTS, "radio.stop")


def chord_of(*, key: str, ctrl: bool, alt: bool, shift: bool) -> str:
    """The binding text a key press names, in keymap spelling. Pure."""
    parts = [name for name, down in (("Ctrl", ctrl), ("Alt", alt), ("Shift", shift)) if down]
    return "+".join([*parts, key])


def _canonical(text: str | None) -> str | None:
    from quill.core.keymap_query import canonical_binding

    return canonical_binding(text) if text else None


def resolve(chord: str, binding_for: Callable[[str], str | None]) -> tuple[str, str] | None:
    """What *chord* means on the main window: ``("command", id)``,
    ``("transport", id)``, or ``None`` for a key this module does not own. Pure.

    The keymap wins over the transport table: if somebody rebinds Stop, the
    new key stops and the transport's own Stop key still stops as well.
    """
    from quill.core.radio import transport_commands as tc

    pressed = _canonical(chord)
    if pressed is None:
        return None
    for command_id in _KEYMAP_COMMANDS:
        if _canonical(binding_for(command_id)) == pressed:
            return ("command", command_id)
    for transport_id in (tc.STOP, tc.MUTE):
        command = tc.command(transport_id)
        if command is not None and _canonical(command.key) == pressed:
            return ("transport", transport_id)
    return None


def _key_name(wx: Any, code: int) -> str:
    if code == getattr(wx, "WXK_SPACE", 32):
        return "Space"
    if 32 < code < 127:
        return chr(code).upper()
    return ""


def _on_key(app: Any, wx: Any, event: Any) -> None:
    # Only chords: a bare letter typed into the search box never gets this far.
    if not (event.ControlDown() or event.AltDown()):
        event.Skip()
        return
    name = _key_name(wx, event.GetKeyCode())
    target = (
        resolve(
            chord_of(
                key=name,
                ctrl=event.ControlDown(),
                alt=event.AltDown(),
                shift=event.ShiftDown(),
            ),
            app._binding_for,
        )
        if name
        else None
    )
    if target is None:
        event.Skip()
        return
    kind, command_id = target
    if kind == "transport":
        from quill.ui.radio import transport_keys

        transport_keys.perform(app, command_id)
        return
    registry = getattr(app, "commands", None)
    if registry is None or registry.get(command_id) is None:
        event.Skip()
        return
    registry.run(command_id)


def install(app: Any, wx: Any) -> None:
    """Give the main window the keys no menu carries (see the module doc)."""
    app.frame.Bind(wx.EVT_CHAR_HOOK, lambda event: _on_key(app, wx, event))
