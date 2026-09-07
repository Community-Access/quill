"""Unsaved-work recovery: a timed copy of every modified window's content.

Each window owns one recovery slot under the data directory. The slot is
written on a timer while the document is modified, and removed when the
document is saved or closed cleanly. On the next start, any slots left behind
are offered back to the user.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from quilllite.paths import recovery_dir


@dataclass
class RecoverySlot:
    slot_id: str
    mode: str  # plain or rich
    original_path: str  # "" when untitled
    content_path: Path
    meta_path: Path

    @property
    def title(self) -> str:
        return Path(self.original_path).name if self.original_path else "Untitled"


def new_slot(mode: str, original_path: str = "") -> RecoverySlot:
    slot_id = uuid.uuid4().hex
    suffix = ".rtf" if mode == "rich" else ".txt"
    directory = recovery_dir()
    return RecoverySlot(
        slot_id,
        mode,
        original_path,
        directory / f"{slot_id}{suffix}",
        directory / f"{slot_id}.json",
    )


def write_meta(slot: RecoverySlot) -> None:
    payload = {
        "mode": slot.mode,
        "original_path": slot.original_path,
        "content": slot.content_path.name,
    }
    tmp = slot.meta_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, slot.meta_path)


def discard(slot: RecoverySlot) -> None:
    for path in (slot.content_path, slot.meta_path):
        try:
            path.unlink()
        except OSError:
            pass


def pending() -> list[RecoverySlot]:
    slots: list[RecoverySlot] = []
    directory = recovery_dir()
    for meta_path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            content = directory / str(payload["content"])
            if not content.exists() or content.stat().st_size == 0:
                meta_path.unlink(missing_ok=True)
                continue
            slots.append(
                RecoverySlot(
                    meta_path.stem,
                    str(payload.get("mode", "plain")),
                    str(payload.get("original_path", "")),
                    content,
                    meta_path,
                )
            )
        except (OSError, ValueError, KeyError):
            continue
    return slots
