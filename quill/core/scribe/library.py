"""Where Scribe downloads go, and the local record of them (PRD 7.6).

* The default folder is ``Documents\\Scribe for Documents\\<document title>``;
  the family's Scribe options can name another.
* A result is named after our own name for the document (the uploaded
  file's stem), never the title Scribe read from inside it -- a scan's title
  can start with a library stamp (F6, Pneuma's corpus). Its extension comes
  from the bytes that arrived (F1). It is made safe, and an existing file is
  never overwritten -- ``Notes (2).docx``.
* :class:`Library` remembers which Scribe document made which file, so Documents in
  My Scribe Account can say "downloaded to ..." and Beacon can find it. It
  holds document IDs, formats and paths only: never a document's text.

wx-free.
"""

from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path
from typing import Any

from quill.core.storage import read_json, write_json_atomic

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_MAX_NAME = 150


def safe_file_name(name: str, *, fallback: str = "Scribe document") -> str:
    """*name* fit for a Windows folder: no separators, no reserved names."""
    cleaned = _UNSAFE.sub("_", str(name or "")).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        cleaned = fallback
    stem, dot, suffix = cleaned.rpartition(".")
    if not dot:
        stem, suffix = cleaned, ""
    if stem.upper() in _RESERVED:
        stem = f"{stem}_"
    if len(stem) > _MAX_NAME:
        stem = stem[:_MAX_NAME].rstrip()
    return f"{stem}.{suffix}" if suffix else stem


#: Added to the offline web page's name, as Pneuma's own corpus names it: it
#: is an HTML file like the accessible HTML, and must not take its name.
OFFLINE_SUFFIX = "-offline"


def saved_name(
    format_id: str,
    downloaded: Path,
    *,
    stem: str = "",
    server_name: str = "",
    fallback: str = "",
) -> str:
    """The safe file name for a downloaded output.

    *stem* is our name for the document; without one the server's file name
    (or *fallback*, the document ID) gives the stem. The extension is read
    from *downloaded*'s first bytes, so an offline web page that arrived as
    one HTML file is never saved as ``.zip``.
    """
    from quill.core.scribe.model import ZIP_MAGIC, extension_for_bytes

    try:
        with downloaded.open("rb") as handle:
            head = handle.read(len(ZIP_MAGIC))
    except OSError:
        head = b""
    server = Path(safe_file_name(server_name)) if server_name else None
    base = (stem or "").strip() or (server.stem if server else "") or fallback
    if format_id == "offline_html" and not base.endswith(OFFLINE_SUFFIX):
        base += OFFLINE_SUFFIX  # never "Notes (2).html" beside the accessible HTML
    extension = extension_for_bytes(format_id, head, server.suffix if server else "")
    return safe_file_name(f"{Path(safe_file_name(base)).name}{extension}")


def unique_path(path: Path) -> Path:
    """*path*, or ``name (2).ext``, ``name (3).ext``... -- never an existing file."""
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for number in range(2, 10_000):
        candidate = path.with_name(f"{stem} ({number}){suffix}")
        if not candidate.exists():
            return candidate
    return path.with_name(f"{stem} ({int(time.time())}){suffix}")


def default_download_root() -> Path:
    """``Documents\\Scribe for Documents``."""
    profile = os.environ.get("USERPROFILE") or str(Path.home())
    return Path(profile) / "Documents" / "Scribe for Documents"


def document_folder(title: str, root: Path | str | None = None) -> Path:
    """The folder one document's results go in: the root, then the title."""
    base = Path(root) if root else default_download_root()
    stem = Path(safe_file_name(title or "Scribe document")).stem or "Scribe document"
    return base / stem


def library_path() -> Path:
    from quill.core.scribe.queue import queue_dir

    return queue_dir() / "library.json"


class Library:
    """The local record: document ID -> its title and the files downloaded."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or library_path()
        self._lock = threading.Lock()

    def _load(self) -> dict[str, Any]:
        data = read_json(self._path, {})
        return data if isinstance(data, dict) else {}

    def record(self, document_id: str, title: str, format_id: str, file_path: Path) -> None:
        with self._lock:
            data = self._load()
            raw = data.get(document_id)
            entry: dict[str, Any] = raw if isinstance(raw, dict) else {}
            files = [f for f in entry.get("files", []) if isinstance(f, dict)]
            files = [f for f in files if f.get("path") != str(file_path)]
            files.append({"format": format_id, "path": str(file_path), "at": time.time()})
            data[document_id] = {"title": title, "files": files}
            write_json_atomic(self._path, data)

    def files_for(self, document_id: str) -> list[tuple[str, Path]]:
        """``(format, path)`` for each recorded file that still exists."""
        entry = self._load().get(document_id)
        if not isinstance(entry, dict):
            return []
        found: list[tuple[str, Path]] = []
        for item in entry.get("files", []):
            if isinstance(item, dict) and item.get("path"):
                path = Path(str(item["path"]))
                if path.exists():
                    found.append((str(item.get("format", "")), path))
        return found

    def document_ids(self) -> list[str]:
        return list(self._load())

    def title_for(self, document_id: str) -> str:
        """Our own name for *document_id* (the uploaded file's stem), or ``""``."""
        entry = self._load().get(document_id)
        return str(entry.get("title") or "") if isinstance(entry, dict) else ""


__all__ = [
    "Library",
    "default_download_root",
    "document_folder",
    "library_path",
    "safe_file_name",
    "saved_name",
    "unique_path",
]
