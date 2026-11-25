"""Quill Converter's durable, editable file and folder queue.

The queue is kept separate from ``converter.json`` so remembered conversion
choices and the user's queued work have independent failure and recovery
behaviour. Every read-modify-write uses the family's process lock and atomic
JSON writer. Unknown fields, including a future version stamp, round-trip
unchanged.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, cast

from quill.core import file_lock, storage
from quill.core.reported_save import save_reported

FILE_NAME = "converter-queue.json"
SCHEMA = 1
_STALE_LOCK_SECONDS = 10.0
_LOCK_WAIT_SECONDS = 5.0
_WHAT = "Quill Converter queue"


@dataclass(slots=True)
class ConverterQueueEntry:
    """One queued file, or a folder whose root is retained for mirroring."""

    source: Path
    root: Path | None = None
    _extra: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __iter__(self) -> Iterator[Path | None]:
        yield self.source
        yield self.root

    @classmethod
    def from_mapping(cls, value: Any) -> ConverterQueueEntry | None:
        if not isinstance(value, dict):
            return None
        source = value.get("source")
        if not isinstance(source, str) or not source:
            return None
        root = value.get("root")
        known = {item.name for item in fields(cls)} - {"_extra"}
        return cls(
            source=Path(source),
            root=Path(root) if isinstance(root, str) and root else None,
            _extra={key: item for key, item in value.items() if key not in known},
        )

    def to_mapping(self) -> dict[str, Any]:
        data = dict(self._extra)
        data["source"] = str(self.source)
        data["root"] = str(self.root) if self.root is not None else None
        return data

    @property
    def is_folder(self) -> bool:
        return self.root is not None

    @property
    def missing(self) -> bool:
        try:
            return not self.source.exists()
        except OSError:
            return True

    @property
    def available(self) -> bool:
        try:
            if self.is_folder:
                return self.source.is_dir()
            return self.source.is_file()
        except OSError:
            return False

    def label(self) -> str:
        suffix: list[str] = []
        if self.is_folder:
            suffix.append("folder")
        if self.missing:
            suffix.append("missing")
        elif not self.available:
            suffix.append("path is now the wrong kind")
        return f"{self.source.name} ({', '.join(suffix)})" if suffix else self.source.name


QueueItem = ConverterQueueEntry | tuple[Path, Path | None]


def as_entry(value: QueueItem) -> ConverterQueueEntry:
    """Normalize a live UI row or the older ``(source, root)`` pair."""
    if isinstance(value, ConverterQueueEntry):
        return value
    source, root = value
    return ConverterQueueEntry(source, root)


def as_pair(value: QueueItem) -> tuple[Path, Path | None]:
    entry = as_entry(value)
    return entry.source, entry.root


def unavailable_note(values: Iterable[QueueItem]) -> str:
    count = sum(not as_entry(value).available for value in values)
    if not count:
        return ""
    noun = "path is" if count == 1 else "paths are"
    return (
        f"{count} queued {noun} missing or no longer the same kind. "
        "They stay in the queue so you can remove them or reconnect the drive."
    )


def queue_path(data_dir: Path | None = None) -> Path:
    if data_dir is None:
        from quill.core.paths import app_data_dir

        data_dir = app_data_dir()
    return Path(data_dir) / FILE_NAME


class ConverterQueueStore:
    """The one versioned queue file for Quill Converter."""

    def __init__(
        self,
        data_dir: Path | None = None,
        *,
        clock: Callable[[], float] | None = None,
        timeout_s: float = _LOCK_WAIT_SECONDS,
    ) -> None:
        self.path = queue_path(data_dir)
        self.lock_path = self.path.with_suffix(".lock")
        self._clock = clock
        self._timeout_s = timeout_s

    def _read(self) -> dict[str, Any]:
        raw = storage.read_json(self.path, {"version": SCHEMA, "entries": []})
        return cast(dict[str, Any], raw) if isinstance(raw, dict) else {}

    def load(self) -> list[ConverterQueueEntry]:
        raw_entries = self._read().get("entries")
        parsed = [
            ConverterQueueEntry.from_mapping(item)
            for item in (raw_entries if isinstance(raw_entries, list) else [])
        ]
        return [entry for entry in parsed if entry is not None]

    def save(self, current: Callable[[], Iterable[QueueItem]]) -> bool:
        """Write the live UI state; a failed write reports a current-state Retry."""
        return save_reported(_WHAT, self.path, lambda: self._write(current()))

    def _write(self, current: Iterable[QueueItem]) -> None:
        clock = self._clock
        lock_args: dict[str, Any] = {
            "timeout_s": self._timeout_s,
            "lock_path": self.lock_path,
            "stale_after_s": _STALE_LOCK_SECONDS,
            "require_lock": True,
        }
        if clock is not None:
            lock_args["clock"] = clock
        with file_lock.guarded_write(self.path, **lock_args):
            document = dict(self._read())
            version = document.get("version")
            if type(version) is not int:  # bool is not a schema version
                document["version"] = SCHEMA
            document["entries"] = [as_entry(item).to_mapping() for item in current]
            storage.write_json_atomic(self.path, document)


__all__ = [
    "FILE_NAME",
    "SCHEMA",
    "ConverterQueueEntry",
    "ConverterQueueStore",
    "QueueItem",
    "as_entry",
    "as_pair",
    "queue_path",
    "unavailable_note",
]
