"""The family's My Words list moves to the family's dictation folder (D-12, D-13).

Until 2026-10-16 the one word list QUILL, QUILL Transcribe, Quill Inkwell and
(when chosen) QUILL Lite read was QUILL's ``dictation.md`` in QUILL's data
folder, with its two neighbours, ``dictation-instructions.md`` and
``dictation-contexts.json``. Now all three live in the family's dictation
folder (:func:`~quill.core.windows_dictation.family_store.family_dictation_dir`),
beside ``family_dictation.json`` and the speech models:

* **Copied, never moved.** The first time any program asks where the list is
  (:func:`family_profile_path`), each of the three files in the old folder is
  copied to the new one if the new one has none, with the atomic replace, and
  the old file is left exactly as it was: it is the backup, and an older build
  still finds it. Nothing is ever deleted.
* **Read through the old place until the copy exists.** If the copy cannot be
  made (a full disk, a folder the person cannot write), the old file is
  returned instead and the reason is logged, so the list never looks empty;
  the copy is tried again the next time.
* **Installed, custom-folder and portable copies.** The old folder is whatever
  QUILL's data folder is for this copy (``%APPDATA%\\Quill``, the folder the
  person chose, or the portable ``data`` folder), so each copy brings its own
  list. A portable copy's new folder is inside its own ``data`` folder.
* **Words added afterwards in the old place are not lost.** Each old file's
  time and size are recorded in ``family-words-moved.json``. If the old list
  changes later -- an older build still running, or a second copy whose data
  is elsewhere -- its new words are added to the family list, the way Import
  adds them (yours are kept where the two differ), after the family list is
  copied to ``dictation-before-merge.md``. The instructions and
  contexts files are copied only while the family has none.

wx-free.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from quill.core.windows_dictation.contexts import FILE_NAME as CONTEXTS_NAME
from quill.core.windows_dictation.instructions import FILE_NAME as INSTRUCTIONS_NAME

_log = logging.getLogger(__name__)

__all__ = ["MERGE_BACKUP_NAME", "RECORD_NAME", "WORDS_NAME", "bring_over", "family_profile_path"]

WORDS_NAME = "dictation.md"
RECORD_NAME = "family-words-moved.json"
#: The family list as it was before the last merge from an old place.
MERGE_BACKUP_NAME = "dictation-before-merge.md"
_FILES = (WORDS_NAME, INSTRUCTIONS_NAME, CONTEXTS_NAME)


def family_profile_path(old_folder: Path) -> Path:
    """The family's ``dictation.md``, after bringing over what *old_folder* has.

    Never raises for the move. When the family's copy does not exist and the
    old list does (the copy failed), the old list is returned: read through
    the old place rather than show an empty list. The old file is untouched."""
    from quill.core.windows_dictation.family_store import family_dictation_dir

    folder = family_dictation_dir()
    old = Path(old_folder)
    try:
        bring_over(old, folder)
    except Exception as error:  # noqa: BLE001 - the old file is still there; try again next time
        _log.warning("The word list could not be copied to %s: %s", folder, error)
    new = folder / WORDS_NAME
    if not new.exists() and (old / WORDS_NAME).is_file():
        return old / WORDS_NAME
    return new


def _same_folder(first: Path, second: Path) -> bool:
    try:
        return first.resolve() == second.resolve()
    except OSError:
        return False


def bring_over(old_folder: Path, folder: Path) -> list[str]:
    """Copy or merge the three files from *old_folder* into *folder*; the
    names of the files that changed in *folder*."""
    from quill.core.storage import read_json, write_json_atomic

    if _same_folder(old_folder, folder):
        return []
    present = [(name, old_folder / name) for name in _FILES if (old_folder / name).is_file()]
    if not present:
        return []
    record_path = folder / RECORD_NAME
    record = read_json(record_path, default={}) if record_path.is_file() else {}
    if not isinstance(record, dict):
        record = {}
    changed: list[str] = []
    recorded = dict(record)
    for name, old in present:
        info = old.stat()
        seen = [info.st_mtime_ns, info.st_size]
        key = str(old)
        if record.get(key) == seen:
            continue
        new = folder / name
        if not new.exists():
            folder.mkdir(parents=True, exist_ok=True)
            _copy(old, new)
            changed.append(name)
        elif name == WORDS_NAME and _merge_words(old, new):
            changed.append(name)
        record[key] = seen
    if record != recorded:  # a list asked for on every phrase writes nothing
        folder.mkdir(parents=True, exist_ok=True)
        write_json_atomic(record_path, record)
    return changed


def _copy(old: Path, new: Path) -> None:
    """A whole copy or none: written beside the target, then put in place."""
    from quill.core.storage import write_bytes_atomic

    write_bytes_atomic(new, old.read_bytes())
    shutil.copystat(old, new)


def _merge_words(old: Path, new: Path) -> bool:
    """Add the old list's new entries to the family's, as Import does, after
    copying the family's list as it was to ``dictation-before-merge.md``."""
    from quill.core.storage import write_bytes_atomic, write_text_atomic
    from quill.core.windows_dictation.words_exchange import apply_merge, plan_merge
    from quill.core.windows_dictation.words_file import load_words, render_words

    current = load_words(new)
    plan = plan_merge(current, load_words(old))
    if not plan.new and not plan.commands_lines:
        return False
    apply_merge(current, plan)
    write_bytes_atomic(new.with_name(MERGE_BACKUP_NAME), new.read_bytes())
    # As save_words writes it: the platform's line ends.
    write_text_atomic(new, render_words(current).replace("\n", os.linesep))
    return True
