"""Notebook store — wx-free data layer for QUILL Notebooks (Milestone 2).

A Notebook is a lightweight project container: an ordered collection of
document entries, named snapshots (formerly "Workspace Snapshots"), a daily
word-count goal, a project vocabulary list, and saved searches.  Everything
persists as a single ``.quillnotebook`` JSON file validated against
``quill/core/schemas/notebook.json``.

This module owns only the data model and I/O.  UI panels, status-bar cells,
and menu wiring are the responsibility of the ``quill/ui`` layer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from quill.core.error_codes import CodedError
from quill.core.storage import write_json_atomic

_SCHEMA_PATH = Path(__file__).parent / "schemas" / "notebook.json"
_SCHEMA_DISCRIMINATOR = "quill.notebook/1"
_FILE_SUFFIX = ".quillnotebook"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class NotebookEntry:
    """A single document tracked by the Notebook."""

    id: str
    path: str
    title: str | None = None
    tags: list[str] = field(default_factory=list)
    last_caret_pos: int = 0
    last_opened: str | None = None
    word_count: int | None = None

    @classmethod
    def create(cls, path: str, *, title: str | None = None) -> NotebookEntry:
        return cls(id=str(uuid4()), path=path, title=title)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "title": self.title,
            "tags": list(self.tags),
            "last_caret_pos": self.last_caret_pos,
            "last_opened": self.last_opened,
            "word_count": self.word_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotebookEntry:
        return cls(
            id=data["id"],
            path=data["path"],
            title=data.get("title"),
            tags=list(data.get("tags", [])),
            last_caret_pos=int(data.get("last_caret_pos", 0)),
            last_opened=data.get("last_opened"),
            word_count=data.get("word_count"),
        )


@dataclass
class NotebookSnapshot:
    """A saved group of open entries (formerly "Workspace Snapshot")."""

    id: str
    name: str
    created: str
    open_entry_ids: list[str]
    active_entry_id: str | None = None

    @classmethod
    def create(
        cls,
        name: str,
        open_entry_ids: list[str],
        active_entry_id: str | None = None,
    ) -> NotebookSnapshot:
        return cls(
            id=str(uuid4()),
            name=name,
            created=datetime.now(UTC).isoformat(),
            open_entry_ids=list(open_entry_ids),
            active_entry_id=active_entry_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "created": self.created,
            "open_entry_ids": list(self.open_entry_ids),
            "active_entry_id": self.active_entry_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotebookSnapshot:
        return cls(
            id=data["id"],
            name=data["name"],
            created=data["created"],
            open_entry_ids=list(data.get("open_entry_ids", [])),
            active_entry_id=data.get("active_entry_id"),
        )


@dataclass
class NotebookGoal:
    """Daily word-count (or character-count) goal."""

    enabled: bool = False
    daily_target: int = 500
    unit: str = "words"
    today_count: int = 0
    today_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "daily_target": self.daily_target,
            "unit": self.unit,
            "today_count": self.today_count,
            "today_date": self.today_date,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotebookGoal:
        return cls(
            enabled=bool(data.get("enabled", False)),
            daily_target=int(data.get("daily_target", 500)),
            unit=str(data.get("unit", "words")),
            today_count=int(data.get("today_count", 0)),
            today_date=data.get("today_date"),
        )


@dataclass
class SavedSearch:
    """A named, reusable search query scoped to this Notebook."""

    id: str
    name: str
    query: str
    is_regex: bool = False
    case_sensitive: bool = False

    @classmethod
    def create(
        cls, name: str, query: str, *, is_regex: bool = False, case_sensitive: bool = False
    ) -> SavedSearch:
        return cls(
            id=str(uuid4()),
            name=name,
            query=query,
            is_regex=is_regex,
            case_sensitive=case_sensitive,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "query": self.query,
            "is_regex": self.is_regex,
            "case_sensitive": self.case_sensitive,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SavedSearch:
        return cls(
            id=data["id"],
            name=data["name"],
            query=data["query"],
            is_regex=bool(data.get("is_regex", False)),
            case_sensitive=bool(data.get("case_sensitive", False)),
        )


# ---------------------------------------------------------------------------
# Notebook
# ---------------------------------------------------------------------------


@dataclass
class Notebook:
    """In-memory representation of a ``.quillnotebook`` file."""

    name: str
    entries: list[NotebookEntry] = field(default_factory=list)
    snapshots: list[NotebookSnapshot] = field(default_factory=list)
    goal: NotebookGoal = field(default_factory=NotebookGoal)
    vocabulary: list[str] = field(default_factory=list)
    saved_searches: list[SavedSearch] = field(default_factory=list)
    root_dir: str | None = None
    created: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_opened: str | None = None

    # Path this Notebook was loaded from / will be saved to.  Set by the store.
    _path: Path | None = field(default=None, init=False, repr=False, compare=False)

    @property
    def path(self) -> Path | None:
        return self._path

    # ------------------------------------------------------------------
    # Entry helpers
    # ------------------------------------------------------------------

    def entry_by_id(self, entry_id: str) -> NotebookEntry | None:
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None

    def entry_by_path(self, path: str) -> NotebookEntry | None:
        for entry in self.entries:
            if entry.path == path:
                return entry
        return None

    def add_entry(self, path: str, *, title: str | None = None) -> NotebookEntry:
        existing = self.entry_by_path(path)
        if existing is not None:
            return existing
        entry = NotebookEntry.create(path, title=title)
        self.entries.append(entry)
        return entry

    def remove_entry(self, entry_id: str) -> bool:
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.id != entry_id]
        return len(self.entries) < before

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------

    def save_snapshot(
        self,
        name: str,
        open_entry_ids: list[str],
        active_entry_id: str | None = None,
    ) -> NotebookSnapshot:
        snap = NotebookSnapshot.create(name, open_entry_ids, active_entry_id)
        self.snapshots.append(snap)
        return snap

    def snapshot_by_id(self, snapshot_id: str) -> NotebookSnapshot | None:
        for snap in self.snapshots:
            if snap.id == snapshot_id:
                return snap
        return None

    def remove_snapshot(self, snapshot_id: str) -> bool:
        before = len(self.snapshots)
        self.snapshots = [s for s in self.snapshots if s.id != snapshot_id]
        return len(self.snapshots) < before

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": _SCHEMA_DISCRIMINATOR,
            "name": self.name,
            "root_dir": self.root_dir,
            "created": self.created,
            "last_opened": self.last_opened,
            "entries": [e.to_dict() for e in self.entries],
            "snapshots": [s.to_dict() for s in self.snapshots],
            "goal": self.goal.to_dict(),
            "vocabulary": list(self.vocabulary),
            "saved_searches": [ss.to_dict() for ss in self.saved_searches],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Notebook:
        if data.get("schema") != _SCHEMA_DISCRIMINATOR:
            raise NotebookFormatError(f"Unrecognised schema discriminator: {data.get('schema')!r}")
        nb = cls(
            name=str(data["name"]),
            root_dir=data.get("root_dir"),
            created=data.get("created", datetime.now(UTC).isoformat()),
            last_opened=data.get("last_opened"),
        )
        nb.entries = [NotebookEntry.from_dict(e) for e in data.get("entries", [])]
        nb.snapshots = [NotebookSnapshot.from_dict(s) for s in data.get("snapshots", [])]
        goal_data = data.get("goal")
        nb.goal = NotebookGoal.from_dict(goal_data) if goal_data else NotebookGoal()
        nb.vocabulary = list(data.get("vocabulary", []))
        nb.saved_searches = [SavedSearch.from_dict(ss) for ss in data.get("saved_searches", [])]
        return nb


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class NotebookFormatError(CodedError):
    """Raised when a .quillnotebook file cannot be parsed."""

    code = "QUILL-NOTEBOOK-FORMAT-INVALID"


# ---------------------------------------------------------------------------
# Store functions
# ---------------------------------------------------------------------------


def load_notebook(path: Path) -> Notebook:
    """Load and return a :class:`Notebook` from *path*.

    Raises :class:`NotebookFormatError` if the file cannot be parsed or has
    an unrecognised schema discriminator.  Raises :class:`OSError` if the
    file cannot be read.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Cannot read notebook file {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise NotebookFormatError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise NotebookFormatError(f"Expected a JSON object in {path}")
    nb = Notebook.from_dict(data)
    nb._path = path  # type: ignore[attr-defined]
    return nb


def save_notebook(notebook: Notebook, path: Path) -> None:
    """Atomically write *notebook* to *path*.

    Uses :func:`quill.core.storage.write_json_atomic` so the write is crash-safe.
    Sets ``notebook._path = path`` on success.
    """
    write_json_atomic(path, notebook.to_dict())
    notebook._path = path  # type: ignore[attr-defined]


def create_notebook(name: str, *, path: Path, root_dir: str | None = None) -> Notebook:
    """Create a new empty Notebook and save it to *path*."""
    nb = Notebook(name=name, root_dir=root_dir)
    save_notebook(nb, path)
    return nb


def create_notebook_from_folder(
    folder: Path,
    *,
    path: Path,
    name: str | None = None,
    extensions: tuple[str, ...] = (".md", ".txt", ".rst"),
) -> Notebook:
    """Create a Notebook from all matching documents in *folder*.

    Each file under *folder* (recursively) whose suffix is in *extensions* is
    added as an entry.  Paths are stored relative to *folder* so the Notebook
    is relocatable.

    ``name`` defaults to ``folder.name``.  ``path`` is where the
    ``.quillnotebook`` file is written.
    """
    nb_name = name or folder.name
    nb = Notebook(name=nb_name, root_dir=str(folder))
    for doc_path in sorted(folder.rglob("*")):
        if doc_path.suffix.lower() in extensions and doc_path.is_file():
            try:
                rel = doc_path.relative_to(folder)
            except ValueError:
                rel = doc_path
            title = doc_path.stem.replace("-", " ").replace("_", " ").title()
            nb.add_entry(str(rel), title=title)
    save_notebook(nb, path)
    return nb
