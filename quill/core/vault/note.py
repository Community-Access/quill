"""Note parsing — turn note text into indexable metadata (wx-free).

``parse_note`` reads a note's optional front matter and body and reports its
title, aliases, tags (front matter + inline ``#tag``), headings, block ids, and
outgoing wikilinks. Offsets are relative to the *whole* file text (front matter
included) so a UI can open a note at a heading or block. Reuses the Story Studio
front-matter codec and heading scanner; Story Studio is a collection view over a
vault, so the two share this machinery.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from quill.core.story.frontmatter import split_front_matter
from quill.core.story.manuscript import Heading, iter_headings
from quill.core.vault.links import WikiLink, parse_links

__all__ = ["NoteInfo", "parse_note"]

# Inline tag: '#' immediately followed by a letter, then word chars / '/' / '-'.
# The letter-first rule keeps ATX headings ("# Heading", space after #) out.
_INLINE_TAG_RE = re.compile(r"(?<!\S)#([A-Za-z][\w/-]*)")
# A block id: '^id' at the end of a line, preceded by whitespace/line start. The
# lookbehind (rather than consuming the space) makes the match start at '^' so
# the recorded offset points at the marker itself.
_BLOCK_ID_RE = re.compile(r"(?<![^\s])\^([A-Za-z0-9][\w-]*)[ \t]*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class NoteInfo:
    """Indexed metadata for one note."""

    title: str
    aliases: tuple[str, ...]
    tags: tuple[str, ...]
    headings: tuple[Heading, ...]
    block_ids: dict[str, int]
    links: tuple[WikiLink, ...]


def parse_note(text: str, stem: str) -> NoteInfo:
    """Parse ``text`` (a note's full contents) with ``stem`` as the filename base."""
    fields, _body = split_front_matter(text)
    headings = tuple(iter_headings(text))
    title = _resolve_title(fields, headings, stem)
    aliases = _string_tuple(fields.get("aliases"))
    tags = _collect_tags(fields.get("tags"), text)
    block_ids = {m.group(1): m.start() for m in _BLOCK_ID_RE.finditer(text)}
    return NoteInfo(
        title=title,
        aliases=aliases,
        tags=tags,
        headings=headings,
        block_ids=block_ids,
        links=tuple(parse_links(text)),
    )


def _resolve_title(fields: dict[str, Any], headings: tuple[Heading, ...], stem: str) -> str:
    raw = fields.get("title")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    for heading in headings:
        if heading.level == 1:
            return heading.title
    return stem


def _string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    return ()


def _collect_tags(front_matter_tags: Any, text: str) -> tuple[str, ...]:
    ordered: list[str] = list(_string_tuple(front_matter_tags))
    for match in _INLINE_TAG_RE.finditer(text):
        ordered.append(match.group(1))
    seen: set[str] = set()
    unique: list[str] = []
    for tag in ordered:
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)
    return tuple(unique)
