"""A project, as an AI agent may see it (code.md 4.4) -- wx-free.

A project is just a folder. This module decides what an agent working in one
may look at, and it is the only place that decides it:

- **Inside the root only.** Every path is resolved, symlinks and junctions
  followed, and must still be under the root. ``..``, absolute paths, UNC
  paths, drive letters, device names (``CON``, ``NUL``, ``COM1``) and
  alternate data streams (``file.txt:hidden``) are refused before anything
  touches the disk.
- **Secrets are invisible.** ``.env`` files, keys, certificates, password
  databases, ``.ssh`` and ``.aws`` folders, credential and token files and
  git's own internals are never listed, read or sent. A listing says how many
  it hid, so the model knows something is there and can ask the person.
- **Content is scrubbed on the way out.** Every excerpt goes through
  :mod:`quill.stability.redaction`, which catches keys pasted into ordinary
  files.
- **Reads are capped,** so a task costs what it needs and no more, and
  **binary files are described, never sent** ("PNG image, 48 KB").

``.gitignore`` at the root is honoured for listing and searching: an ignored
file is left out of both, though a read of it by name still works when it is
not a secret, because the person may well ask about a build log.
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from quill.core.error_codes import CodedError

__all__ = [
    "MAX_READ_LINES",
    "ListEntry",
    "ListResult",
    "OutlineItem",
    "Project",
    "ProjectError",
    "ReadResult",
    "SearchHit",
    "is_secret_path",
    "scrub",
]

#: The most lines one read returns; the model asks for ranges after that.
MAX_READ_LINES = 400
#: The most entries one listing returns.
MAX_LIST_ENTRIES = 600
#: The most hits one search returns.
MAX_SEARCH_HITS = 200
#: Files bigger than this are never read whole or searched.
MAX_FILE_BYTES = 2 * 1024 * 1024

#: Names that are secrets wherever they appear (matched case-insensitively).
SECRET_NAME_PATTERNS: tuple[str, ...] = (
    ".env",
    ".env.*",
    "*.env",
    "*.pem",
    "*.key",
    "*.pfx",
    "*.p12",
    "*.keystore",
    "*.jks",
    "id_rsa*",
    "id_dsa*",
    "id_ecdsa*",
    "id_ed25519*",
    "*.kdbx",
    "*.kdb",
    "credentials*",
    "secrets*",
    "secret.*",
    "*.token",
    "token.json",
    "tokens.json",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "_netrc",
    ".git-credentials",
    ".htpasswd",
)

#: Folders whose whole contents are secret, or are git's own machinery.
SECRET_DIRS: frozenset[str] = frozenset({".ssh", ".aws", ".gnupg", ".azure", ".git"})

#: Folders never listed or searched: generated, vendored or caches.
SKIPPED_DIRS: frozenset[str] = frozenset({
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".idea",
    ".vs",
})

_DEVICE_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{n}" for n in range(1, 10)}
    | {f"lpt{n}" for n in range(1, 10)}
)

_BINARY_KINDS: dict[str, str] = {
    ".png": "PNG image",
    ".jpg": "JPEG image",
    ".jpeg": "JPEG image",
    ".gif": "GIF image",
    ".bmp": "bitmap image",
    ".ico": "icon",
    ".webp": "WebP image",
    ".pdf": "PDF document",
    ".zip": "zip archive",
    ".exe": "program",
    ".dll": "library",
    ".pyd": "compiled Python module",
    ".pyc": "compiled Python file",
    ".mp3": "MP3 audio",
    ".wav": "WAV audio",
    ".docx": "Word document",
    ".xlsx": "Excel workbook",
}


class ProjectError(CodedError):
    """A path the agent asked for is outside the project, secret, or unreadable."""

    code = "QUILL-AI-PROJECT-REFUSED"


@dataclass(frozen=True, slots=True)
class ListEntry:
    path: str  # project-relative, forward slashes
    size: int
    is_dir: bool = False


@dataclass(frozen=True, slots=True)
class ListResult:
    entries: tuple[ListEntry, ...]
    hidden_secrets: int
    ignored: int
    truncated: bool


@dataclass(frozen=True, slots=True)
class ReadResult:
    path: str
    text: str  # numbered lines, or a description for a binary file
    start: int
    end: int
    total_lines: int
    binary: bool = False

    @property
    def truncated(self) -> bool:
        return not self.binary and self.end < self.total_lines


@dataclass(frozen=True, slots=True)
class SearchHit:
    path: str
    line: int
    text: str


@dataclass(frozen=True, slots=True)
class OutlineItem:
    kind: str  # "class" | "function"
    name: str
    line: int
    depth: int = 0


def scrub(text: str) -> str:
    """*text* with known secrets and token-shaped strings replaced."""
    from quill.stability.redaction import redact_known_secrets, redact_source_tokens

    return redact_source_tokens(redact_known_secrets(text))


def is_secret_path(rel: str) -> bool:
    """True when any part of the project-relative *rel* names a secret."""
    parts = [p for p in re.split(r"[\\/]+", rel) if p]
    for index, part in enumerate(parts):
        low = part.lower()
        if low in SECRET_DIRS and index < len(parts) - 1:
            return True
        if low in SECRET_DIRS and index == len(parts) - 1:
            return True
        if any(fnmatch.fnmatchcase(low, pattern) for pattern in SECRET_NAME_PATTERNS):
            return True
    return False


def _check_relative(rel: str) -> PurePosixPath:
    """Refuse anything that is not a plain path inside a folder."""
    text = str(rel or "").strip()
    if not text or text in (".", "./"):
        return PurePosixPath(".")
    if text.startswith(("\\\\", "//")):
        raise ProjectError("Network paths are outside the project.")
    if text.startswith(("/", "\\")) or os.path.isabs(text) or re.match(r"^[A-Za-z]:", text):
        raise ProjectError("Use a path inside the project, not a full path.")
    if ":" in text:
        raise ProjectError("That path names a stream or a drive, which is refused.")
    parts = [p for p in re.split(r"[\\/]+", text) if p not in ("", ".")]
    for part in parts:
        if part == "..":
            raise ProjectError("Paths may not climb out of the project with '..'.")
        stem = part.split(".", 1)[0].strip().lower()
        if stem in _DEVICE_NAMES:
            raise ProjectError(f"{part} is a device name, not a file.")
    return PurePosixPath(*parts) if parts else PurePosixPath(".")


class _IgnoreRules:
    """The root ``.gitignore``, simply: globs, ``dir/`` rules, ``/anchored`` and ``!``."""

    def __init__(self, lines: list[str]) -> None:
        self._rules: list[tuple[bool, bool, bool, str]] = []
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            negate = line.startswith("!")
            if negate:
                line = line[1:]
            dir_only = line.endswith("/")
            line = line.rstrip("/")
            anchored = line.startswith("/") or "/" in line
            line = line.lstrip("/")
            if line:
                self._rules.append((negate, dir_only, anchored, line))

    def ignored(self, rel: str, is_dir: bool) -> bool:
        verdict = False
        parts = rel.split("/")
        for negate, dir_only, anchored, pattern in self._rules:
            if self._matches(pattern, rel, parts, is_dir, dir_only, anchored):
                verdict = not negate
        return verdict

    @staticmethod
    def _matches(
        pattern: str, rel: str, parts: list[str], is_dir: bool, dir_only: bool, anchored: bool
    ) -> bool:
        glob = pattern.replace("**/", "*").replace("/**", "/*")
        if anchored:
            # A match on the path or on any of its parent folders.
            for count in range(1, len(parts) + 1):
                prefix = "/".join(parts[:count])
                last = count == len(parts)
                if fnmatch.fnmatch(prefix, glob) and (not dir_only or not last or is_dir):
                    return True
            return False
        for index, part in enumerate(parts):
            last = index == len(parts) - 1
            if fnmatch.fnmatch(part, glob) and (not dir_only or not last or is_dir):
                return True
        return False


class Project:
    """One folder, with the rules for what an agent may see in it."""

    def __init__(self, root: Path | str) -> None:
        resolved = Path(root).expanduser().resolve()
        if not resolved.is_dir():
            raise ProjectError(f"{resolved} is not a folder.")
        self._root = resolved
        self._ignore = _IgnoreRules(self._gitignore_lines())

    @property
    def root(self) -> Path:
        return self._root

    @property
    def name(self) -> str:
        return self._root.name or str(self._root)

    @property
    def key(self) -> str:
        """A stable, private id for this folder, for QUILL's own app data."""
        text = os.path.normcase(str(self._root))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    @property
    def is_git(self) -> bool:
        return (self._root / ".git").exists()

    def _gitignore_lines(self) -> list[str]:
        try:
            return (self._root / ".gitignore").read_text("utf-8", errors="replace").splitlines()
        except OSError:
            return []

    # -- paths ------------------------------------------------------------- #

    def relative(self, path: Path) -> str:
        """*path* (absolute, inside the root) as a project-relative string."""
        return Path(path).resolve().relative_to(self._root).as_posix()

    def resolve(self, rel: str, *, allow_secret: bool = False) -> Path:
        """The absolute path for *rel*, or :class:`ProjectError` with a reason."""
        clean = _check_relative(rel)
        if not allow_secret and is_secret_path(clean.as_posix()):
            raise ProjectError(
                f"{clean.as_posix()} looks like a secret, so QUILL keeps it from the agent."
            )
        candidate = (self._root / clean.as_posix()).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise ProjectError(f"{clean.as_posix()} leads outside the project.")
        return candidate

    def is_ignored(self, rel: str, is_dir: bool = False) -> bool:
        return self._ignore.ignored(rel, is_dir)

    # -- walking ----------------------------------------------------------- #

    def walk(self, folder: str = "") -> Iterator[tuple[str, Path, str]]:
        """``(rel, path, kind)`` for every visible file below *folder*.

        *kind* is ``"file"``, ``"secret"`` or ``"ignored"``; skipped folders
        are not entered, and nothing outside the root is ever followed.
        """
        start = self.resolve(folder) if folder else self._root
        for dirpath, dirnames, filenames in os.walk(start):
            here = Path(dirpath)
            kept: list[str] = []
            for name in sorted(dirnames):
                full = here / name
                rel = full.relative_to(self._root).as_posix()
                if name in SKIPPED_DIRS or name.lower() in SECRET_DIRS:
                    continue
                if full.is_symlink() or not self._inside(full):
                    continue
                if self.is_ignored(rel, True):
                    continue
                kept.append(name)
            dirnames[:] = kept
            for name in sorted(filenames):
                full = here / name
                if not self._inside(full):
                    continue
                rel = full.relative_to(self._root).as_posix()
                if is_secret_path(rel):
                    yield rel, full, "secret"
                elif self.is_ignored(rel):
                    yield rel, full, "ignored"
                else:
                    yield rel, full, "file"

    def _inside(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
        except OSError:
            return False
        return resolved == self._root or self._root in resolved.parents

    def files(self, limit: int = 5000) -> list[tuple[str, Path]]:
        """Every visible file, up to *limit*, for checkpoints and search."""
        found: list[tuple[str, Path]] = []
        for rel, path, kind in self.walk():
            if kind == "file":
                found.append((rel, path))
                if len(found) >= limit:
                    break
        return found

    # -- the agent's reads -------------------------------------------------- #

    def list_folder(self, folder: str = "", limit: int = MAX_LIST_ENTRIES) -> ListResult:
        entries: list[ListEntry] = []
        secrets = ignored = 0
        truncated = False
        for rel, path, kind in self.walk(folder):
            if kind == "secret":
                secrets += 1
                continue
            if kind == "ignored":
                ignored += 1
                continue
            if len(entries) >= limit:
                truncated = True
                continue
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            entries.append(ListEntry(rel, size))
        return ListResult(tuple(entries), secrets, ignored, truncated)

    def describe_binary(self, path: Path) -> str | None:
        """A sentence for a binary file, or None when it is text."""
        kind = _BINARY_KINDS.get(path.suffix.lower())
        try:
            size = path.stat().st_size
            with path.open("rb") as handle:
                head = handle.read(8192)
        except OSError as error:
            raise ProjectError(f"{path.name} could not be read: {error.strerror}") from error
        if kind is None and b"\x00" not in head:
            return None
        return f"{kind or 'Binary file'}, {_size_words(size)}. Not sent."

    def read_text(self, rel: str) -> str:
        """The whole text of a project file, for edits. Refuses binaries and big files."""
        path = self.resolve(rel)
        if not path.is_file():
            raise ProjectError(f"{rel} is not a file in the project.")
        if self.describe_binary(path) is not None:
            raise ProjectError(f"{rel} is not a text file.")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ProjectError(f"{rel} is too large to edit through a task.")
        try:
            return path.read_text("utf-8")
        except UnicodeDecodeError as error:
            raise ProjectError(f"{rel} is not UTF-8 text, so it cannot be edited here.") from error

    def read(self, rel: str, start: int = 1, end: int = 0) -> ReadResult:
        """Lines *start* to *end* (1-based, inclusive) with numbers, scrubbed."""
        path = self.resolve(rel)
        if not path.is_file():
            raise ProjectError(f"{rel} is not a file in the project.")
        clean = self.relative(path)
        described = self.describe_binary(path)
        if described is not None:
            return ReadResult(clean, described, 0, 0, 0, binary=True)
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ProjectError(f"{rel} is too large to read; search it instead.")
        lines = path.read_text("utf-8", errors="replace").splitlines()
        total = len(lines)
        first = max(1, int(start or 1))
        last = int(end or 0) or total
        last = min(total, last, first + MAX_READ_LINES - 1)
        width = len(str(max(last, 1)))
        body = "\n".join(
            f"{number:>{width}}: {lines[number - 1]}" for number in range(first, last + 1)
        )
        return ReadResult(clean, scrub(body), first, last, total)

    def search(
        self, query: str, *, regex: bool = False, glob: str = "", limit: int = MAX_SEARCH_HITS
    ) -> list[SearchHit]:
        if not query:
            return []
        try:
            pattern = re.compile(query if regex else re.escape(query), re.IGNORECASE)
        except re.error as error:
            raise ProjectError(f"That search pattern is not valid: {error}") from error
        hits: list[SearchHit] = []
        for rel, path in self.files():
            if glob and not fnmatch.fnmatch(rel, glob) and not fnmatch.fnmatch(path.name, glob):
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES or self.describe_binary(path):
                    continue
                text = path.read_text("utf-8", errors="replace")
            except (OSError, ProjectError):
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line):
                    hits.append(SearchHit(rel, number, scrub(line.strip())[:240]))
                    if len(hits) >= limit:
                        return hits
        return hits

    def outline(self, rel: str) -> list[OutlineItem]:
        from quill.core.ai.project_outline import outline_text

        path = self.resolve(rel)
        if not path.is_file() or self.describe_binary(path) is not None:
            raise ProjectError(f"{rel} is not a text file in the project.")
        return outline_text(path.suffix.lower(), path.read_text("utf-8", errors="replace"))


def _size_words(size: int) -> str:
    if size < 1024:
        return f"{size} bytes"
    if size < 1024 * 1024:
        return f"{round(size / 1024)} KB"
    return f"{size / (1024 * 1024):.1f} MB"
