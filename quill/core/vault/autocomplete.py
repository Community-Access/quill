"""Wikilink / tag completion at the cursor (Accessible Vault) — wx-free.

Detects an in-progress `[[note` or `#tag` at the caret and offers the matching notes or
tags. Delivered as a **command-triggered** completion (pick from a filtered, spoken list)
rather than a floating as-you-type popup — a focused list a screen reader announces beats
a popup a screen-reader user must chase. Pure trigger + candidate logic here; the wx shell
shows the list and applies :func:`completion_edit`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.vault.vault import Vault

# A `#tag` at a word boundary, capturing the partial after '#'.
_TAG_RE = re.compile(r"(?<!\S)#([A-Za-z][\w/-]*)?$")


@dataclass(frozen=True, slots=True)
class Trigger:
    """An active completion context at the caret."""

    kind: str  # "wikilink" | "tag"
    prefix: str  # the partial text already typed (after '[[' or '#')
    start: int  # offset where ``prefix`` begins
    has_close: bool  # wikilink only: a ``]]`` already follows the caret


def active_trigger(text: str, cursor: int) -> Trigger | None:
    """Return the completion trigger at ``cursor``, or None.

    A wikilink trigger is the nearest unclosed ``[[`` on the line before the caret; a tag
    trigger is a ``#`` at a word boundary. Wikilinks take precedence when both could match.
    """
    before = text[:cursor]
    open_idx = before.rfind("[[")
    if open_idx != -1 and open_idx > before.rfind("]]"):
        segment = before[open_idx + 2 :]
        if "\n" not in segment:
            return Trigger("wikilink", segment, open_idx + 2, text[cursor : cursor + 2] == "]]")
    match = _TAG_RE.search(before)
    if match:
        return Trigger("tag", match.group(1) or "", match.start() + 1, False)
    return None


def wikilink_candidates(vault: Vault, prefix: str, *, limit: int = 50) -> list[str]:
    """Note titles matching ``prefix`` — prefix matches first, then substring, then all."""
    needle = prefix.strip().casefold()
    titles = sorted({info.title for info in vault.notes.values()})
    if not needle:
        return titles[:limit]
    starts = [t for t in titles if t.casefold().startswith(needle)]
    contains = [t for t in titles if needle in t.casefold() and t not in starts]
    return (starts + contains)[:limit]


def completion_edit(trigger: Trigger, choice: str, cursor: int) -> tuple[int, int, str]:
    """``(replace_start, replace_end, new_text)`` to drop ``choice`` in for the trigger.

    For a wikilink the partial is replaced by ``choice`` plus a closing ``]]`` (unless one
    already follows); for a tag, by the tag name. The caller applies this as one edit.
    """
    if trigger.kind == "wikilink":
        return trigger.start, cursor, choice + ("" if trigger.has_close else "]]")
    return trigger.start, cursor, choice
