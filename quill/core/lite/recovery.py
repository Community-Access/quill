"""Unsaved-work recovery: a timed copy of every modified window's content.

Each modified window owns one *slot* under the data directory: a content file
(``.txt`` or ``.rtf``, whichever the document is) and a small ``.json`` beside
it saying which mode it is in and which file it came from. The slot is written
on a timer while the document is modified and removed the moment it is saved or
closed cleanly, so a clean shutdown leaves the recovery folder empty. Anything
still there on the next start is work the last session did not get to keep, and
is offered back.

Two decisions worth stating, because both are the difference between recovery
that helps and recovery that hurts:

* **The original file is never touched.** A slot is a copy beside it, so a
  crash mid-save cannot leave the user with a truncated original *and* no
  recovery. Restoring puts the content in a window and leaves saving to them.
* **An empty slot is not a slot.** A zero-byte content file means the window
  was modified and then emptied, or the copy never completed; offering it back
  would replace a real document with nothing. :func:`pending` drops those and
  removes their metadata.

wx-free, so the whole thing is directly testable without a display.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from quill.core.lite.paths import recovery_dir
from quill.core.storage import write_json_atomic

__all__ = ["RecoverySlot", "discard", "new_slot", "pending", "write_meta"]

#: The two modes a slot's content can be in, and the suffix each is stored with.
_SUFFIXES = {"rich": ".rtf", "plain": ".txt"}


@dataclass
class RecoverySlot:
    """One window's aside copy: where the bytes are, and what they were."""

    slot_id: str
    #: ``plain`` or ``rich`` -- which reader restores it.
    mode: str
    #: The file the window was editing, or "" when it was never saved.
    original_path: str
    content_path: Path
    meta_path: Path
    #: The *original document's* encoding, not the slot's. The slot itself is
    #: always UTF-8, because the copy has to hold whatever was typed; what this
    #: records is how the file it came from was written, so restoring a cp1252
    #: document after a crash does not silently save it back as UTF-8 (F2).
    #: Empty when the window had no file, in which case the defaults apply.
    encoding: str = ""
    #: And its line endings, for the same reason. ``"\r\n"``, ``"\n"`` or
    #: ``"\r"``; empty when unknown.
    newline: str = ""

    @property
    def title(self) -> str:
        """What to call this slot when offering it back."""
        return Path(self.original_path).name if self.original_path else "Untitled"


def new_slot(mode: str, original_path: str = "") -> RecoverySlot:
    """A fresh slot for a window in *mode*. Nothing is written until the timer."""
    slot_id = uuid.uuid4().hex
    directory = recovery_dir()
    suffix = _SUFFIXES.get(mode, ".txt")
    return RecoverySlot(
        slot_id=slot_id,
        mode=mode,
        original_path=original_path,
        content_path=directory / f"{slot_id}{suffix}",
        meta_path=directory / f"{slot_id}.json",
    )


def write_meta(slot: RecoverySlot) -> None:
    """Record what the slot's content file is, atomically.

    Written *after* the content, so a metadata file always describes bytes that
    are already on disk rather than bytes a crash interrupted.
    """
    write_json_atomic(
        slot.meta_path,
        {
            "mode": slot.mode,
            "original_path": slot.original_path,
            "content": slot.content_path.name,
            # What the *document* was, not what the slot is. Without these a
            # recovered cp1252/CRLF file was saved back as UTF-8/LF, silently,
            # because the window adopted the slot's own encoding (F2).
            "encoding": slot.encoding,
            "newline": slot.newline,
        },
    )


def discard(slot: RecoverySlot) -> None:
    """Remove a slot. Never raises: a slot that cannot be deleted is offered
    back once more, which is the harmless direction to fail in."""
    for path in (slot.content_path, slot.meta_path):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def pending(directory: Path | None = None) -> list[RecoverySlot]:
    """Every slot left behind by a previous session, oldest first.

    A slot whose content file is missing or empty is not work; its metadata is
    removed here rather than offered back as an empty document.
    """
    root = directory if directory is not None else recovery_dir()
    slots: list[RecoverySlot] = []
    try:
        metas = sorted(root.glob("*.json"))
    except OSError:
        return slots
    for meta_path in metas:
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("recovery metadata is not an object")
            content = root / str(payload["content"])
            if not content.is_file() or content.stat().st_size == 0:
                meta_path.unlink(missing_ok=True)
                continue
            slots.append(
                RecoverySlot(
                    slot_id=meta_path.stem,
                    mode=str(payload.get("mode", "plain")),
                    original_path=str(payload.get("original_path", "")),
                    content_path=content,
                    meta_path=meta_path,
                    encoding=str(payload.get("encoding", "")),
                    newline=str(payload.get("newline", "")),
                )
            )
        except (OSError, ValueError, KeyError):
            # A metadata file we cannot read is not a document we can restore.
            # Leave it: deleting somebody's unreadable file is worse than
            # ignoring it, and the folder is visible from Help > About.
            continue
    return slots
