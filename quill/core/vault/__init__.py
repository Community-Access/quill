"""QUILL Accessible Vault — wx-free domain logic for linked knowledge.

A *vault* is a folder of Markdown/plain-text notes. This package owns the note
model, the wikilink codec, the link/backlink index, name/anchor resolution, and
(later phases) vault-wide search, tags, embeds, and templates. It imports no
``wx`` and is strict-typed; all file IO is injected as callables so the model
and indexes are unit-tested without disk.

Canonical specification: the plan at
``docs/planning/quill-accessible-vault-obsidian-parity-plan.md``.
"""

from __future__ import annotations

from quill.core.vault.index import (
    Backlink,
    LinkIndex,
    Mention,
    backlinks,
    build_index,
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
    "NoteInfo",
    "Resolver",
    "Vault",
    "WikiLink",
    "backlinks",
    "build_index",
    "build_resolver",
    "link_at_offset",
    "parse_links",
    "parse_note",
    "resolve_link",
    "scan_vault",
    "unlinked_mentions",
]
