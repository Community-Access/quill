"""Vault refactors that touch many notes at once — starting with rename (wx-free).

Renaming a note should offer to update the inbound `[[links]]` that named it by its old
title, so links do not silently break. This module computes the exact, offset-precise
edits for that — it does not write files (the UI applies them as one undoable step and
summarizes "Updated N inbound links in M notes"). Only links whose *target* used the old
title are rewritten; links that reached the note by alias or filename still resolve and
are left alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.vault.links import WikiLink, parse_links
from quill.core.vault.vault import Vault


@dataclass(frozen=True, slots=True)
class Replacement:
    """Replace ``text[start:end]`` with ``new_text`` in one note."""

    start: int
    end: int
    new_text: str


@dataclass(frozen=True, slots=True)
class NoteEdit:
    """All replacements for one note, in ascending offset order."""

    path: str
    replacements: tuple[Replacement, ...]


def _norm(name: str) -> str:
    return name.strip().casefold()


def _rebuild(link: WikiLink, new_target: str) -> str:
    """Reconstruct a `[[...]]` link with a new target, preserving heading/block/alias."""
    inner = new_target
    if link.heading:
        inner += f"#{link.heading}"
    if link.block:
        inner += f"#^{link.block}"
    if link.alias:
        inner += f"|{link.alias}"
    return f"[[{inner}]]"


def plan_note_rename(vault: Vault, old_title: str, new_title: str) -> list[NoteEdit]:
    """Return the per-note edits that retarget inbound links from ``old_title`` to it.

    Matches non-embed links whose target equals ``old_title`` (case/space-insensitive);
    the alias, heading, and block portions are preserved. Returns ``[]`` when the titles
    are equivalent or nothing links by the old title. Deterministic order (by path).
    """
    if _norm(old_title) == _norm(new_title) or not new_title.strip():
        return []
    target_norm = _norm(old_title)
    edits: list[NoteEdit] = []
    for path in sorted(vault.texts):
        text = vault.texts[path]
        reps: list[Replacement] = []
        for link in parse_links(text):
            if link.embed or _norm(link.target) != target_norm:
                continue
            reps.append(Replacement(link.start, link.end, _rebuild(link, new_title)))
        if reps:
            edits.append(NoteEdit(path=path, replacements=tuple(reps)))
    return edits


def apply_replacements(text: str, replacements: tuple[Replacement, ...]) -> str:
    """Apply ``replacements`` to ``text`` (last-first so earlier offsets stay valid)."""
    result = text
    for rep in sorted(replacements, key=lambda r: r.start, reverse=True):
        result = result[: rep.start] + rep.new_text + result[rep.end :]
    return result


def rename_link_count(edits: list[NoteEdit]) -> tuple[int, int]:
    """``(total inbound links updated, notes touched)`` for the confirmation prompt."""
    total = sum(len(edit.replacements) for edit in edits)
    return total, len(edits)


def retitle_heading(text: str, old_title: str, new_title: str) -> str:
    """Rewrite a leading ``# Old Title`` H1 to the new title (first exact match only).

    Keeps a note whose title comes from its H1 consistent after a rename. Notes titled by
    filename (or front matter) have no matching H1 and are returned unchanged.
    """
    pattern = re.compile(rf"^#[ \t]+{re.escape(old_title)}[ \t]*$", re.MULTILINE)
    return pattern.sub(f"# {new_title}", text, count=1)
