"""Read and write ``list_speech_templates.json``.

Written atomically through :func:`quill.core.storage.write_json_atomic`,
schema-stamped, coerced entry by entry on read. A **damaged** file is never
silently replaced: its bytes are copied aside first (``backup_corrupt_file``)
and :func:`load_library` says so, so the editor can tell the person where
their old file went.

Wx-free and strict-typed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quill.core.list_speech.library import Library
from quill.core.list_speech.template import template_from_dict, template_to_dict
from quill.core.migration_backup import backup_corrupt_file
from quill.core.paths import app_data_dir
from quill.core.storage import write_json_atomic

__all__ = [
    "BACKUP_NAME",
    "DAMAGED_NOTICE",
    "FILENAME",
    "SCHEMA_VERSION",
    "export_text",
    "import_text",
    "library_path",
    "load_cached",
    "load_library",
    "save_library",
]

FILENAME = "list_speech_templates.json"
SCHEMA_VERSION = 1
BACKUP_NAME = "list_speech_templates"
DAMAGED_NOTICE = (
    "Your list speech template file could not be read. A copy was kept in the "
    "migration backups folder, and the usual wording is used until you save again."
)


def library_path() -> Path:
    return app_data_dir() / FILENAME


def _to_data(library: Library) -> dict[str, Any]:
    return {
        "version": SCHEMA_VERSION,
        "templates": [template_to_dict(t) for t in library.templates],
        "assignments": dict(sorted(library.assignments.items())),
    }


def _from_data(data: object) -> Library | None:
    if not isinstance(data, dict):
        return None
    templates = []
    raw_templates = data.get("templates")
    if isinstance(raw_templates, list):
        for raw in raw_templates:
            if isinstance(raw, dict):
                template = template_from_dict(raw)
                if template is not None:
                    templates.append(template)
    assignments: dict[str, str] = {}
    raw_assignments = data.get("assignments")
    if isinstance(raw_assignments, dict):
        assignments = {
            k: v for k, v in raw_assignments.items() if isinstance(k, str) and isinstance(v, str)
        }
    return Library(tuple(templates), assignments)


def load_library(path: Path | None = None) -> tuple[Library, str]:
    """The saved library, and a notice sentence (empty when all is well).

    A missing file is an empty library. An unreadable one is set aside, never
    overwritten here, and reads as empty with :data:`DAMAGED_NOTICE`.
    """
    target = path or library_path()
    if not target.exists():
        return Library(), ""
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        data = None
    library = _from_data(data)
    if library is None:
        backup_corrupt_file(BACKUP_NAME, target)
        return Library(), DAMAGED_NOTICE
    return library, ""


def save_library(library: Library, path: Path | None = None) -> None:
    write_json_atomic(path or library_path(), _to_data(library))


_cache: dict[str, tuple[tuple[int, int], Library]] = {}


def load_cached(path: Path | None = None) -> Library:
    """The library for speaking rows: re-read only when the file changes."""
    target = path or library_path()
    try:
        stat = target.stat()
        stamp = (stat.st_mtime_ns, stat.st_size)
    except OSError:
        return Library()
    hit = _cache.get(str(target))
    if hit is not None and hit[0] == stamp:
        return hit[1]
    library, _notice = load_library(target)
    _cache[str(target)] = (stamp, library)
    return library


def export_text(library: Library) -> str:
    """The library as text for a person's profile export."""
    return json.dumps(_to_data(library), indent=2, sort_keys=True, ensure_ascii=False)


def import_text(text: str) -> Library | None:
    """A library from exported text, or None when the text is not one."""
    try:
        return _from_data(json.loads(text))
    except ValueError:
        return None
