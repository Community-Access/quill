"""Keyboard Quill Packs (``.kqp``): a shareable file of key bindings.

Extracted from :mod:`quill.core.keymap` rather than grown (GATE-11): the pack
file format is its own concern -- a versioned JSON document holding only the
bindings that differ from the defaults -- and the keymap module re-exports both
functions, so every caller still imports them from there.

The keymap's own functions are reached through the module at call time
(``_keymap.save_keymap``), not bound at import, so a test that replaces one of
them on :mod:`quill.core.keymap` is replacing the one a pack uses.
"""

from __future__ import annotations

from pathlib import Path

from quill.core import keymap as _keymap
from quill.core.storage import read_json, write_json_atomic

__all__ = ["KQP_EXTENSION", "export_keyboard_pack", "import_keyboard_pack"]

KQP_EXTENSION = ".kqp"
_KQP_VERSION = 1


def export_keyboard_pack(
    target: Path,
    keymap: dict[str, str],
    name: str,
    description: str,
    author: str = "",
    version: str = "1.0",
) -> None:
    """Write a .kqp (Keyboard Quill Pack) file.

    Only bindings that differ from DEFAULT_KEYMAP are stored so the file
    captures intent rather than a snapshot of defaults that may change.
    """
    defaults = _keymap.DEFAULT_KEYMAP
    delta: dict[str, str] = {k: v for k, v in keymap.items() if v != defaults.get(k)}
    payload: dict[str, object] = {
        "kqp_version": _KQP_VERSION,
        "name": name.strip(),
        "description": description.strip(),
        "author": author.strip(),
        "version": version.strip(),
        "bindings": delta,
    }
    write_json_atomic(target, payload)


def import_keyboard_pack(source: Path) -> tuple[str, str, dict[str, str]]:
    """Read a .kqp file. Return (name, description, merged_keymap).

    Raises ValueError if the file is missing, malformed, uses an unsupported
    kqp_version, or fails the kqp validator.  The merged keymap is persisted
    via save_keymap *only* after validation succeeds (finding #42: a bad
    pack must never silently overwrite the user's bindings).
    """
    raw = read_json(source, default=None)
    if not isinstance(raw, dict):
        raise ValueError(f"{source.name} is not a valid Keyboard Quill Pack (expected JSON object)")
    file_version = raw.get("kqp_version")
    if file_version != _KQP_VERSION:
        raise ValueError(
            f"{source.name}: unsupported kqp_version {file_version!r} "
            f"(this build supports version {_KQP_VERSION})"
        )
    name = str(raw.get("name", source.stem)) or source.stem
    description = str(raw.get("description", ""))
    bindings = raw.get("bindings", {})
    if not isinstance(bindings, dict):
        raise ValueError(f"{source.name}: 'bindings' must be a JSON object")
    # Re-write the parsed payload to a temp buffer and run the same validator
    # the standalone ``quill.tools.kqp_validator`` runs, so the import path
    # uses the same rules as the CLI.
    from quill.tools.kqp_validator import validate_file  # local import: avoid cycles

    issues = validate_file(source, strict=False)
    if issues:
        joined = "; ".join(issues)
        raise ValueError(f"{source.name} failed keyboard pack validation: {joined}")
    merged = _keymap.merge_keymaps(bindings)
    _keymap.save_keymap(merged)
    return name, description, merged
