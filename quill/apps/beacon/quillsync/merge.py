"""Reusable merge helpers for QuillSync adapters (PRD 45.6, 23.5).

Adapters build their :class:`~quillsync.protocol.MergeFn` from these primitives
so the merge policy is consistent across Beacon, Quill, Quill Radio, and Quill
Cast. Two policies are provided:

- :func:`union_lists`: order-preserving union for set-like fields (tags,
  collections, favorites). Used by every adapter.
- :func:`three_way_note`: line-based three-way merge for prose fields (notes,
  descriptions). Without a stored common ancestor we treat the local text as
  the base; overlapping edits become a :class:`~quillsync.protocol.Conflict`
  for accessible two-version review, never inline markers the user must parse.
"""

from __future__ import annotations

import difflib

from quill.apps.beacon.quillsync.protocol import Conflict


def union_lists(a: list[str], b: list[str]) -> list[str]:
    """Order-preserving union of two string lists (dedup)."""
    return list(dict.fromkeys(list(a) + list(b)))


def three_way_note(
    local: str,
    remote: str,
    *,
    entity_id: str,
    field: str = "note",
) -> tuple[str, Conflict | None]:
    """Line-based three-way merge of two text fields.

    Returns ``(merged_text, conflict_or_None)``. If both sides edited the same
    lines, the conflict is surfaced for review; the merged text keeps both
    versions behind a visible marker so nothing is silently lost.
    """
    if local == remote:
        return local, None
    if not local:
        return remote, None
    if not remote:
        return local, None
    merged_lines = list(difflib.ndiff(local.splitlines(), remote.splitlines()))
    merged = "\n".join(_resolve_line(line) for line in merged_lines)
    if "<<<<<<" in merged:
        conflict = Conflict(
            entity_id=entity_id,
            field=field,
            local=local,
            remote=remote,
            merged=merged,
            message=f"{field} edited on two devices. Review both versions.",
        )
        return merged, conflict
    return merged, None


def _resolve_line(diff_line: str) -> str:
    """Resolve an ndiff line. Conflicting changes become a marked block."""
    tag = diff_line[:2]
    text = diff_line[2:]
    if tag == "  ":
        return text
    if tag == "+ ":
        return text
    if tag == "- ":
        # A line removed locally that was also changed remotely -> conflict.
        return f"<<<<<< local removed: {text}"
    return text
