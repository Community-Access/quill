"""Platform-aware user-facing nouns for UI strings (#37).

Several UI strings name a Windows-only mechanism outright -- "Windows Credential
Manager", or a "Ctrl+Alt" chord. On macOS those render factually wrong: macOS
keeps secrets in the Keychain and uses Cmd (not Ctrl) as the command modifier.
These helpers return the correct noun for the current platform, each wrapped in
:func:`quill.core.i18n._` so the noun is extracted into the translation catalog
like every other user-visible string.

``sys.platform`` is read at *call* time (not import time) so a test can
monkeypatch it. On Windows the helpers return the original Windows strings,
so existing behaviour and the accessibility source-contract tests are
unchanged on the primary platform.
"""

from __future__ import annotations

import sys

from quill.core.i18n import _


def credential_store_name() -> str:
    """The user-facing name of the OS credential vault.

    "Windows Credential Manager" on Windows, "macOS Keychain" on macOS, and a
    neutral "the system credential store" elsewhere. Use this wherever a string
    names the vault a secret is kept in (API-key hints, forget-key confirmations,
    publish/SFTP password notes).
    """
    if sys.platform == "darwin":
        return _("macOS Keychain")
    if sys.platform == "win32":
        return _("Windows Credential Manager")
    return _("the system credential store")


def primary_command_chord_label() -> str:
    """The user-facing "Ctrl+Alt" / "Cmd+Alt" chord prefix.

    QUILL's QUILL-key-adjacent chords are written Ctrl+Alt on Windows and
    Cmd+Alt on macOS. Use this in help/status text that names such a chord as
    an example (e.g. "press Cmd+Alt+M"), not where the actual binding is
    resolved from the keymap.
    """
    if sys.platform == "darwin":
        return _("Cmd+Alt")
    return _("Ctrl+Alt")
