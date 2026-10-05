"""Quill Inkwell's system-wide keys: show/hide, Quick Insert, Expand Word, and
(2026-10-05) Dictate Anywhere.

None is registered until the listener chooses it (questions.md 37b, option 3,
widened 2026-10-05): each old default was a menu key somewhere else in the
family, and a key registered system-wide silently wins over every one of them.
All three are chosen in the File menu through the one shared picker
(``quill/ui/show_hide_key_picker.py``) and refused by the same rules. Somebody
still on the old defaults is moved to none and told once
(``InkwellSettings.take_system_keys``).
"""

from __future__ import annotations

import sys
from typing import Any

import wx

__all__ = ["InkwellKeysMixin"]

#: Hotkey ids for the two system-wide keys this app registers of its own
#: (the tray toggle's id belongs to AppShellFrame).
_QUICK_INSERT_HOTKEY_ID = 0x51A1
_EXPAND_NOW_HOTKEY_ID = 0x51A2
_DICTATE_ANYWHERE_HOTKEY_ID = 0x51A3

#: field -> (hotkey id, caption, what it does, its name, handler method).
_KEYS: dict[str, tuple[int, str, str, str, str]] = {
    "quick_insert_hotkey": (
        _QUICK_INSERT_HOTKEY_ID,
        "Quick Insert Key",
        "opens Quill Inkwell's Quick Insert",
        "Quick Insert",
        "open_quick_insert",
    ),
    "expand_now_hotkey": (
        _EXPAND_NOW_HOTKEY_ID,
        "Expand Word Key",
        "expands the word you just typed",
        "Expand Word",
        "expand_now",
    ),
    "dictate_anywhere_hotkey": (
        _DICTATE_ANYWHERE_HOTKEY_ID,
        "Dictate Anywhere Key",
        "starts and stops dictating into the program in front",
        "Dictate Anywhere",
        "toggle_dictate_anywhere",
    ),
}


class InkwellKeysMixin:
    """On ``QuillInkwellFrame``: register, choose and keep the three keys."""

    _settings: Any
    _data_dir: Any
    frame: Any
    #: hotkey id -> the key registered under it now ("" for none).
    _inkwell_keys: dict[int, str]

    def _start_inkwell_keys(self) -> None:
        """At launch: migrate, register what was chosen, and say the once-only
        sentence if this launch moved somebody off the old defaults."""
        from quill.core.show_hide_keys import has_run_before

        try:
            ran_before = has_run_before(self._data_dir, "inkwell")
            chord, notice = self._settings.take_system_keys(self._data_dir, ran_before=ran_before)
        except Exception:  # noqa: BLE001 - a key must never stop the app opening
            chord, notice = self._settings.tray_hotkey, ""
        self._begin_show_hide_key(chord, notice)  # type: ignore[attr-defined]
        for field, (hotkey_id, _caption, _does, _name, handler) in _KEYS.items():
            self.frame.Bind(wx.EVT_HOTKEY, lambda _e, h=handler: getattr(self, h)(), id=hotkey_id)
            if getattr(self._settings, field):
                self._replace_global_hotkey(hotkey_id, getattr(self._settings, field))

    def _replace_global_hotkey(self, hotkey_id: int, chord: str) -> bool:
        """Swap the key registered under *hotkey_id* for *chord* ("" for none).

        False, with the old key back in place, when Windows will not give it --
        another program owns it, which is said rather than appearing to work.
        Failing to register must never stop the app from starting.
        """
        if not hasattr(self, "_inkwell_keys"):
            self._inkwell_keys = {}
        old = self._inkwell_keys.get(hotkey_id, "")
        if old:
            self._register_or_release(hotkey_id, "")
        if self._register_or_release(hotkey_id, chord):
            self._inkwell_keys[hotkey_id] = chord
            return True
        self._set_status(f"{chord} is already in use by another program.")  # type: ignore[attr-defined]
        if old:
            self._register_or_release(hotkey_id, old)
        return False

    def _register_or_release(self, hotkey_id: int, chord: str) -> bool:
        if not sys.platform.startswith("win"):
            return True
        try:
            if not chord:
                self.frame.UnregisterHotKey(hotkey_id)
                self._inkwell_keys[hotkey_id] = ""
                return True
            from quill.ui.tray_hotkey import parse_hotkey

            parsed = parse_hotkey(wx, chord)
            return parsed is not None and bool(self.frame.RegisterHotKey(hotkey_id, *parsed))
        except Exception:  # noqa: BLE001 - a denied key must never block startup
            return False

    def _own_keys(self, except_field: str) -> dict[str, str]:
        """Inkwell's other system-wide keys, which a new one may not equal."""
        keys = {"show and hide key": str(getattr(self, "_show_hide_key", "") or "")}
        for field, (_id, caption, _does, _name, _handler) in _KEYS.items():
            if field != except_field:
                keys[caption.replace(" Key", " key")] = str(getattr(self._settings, field))
        return keys

    def _append_inkwell_key_items(self, file_menu: Any) -> None:
        """File > Show and Hide Key..., Quick Insert Key... and Expand Word Key..."""
        self._append_show_hide_key_item(  # type: ignore[attr-defined]
            file_menu, "inkwell", self._save_tray_hotkey, lambda: self._own_keys("")
        )
        rows = (
            ("quick_insert_hotkey", "&Quick Insert Key...\tCtrl+Alt+Shift+K"),
            ("expand_now_hotkey", "Expand &Word Key...\tCtrl+Alt+Shift+E"),
            ("dictate_anywhere_hotkey", "&Dictate Anywhere Key...\tCtrl+Alt+Shift+D"),
        )
        for field, label in rows:
            item_id = wx.NewIdRef()
            file_menu.Append(item_id, label)
            self.frame.Bind(wx.EVT_MENU, lambda _e, f=field: self.choose_inkwell_key(f), id=item_id)
            self._keep_menu_ids(item_id)  # type: ignore[attr-defined]

    def choose_inkwell_key(self, field: str) -> None:
        """Choose the Quick Insert or Expand Word key with the shared picker."""
        from quill.core.expansion.settings import save_settings
        from quill.ui.show_hide_key_picker import run_system_key_command

        hotkey_id, caption, does, name, _handler = _KEYS[field]

        def save(chord: str) -> None:
            setattr(self._settings, field, chord)
            save_settings(self._data_dir, self._settings)

        run_system_key_command(
            self,
            wx,
            app_id="inkwell",
            current=str(getattr(self._settings, field)),
            caption=caption,
            purpose=does,
            name=name,
            replace=lambda chord: self._replace_global_hotkey(hotkey_id, chord),
            save=save,
            own=self._own_keys(field),
        )

    def _save_tray_hotkey(self, chord: str) -> None:
        from quill.core.expansion.settings import save_settings

        self._settings.tray_hotkey = chord
        save_settings(self._data_dir, self._settings)
