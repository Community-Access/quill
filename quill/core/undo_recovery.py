"""Protect an interrupted file restore from the next launch's Undo cleanup."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import NamedTuple

from quill.core.error_codes import CodedError
from quill.core.storage import resolve_within, write_json_atomic
from quill.core.undo_last import restore_held

MARKER = "restore-pending.json"


class UndoRecoveryError(CodedError):
    code = "QUILL-UNDO-RESTORE-RECOVERY"


class RestoreEntry(NamedTuple):
    name: str
    original: Path


def _validate(payload: object) -> tuple[RestoreEntry, ...]:
    """Validate the on-disk undo_recovery.json contract without a runtime dependency."""
    if (
        not isinstance(payload, dict)
        or set(payload) != {"version", "files"}
        or type(payload["version"]) is not int
        or payload["version"] != 1
        or not isinstance(payload["files"], list)
    ):
        raise ValueError("Invalid Undo recovery record")
    entries: list[RestoreEntry] = []
    names: set[str] = set()
    for item in payload["files"]:
        if not isinstance(item, dict) or set(item) != {"held", "original"}:
            raise ValueError("Invalid Undo recovery file")
        name, original = item["held"], item["original"]
        if (
            not isinstance(name, str)
            or re.fullmatch(r"\d+-[^\\/]+", name) is None
            or name in names
            or not isinstance(original, str)
            or not original
            or "\x00" in name
            or "\x00" in original
            or not Path(original).is_absolute()
        ):
            raise ValueError("Invalid Undo recovery location")
        names.add(name)
        entries.append(RestoreEntry(name, Path(original)))
    return tuple(entries)


def prepare_restore(held: dict[Path, Path]) -> set[Path]:
    """Record the recovery intent before changing any file or library metadata."""
    directories = {target.parent for target in held}
    for directory in directories:
        payload = {
            "version": 1,
            "files": [
                {"held": target.name, "original": str(original.absolute())}
                for target, original in held.items()
                if target.parent == directory
            ],
        }
        _validate(payload)
        write_json_atomic(directory / MARKER, payload, base=directory)
    return directories


def restore_files(held: dict[Path, Path]) -> tuple[int, int]:
    """Restore without overwriting; leave a recovery marker on every failure."""
    if not held:
        return 0, 0
    directories = prepare_restore(held)
    errors: list[Path] = []
    restored = restore_held(held, on_error=lambda path, _error: errors.append(path))
    for directory in directories:
        if not errors and not any(target.exists() for target in held if target.parent == directory):
            (directory / MARKER).unlink(missing_ok=True)
    return restored, len(errors)


def recover(directory: Path) -> tuple[int, int]:
    """Read a validated request; malformed requests preserve the whole step."""
    try:
        payload = json.loads((directory / MARKER).read_text(encoding="utf-8"))
        held: dict[Path, Path] = {}
        for entry in _validate(payload):
            target = resolve_within(directory, directory / entry.name)
            held[target] = entry.original
    except Exception as error:
        raise UndoRecoveryError(
            "An interrupted Undo record could not be read. Its held files have been kept."
        ) from error
    return restore_files(held)
