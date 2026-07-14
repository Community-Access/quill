"""Favorite folders (wx-free domain logic).

Kurzweil-1000-style "favorite folders" (community feature request): a short,
user-curated list of folders for quick access, distinct from Windows' "recent
folders" (which tracks what was *recently* opened, not what the user actually
wants fast access to). A folder used constantly but not touched in months
(the example in the original request: a document the user's boss might ask
about at any moment) belongs in favorites even though it would long since
have aged out of any recency-based list.

Modeled directly on :class:`quill.core.bookmarks.BookmarkVault`: a tiny,
stateless-beyond-its-file wrapper with forgiving load (missing/malformed file
yields an empty list, never raises) and atomic writes via ``core.storage``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

FAVORITE_FOLDERS_FILENAME = "favorite_folders.json"


@dataclass(slots=True)
class FavoriteFolders:
    """Persistent, ordered list of favorite folder paths.

    Order is insertion order (most-recently-added last), not alphabetical --
    matches how a short, deliberately curated list is actually scanned: a few
    familiar names in a stable, user-recognizable order, not resorted every
    time something is added.
    """

    path: Path = field(default_factory=lambda: app_data_dir() / FAVORITE_FOLDERS_FILENAME)
    folders: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | None = None) -> FavoriteFolders:
        target = path if path is not None else app_data_dir() / FAVORITE_FOLDERS_FILENAME
        try:
            raw = read_json(target, default=[])
        except (OSError, ValueError):
            raw = []
        folders: list[str] = []
        if isinstance(raw, list):
            for entry in raw:
                if isinstance(entry, str) and entry.strip() and entry not in folders:
                    folders.append(entry)
        return cls(path=target, folders=folders)

    def save(self) -> None:
        write_json_atomic(self.path, self.folders)

    def add(self, folder: str) -> bool:
        """Add *folder* if not already present. Returns True if it was added."""
        normalized = folder.strip()
        if not normalized or normalized in self.folders:
            return False
        self.folders.append(normalized)
        self.save()
        return True

    def remove(self, folder: str) -> bool:
        if folder not in self.folders:
            return False
        self.folders.remove(folder)
        self.save()
        return True

    def names(self) -> list[str]:
        """Display labels: the folder's own name, falling back to the full path
        for folders whose name collides (e.g. two different "Reports" folders)."""
        labels: list[str] = []
        seen_names: dict[str, int] = {}
        for folder in self.folders:
            name = Path(folder).name or folder
            seen_names[name] = seen_names.get(name, 0) + 1
        for folder in self.folders:
            name = Path(folder).name or folder
            labels.append(folder if seen_names[name] > 1 else name)
        return labels


@dataclass(frozen=True, slots=True)
class FavoriteFile:
    """One file found while scanning favorite folders for Quick Open."""

    path: Path
    folder_label: str  # the favorite folder's display name, for disambiguation


_RECURSIVE_SCAN_CAP = 5_000
# Ceiling on how many files a recursive scan collects (per call, across all
# favorites combined). Top-level scanning has no such cap since a "short
# curated list" of folders scanned shallowly is inherently bounded; a favorite
# that turns out to contain a huge nested tree should not be able to freeze
# Quick Open when the user explicitly opts into recursive search.


def list_files_in_favorites(
    vault: FavoriteFolders, *, recursive: bool = False
) -> list[FavoriteFile]:
    """File listing across every favorite folder.

    Non-recursive (the default) lists top-level files only -- a deliberate
    scope choice, not an oversight: favorites are meant to be a *short*
    curated list, and a shallow scan keeps Quick Open instant even for a
    favorite that happens to contain a huge tree. Pass ``recursive=True``
    (an explicit, user-opted-into checkbox in the UI) to search every
    subfolder too, capped at ``_RECURSIVE_SCAN_CAP`` files total so a
    pathologically large favorite still can't hang the dialog.

    A missing or unreadable favorite folder is skipped silently (it may have
    been moved or the drive may be offline) rather than raising.
    """
    names = vault.names()
    results: list[FavoriteFile] = []
    for folder, label in zip(vault.folders, names, strict=True):
        root = Path(folder)
        try:
            entries = (
                sorted(root.rglob("*"), key=lambda p: p.name.lower())
                if recursive
                else sorted(root.iterdir(), key=lambda p: p.name.lower())
            )
        except OSError:
            continue
        for entry in entries:
            if entry.is_file():
                results.append(FavoriteFile(path=entry, folder_label=label))
                if recursive and len(results) >= _RECURSIVE_SCAN_CAP:
                    return results
    return results


def filter_favorite_files(files: list[FavoriteFile], query: str) -> list[FavoriteFile]:
    """VSCode-Quick-Open-style type-to-filter: case-insensitive substring match
    against the filename, scoped to favorite folders instead of a whole
    workspace (Quill has no single-project-root concept to scan). An empty
    query returns every file unfiltered."""
    normalized = query.strip().lower()
    if not normalized:
        return list(files)
    return [item for item in files if normalized in item.path.name.lower()]
