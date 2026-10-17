"""Edit > Dictate Here in Quill Cast and Quill Radio (dict.md D-16).

The frame's side of :mod:`quill.core.windows_dictation.dictate_here`: one
command, ``app.dictate_here`` on Ctrl+F11 (``APP_KEYMAPS``), registered and
menu-wired once for both listening apps through :mod:`quill.ui.app_support`
and :func:`quill.ui.support_menu.insert_edit_menu`.

**The key in a dialog, too.** The search boxes people dictate into most --
Cast's Add Podcast and Search Everywhere, Radio's Search Stations -- are in
modal dialogs, where Windows never consults the main window's menu
accelerators. So the command also installs one :class:`wx.EventFilter` that
answers the same key, as bound now, in a text field of any *other* window of
this app. In the main window the menu accelerator answers it, and the filter
stays out of the way, so the key never fires twice.

It speaks only what QUILL Transcribe will not: nothing when the request is
passed on (QUILL Transcribe says "Dictation on" itself), and a sentence when it
is starting QUILL Transcribe, when Quill Inkwell has the microphone, or when
there is no QUILL Transcribe to ask (GATE-13).
"""

from __future__ import annotations

from typing import Any

import wx

#: The command, its title and its key's home (``APP_KEYMAPS["cast"]`` and
#: ``APP_KEYMAPS["radio"]``).
COMMAND_ID = "app.dictate_here"
TITLE = "Dictate Here"

_MODIFIERS = (
    (wx.ACCEL_CTRL, wx.MOD_CONTROL),
    (wx.ACCEL_ALT, wx.MOD_ALT),
    (wx.ACCEL_SHIFT, wx.MOD_SHIFT),
)


def dictate_here_available() -> bool:
    """Whether to offer the item at all: only where QUILL Transcribe may be
    launched or advertised (``RELEASED_APPS``, or a developer build). A public
    build without it would offer a key whose only answer is "not installed"."""
    from quill.core.app_launcher import is_app_released

    return is_app_released("transcribe")


def key_matches(binding: str, key_code: int, modifiers: int) -> bool:
    """Whether a key press (*key_code*, wx ``MOD_*`` *modifiers*) is *binding*."""
    entry = wx.AcceleratorEntry()
    if not binding or not entry.FromString(binding):
        return False
    wanted = 0
    for accel, mod in _MODIFIERS:
        if entry.GetFlags() & accel:
            wanted |= mod
    return bool(entry.GetKeyCode() == key_code and wanted == modifiers)


class _DialogKeyFilter(wx.EventFilter):
    """Ctrl+F11 (as bound) in a text field of one of this app's dialogs."""

    def __init__(self, host: DictateHereMixin) -> None:
        super().__init__()
        self._host = host

    def FilterEvent(self, event: wx.Event) -> int:  # noqa: N802 - wx's name
        if event.GetEventType() != wx.wxEVT_KEY_DOWN:
            return int(wx.EventFilter.Event_Skip)
        try:
            if self._host._dictate_here_key_in_dialog(event):
                return int(wx.EventFilter.Event_Processed)
        except Exception:  # noqa: BLE001 - a key filter must never break typing
            pass
        return int(wx.EventFilter.Event_Skip)


class DictateHereMixin:
    """Mixed into ``RadioAppFrame`` and ``PodcastsAppFrame`` through
    :class:`~quill.ui.app_support.ListeningAppSupportMixin`."""

    def _register_dictate_here_command(self) -> None:
        if not dictate_here_available():
            return
        commands: Any = self.commands  # type: ignore[attr-defined]
        binding_for = getattr(self, "_binding_for", None)
        commands.try_register(
            COMMAND_ID,
            TITLE,
            self.dictate_here,
            binding_for(COMMAND_ID) if callable(binding_for) else None,
            feature_id="core.app",
        )
        self._install_dictate_here_filter()

    def _install_dictate_here_filter(self) -> None:
        if getattr(self, "_dictate_here_filter", None) is not None:
            return
        key_filter = _DialogKeyFilter(self)
        wx.EvtHandler.AddFilter(key_filter)
        self._dictate_here_filter = key_filter
        frame = getattr(self, "frame", None)
        if frame is not None:
            frame.Bind(wx.EVT_WINDOW_DESTROY, self._on_dictate_here_frame_destroyed)

    def _remove_dictate_here_filter(self) -> None:
        key_filter = getattr(self, "_dictate_here_filter", None)
        if key_filter is not None:
            wx.EvtHandler.RemoveFilter(key_filter)
            self._dictate_here_filter = None

    def _on_dictate_here_frame_destroyed(self, event: Any) -> None:
        if event.GetEventObject() is getattr(self, "frame", None):
            self._remove_dictate_here_filter()
        event.Skip()

    def _dictate_here_key_in_dialog(self, event: Any) -> bool:
        """Answer the key in a text field outside the main window; ``True``
        when it was ours. The main window has the menu accelerator."""
        keymap = getattr(self, "keymap", None) or {}
        if not key_matches(
            str(keymap.get(COMMAND_ID, "")), event.GetKeyCode(), event.GetModifiers()
        ):
            return False
        field = event.GetEventObject()
        if not isinstance(field, wx.TextCtrl | wx.ComboBox | wx.SearchCtrl):
            return False
        if wx.GetTopLevelParent(field) is getattr(self, "frame", None):
            return False
        self.dictate_here()
        return True

    def _dictate_here_sender(self) -> str:
        """``"cast"`` or ``"radio"``: the app id the shell's keymap was applied for."""
        app = str(getattr(self, "_app_keymap_id", "") or "")
        return app if app in ("cast", "radio") else "radio"

    def dictate_here(self) -> None:
        """Ctrl+F11: QUILL Transcribe dictates into the field you are in."""
        from quill.core.windows_dictation.dictate_here import dictate_here

        outcome = dictate_here(self._dictate_here_sender())
        if outcome.sentence:
            announce: Any = getattr(self, "_announce", None)
            if callable(announce):
                announce(outcome.sentence)
