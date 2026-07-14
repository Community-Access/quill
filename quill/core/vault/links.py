"""Wikilink codec (wx-free).

Parses wiki-style links out of note text:

* ``[[Note]]``               — a link to another note
* ``[[Note|alias]]``         — with the display text shown in place of the target
* ``[[Note#Heading]]``       — to a heading within the target
* ``[[Note#^blockid]]``      — to a specific block within the target
* ``[[#Heading]]``           — to a heading in the *same* note (empty target)
* ``![[Note]]`` / ``![[Note#Heading]]`` — an *embed* (transclusion), phase 5

Markdown links ``[label](url)`` are left alone (single brackets). Links inside
inline code spans and fenced code blocks are ignored so code samples that
mention ``[[…]]`` are not mistaken for real links.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["WikiLink", "parse_links", "link_at_offset", "code_spans"]

# ![[...]] or [[...]]; the inner text is captured lazily and dissected below.
_LINK_RE = re.compile(r"(!?)\[\[([^\[\]]+?)\]\]")
# Fenced code blocks (``` or ~~~) and inline code spans (`...`), masked out.
_FENCE_RE = re.compile(r"^[ \t]*(```+|~~~+).*?^[ \t]*\1[ \t]*$", re.MULTILINE | re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`+[^`]*`+")


@dataclass(frozen=True, slots=True)
class WikiLink:
    """One parsed wikilink and where it sits in the source text."""

    target: str
    heading: str | None
    block: str | None
    alias: str | None
    embed: bool
    start: int
    end: int


def parse_links(text: str) -> list[WikiLink]:
    """Return every wikilink in ``text``, in document order (code regions skipped)."""
    masked = code_spans(text)
    links: list[WikiLink] = []
    for match in _LINK_RE.finditer(text):
        if _within_any(match.start(), masked):
            continue
        target, heading, block, alias = _dissect(match.group(2))
        links.append(
            WikiLink(
                target=target,
                heading=heading,
                block=block,
                alias=alias,
                embed=match.group(1) == "!",
                start=match.start(),
                end=match.end(),
            )
        )
    return links


def link_at_offset(text: str, offset: int) -> WikiLink | None:
    """Return the wikilink whose span contains ``offset`` (the caret), or None.

    Used by Follow Link: the caret anywhere on a ``[[link]]`` (including its
    brackets) resolves to that link.
    """
    for link in parse_links(text):
        if link.start <= offset <= link.end:
            return link
    return None


def _dissect(inner: str) -> tuple[str, str | None, str | None, str | None]:
    """Split ``target#anchor|alias`` into its parts (any part may be absent)."""
    alias: str | None = None
    if "|" in inner:
        inner, alias = (part.strip() for part in inner.split("|", 1))
    heading: str | None = None
    block: str | None = None
    if "#" in inner:
        inner, anchor = (part.strip() for part in inner.split("#", 1))
        if anchor.startswith("^"):
            block = anchor[1:].strip()
        else:
            heading = anchor
    return inner.strip(), heading, block, alias


def code_spans(text: str) -> list[tuple[int, int]]:
    """(start, end) spans of fenced blocks and inline code — the regions the
    link and mention scanners must ignore."""
    spans = [(m.start(), m.end()) for m in _FENCE_RE.finditer(text)]
    spans += [(m.start(), m.end()) for m in _INLINE_CODE_RE.finditer(text)]
    return spans


def _within_any(position: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in spans)
