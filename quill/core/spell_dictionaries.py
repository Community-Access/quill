"""Where the words a person has taught the spell checker are kept.

Three scopes, read together: **personal** (every document, in the app's data
folder or a folder QUILL Lite shares with QUILL), **document** (a
``.quill-dict.json`` beside the file) and **project** (a
``.quill-dictionary.json`` at the project root). Split from
:mod:`quill.core.spellcheck` under GATE-11 when the checker learned to skip
web addresses and code; that module re-exports these names, so callers are
unchanged. wx-free.
"""

from __future__ import annotations

import logging
from pathlib import Path

from quill.core.file_lock import guarded_write
from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

logger = logging.getLogger(__name__)


def personal_dictionary_revision(personal_dir: Path | None = None) -> tuple[int, int]:
    """``(mtime_ns, size)`` of the personal dictionary; ``(0, 0)`` if absent.

    What a caller compares against to find out whether the shared list has
    changed under it. Each app used to load the dictionary once and keep the
    set, so a word taught in QUILL Lite stayed underlined in QUILL until QUILL
    was restarted -- which makes a *shared* dictionary look broken rather than
    shared (bad.md S10).
    """
    path = _dictionary_path("personal", None, None, personal_dir)
    if path is None:
        return (0, 0)
    try:
        stat = path.stat()
    except OSError:
        return (0, 0)
    return (int(stat.st_mtime_ns), int(stat.st_size))


def add_word_to_scope(
    word: str,
    scope: str,
    document_path: Path | None,
    project_root: Path | None,
    personal_dir: Path | None = None,
) -> bool:
    """Teach *word* in *scope*. ``False`` when there was nowhere to write it.

    The return value is bad.md S3. The "this document only" and "this project"
    dictionaries are files *beside* the document, so an unsaved buffer has no
    such file and nothing is written -- and the caller went on announcing
    ``Added "word" to this document only`` regardless. The word stayed
    underlined, and the only way to learn that was to try again and hear the
    same sentence a second time. Callers must now say which of the two
    happened.
    """
    token = word.strip().lower()
    if not token:
        return False
    path = _dictionary_path(scope, document_path, project_root, personal_dir)
    if path is None:
        return False
    # Read and write inside the lock, not either side of it: the point is that
    # nothing else rewrites the file between the two (bad.md S10).
    # The lock is quill/core/file_lock.py: every shared read-modify-write in
    # the product has the same race and deserves the same answer, not a second
    # implementation of it (bad.md S10).
    with guarded_write(path):
        existing = load_scope_dictionary(scope, document_path, project_root, personal_dir)
        existing.add(token)
        write_json_atomic(path, sorted(existing))
    return True


def load_combined_dictionary(
    document_path: Path | None,
    project_root: Path | None,
    personal_dir: Path | None = None,
) -> set[str]:
    personal = load_scope_dictionary("personal", document_path, project_root, personal_dir)
    document = load_scope_dictionary("document", document_path, project_root, personal_dir)
    project = load_scope_dictionary("project", document_path, project_root, personal_dir)
    return personal | document | project


def load_scope_dictionary(
    scope: str,
    document_path: Path | None,
    project_root: Path | None,
    personal_dir: Path | None = None,
) -> set[str]:
    path = _dictionary_path(scope, document_path, project_root, personal_dir)
    if path is None:
        return set()
    raw = read_json(path, default=None)
    if isinstance(raw, list):
        return {item.strip().lower() for item in raw if isinstance(item, str) and item.strip()}
    # EdSharp standard (magic2, 2026-08-27): a taught dictionary is an asset
    # the user may open and edit by hand. A hand edit that breaks the JSON
    # must not silently wipe two hundred taught words -- so a file that does
    # not parse as JSON is read as a plain word list, one per line (which is
    # also what a hand-authored file naturally looks like). Commas, brackets
    # and quotes left over from JSON editing are stripped per line.
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return set()
    words: set[str] = set()
    for line in text.splitlines():
        token = line.strip().strip("[],").strip().strip('"').strip("'").strip().lower()
        if token and all(ch.isalpha() or ch in "-'" for ch in token):
            words.add(token)
    if words:
        logger.warning(
            "Scope dictionary %s is not valid JSON; recovered %d words from it "
            "as a plain word list",
            path,
            len(words),
        )
        return words
    if text.strip():
        logger.warning("Scope dictionary %s is malformed; falling back to empty set", path)
    return set()


def _dictionary_path(
    scope: str,
    document_path: Path | None,
    project_root: Path | None,
    personal_dir: Path | None = None,
) -> Path | None:
    """Where a scope's taught words live.

    ``personal_dir`` overrides the data folder the personal dictionary is kept
    in, and exists for the sibling apps: QUILL Lite keeps its own dictionary in
    its own folder, because a machine that has never had QUILL installed must
    not grow a Quill data folder because somebody taught a text editor a word.
    QUILL passes nothing and gets ``app_data_dir()``, exactly as before.
    """
    if scope == "personal":
        root = personal_dir if personal_dir is not None else app_data_dir()
        return root / "dictionaries" / "personal.json"
    if scope == "document":
        if document_path is None:
            return None
        return document_path.with_suffix(document_path.suffix + ".quill-dict.json")
    if scope == "project":
        if project_root is None:
            return None
        return project_root / ".quill-dictionary.json"
    return None
