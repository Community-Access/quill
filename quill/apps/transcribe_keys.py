"""QUILL Transcribe's system-wide keys: start and stop, command, show and hide,
and Dictation Status, Resume and Discard Held Words.

Only the start and stop key has a default (Alt+Shift+\\, owner 2026-10-12); the
others are not registered until the person chooses them (spec section 7.1): a
key registered system-wide silently wins over every program's own use of it, so
the choice has to be theirs. All are chosen through the family's one picker
(:mod:`quill.ui.show_hide_key_picker`), which refuses a key any QuillVille app
already uses and says whose it is. When Windows refuses a key -- another program
has it -- that is said too. Windows can say that a key is taken, but not which
program took it, so the sentence never guesses.

**The Command Key** (D-1, 2026-10-15) is the keyboard way to the command word:
pressed in the field you are dictating into, the next thing you say is a
command; pressed again before you say it, command mode; pressed in command
mode, back to dictation. Empty by default, offered in setup beside Record Key,
and chosen from the File menu (Command Key..., Ctrl+Alt+Shift+K).

**Dictation Status, Resume and Discard Held Words** (D-6, 2026-10-15) are the
window's commands from wherever the person is working: one sentence of status,
the held words written back into their field, or thrown away. Each is empty by
default and chosen from the File menu through the same picker
(:data:`OPTIONAL_KEYS`); none is registered until it is chosen.

The tray menu and the window do everything the keys do, so no key is needed to
use the app.
"""

from __future__ import annotations

import sys
from typing import Any

import wx

__all__ = ["OPTIONAL_KEYS", "TranscribeKeysMixin"]

#: The start and stop key's hotkey id (the tray toggle's belongs to AppShellFrame).
_DICTATION_HOTKEY_ID = 0x51B1
#: The Command Key's (D-1).
_COMMAND_HOTKEY_ID = 0x51B2

_CAPTION = "Start and Stop Key"
_PURPOSE = "starts and stops dictation in the field you are in"
_COMMAND_CAPTION = "Command Key"
_COMMAND_PURPOSE = "makes the next thing you say a command; pressed twice, command mode"

#: The D-6 keys: settings field -> (hotkey id, caption, what it does, its name
#: when said back, the method it runs, the File menu row).
OPTIONAL_KEYS: dict[str, tuple[int, str, str, str, str, str]] = {
    "status_hotkey": (
        0x51B3,
        "Dictation Status Key",
        "says what dictation is doing, where, and with which model",
        "Dictation Status",
        "speak_dictation_status",
        "Dictation St&atus Key...\tCtrl+Alt+Shift+A",
    ),
    "resume_hotkey": (
        0x51B4,
        "Resume Key",
        "writes held words into their field and carries on dictating",
        "Resume",
        "resume_dictation",
        "Res&ume Key...\tCtrl+Alt+Shift+U",
    ),
    "discard_hotkey": (
        0x51B5,
        "Discard Held Words Key",
        "throws away the words held while dictation is paused",
        "Discard Held Words",
        "discard_held_words",
        "Discard Held Words Ke&y...\tCtrl+Alt+Shift+Y",
    ),
}


class TranscribeKeysMixin:
    """On ``QuillTranscribeFrame``: register, choose and keep the three keys."""

    _settings: Any
    _data_dir: Any
    _safe_mode: bool
    frame: Any

    def _start_transcribe_keys(self) -> str:
        """At launch: the show/hide key, then the start and stop key, then the
        Command Key, then the D-6 keys. Returns a sentence to say once when a
        saved key is not usable."""
        self._dictation_key_registered = ""
        self._command_key_registered = ""
        self._optional_registered: dict[str, str] = {}
        if self._safe_mode:
            return ""  # Safe Mode registers nothing system-wide (spec 9.3)
        self._start_show_hide_key("transcribe")  # type: ignore[attr-defined]
        self.frame.Bind(
            wx.EVT_HOTKEY,
            lambda _e: self.toggle_dictation(),  # type: ignore[attr-defined]
            id=_DICTATION_HOTKEY_ID,
        )
        self.frame.Bind(
            wx.EVT_HOTKEY,
            lambda _e: self.command_key_pressed(),  # type: ignore[attr-defined]
            id=_COMMAND_HOTKEY_ID,
        )
        notices: list[str] = []
        chord = self._settings.dictation_hotkey
        if chord and not self._register_dictation_key(chord):
            notices.append(
                f"Your start and stop key, {chord}, is not working: Windows says another "
                "program is using it. If that is Quill Inkwell with the same key, Inkwell "
                "passes it to QUILL Transcribe. To choose another, open the File menu "
                "and choose Start and Stop Key."
            )
        command = str(getattr(self._settings, "command_hotkey", "") or "")
        if command and not self._register_command_key(command):
            notices.append(
                f"Your Command Key, {command}, is not working: Windows says another program "
                "is using it. To choose another, open the File menu and choose Command Key."
            )
        for field, (hotkey_id, caption, _does, _name, method, _row) in OPTIONAL_KEYS.items():
            self.frame.Bind(
                wx.EVT_HOTKEY, lambda _e, run=method: getattr(self, run)(), id=hotkey_id
            )
            chosen = str(getattr(self._settings, field, "") or "")
            if chosen and not self._register_optional_key(field, chosen):
                notices.append(
                    f"Your {caption}, {chosen}, is not working: Windows says another program "
                    f"is using it. To choose another, open the File menu and choose {caption}."
                )
        return " ".join(notices)

    def optional_key(self, field: str) -> str:
        """The D-6 key registered now for *field* ("" when there is none)."""
        return str(getattr(self, "_optional_registered", {}).get(field, "") or "")

    def _register_optional_key(self, field: str, chord: str) -> bool:
        """Swap the registered key for *field* (``status_hotkey`` ...)."""
        registered = getattr(self, "_optional_registered", None)
        if registered is None:
            registered = self._optional_registered = {}
        attribute = f"_optional_{field}"
        setattr(self, attribute, registered.get(field, ""))
        done = self._swap_key(OPTIONAL_KEYS[field][0], attribute, chord)
        registered[field] = str(getattr(self, attribute, "") or "")
        return done

    def dictation_key(self) -> str:
        """The key registered now ("" when there is none)."""
        return str(getattr(self, "_dictation_key_registered", "") or "")

    def command_key(self) -> str:
        """The Command Key registered now ("" when there is none)."""
        return str(getattr(self, "_command_key_registered", "") or "")

    def _register_dictation_key(self, chord: str) -> bool:
        """Swap the registered start and stop key for *chord* ("" for none).
        ``False``, with the old key back, when Windows will not give it."""
        return self._swap_key(_DICTATION_HOTKEY_ID, "_dictation_key_registered", chord)

    def _register_command_key(self, chord: str) -> bool:
        """The same, for the Command Key."""
        return self._swap_key(_COMMAND_HOTKEY_ID, "_command_key_registered", chord)

    def _swap_key(self, hotkey_id: int, field: str, chord: str) -> bool:
        old = str(getattr(self, field, "") or "")
        if old:
            self._hotkey(old, register=False, hotkey_id=hotkey_id)
            setattr(self, field, "")
        if not chord:
            return True
        if self._hotkey(chord, register=True, hotkey_id=hotkey_id):
            setattr(self, field, chord)
            return True
        if old and self._hotkey(old, register=True, hotkey_id=hotkey_id):
            setattr(self, field, old)
        return False

    def _hotkey(self, chord: str, *, register: bool, hotkey_id: int = _DICTATION_HOTKEY_ID) -> bool:
        if not sys.platform.startswith("win"):
            return True
        try:
            if not register:
                self.frame.UnregisterHotKey(hotkey_id)
                return True
            from quill.ui.tray_hotkey import parse_hotkey

            parsed = parse_hotkey(wx, chord)
            return parsed is not None and bool(self.frame.RegisterHotKey(hotkey_id, *parsed))
        except Exception:  # noqa: BLE001 - a denied key must never block startup
            return False

    def _own_keys(self, field: str) -> dict[str, str]:
        """This app's other system-wide keys, which a new one may not equal."""
        keys = {
            "show_hide": ("show and hide key", str(getattr(self, "_show_hide_key", "") or "")),
            "dictation": ("start and stop key", self._settings.dictation_hotkey),
            "command": ("Command Key", str(getattr(self._settings, "command_hotkey", "") or "")),
        }
        for name, row in OPTIONAL_KEYS.items():
            keys[name] = (row[1], str(getattr(self._settings, name, "") or ""))
        return {name: chord for key, (name, chord) in keys.items() if key != field}

    def choose_dictation_key(self) -> None:
        """Dictation > Start and Stop Key...: the shared picker."""

        def save(chord: str) -> None:
            self._settings.dictation_hotkey = chord

        self._choose_key(
            current=self._settings.dictation_hotkey,
            caption=_CAPTION,
            purpose=_PURPOSE,
            name="Dictation",
            replace=self._register_dictation_key,
            save=save,
            field="dictation",
        )

    def choose_command_key(self) -> None:
        """File > Command Key...: the shared picker, for the Command Key."""

        def save(chord: str) -> None:
            self._settings.command_hotkey = chord

        self._choose_key(
            current=str(getattr(self._settings, "command_hotkey", "") or ""),
            caption=_COMMAND_CAPTION,
            purpose=_COMMAND_PURPOSE,
            name="The Command Key",
            replace=self._register_command_key,
            save=save,
            field="command",
        )

    def choose_optional_key(self, field: str) -> None:
        """File > Dictation Status Key..., Resume Key... or Discard Held Words
        Key...: the shared picker, for one of the D-6 keys."""
        _hotkey_id, caption, does, name, _method, _row = OPTIONAL_KEYS[field]

        def save(chord: str) -> None:
            setattr(self._settings, field, chord)

        self._choose_key(
            current=str(getattr(self._settings, field, "") or ""),
            caption=caption,
            purpose=does,
            name=name,
            replace=lambda chord: self._register_optional_key(field, chord),
            save=save,
            field=field,
        )

    def _choose_key(self, *, save: Any, field: str, **picker: Any) -> None:
        from quill.core.transcribe.settings import save_settings
        from quill.ui.show_hide_key_picker import run_system_key_command

        if self._safe_mode:
            self._announce("Safe Mode is on, so no system-wide key is registered.")  # type: ignore[attr-defined]
            return

        def keep(chord: str) -> None:
            save(chord)
            save_settings(self._data_dir, self._settings)
            refresh = getattr(self, "_refresh_view", None)
            if callable(refresh):
                refresh()

        run_system_key_command(
            self, wx, app_id="transcribe", save=keep, own=self._own_keys(field), **picker
        )

    def _append_key_items(self, menu: Any) -> None:
        """Show and Hide Key..., Start and Stop Key..., Command Key... and the
        D-6 keys, in one menu."""
        self._append_show_hide_key_item(  # type: ignore[attr-defined]
            menu, "transcribe", None, lambda: self._own_keys("show_hide")
        )
        rows: list[tuple[str, Any]] = [
            ("Start and Stop &Key...\tCtrl+Alt+Shift+D", self.choose_dictation_key),
            ("Co&mmand Key...\tCtrl+Alt+Shift+K", self.choose_command_key),
        ]
        for field, row in OPTIONAL_KEYS.items():
            rows.append((row[5], lambda chosen=field: self.choose_optional_key(chosen)))
        for label, handler in rows:
            item_id = wx.NewIdRef()
            menu.Append(item_id, label)
            self.frame.Bind(wx.EVT_MENU, lambda _e, run=handler: run(), id=item_id)
            self._keep_menu_ids(item_id)  # type: ignore[attr-defined]

    def _release_transcribe_keys(self) -> None:
        if self.dictation_key():
            self._hotkey(self.dictation_key(), register=False)
            self._dictation_key_registered = ""
        if self.command_key():
            self._hotkey(self.command_key(), register=False, hotkey_id=_COMMAND_HOTKEY_ID)
            self._command_key_registered = ""
        for field in OPTIONAL_KEYS:
            if self.optional_key(field):
                self._register_optional_key(field, "")
        self._release_tray_hotkey()  # type: ignore[attr-defined]
