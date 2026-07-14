from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.shell_verbs import ShellVerb, default_shell_verbs, verb_actions

if TYPE_CHECKING:  # noqa: I001 - deferred to avoid a circular import at runtime
    from quill.platform.shell_integration import ShellIntegrationStatus

try:  # pragma: no cover - Windows-only module
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None

APP_DISPLAY_NAME = "Quill"
APPLICATION_NAME = "quill"
APPLICATION_KEY = rf"Software\Classes\Applications\{APPLICATION_NAME}.exe"
PROGID_TEXT = "Quill.Text"
PROGID_MARKUP = "Quill.Markup"
PROGID_HTML = "Quill.HTML"

#: Namespace prefix for QUILL "Send to Quill" context-menu verb keys.
VERB_KEY_PREFIX = "Quill"
#: Per-extension context menus live under this Windows registry root.
SYSTEM_FILE_ASSOCIATIONS = r"Software\Classes\SystemFileAssociations"

TEXT_EXTENSIONS = (".txt",)
MARKUP_EXTENSIONS = (".md", ".markdown", ".mdx")
HTML_EXTENSIONS = (".html", ".htm", ".xhtml")


@dataclass(frozen=True, slots=True)
class RegistryValue:
    name: str
    value: object
    kind: int


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    path: str
    values: tuple[RegistryValue, ...]


def launcher_command() -> str:
    executable = Path(sys.executable)
    return f'"{executable}" -m quill "%1"'


def verb_launcher_command(action: str) -> str:
    """Return the launch command for a "Send to Quill" verb.

    The selected file is passed as ``%1`` and the verb is carried through the
    ``--action`` flag so the running (or new) instance knows what to do.

    SECURITY (SEC-17): the returned string is written verbatim into the Windows
    registry as a shell command. It must never embed untrusted, free-form user
    input. The executable is derived from :data:`sys.executable` (never a
    user-supplied path) and ``action`` is validated against the closed
    :func:`~quill.core.shell_verbs.verb_actions` registry below; an unknown or
    malformed action raises :class:`ValueError` rather than reaching the
    registry. If this function is ever extended to accept a configurable
    launcher path or a free-form action, those inputs MUST be validated against
    an allowlist (or quoted) before inclusion here.
    """

    executable = Path(sys.executable)
    safe_action = (action or "open").strip().lower()
    if safe_action not in verb_actions():
        raise ValueError(f"Unknown shell verb action: {action!r}")
    return f'"{executable}" -m quill --action {safe_action} "%1"'


def _verb_key_name(verb: ShellVerb) -> str:
    return f"{VERB_KEY_PREFIX}.{verb.verb_id}"


def build_context_menu_plan(
    verbs: tuple[ShellVerb, ...] | list[ShellVerb] | None = None,
) -> list[RegistryEntry]:
    """Return registry entries for the file-manager right-click verbs.

    Each verb is registered per file extension under
    ``SystemFileAssociations\\<ext>\\shell\\Quill.<verb_id>`` so QUILL appears
    in the context menu without owning the file's default association.
    """

    selected = tuple(verbs) if verbs is not None else default_shell_verbs()
    entries: list[RegistryEntry] = []
    for verb in selected:
        key_name = _verb_key_name(verb)
        command = verb_launcher_command(verb.action)
        for extension in verb.extensions:
            shell_key = rf"{SYSTEM_FILE_ASSOCIATIONS}\{extension}\shell\{key_name}"
            entries.append(
                RegistryEntry(
                    path=shell_key,
                    values=(
                        RegistryValue("", verb.label, _reg_kind("sz")),
                        RegistryValue("MUIVerb", verb.label, _reg_kind("sz")),
                    ),
                )
            )
            entries.append(
                RegistryEntry(
                    path=rf"{shell_key}\command",
                    values=(RegistryValue("", command, _reg_kind("sz")),),
                )
            )
    return entries


def context_menu_registry_paths(
    verbs: tuple[ShellVerb, ...] | list[ShellVerb] | None = None,
) -> list[str]:
    """Return registry key paths created for the given (or all) verbs."""

    selected = tuple(verbs) if verbs is not None else default_shell_verbs()
    paths: list[str] = []
    for verb in selected:
        key_name = _verb_key_name(verb)
        for extension in verb.extensions:
            shell_key = rf"{SYSTEM_FILE_ASSOCIATIONS}\{extension}\shell\{key_name}"
            paths.append(rf"{shell_key}\command")
            paths.append(shell_key)
    return paths


def install_context_menu(
    verbs: tuple[ShellVerb, ...] | list[ShellVerb] | None = None,
) -> None:
    """Write the "Send to Quill" context-menu verbs to the registry."""

    if winreg is None:  # pragma: no cover - non-Windows fallback
        raise RuntimeError("Windows registry access is unavailable")
    for entry in build_context_menu_plan(verbs):
        _write_entry(entry)


def remove_context_menu(
    verbs: tuple[ShellVerb, ...] | list[ShellVerb] | None = None,
) -> None:
    """Remove the "Send to Quill" context-menu verbs from the registry.

    When ``verbs`` is ``None`` every known default verb key is removed, so a
    full uninstall clears stale entries regardless of current settings.
    """

    if winreg is None:  # pragma: no cover - non-Windows fallback
        raise RuntimeError("Windows registry access is unavailable")
    for path in context_menu_registry_paths(verbs):
        _delete_tree(winreg.HKEY_CURRENT_USER, path)


def apply_shell_verb_settings(settings: object) -> None:
    """Reconcile the context-menu verbs with the current settings.

    Removes every known default verb key, then installs only the verbs the user
    has enabled. ``settings`` is any object exposing the verb settings as
    attributes (typically :class:`~quill.core.settings.Settings`).
    """

    from quill.core.shell_verbs import enabled_verbs

    if winreg is None:  # pragma: no cover - non-Windows fallback
        raise RuntimeError("Windows registry access is unavailable")
    remove_context_menu()
    active = enabled_verbs(
        settings_values=settings,
        master_enabled=bool(getattr(settings, "shell_integration_enabled", False)),
        assistant_enabled=bool(getattr(settings, "assistant_enabled", False)),
    )
    if active:
        install_context_menu(active)


def build_shell_integration_plan(command: str | None = None) -> list[RegistryEntry]:
    command = command or launcher_command()
    entries: list[RegistryEntry] = [
        RegistryEntry(
            path=APPLICATION_KEY,
            values=(
                RegistryValue("", APP_DISPLAY_NAME, _reg_kind("sz")),
                RegistryValue("FriendlyAppName", APP_DISPLAY_NAME, _reg_kind("sz")),
                RegistryValue(
                    "FriendlyAppUserModelID",
                    f"GitHub.{APP_DISPLAY_NAME}",
                    _reg_kind("sz"),
                ),
            ),
        ),
        RegistryEntry(
            path=rf"{APPLICATION_KEY}\shell\open\command",
            values=(RegistryValue("", command, _reg_kind("sz")),),
        ),
        RegistryEntry(
            path=rf"{APPLICATION_KEY}\SupportedTypes",
            values=tuple(
                RegistryValue(extension, "", _reg_kind("sz"))
                for extension in TEXT_EXTENSIONS + MARKUP_EXTENSIONS + HTML_EXTENSIONS
            ),
        ),
    ]

    entries.extend(
        _association_entries(
            PROGID_TEXT,
            "Plain Text Document",
            TEXT_EXTENSIONS,
            command,
        )
    )
    entries.extend(
        _association_entries(
            PROGID_MARKUP,
            "Markdown Document",
            MARKUP_EXTENSIONS,
            command,
        )
    )
    entries.extend(
        _association_entries(
            PROGID_HTML,
            "HTML Document",
            HTML_EXTENSIONS,
            command,
        )
    )
    return entries


def install_shell_integration(command: str | None = None) -> ShellIntegrationStatus:
    if winreg is None:  # pragma: no cover - non-Windows fallback
        raise RuntimeError("Windows registry access is unavailable")
    for entry in build_shell_integration_plan(command):
        _write_entry(entry)
    from quill.platform.shell_integration import ShellIntegrationStatus  # noqa: I001 - deferred to avoid a circular import (neutral re-exports this module)

    return ShellIntegrationStatus(
        True, "Installed per-user Open-with associations and shell verbs for Quill."
    )


def remove_shell_integration() -> None:
    if winreg is None:  # pragma: no cover - non-Windows fallback
        raise RuntimeError("Windows registry access is unavailable")
    for path in [
        APPLICATION_KEY,
        rf"{APPLICATION_KEY}\shell\open\command",
        rf"{APPLICATION_KEY}\SupportedTypes",
        rf"Software\Classes\{PROGID_TEXT}",
        rf"Software\Classes\{PROGID_TEXT}\shell\open\command",
        rf"Software\Classes\{PROGID_TEXT}\SupportedTypes",
        rf"Software\Classes\{PROGID_MARKUP}",
        rf"Software\Classes\{PROGID_MARKUP}\shell\open\command",
        rf"Software\Classes\{PROGID_MARKUP}\SupportedTypes",
        rf"Software\Classes\{PROGID_HTML}",
        rf"Software\Classes\{PROGID_HTML}\shell\open\command",
        rf"Software\Classes\{PROGID_HTML}\SupportedTypes",
    ]:
        _delete_tree(winreg.HKEY_CURRENT_USER, path)


def _association_entries(
    progid: str,
    friendly_name: str,
    extensions: tuple[str, ...],
    command: str,
) -> list[RegistryEntry]:
    entries = [
        RegistryEntry(
            path=rf"Software\Classes\{progid}",
            values=(
                RegistryValue("", friendly_name, _reg_kind("sz")),
                RegistryValue("FriendlyTypeName", friendly_name, _reg_kind("sz")),
            ),
        ),
        RegistryEntry(
            path=rf"Software\Classes\{progid}\shell\open\command",
            values=(RegistryValue("", command, _reg_kind("sz")),),
        ),
        RegistryEntry(
            path=rf"Software\Classes\{progid}\SupportedTypes",
            values=tuple(RegistryValue(extension, "", _reg_kind("sz")) for extension in extensions),
        ),
    ]
    for extension in extensions:
        entries.append(
            RegistryEntry(
                path=rf"Software\Classes\{extension}\OpenWithProgids",
                values=(RegistryValue(progid, "", _reg_kind("none")),),
            )
        )
    return entries


def _write_entry(entry: RegistryEntry) -> None:
    key = _create_key(winreg.HKEY_CURRENT_USER, entry.path)
    try:
        for value in entry.values:
            winreg.SetValueEx(
                key, value.name, 0, value.kind, _coerce_registry_value(value.kind, value.value)
            )
    finally:
        winreg.CloseKey(key)


def _coerce_registry_value(kind: int, value: object) -> object:
    """Coerce a Python value to the type ``winreg.SetValueEx`` accepts for *kind*.

    Python 3.13's ``winreg`` is strict: a ``str`` passed for a binary registry
    kind (``REG_NONE`` / ``REG_BINARY``) raises ``TypeError: Objects of type
    'str' can not be used as binary registry values`` -- the crash in #921, hit
    by the ``OpenWithProgids`` entry which writes an empty ``REG_NONE`` value
    with the progid as the value *name*. Older Pythons silently accepted the
    str, so the bug only surfaced on the 3.13 embedded runtime. Map each kind
    to the type ``winreg`` requires: bytes for binary kinds, str for string
    kinds, int for integer kinds. A value already of the right type is passed
    through unchanged.
    """
    assert winreg is not None
    if kind in (winreg.REG_SZ, winreg.REG_EXPAND_SZ, winreg.REG_MULTI_SZ):
        if isinstance(value, str):
            return value
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)
    if kind in (winreg.REG_DWORD, winreg.REG_DWORD_BIG_ENDIAN, winreg.REG_QWORD):
        return int(value)  # type: ignore[arg-type]
    # Binary kinds: REG_NONE, REG_BINARY, REG_LINK -> bytes (the only type
    # winreg accepts for them). An empty str (the OpenWithProgids case) and
    # None both become b"".
    if isinstance(value, bytes):
        return value
    if value is None:
        return b""
    if isinstance(value, str):
        return value.encode("utf-8")
    return bytes(value)  # type: ignore[arg-type]


def _create_key(root: object, path: str):
    assert winreg is not None
    key = root
    for part in path.split("\\"):
        key = winreg.CreateKeyEx(key, part, 0, winreg.KEY_WRITE)
    return key


def _delete_tree(root: object, path: str) -> None:
    assert winreg is not None
    try:
        key = winreg.OpenKey(root, path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
    except FileNotFoundError:
        return
    try:
        while True:
            try:
                child = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_tree(key, child)
        winreg.CloseKey(key)
        winreg.DeleteKey(root, path)
    except OSError:
        winreg.CloseKey(key)


def _reg_kind(kind: str) -> int:
    assert winreg is not None
    return {
        "sz": winreg.REG_SZ,
        "none": winreg.REG_NONE,
    }[kind]
