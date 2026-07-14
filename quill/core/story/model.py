"""Story Studio data model (wx-free, strict-typed).

The persisted shape of a project is a small, forgiving document: a title, an
ordered list of manuscript file paths (chapters are derived from their
headings, not stored), and a list of non-manuscript *elements* (characters,
places, plot threads, research, brainstorming). Loading is corrupt-tolerant in
the spirit of :mod:`quill.core.settings_migration`: a bad entry is dropped and
the rest is kept, so a hand-edited or partially-written sidecar never discards
good data. Paths are relative POSIX strings, so a project folder stays portable.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

__all__ = ["ElementKind", "StoryElement", "StoryProject", "new_element"]


class ElementKind(StrEnum):
    """The non-manuscript element types a project can hold."""

    CHARACTER = "character"
    LOCATION = "location"
    PLOT = "plot"
    RESEARCH = "research"
    BRAINSTORM = "brainstorm"

    @classmethod
    def coerce(cls, value: object) -> ElementKind:
        """Return the matching kind, or RESEARCH for anything unrecognized."""
        if isinstance(value, ElementKind):
            return value
        try:
            return cls(str(value))
        except ValueError:
            return cls.RESEARCH


def _is_relative_posix_path(path: str) -> bool:
    """True for the only path shape the sidecar may hold: relative POSIX.

    Rejects absolute paths, Windows drive/backslash forms, and traversal
    segments so a hand-edited or machine-copied sidecar can neither leak
    machine-specific paths nor escape the project folder.
    """
    if not path or "\\" in path:
        return False
    if path.startswith("/") or ":" in path.split("/", 1)[0]:
        return False
    return all(segment not in ("", "..") for segment in path.split("/"))


@dataclass(frozen=True, slots=True)
class StoryElement:
    """One non-manuscript element backed by a plain-text file."""

    id: str
    kind: ElementKind
    title: str
    path: str
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "title": self.title,
            "path": self.path,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Any) -> StoryElement | None:
        """Build an element, or return None when required fields are missing.

        ``id``, ``title``, and ``path`` are required (a binder node is useless
        without them). ``kind`` falls back to RESEARCH; ``tags`` defaults empty.
        """
        if not isinstance(data, dict):
            return None
        element_id = data.get("id")
        title = data.get("title")
        path = data.get("path")
        if not (isinstance(element_id, str) and element_id):
            return None
        if not (isinstance(title, str) and title):
            return None
        if not (isinstance(path, str) and _is_relative_posix_path(path)):
            return None
        raw_tags = data.get("tags", [])
        tags = (
            tuple(str(tag) for tag in raw_tags if isinstance(tag, str))
            if isinstance(raw_tags, list)
            else ()
        )
        return cls(
            id=element_id,
            kind=ElementKind.coerce(data.get("kind")),
            title=title,
            path=path,
            tags=tags,
        )


def new_element(
    kind: ElementKind, title: str, path: str, tags: tuple[str, ...] = ()
) -> StoryElement:
    """Create an element with a freshly minted unique id."""
    return StoryElement(id=uuid.uuid4().hex, kind=kind, title=title, path=path, tags=tags)


@dataclass(frozen=True, slots=True)
class StoryProject:
    """A whole project: title, manuscript spine, and non-manuscript elements."""

    #: Bump when the on-disk document shape changes incompatibly.
    SCHEMA_VERSION = 1

    title: str = "Untitled Project"
    manuscript: tuple[str, ...] = ()
    elements: tuple[StoryElement, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "title": self.title,
            "manuscript": list(self.manuscript),
            "elements": [element.to_dict() for element in self.elements],
        }

    @classmethod
    def from_dict(cls, data: Any) -> StoryProject:
        """Build a project from any mapping, dropping individually-invalid parts."""
        if not isinstance(data, dict):
            return cls()
        raw_title = data.get("title")
        title = raw_title if isinstance(raw_title, str) and raw_title else "Untitled Project"
        raw_manuscript = data.get("manuscript", [])
        manuscript = (
            tuple(
                item
                for item in raw_manuscript
                if isinstance(item, str) and _is_relative_posix_path(item)
            )
            if isinstance(raw_manuscript, list)
            else ()
        )
        raw_elements = data.get("elements", [])
        elements: list[StoryElement] = []
        if isinstance(raw_elements, list):
            for entry in raw_elements:
                element = StoryElement.from_dict(entry)
                if element is not None:
                    elements.append(element)
        return cls(title=title, manuscript=manuscript, elements=tuple(elements))
