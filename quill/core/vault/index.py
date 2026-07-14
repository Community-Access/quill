"""The link index — forward links, backlinks, and unlinked mentions (wx-free).

``build_index`` walks every note's resolved outgoing links to build both the
forward adjacency (what a note links to) and the reverse adjacency (the
backlinks — who links to a note, with the linking line quoted for context).
Same-note anchors, self-links, and unresolved names are excluded from the graph.

``unlinked_mentions`` finds notes that name a note's title or alias in plain
text without linking it — the "link this mention" opportunity — matched
whole-word and case-insensitively, skipping occurrences already inside a link.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.vault.links import code_spans
from quill.core.vault.resolve import Resolver, resolve_link
from quill.core.vault.vault import Vault

__all__ = [
    "Backlink",
    "Mention",
    "LinkIndex",
    "Neighborhood",
    "build_index",
    "backlinks",
    "unlinked_mentions",
    "neighborhood",
]


@dataclass(frozen=True, slots=True)
class Backlink:
    """A note that links to the current one, with the linking line for context."""

    source_path: str
    context: str
    offset: int


@dataclass(frozen=True, slots=True)
class Mention:
    """A plain-text occurrence of a note's name that is not (yet) a link."""

    source_path: str
    context: str
    offset: int


@dataclass(frozen=True, slots=True)
class LinkIndex:
    """Forward and reverse adjacency across the vault."""

    forward: dict[str, tuple[str, ...]]
    reverse: dict[str, tuple[Backlink, ...]]


def build_index(vault: Vault, resolver: Resolver) -> LinkIndex:
    forward: dict[str, tuple[str, ...]] = {}
    reverse: dict[str, list[Backlink]] = {}
    for path, info in vault.notes.items():
        targets: list[str] = []
        for link in info.links:
            if link.target == "":
                continue  # same-note anchor, not a cross-note edge
            resolved = resolve_link(vault, resolver, link, path)
            # Ambiguous names are not edges: guessing a candidate would build a
            # wrong graph. They stay out until the UI disambiguates (#787).
            if resolved is None or resolved.ambiguous or resolved.path == path:
                continue
            if resolved.path not in targets:
                targets.append(resolved.path)
            context = _line_at(vault.texts.get(path, ""), link.start)
            reverse.setdefault(resolved.path, []).append(
                Backlink(source_path=path, context=context, offset=link.start)
            )
        forward[path] = tuple(targets)
    reverse_sorted = {
        target: tuple(sorted(links, key=lambda bl: (bl.source_path, bl.offset)))
        for target, links in reverse.items()
    }
    return LinkIndex(forward=forward, reverse=reverse_sorted)


def backlinks(index: LinkIndex, path: str) -> tuple[Backlink, ...]:
    return index.reverse.get(path, ())


@dataclass(frozen=True, slots=True)
class Neighborhood:
    """A note's immediate graph: what it links to and what links to it.

    ``outgoing`` is ``(path, title)`` per linked-to note; ``incoming`` is the backlinks
    (source path + linking sentence). This is the data behind the spoken "neighborhood"
    command that lets a writer traverse the web of notes purely by keyboard and ear.
    """

    path: str
    title: str
    outgoing: tuple[tuple[str, str], ...]
    incoming: tuple[Backlink, ...]


def neighborhood(vault: Vault, index: LinkIndex, path: str) -> Neighborhood:
    """Forward links (with their titles) and backlinks for ``path``, together."""
    info = vault.notes.get(path)
    title = info.title if info is not None else path
    outgoing = tuple(
        (target, vault.notes[target].title if target in vault.notes else target)
        for target in index.forward.get(path, ())
    )
    return Neighborhood(path=path, title=title, outgoing=outgoing, incoming=backlinks(index, path))


def unlinked_mentions(vault: Vault, resolver: Resolver, path: str) -> tuple[Mention, ...]:
    info = vault.notes.get(path)
    if info is None:
        return ()
    names = [name for name in (info.title, *info.aliases) if name.strip()]
    patterns = [re.compile(rf"(?<!\w){re.escape(name)}(?!\w)", re.IGNORECASE) for name in names]
    mentions: list[Mention] = []
    for other, text in vault.texts.items():
        if other == path:
            continue
        # Skip occurrences already inside a link, and anything in code regions
        # — a name inside a code sample is not a "link this mention" prospect.
        skip_spans = [(link.start, link.end) for link in vault.notes[other].links]
        skip_spans += code_spans(text)
        for pattern in patterns:
            for match in pattern.finditer(text):
                if _within_any(match.start(), skip_spans):
                    continue
                mentions.append(
                    Mention(
                        source_path=other,
                        context=_line_at(text, match.start()),
                        offset=match.start(),
                    )
                )
    return tuple(sorted(mentions, key=lambda m: (m.source_path, m.offset)))


def _line_at(text: str, position: int) -> str:
    start = text.rfind("\n", 0, position) + 1
    end = text.find("\n", position)
    if end == -1:
        end = len(text)
    return text[start:end].strip()


def _within_any(position: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in spans)
