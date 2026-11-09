"""Layer 2 of IntelliSense: names from the rest of the project.

Layer 1 (:mod:`quill.core.code_names`) offers the names in this file. This
module fills the rest of the list from the project around it: every name
defined or used in the other source files of the same project, found by a
walk built in the background (on the task manager), so pressing Ctrl+. never
waits for a disk.

What counts as the project: the nearest folder above the document that holds
``.git`` (or another project marker), else the document's own folder. The walk
skips build, dependency and hidden folders, reads only files whose extension
Pygments calls code (the same rule as layer 1), and stops at caps, so a home
folder opened by mistake costs seconds, not minutes.

Order, when the list has room after this file's names: names from files this
file imports, then names from other files the project defines (functions and
classes), then every other name. Within each, the same-case match first.

Pure, no ``wx``, no network. ripgrep, if the shared runtime carries it later
(the plan's layer 4 phase), can replace the walk; the pure-Python walk stays
as the fallback.
"""

from __future__ import annotations

import bisect
import os
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.code_names import CodeName, code_language_for

__all__ = [
    "PROJECT_MARKERS",
    "ProjectNameIndex",
    "build_project_index",
    "imported_modules",
    "project_root_for",
]

#: Files or folders whose presence marks a project's top folder.
PROJECT_MARKERS = (
    ".git",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    ".sln",
    "composer.json",
)

#: Folders the walk never enters.
_SKIPPED_FOLDERS = frozenset({
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    "target",
    "bin",
    "obj",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".idea",
    ".vs",
    ".vscode",
})

#: Caps on one walk: files read, bytes per file, bytes in all.
MAX_FILES = 5_000
MAX_FILE_BYTES = 1_000_000
MAX_TOTAL_BYTES = 40_000_000

_IDENTIFIER = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]{2,}")
_DEFINITION = re.compile(
    r"(?<![A-Za-z0-9_])(def|class|function|fn|func|struct|interface|enum|trait|sub|procedure)"
    r"\s+\*?\s*([A-Za-z_][A-Za-z0-9_]*)"
)
_CLASS_WORDS = frozenset({"class", "struct", "interface", "enum", "trait"})
_IMPORT = re.compile(
    r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+)|.*?require\(\s*['\"]([^'\"]+)['\"]"
    r"|.*?\bfrom\s+['\"]([^'\"]+)['\"]|#include\s+[<\"]([^>\"]+)[>\"]|use\s+([\w:]+))",
    re.MULTILINE,
)


def project_root_for(path: Path | str | None) -> Path | None:
    """The project folder around *path*: the nearest marked folder, else its own."""
    if path is None:
        return None
    start = Path(path).resolve().parent
    for folder in (start, *start.parents):
        if any((folder / marker).exists() for marker in PROJECT_MARKERS):
            return folder
    return start


def imported_modules(text: str) -> set[str]:
    """The module stems *text* imports: ``from a.b import c`` gives ``b``, and so on."""
    stems: set[str] = set()
    for match in _IMPORT.finditer(text):
        target = next((group for group in match.groups() if group), "")
        if not target:
            continue
        target = target.replace("\\", "/").strip()
        if "/" in target or Path(target).suffix in {".h", ".hpp", ".js", ".ts", ".mjs", ".py"}:
            last = Path(target).stem  # a path: "./lib/util", "point.h"
        else:
            last = re.split(r"[.:]+", target)[-1]  # a module: "a.b.c", "std::io"
        if last:
            stems.add(last.lower())
    return stems


@dataclass
class ProjectNameIndex:
    """Every name in a project's source files, and where it is defined."""

    root: Path
    #: name -> the stems (file names without extension) it appears in.
    files_for: dict[str, set[str]] = field(default_factory=dict)
    #: name -> "function" or "class", where some file defines it.
    kinds: dict[str, str] = field(default_factory=dict)
    files_read: int = 0
    #: True when a cap stopped the walk before it saw every file.
    truncated: bool = False
    _keys: list[tuple[str, str]] | None = field(default=None, repr=False)

    def _sorted_keys(self) -> list[tuple[str, str]]:
        """(lower-cased name, name), sorted, so a prefix is a bisect away."""
        if self._keys is None:
            self._keys = sorted((name.lower(), name) for name in self.files_for)
        return self._keys

    def add_file(self, stem: str, text: str) -> None:
        self._keys = None
        stem = stem.lower()
        for name in set(_IDENTIFIER.findall(text)):
            self.files_for.setdefault(name, set()).add(stem)
        for word, name in _DEFINITION.findall(text):
            self.kinds.setdefault(name, "class" if word in _CLASS_WORDS else "function")
        self.files_read += 1

    def complete(
        self,
        fragment: str,
        *,
        exclude: set[str],
        imports: set[str],
        own_stem: str = "",
        limit: int = 8,
    ) -> list[CodeName]:
        """Names starting with *fragment* that are not in *exclude*, best first."""
        if not fragment:
            return []
        lowered = fragment.lower()
        own = own_stem.lower()
        keys = self._sorted_keys()
        candidates: list[str] = []
        for key, name in keys[bisect.bisect_left(keys, (lowered, "")) :]:
            if not key.startswith(lowered):
                break
            # A name seen only in this very file is layer 1's to offer.
            if name not in exclude and name != fragment and self.files_for[name] - {own}:
                candidates.append(name)

        def rank(name: str) -> tuple[int, int, int, str]:
            imported = 0 if self.files_for[name] & imports else 1
            defined = 0 if name in self.kinds else 1
            same_case = 0 if name.startswith(fragment) else 1
            return (same_case, imported, defined, name)

        return [
            CodeName(name, self.kinds.get(name, "name"))
            for name in sorted(candidates, key=rank)[:limit]
        ]


def build_project_index(root: Path, *, cancel: threading.Event | None = None) -> ProjectNameIndex:
    """Walk *root* and index its source files. Meant for a background task."""
    index = ProjectNameIndex(root=root)
    total = 0
    for folder, folders, files in os.walk(root):
        folders[:] = sorted(
            name for name in folders if name not in _SKIPPED_FOLDERS and not name.startswith(".")
        )
        for name in sorted(files):
            if cancel is not None and cancel.is_set():
                index.truncated = True
                return index
            if code_language_for(name) is None:
                continue
            path = Path(folder) / name
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            if index.files_read >= MAX_FILES or total + size > MAX_TOTAL_BYTES:
                index.truncated = True
                return index
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            total += size
            index.add_file(path.stem, text)
    return index
