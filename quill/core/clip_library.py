"""The Clip Library (#895): a rolling history of kept Fragments, complementary
to (never a replacement for) the 12-slot curated Copy Tray.

Copy Tray stays exactly as it is -- 12 deliberate, labeled, pinnable slots.
The Clip Library is the wider net beneath it: up to 200 remembered Fragments,
de-duplicated by content, with favorites protected from the ring buffer's
eviction. ``promote_to_tray`` is the bridge the issue asks about: a clip that
earns a permanent, labeled home graduates into a Copy Tray slot.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from quill.core.fragment import Fragment
from quill.core.storage import write_json_atomic

__all__ = ["ClipEntry", "ClipLibrary"]


class _TraySlotTarget(Protocol):
    """The one CopyTray method promote_to_tray needs (duck-typed to avoid a
    quill.core.copy_tray import at load time -- copy_tray has no dependency on
    this module and should not gain one)."""

    def copy_to(self, slot: int, text: str) -> None: ...


@dataclass(slots=True)
class ClipEntry:
    """One remembered Fragment plus library-specific bookkeeping."""

    fragment: Fragment
    favorite: bool = False
    remembered_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())

    def preview(self, max_chars: int = 60) -> str:
        flat = " ".join(self.fragment.markup.split())
        return flat[:max_chars] + ("..." if len(flat) > max_chars else "")

    def display_label(self) -> str:
        if self.fragment.title:
            return self.fragment.title
        return self.preview(40)


class ClipLibrary:
    """Rolling history of Fragments -- the automatic tier beneath Copy Tray."""

    CAPACITY = 200
    _FILENAME = "clip_library.json"
    _VERSION = 1

    def __init__(self, data_dir: Path) -> None:
        self._path = data_dir / self._FILENAME
        self._entries: list[ClipEntry] = []
        self._load()

    # -- write --

    def remember(self, frag: Fragment) -> bool:
        """Add *frag* to the library. Returns False (a no-op) for a duplicate.

        De-duplicates by (markup, source): re-copying the same content moves
        nothing and adds nothing, so re-keeping a fact doesn't clutter the
        library with repeats. When at capacity, the oldest non-favorite entry
        is evicted first; favorites are never silently dropped.
        """
        if not frag.markup.strip():
            return False
        for entry in self._entries:
            if entry.fragment.markup == frag.markup and entry.fragment.source == frag.source:
                return False
        if len(self._entries) >= self.CAPACITY:
            self._evict_oldest_non_favorite()
        self._entries.insert(0, ClipEntry(fragment=frag))
        self._save()
        return True

    def _evict_oldest_non_favorite(self) -> None:
        for index in range(len(self._entries) - 1, -1, -1):
            if not self._entries[index].favorite:
                del self._entries[index]
                return
        # Every entry is a favorite: drop the oldest anyway rather than grow
        # without bound (a full library of favorites is a deliberate choice,
        # but the ring buffer's cap is a hard limit, not a suggestion).
        if self._entries:
            del self._entries[-1]

    def set_favorite(self, index: int, favorite: bool) -> None:
        self._check(index)
        self._entries[index].favorite = favorite
        self._save()

    def remove(self, index: int) -> None:
        self._check(index)
        del self._entries[index]
        self._save()

    def clear(self) -> None:
        self._entries = []
        self._save()

    def promote_to_tray(
        self, index: int, tray: _TraySlotTarget, slot: int, *, link_style: str = "text_url"
    ) -> str:
        """Render entry *index* as plain text and copy it into Copy Tray *slot*.

        *tray* is a :class:`~quill.core.copy_tray.CopyTray` (duck-typed here so
        this module never imports wx or the tray's own module at load time).
        Returns the text that was copied.
        """
        from quill.core.fragment import FragmentFormat, render_fragment

        self._check(index)
        text = render_fragment(
            self._entries[index].fragment, FragmentFormat.TEXT, link_style=link_style
        )
        tray.copy_to(slot, text)
        return text

    # -- read --

    def all_entries(self) -> list[tuple[int, ClipEntry]]:
        return list(enumerate(self._entries))

    def entry(self, index: int) -> ClipEntry:
        self._check(index)
        return self._entries[index]

    def search(self, query: str) -> list[tuple[int, ClipEntry]]:
        """Return (index, entry) pairs whose title, source, or markup contains *query*."""
        q = query.lower().strip()
        if not q:
            return self.all_entries()
        results = []
        for index, entry in enumerate(self._entries):
            haystack = f"{entry.fragment.title} {entry.fragment.source} {entry.fragment.markup}"
            if q in haystack.lower():
                results.append((index, entry))
        return results

    def __len__(self) -> int:
        return len(self._entries)

    # -- persistence --

    def _save(self) -> None:
        write_json_atomic(
            self._path,
            {
                "version": self._VERSION,
                "entries": [
                    {
                        "fragment": asdict(e.fragment),
                        "favorite": e.favorite,
                        "remembered_at": e.remembered_at,
                    }
                    for e in self._entries
                ],
            },
        )

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw: dict = json.loads(self._path.read_text(encoding="utf-8"))
            entries: list[ClipEntry] = []
            for item in raw.get("entries", [])[: self.CAPACITY]:
                frag_data = item.get("fragment", {})
                if not isinstance(frag_data, dict):
                    continue
                entries.append(
                    ClipEntry(
                        fragment=Fragment(
                            markup=str(frag_data.get("markup", "")),
                            title=str(frag_data.get("title", "")),
                            source=str(frag_data.get("source", "")),
                            source_url=str(frag_data.get("source_url", "")),
                            kind=str(frag_data.get("kind", "text")),
                            created_at=str(frag_data.get("created_at", "")),
                        ),
                        favorite=bool(item.get("favorite", False)),
                        remembered_at=str(item.get("remembered_at", "")),
                    )
                )
            self._entries = entries
        except Exception:  # noqa: BLE001 - corrupt data -- start fresh
            pass

    def _check(self, index: int) -> None:
        if not 0 <= index < len(self._entries):
            raise ValueError(f"Clip index out of range: {index!r}")
