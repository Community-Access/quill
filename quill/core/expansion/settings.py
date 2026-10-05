"""Quill Inkwell's own preferences (the abbreviations themselves are shared).

Kept deliberately small. The abbreviation library lives in QUILL's
``abbreviations.json`` and is shared by every app in the family; this file only
records how the system-wide expander should behave on this machine.

Persisted with the usual atomic write, wx-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path

from quill.core.settings_portable import (
    PortabilityReport,
    portable_export,
    portable_import,
)

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
    #: Show/hide the Inkwell window from anywhere. None until the listener
    #: chooses one (File > Show and Hide Key): Ctrl+Alt+Shift+I until
    #: 2026-10-05, which is a menu key in both editors (core/family_chords.py).
    tray_hotkey: str = ""
    #: Open Quick Insert from anywhere, so a "manual" entry is always reachable.
    #: None until the listener chooses one (File > Quick Insert Key):
    #: Ctrl+Alt+Shift+K until 2026-10-05, a menu key elsewhere in the family.
    quick_insert_hotkey: str = ""
    #: Expand the word just typed, without waiting for a trigger character --
    #: the system-wide twin of QUILL's Expand Abbreviation command. Works
    #: mid-word and at the end of a line. None until chosen (File > Expand Word
    #: Key): Ctrl+Alt+Shift+X until 2026-10-05, Quill Radio's Export My Setup.
    expand_now_hotkey: str = ""
    #: Set when the file on disk came from a newer build. Not persisted: it is
    #: a fact about *this* load, and saving would be the thing it prevents.
    read_only: bool = False

    def take_system_keys(self, data_dir: Path, *, ran_before: bool) -> tuple[str, str]:
        """``(show/hide key to register, sentence to say once)`` at launch, for
        all three of Inkwell's system-wide keys.

        A key still on its old default moves to none and is saved; a key the
        listener chose is kept. With no settings file at all nothing was ever
        changed, so somebody who has run Inkwell before (*ran_before*) had all
        three old defaults; somebody new is told nothing. Either way the file
        is written, so the sentence is said once.
        """
        from quill.core.family_chords import migrate_show_hide_key
        from quill.core.lite.keymap import chord_identity

        moved: list[str] = []
        if not settings_path(data_dir).exists():
            if ran_before:
                moved = [_SHOW_HIDE, *(label for _old, label in _RETIRED_HOTKEYS.values())]
            save_settings(data_dir, self)
            return self.tray_hotkey, retired_keys_notice(moved)
        chord, tell = migrate_show_hide_key("inkwell", self.tray_hotkey, existing_user=True)
        if tell:
            self.tray_hotkey = chord
            moved.append(_SHOW_HIDE)
        for name, (old, label) in _RETIRED_HOTKEYS.items():
            value = str(getattr(self, name)).strip()
            if value and chord_identity(value) == chord_identity(old):
                setattr(self, name, "")
                moved.append(label)
        if moved:
            save_settings(data_dir, self)
        return self.tray_hotkey, retired_keys_notice(moved)


_SHOW_HIDE = "show and hide"

#: The two keys Inkwell registered system-wide until 2026-10-05, each a menu key
#: elsewhere in the family, and the name each is called by now. A saved key
#: equal to its old default moves to none, and the listener is told once.
_RETIRED_HOTKEYS: dict[str, tuple[str, str]] = {
    "quick_insert_hotkey": ("Ctrl+Alt+Shift+K", "Quick Insert"),
    "expand_now_hotkey": ("Ctrl+Alt+Shift+X", "Expand Word"),
}

#: ``{field: old default}``.
RETIRED_HOTKEY_DEFAULTS: dict[str, str] = {
    name: old for name, (old, _label) in _RETIRED_HOTKEYS.items()
}


def retired_keys_notice(moved: list[str]) -> str:
    """What somebody whose keys were on the old defaults is told, once.

    The show-and-hide key alone keeps the family's own sentence, word for word.
    """
    from quill.core.family_chords import retired_key_notice

    if not moved:
        return ""
    if moved == [_SHOW_HIDE]:
        return retired_key_notice("inkwell")
    if len(moved) == 1:
        return (
            f"Quill Inkwell's {moved[0]} key is now off by default so it no longer "
            "blocks other apps' shortcuts. To choose one, open the File menu and "
            f"choose {moved[0]} Key."
        )
    names = ", ".join(moved[:-1]) + " and " + moved[-1]
    return (
        f"Quill Inkwell's {names} keys are now off by default so they no longer "
        "block other apps' shortcuts. To choose them, open the File menu."
    )


#: Bumped when a field changes meaning (never merely when one is added --
#: every field defaults, so an added one needs no migration).
SCHEMA_VERSION = 1


def settings_path(data_dir: Path) -> Path:
    return data_dir / _SETTINGS_FILE


def load_settings(data_dir: Path) -> InkwellSettings:
    from quill.core.storage import read_json

    raw = read_json(settings_path(data_dir), default={})
    if not isinstance(raw, dict):
        return InkwellSettings()
    # A file from a *newer* build is read for what this build understands and
    # never written back over: an older Inkwell that saved would silently drop
    # every field it had never heard of, which for a settings file people share
    # between machines is how a preference disappears with no error anywhere.
    if int(raw.get("schema_version", SCHEMA_VERSION) or SCHEMA_VERSION) > SCHEMA_VERSION:
        settings = _read_fields(raw)
        settings.read_only = True
        return settings
    return _read_fields(raw)


def _read_fields(raw: dict) -> InkwellSettings:
    """Every field this build knows, defaulted individually.

    Field by field rather than wholesale, so a file missing a key (an older
    build) and a file with an unknown one (a newer build) both load without a
    migration step -- which is the versioned contract's whole point.
    """
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
    settings.tray_hotkey = str(raw.get("tray_hotkey", ""))
    # A file without these keys came from a build that registered the old
    # defaults, so that is what it had; take_system_keys moves them to none.
    for name, old in RETIRED_HOTKEY_DEFAULTS.items():
        setattr(settings, name, str(raw.get(name, old)))
    return settings


def save_settings(data_dir: Path, settings: InkwellSettings) -> None:
    """Persist, stamped with the schema version (the versioned contract).

    Refuses when the loaded file came from a newer build: writing would drop
    every field this build does not know about.
    """
    from quill.core.storage import write_json_atomic

    if settings.read_only:
        return
    write_json_atomic(
        settings_path(data_dir),
        {
            "schema_version": SCHEMA_VERSION,
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


#: Settings that describe *this machine* rather than how the app behaves, and so
#: are left out of a portable backup. The two process lists name programs
#: installed on this machine, so they do not travel; the hotkeys and the
#: expansion behaviour do (#1501).
LOCAL_SETTINGS: frozenset[str] = frozenset({
    "excluded_processes",
    "paste_processes",
})


def export_portable(settings: InkwellSettings) -> tuple[dict[str, object], PortabilityReport]:
    """These settings as a portable file, and what was left behind."""
    return portable_export(settings, app="inkwell", local_fields=LOCAL_SETTINGS)


def import_portable(raw: object) -> tuple[dict[str, object], PortabilityReport]:
    """The settings in *raw* this build can use, and what was different."""
    known = frozenset(field.name for field in fields(InkwellSettings))
    return portable_import(raw, known=known, local_fields=LOCAL_SETTINGS)
