"""Sidecar persistence for a story project (wx-free).

The project lives in ``project.quillstory.json`` beside the writer's files,
written atomically (temp + ``os.replace``) through :mod:`quill.core.storage`.
The sidecar is *advisory*: when it is absent, the folder is still a project —
:func:`load_project` synthesizes one by listing the plain-text files as the
manuscript spine, so deleting the sidecar never loses any writing. A corrupt
sidecar falls back to an empty project rather than raising.

Only relative POSIX paths are stored, so a project folder is portable across
machines and sync services.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.storage import read_json, write_json_atomic
from quill.core.story.model import StoryProject

__all__ = ["PROJECT_FILENAME", "load_project", "save_project"]

PROJECT_FILENAME = "project.quillstory.json"

#: File suffixes treated as manuscript text when synthesizing a project from a
#: bare folder (no sidecar).
_TEXT_SUFFIXES = (".md", ".markdown", ".txt")


def load_project(folder: Path) -> StoryProject:
    """Load the project in ``folder``.

    Reads ``project.quillstory.json`` when present (corrupt files fall back to an
    empty project). When absent, synthesizes a project from the folder's
    plain-text files, sorted by name, as the manuscript spine.
    """
    sidecar = folder / PROJECT_FILENAME
    if sidecar.exists():
        return StoryProject.from_dict(read_json(sidecar, {}))
    return _project_from_folder_scan(folder)


def save_project(folder: Path, project: StoryProject) -> None:
    """Write the project's sidecar into ``folder`` atomically."""
    write_json_atomic(folder / PROJECT_FILENAME, project.to_dict())


def _project_from_folder_scan(folder: Path) -> StoryProject:
    names = sorted(
        entry.name
        for entry in folder.iterdir()
        if entry.is_file()
        and entry.name != PROJECT_FILENAME
        and entry.suffix.lower() in _TEXT_SUFFIXES
    )
    return StoryProject(title=folder.name, manuscript=tuple(names))
