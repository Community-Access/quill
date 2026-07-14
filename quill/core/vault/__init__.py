"""QUILL Accessible Vault — wx-free domain logic for linked knowledge.

A *vault* is a folder of Markdown/plain-text notes. This package owns the note
model, the wikilink codec, the link/backlink index, name/anchor resolution, and
(later phases) vault-wide search, tags, embeds, and templates. It imports no
``wx`` and is strict-typed. ``scan_vault`` is the one disk touchpoint (walk the
folder, read the notes); everything downstream — parsing, resolution, the
indexes — operates on the in-memory :class:`Vault` and is unit-tested without
touching a real vault on disk.

Canonical specification: ``QUILL-PRD.md`` §5.89d; remaining phases in
``docs/planning/roadmap.md`` §1.7.
"""

from __future__ import annotations

from quill.core.vault.index import (
    Backlink,
    LinkIndex,
    Mention,
    Neighborhood,
    backlinks,
    build_index,
    neighborhood,
    unlinked_mentions,
)
from quill.core.vault.links import WikiLink, link_at_offset, parse_links
from quill.core.vault.note import NoteInfo, parse_note
from quill.core.vault.resolve import LinkTarget, Resolver, build_resolver, resolve_link
from quill.core.vault.vault import CACHE_DIRNAME, Vault, scan_vault

__all__ = [
    "CACHE_DIRNAME",
    "Backlink",
    "LinkIndex",
    "LinkTarget",
    "Mention",
    "Neighborhood",
    "NoteInfo",
    "Resolver",
    "Vault",
    "WikiLink",
    "backlinks",
    "build_index",
    "build_resolver",
    "link_at_offset",
    "neighborhood",
    "parse_links",
    "parse_note",
    "resolve_link",
    "scan_vault",
    "unlinked_mentions",
]
