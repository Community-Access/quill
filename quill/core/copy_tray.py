"""Twelve-slot persistent copy tray for the Copy Tray feature."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from quill.core.storage import write_json_atomic


@dataclass
class TraySlot:
    text: str = ""
    label: str = ""
    copied_at: str = ""
    pinned: bool = False

    def is_empty(self) -> bool:
        return not self.text

    def display_label(self, n: int) -> str:
        """Return a short label for screen reader / list display."""
        if self.label:
            return f"Slot {n}: {self.label}"
        return f"Slot {n}"

    def preview(self, max_chars: int = 60) -> str:
        if not self.text:
            return "(empty)"
        flat = " ".join(self.text.split())
        return flat[:max_chars] + ("..." if len(flat) > max_chars else "")


class CopyTray:
    """Persistent store for 12 independently addressable copy slots."""

    SLOT_COUNT = 12
    _FILENAME = "copy_tray.json"
    _VERSION = 1

    def __init__(self, data_dir: Path) -> None:
        self._path = data_dir / self._FILENAME
        self._slots: list[TraySlot] = [TraySlot() for _ in range(self.SLOT_COUNT)]
        self._load()

    # -- write --

    def copy_to(self, slot: int, text: str) -> None:
        """Store *text* in *slot* (1-12)."""
        self._check(slot)
        self._slots[slot - 1] = TraySlot(
            text=text,
            copied_at=datetime.now(tz=UTC).isoformat(),
        )
        self._save()

    def set_label(self, slot: int, label: str) -> None:
        self._check(slot)
        self._slots[slot - 1].label = label.strip()
        self._save()

    def pin_slot(self, slot: int) -> None:
        self._check(slot)
        self._slots[slot - 1].pinned = True
        self._save()

    def unpin_slot(self, slot: int) -> None:
        self._check(slot)
        self._slots[slot - 1].pinned = False
        self._save()

    def clear_slot(self, slot: int) -> None:
        self._check(slot)
        self._slots[slot - 1] = TraySlot()
        self._save()

    def clear_all(self) -> None:
        self._slots = [TraySlot() for _ in range(self.SLOT_COUNT)]
        self._save()

    # -- read --

    def paste_from(self, slot: int) -> str:
        """Return text in *slot* (1-12), or '' if empty."""
        self._check(slot)
        return self._slots[slot - 1].text

    def slot(self, n: int) -> TraySlot:
        self._check(n)
        return self._slots[n - 1]

    def all_slots(self) -> list[tuple[int, TraySlot]]:
        return list(enumerate(self._slots, start=1))

    def first_empty_slot(self) -> int | None:
        """Return the slot number of the first empty, non-pinned slot, or None."""
        for n, slot in enumerate(self._slots, start=1):
            if not slot.pinned and slot.is_empty():
                return n
        return None

    def search_slots(self, query: str) -> list[tuple[int, TraySlot]]:
        """Return (slot_number, slot) pairs whose text or label contains *query*."""
        q = query.lower()
        return [
            (n, slot)
            for n, slot in enumerate(self._slots, start=1)
            if not slot.is_empty() and (q in slot.text.lower() or q in slot.label.lower())
        ]

    # -- persistence --

    def _save(self) -> None:
        write_json_atomic(
            self._path,
            {"version": self._VERSION, "slots": [asdict(s) for s in self._slots]},
        )

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw: dict = json.loads(self._path.read_text(encoding="utf-8"))
            for i, s in enumerate(raw.get("slots", [])[: self.SLOT_COUNT]):
                self._slots[i] = TraySlot(
                    text=s.get("text", ""),
                    label=s.get("label", ""),
                    copied_at=s.get("copied_at", ""),
                    pinned=bool(s.get("pinned", False)),
                )
        except Exception:  # noqa: BLE001  # corrupt data — start fresh
            pass

    @staticmethod
    def _check(n: int) -> None:
        if not 1 <= n <= CopyTray.SLOT_COUNT:
            raise ValueError(f"Slot must be 1-{CopyTray.SLOT_COUNT}, got {n!r}")
