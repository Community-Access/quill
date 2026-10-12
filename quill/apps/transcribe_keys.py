"""QUILL Transcribe's system-wide keys: start and stop, and show and hide.

Neither is registered until the person chooses it (spec section 7.1): a key
registered system-wide silently wins over every program's own use of it, so
the choice has to be theirs. Both are chosen through the family's one picker
(:mod:`quill.ui.show_hide_key_picker`), which refuses a key any QuillVille app
already uses and says whose it is. When Windows refuses a key -- another program
has it -- that is said too. Windows can say that a key is taken, but not which
program took it, so the sentence never guesses.

The tray menu and the window do everything the keys do, so neither key is
needed to use the app.
"""

from __future__ import annotations

import sys
from typing import Any

import wx

__all__ = ["TranscribeKeysMixin"]

#: The start and stop key's hotkey id (the tray toggle's belongs to AppShellFrame).
_DICTATION_HOTKEY_ID = 0x51B1

_CAPTION = "Start and Stop Key"
_PURPOSE = "starts and stops dictation in the field you are in"


class TranscribeKeysMixin:
    """On ``QuillTranscribeFrame``: register, choose and keep the two keys."""

    _settings: Any
    _data_dir: Any
    _safe_mode: bool
    frame: Any

    def _start_transcribe_keys(self) -> str:
        """At launch: the show/hide key, then the start and stop key. Returns a
        sentence to say once when the saved start and stop key is not usable."""
        self._dictation_key_registered = ""
        if self._safe_mode:
            return ""  # Safe Mode registers nothing system-wide (spec 9.3)
        self._start_show_hide_key("transcribe")  # type: ignore[attr-defined]
        self.frame.Bind(
            wx.EVT_HOTKEY,
            lambda _e: self.toggle_dictation(),  # type: ignore[attr-defined]
            id=_DICTATION_HOTKEY_ID,
        )
        chord = self._settings.dictation_hotkey
        if not chord:
            return ""
        if self._register_dictation_key(chord):
            return ""
        return (
            f"Your start and stop key, {chord}, is not working: Windows says another "
            "program is using it. If that is Quill Inkwell with the same key, Inkwell "
            "passes it to QUILL Transcribe. To choose another, open the Dictation menu "
            "and choose Start and Stop Key."
        )

    def dictation_key(self) -> str:
        """The key registered now ("" when there is none)."""
        return str(getattr(self, "_dictation_key_registered", "") or "")

    def _register_dictation_key(self, chord: str) -> bool:
        """Swap the registered start and stop key for *chord* ("" for none).
        ``False``, with the old key back, when Windows will not give it."""
        old = self.dictation_key()
        if old:
            self._hotkey(old, register=False)
            self._dictation_key_registered = ""
        if not chord:
            return True
        if self._hotkey(chord, register=True):
            self._dictation_key_registered = chord
            return True
        if old and self._hotkey(old, register=True):
            self._dictation_key_registered = old
        return False

    def _hotkey(self, chord: str, *, register: bool) -> bool:
        if not sys.platform.startswith("win"):
            return True
        try:
            if not register:
                self.frame.UnregisterHotKey(_DICTATION_HOTKEY_ID)
                return True
            from quill.ui.tray_hotkey import parse_hotkey

            parsed = parse_hotkey(wx, chord)
            return parsed is not None and bool(
                self.frame.RegisterHotKey(_DICTATION_HOTKEY_ID, *parsed)
            )
        except Exception:  # noqa: BLE001 - a denied key must never block startup
            return False

    def _own_keys(self, field: str) -> dict[str, str]:
        """This app's other system-wide key, which a new one may not equal."""
        if field == "show_hide":
            return {"start and stop key": self._settings.dictation_hotkey}
        return {"show and hide key": str(getattr(self, "_show_hide_key", "") or "")}

    def choose_dictation_key(self) -> None:
        """Dictation > Start and Stop Key...: the shared picker."""
        from quill.core.transcribe.settings import save_settings
        from quill.ui.show_hide_key_picker import run_system_key_command

        if self._safe_mode:
            self._announce("Safe Mode is on, so no system-wide key is registered.")  # type: ignore[attr-defined]
            return

        def save(chord: str) -> None:
            self._settings.dictation_hotkey = chord
            save_settings(self._data_dir, self._settings)
            refresh = getattr(self, "_refresh_view", None)
            if callable(refresh):
                refresh()

        run_system_key_command(
            self,
            wx,
            app_id="transcribe",
            current=self._settings.dictation_hotkey,
            caption=_CAPTION,
            purpose=_PURPOSE,
            name="Dictation",
            replace=self._register_dictation_key,
            save=save,
            own=self._own_keys("dictation"),
        )

    def _append_key_items(self, menu: Any) -> None:
        """Show and Hide Key... and Start and Stop Key..., in one menu."""
        self._append_show_hide_key_item(  # type: ignore[attr-defined]
            menu, "transcribe", None, lambda: self._own_keys("show_hide")
        )
        item_id = wx.NewIdRef()
        menu.Append(item_id, "Start and Stop &Key...\tCtrl+Alt+Shift+D")
        self.frame.Bind(wx.EVT_MENU, lambda _e: self.choose_dictation_key(), id=item_id)
        self._keep_menu_ids(item_id)  # type: ignore[attr-defined]

    def _release_transcribe_keys(self) -> None:
        if self.dictation_key():
            self._hotkey(self.dictation_key(), register=False)
            self._dictation_key_registered = ""
        self._release_tray_hotkey()  # type: ignore[attr-defined]
