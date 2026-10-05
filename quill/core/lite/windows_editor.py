"""QUILL Lite's half of the shared text-editor registration: its profile, bound.

The capability lives in :mod:`quill.core.windows_editor`, because QUILL has the
same two commands and the same installer keys (the family rule: QUILL Lite is
never ahead of QUILL). This module only fixes the profile to QUILL Lite's, so
the names QUILL Lite's code and tests have always used -- ``PROGID``,
``EXTENSIONS``, ``registration_plan(argv, icon)`` -- keep meaning what they did.
"""

from __future__ import annotations

from collections.abc import Sequence

from quill.core import windows_editor as _shared
from quill.core.windows_editor import (
    IFEO_KEY,
    NOTEPAD_FLAG,
    NotepadState,
    RegistryReader,
    RegistryWriter,
    RegKey,
    RegValue,
    elevated_parameters,
    notepad_debugger_value,
    notepad_keys,
    open_command,
    reg_add_arguments,
    reg_delete_arguments,
    safe_for_cmd,
    translate_notepad_argv,
    turn_on_commands,
    write_plan,
)

__all__ = [
    "CAPABILITIES_KEY",
    "EXE_NAME",
    "EXTENSIONS",
    "IFEO_KEY",
    "NOTEPAD_FLAG",
    "PROFILE",
    "PROGID",
    "NotepadState",
    "RegKey",
    "RegistryReader",
    "RegistryWriter",
    "RegValue",
    "default_apps_uri",
    "elevated_parameters",
    "is_ours",
    "machine_registered",
    "notepad_debugger_value",
    "notepad_keys",
    "open_command",
    "read_notepad_state",
    "reg_add_arguments",
    "reg_delete_arguments",
    "registration_plan",
    "safe_for_cmd",
    "translate_notepad_argv",
    "turn_off_commands",
    "turn_on_commands",
    "write_plan",
]

PROFILE = _shared.QUILL_LITE
PROGID = PROFILE.progid
EXE_NAME = PROFILE.exe_name
EXTENSIONS = PROFILE.extensions
CAPABILITIES_KEY = PROFILE.capabilities_key


def registration_plan(launcher_argv: Sequence[str], icon: str) -> list[RegKey]:
    return _shared.registration_plan(PROFILE, launcher_argv, icon)


def machine_registered(reader: RegistryReader, launcher_argv: Sequence[str]) -> bool:
    return _shared.machine_registered(PROFILE, reader, launcher_argv)


def default_apps_uri(build: int, *, machine: bool = False) -> str:
    return _shared.default_apps_uri(PROFILE, build, machine=machine)


def is_ours(value: object) -> bool:
    return _shared.is_ours(PROFILE, value)


def read_notepad_state(reader: RegistryReader) -> NotepadState:
    return _shared.read_notepad_state(PROFILE, reader)


def turn_off_commands(reader: RegistryReader) -> list[list[str]]:
    return _shared.turn_off_commands(PROFILE, reader)
