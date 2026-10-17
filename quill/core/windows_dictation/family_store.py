"""One dictation settings store for the family, both directions (dict.md D-13).

Until 2026-10-16 QUILL Transcribe and Quill Inkwell kept their own copy of the
dictation settings, refreshed only when an editor handed its settings over
(:func:`quill.core.windows_dictation.anywhere.write_handoff`): a model chosen in
QUILL Transcribe never reached QUILL, and one chosen in QUILL Lite reached
QUILL Transcribe only through Dictate in Other Programs.

Now there is one file, ``family_dictation.json``, in the family's dictation
folder (:func:`family_dictation_dir`):

* **Written when Dictation Settings is saved**, in any of QUILL, QUILL Lite,
  QUILL Transcribe and Quill Inkwell, by :func:`publish_fields`, with the
  atomic write every QUILL setting uses. Two programs saving at once is not a
  conflict: each write is whole, and the last one wins.
* **Read when a program comes to the front** (and, in QUILL Transcribe, which
  lives in the tray, on its own clock), by :func:`adopt_fields`. What it holds
  replaces the program's own values for the shared fields only.
* **Behind one setting**, "Share dictation settings with every QuillVille program"
  (``windows_dictation_share_family``, ``"on"`` or ``"off"``). On for a
  program whose shared settings are all still the defaults, which loses
  nothing by sharing -- every new install; off for one where the person chose
  something, until they turn it on, so an upgrade never changes somebody's
  choices behind their back
  (:func:`~quill.core.windows_dictation.settings_fields.shares_by_default`).
* **Never loses a setting.** The first time a program takes values from the
  family file, its own values are copied first to ``before-sharing-<app>.json``
  beside it, once. If that copy cannot be written, nothing is taken.
* **A write that fails is said, never swallowed.** :func:`publish_fields`
  raises :class:`FamilyDictationError` with a sentence; each program says it
  after "Dictation settings saved", because its own copy *was* saved and only
  the family's was not.

**Not shared** (:data:`~quill.core.windows_dictation.settings_fields.FAMILY_LOCAL_FIELDS`):
what each program sets differently on purpose (the working tick and strict
mode, on in QUILL Transcribe; the read-back's tone in a program that types into
others), the one-time sentences, and every consent -- agreeing to send speech
to a provider from one program is not agreeing for another. Keys and the tray
were never dictation settings and stay where they are.

**Where:** an installed copy, ``%LOCALAPPDATA%\\QuillVille\\Dictation`` (the
model store's folder); a portable copy, the ``dictation`` folder in its own
``data`` folder, so a portable copy shares only with programs in the same
bundle and never writes to the host.

wx-free.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import fields
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.windows_dictation.settings_fields import (
    FAMILY_LOCAL_FIELDS,
    SHARE_FIELD,
    DictationSettings,
    load_fields,
    share_on,
)

__all__ = [
    "BACKUP_PREFIX",
    "FILE_NAME",
    "FamilyDictationError",
    "SCHEMA",
    "SHARED_FIELDS",
    "adopt",
    "adopt_fields",
    "family_dictation_dir",
    "publish",
    "publish_fields",
    "read_shared",
    "settings_path",
    "sharing",
    "stamp",
]

FILE_NAME = "family_dictation.json"
#: Bumped only when a field changes meaning; a newer file's unknown fields are
#: kept on every write (:func:`publish_fields`).
SCHEMA = 1
BACKUP_PREFIX = "before-sharing-"

#: Every dictation setting the family shares, by its one name.
SHARED_FIELDS: frozenset[str] = frozenset(
    item.name for item in fields(DictationSettings) if item.name not in FAMILY_LOCAL_FIELDS
)


class FamilyDictationError(CodedError):
    """The family's dictation settings could not be written. The message is a
    sentence a program can say as it is."""

    code = "QUILL-DICTATION-FAMILY-WRITE"

    @property
    def sentence(self) -> str:
        """What to say, without the code ``str()`` puts in front for the log."""
        return str(self.args[0]) if self.args else ""


def _default_dir() -> Path:
    """The folder for this copy. The test suite points it at a folder of its own."""
    from quill.core import paths

    if paths._DEV_BUILD and os.environ.get("QUILL_DATA_DIR", "").strip():
        return paths.app_data_dir() / "QuillVille" / "Dictation"
    try:
        bundle = paths.portable_bundle_root()
    except Exception:  # noqa: BLE001 - no portable answer is an installed copy
        bundle = None
    if bundle is not None:
        return bundle / "data" / "dictation"
    try:
        from quill.core.lite.paths import _portable_root

        lite = _portable_root()
    except Exception:  # noqa: BLE001 - not QUILL Lite, or no anchor
        lite = None
    if lite is not None:
        return lite / "dictation"
    local = os.environ.get("LOCALAPPDATA", "").strip()
    base = Path(local) if local else Path.home() / ".quillville"
    return base / "QuillVille" / "Dictation"


def family_dictation_dir() -> Path:
    """The family's dictation folder (not created here)."""
    return _default_dir()


def settings_path() -> Path:
    return family_dictation_dir() / FILE_NAME


def stamp() -> tuple[int, int] | None:
    """The family file's time and size, so a program that looks often (QUILL
    Transcribe, on its clock) reads it only when it changed."""
    try:
        info = settings_path().stat()
    except OSError:
        return None
    return info.st_mtime_ns, info.st_size


def sharing(stored: Mapping[str, Any]) -> bool:
    """Whether the program whose settings are *stored* shares them."""
    return share_on(stored)


def _read_raw() -> dict[str, Any]:
    from quill.core.storage import read_json

    raw = read_json(settings_path(), default={})
    if not isinstance(raw, dict):
        return {}
    stored = raw.get("dictation")
    return dict(stored) if isinstance(stored, dict) else {}


def read_shared() -> dict[str, Any]:
    """The shared fields the family file holds, cleaned; empty when there is none."""
    raw = _read_raw()
    known = {name: value for name, value in raw.items() if name in SHARED_FIELDS}
    if not known:
        return {}
    cleaned = load_fields(known)
    return {name: cleaned[name] for name in known}


def publish_fields(stored: Mapping[str, Any], *, app: str) -> bool:
    """Write *stored*'s shared fields to the family file, when sharing is on.

    ``True`` when written, ``False`` when sharing is off here. Fields a newer
    build wrote and this one does not know are kept. Raises
    :class:`FamilyDictationError` when the file cannot be written: the
    program's own copy is saved either way, so nothing is lost, but the person
    is told that the other programs will not see the change."""
    if not sharing(stored):
        return False
    from quill.core.storage import write_json_atomic

    shared = {name: stored[name] for name in sorted(SHARED_FIELDS) if name in stored}
    kept = {
        name: value
        for name, value in _read_raw().items()
        if name not in SHARED_FIELDS and name not in FAMILY_LOCAL_FIELDS
    }
    try:
        folder = family_dictation_dir()
        folder.mkdir(parents=True, exist_ok=True)
        write_json_atomic(
            folder / FILE_NAME,
            {"schema": SCHEMA, "written_by": app, "dictation": {**kept, **shared}},
        )
    except OSError as error:
        reason = error.strerror or str(error) or type(error).__name__
        raise FamilyDictationError(
            "Saved here, but the other QuillVille programs will not see this "
            f"change: the shared dictation settings could not be written ({reason})."
        ) from error
    return True


def adopt_fields(stored: Mapping[str, Any], *, app: str) -> dict[str, Any] | None:
    """*stored* with the family's values in it, or ``None`` when nothing changes.

    The first time anything changes, *stored*'s own shared values are written
    to ``before-sharing-<app>.json`` first."""
    if not sharing(stored):
        return None
    family = read_shared()
    if not family:
        return None
    mine = load_fields(stored)
    changed = {name: value for name, value in family.items() if mine.get(name) != value}
    if not changed:
        return None
    if not _back_up_once(mine, app):
        return None  # without the copy of this program's own values, take nothing
    return {**dict(stored), **changed, SHARE_FIELD: "on"}


def _back_up_once(mine: Mapping[str, Any], app: str) -> bool:
    """Copy this program's own shared values aside, once. ``False`` when the
    copy is needed and could not be written."""
    from quill.core.storage import write_json_atomic

    path = family_dictation_dir() / f"{BACKUP_PREFIX}{app}.json"
    if path.exists():
        return True
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        own = {name: mine[name] for name in sorted(SHARED_FIELDS) if name in mine}
        write_json_atomic(path, {"schema": SCHEMA, "app": app, "dictation": own})
    except OSError:
        return False
    return True


def publish(settings: object, *, app: str) -> bool:
    """:func:`publish_fields` for a settings object (both editors' ``Settings``)."""
    from quill.core.windows_dictation.anywhere import dictation_fields

    return publish_fields(dictation_fields(settings), app=app)


def adopt(settings: object, *, app: str) -> bool:
    """:func:`adopt_fields` for a settings object; ``True`` when it changed."""
    from quill.core.windows_dictation.anywhere import dictation_fields

    stored = dictation_fields(settings)
    updated = adopt_fields(stored, app=app)
    if updated is None:
        return False
    for name, value in updated.items():
        if stored.get(name) != value and hasattr(settings, name):
            setattr(settings, name, value)
    return True
