"""Quill Inkwell's own preferences (the abbreviations themselves are shared).

Kept deliberately small. The abbreviation library lives in QUILL's
``abbreviations.json`` and is shared by every app in the family; this file only
records how the system-wide expander should behave on this machine.

Persisted with the usual atomic write, wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_SETTINGS_FILE = "inkwell.json"

#: How the expansion reaches the focused application.
INJECTION_MODES: tuple[str, ...] = ("type", "paste")


@dataclass(slots=True)
class InkwellSettings:
    #: Master switch for system-wide expansion. When off, Inkwell still manages
    #: abbreviations; it just never types into other applications.
    expansion_enabled: bool = True
    #: "type" sends keystrokes and never touches the clipboard (the default);
    #: "paste" borrows the clipboard, pastes, and restores it -- only for the
    #: few targets that drop synthetic keystrokes.
    injection_mode: str = "type"
    #: Extra executables (lower-case basenames) where expansion never fires, on
    #: top of the built-in password-manager list.
    excluded_processes: list[str] = field(default_factory=list)
    #: Executables that need the clipboard route because they drop synthetic
    #: keystrokes. Per application, so one stubborn program does not force every
    #: other one to have its clipboard borrowed.
    paste_processes: list[str] = field(default_factory=list)
    #: Speak a short confirmation after each expansion, on top of whatever the
    #: individual entry asks for. Off by default: the expanded text is already
    #: in the application, and the screen reader usually says it.
    announce_expansions: bool = False
    start_in_tray: bool = False
    close_to_tray: bool = True
    #: Show/hide the Inkwell window from anywhere.
    tray_hotkey: str = "Ctrl+Alt+Shift+I"
    #: Open Quick Insert from anywhere, so a "manual" entry is always reachable.
    quick_insert_hotkey: str = "Ctrl+Alt+Shift+K"
    #: Expand the word just typed, without waiting for a trigger character --
    #: the system-wide twin of QUILL's Expand Abbreviation command. Works
    #: mid-word and at the end of a line.
    expand_now_hotkey: str = "Ctrl+Alt+Shift+X"


def settings_path(data_dir: Path) -> Path:
    return data_dir / _SETTINGS_FILE


def load_settings(data_dir: Path) -> InkwellSettings:
    from quill.core.storage import read_json

    raw = read_json(settings_path(data_dir), default={})
    if not isinstance(raw, dict):
        return InkwellSettings()
    settings = InkwellSettings()
    settings.expansion_enabled = bool(raw.get("expansion_enabled", True))
    mode = str(raw.get("injection_mode", "type"))
    settings.injection_mode = mode if mode in INJECTION_MODES else "type"
    excluded = raw.get("excluded_processes", [])
    if isinstance(excluded, list):
        settings.excluded_processes = [str(p).strip().lower() for p in excluded if str(p).strip()]
    paste_list = raw.get("paste_processes", [])
    if isinstance(paste_list, list):
        settings.paste_processes = [str(p).strip().lower() for p in paste_list if str(p).strip()]
    settings.announce_expansions = bool(raw.get("announce_expansions", False))
    settings.start_in_tray = bool(raw.get("start_in_tray", False))
    settings.close_to_tray = bool(raw.get("close_to_tray", True))
    settings.tray_hotkey = str(raw.get("tray_hotkey", "Ctrl+Alt+Shift+I"))
    settings.quick_insert_hotkey = str(raw.get("quick_insert_hotkey", "Ctrl+Alt+Shift+K"))
    settings.expand_now_hotkey = str(raw.get("expand_now_hotkey", "Ctrl+Alt+Shift+X"))
    return settings


def save_settings(data_dir: Path, settings: InkwellSettings) -> None:
    from quill.core.storage import write_json_atomic

    write_json_atomic(
        settings_path(data_dir),
        {
            "expansion_enabled": settings.expansion_enabled,
            "injection_mode": settings.injection_mode,
            "excluded_processes": settings.excluded_processes,
            "paste_processes": settings.paste_processes,
            "announce_expansions": settings.announce_expansions,
            "start_in_tray": settings.start_in_tray,
            "close_to_tray": settings.close_to_tray,
            "tray_hotkey": settings.tray_hotkey,
            "quick_insert_hotkey": settings.quick_insert_hotkey,
            "expand_now_hotkey": settings.expand_now_hotkey,
        },
    )
