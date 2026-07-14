"""Global tag index for the vault (Accessible Vault, Phase 4) — wx-free.

Indexes inline `#tag` and front-matter `tags:` across every note, **nested-tag aware**
(a note tagged `#area/sub` also answers to `#area`), and drives three surfaces the UI
dresses accessibly: the **tag pane** (every tag with a spoken count), **notes for a tag**
(Enter opens a note), and **`#` autocomplete** (existing tags first, most-used first).
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.vault.vault import Vault


@dataclass(frozen=True, slots=True)
class TaggedNote:
    path: str
    title: str


@dataclass(frozen=True, slots=True)
class TagIndex:
    """``tag -> the notes carrying it`` (ancestors included for nested tags)."""

    by_tag: dict[str, tuple[TaggedNote, ...]]


def _ancestors(tag: str) -> list[str]:
    """`area/sub/leaf` -> ['area', 'area/sub', 'area/sub/leaf']."""
    parts = [p for p in tag.split("/") if p]
    return ["/".join(parts[: i + 1]) for i in range(len(parts))]


def build_tag_index(vault: Vault) -> TagIndex:
    """Build the vault-wide, nested-aware tag index (each note listed once per tag)."""
    acc: dict[str, list[TaggedNote]] = {}
    for path in sorted(vault.notes):
        info = vault.notes[path]
        note = TaggedNote(path=path, title=info.title)
        seen: set[str] = set()
        for raw in info.tags:
            for tag in _ancestors(raw.lstrip("#")):
                if tag in seen:
                    continue
                seen.add(tag)
                acc.setdefault(tag, []).append(note)
    return TagIndex(by_tag={tag: tuple(notes) for tag, notes in acc.items()})


def tag_counts(index: TagIndex) -> list[tuple[str, int]]:
    """``(tag, note count)`` ordered by count (desc) then tag name — for the tag pane."""
    counts = [(tag, len(notes)) for tag, notes in index.by_tag.items()]
    counts.sort(key=lambda item: (-item[1], item[0]))
    return counts


def notes_for_tag(index: TagIndex, tag: str) -> tuple[TaggedNote, ...]:
    return index.by_tag.get(tag.lstrip("#"), ())


def tag_suggestions(index: TagIndex, prefix: str, *, limit: int = 20) -> list[str]:
    """Existing tags starting with ``prefix`` (case-insensitive), most-used first.

    Empty prefix returns the most-used tags. Drives the `#` autocomplete popup.
    """
    needle = prefix.lstrip("#").casefold()
    matches = [
        (tag, len(notes))
        for tag, notes in index.by_tag.items()
        if tag.casefold().startswith(needle)
    ]
    matches.sort(key=lambda item: (-item[1], item[0]))
    return [tag for tag, _count in matches[:limit]]
