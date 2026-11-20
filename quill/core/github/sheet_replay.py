"""Undo and Redo GitHub Change: a recorded change sent again, safely (GitHub PRD 16.5).

Change History keeps each proven change as fields, before and after, and the
ident of the object as it was left (after a rename, its new name). Sending
that back is not a save from an open sheet: nothing is loaded, the pickers'
choices are not to hand, and an object GitHub replaces whole (a ruleset, a
branch protection, an environment, a team's review assignment) needs its
current state to be rebuilt from. So :func:`replay` does what the sheet did
when it opened:

- reads the object **fresh**, for its node id and its current state;
- loads the pickers' **choices**, so a milestone goes back as its number and a
  project as its id, never as a title GitHub would read as "none";
- **stops** when somebody changed one of the fields on GitHub since (their
  value is not what this change left), and says so, rather than overwrite it;
- then saves through :func:`~quill.core.github.sheet_engine.save`, so the
  re-read decides what is reported, as for any save.

:func:`undo` sends the inverse; :func:`redo` sends the change again, to where
the undo left the object. :func:`undo_refusal` is the plain sentence for a
change GitHub cannot reverse, said in the save's preview before it happens
(:func:`undo_notes`) and again if Undo is asked for.

wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Sequence

from quill.core.github.sheet_engine import (
    Ident,
    SaveOutcome,
    SheetDef,
    inverse,
    is_set,
    load,
    load_options,
    save,
)
from quill.core.github.workbench_api import GitHubApi
from quill.core.workbench.properties import MIXED, FieldChange, ListDelta

__all__ = ["redo", "redo_ident", "replay", "undo", "undo_notes", "undo_refusal"]

_NO_UNDO = "GitHub has no way to put it back as it was"


def _why(sheet: SheetDef, change: FieldChange, *, recorded: bool) -> str:
    write = sheet.writes.get(change.key)
    if write is None:
        return "it cannot be changed from this sheet"
    if not write.undo:
        return write.why_no_undo or _NO_UNDO
    if recorded and (change.before is MIXED or isinstance(change.before, ListDelta)):
        return "it differed across the items, so there is no one value to put back"
    return ""


def _sentences(sheet: SheetDef, changes: Sequence[FieldChange], *, recorded: bool) -> list[str]:
    notes: list[str] = []
    for change in changes:
        why = _why(sheet, change, recorded=recorded)
        if why:
            notes.append(f"{change.label} cannot be undone: {why}.")
    return notes


def _same(expected: object, now: object) -> bool:
    """Whether GitHub still has what the change left (empty is empty, a list in any order)."""
    if isinstance(expected, tuple) and isinstance(now, tuple):
        return sorted(expected) == sorted(now)
    if expected in (None, "") and now in (None, ""):
        return True
    return expected == now


def undo_notes(sheet: SheetDef, changes: Sequence[FieldChange]) -> list[str]:
    """One sentence per pending change Undo will not be able to reverse, for the preview.

    A batch's changes are recorded per item, each with its own value, so a
    field that is Mixed before the save is no reason by itself.
    """
    return _sentences(sheet, changes, recorded=False)


def undo_refusal(sheet: SheetDef, done: Sequence[FieldChange]) -> str:
    """Why recorded *done* cannot be undone, in one or more sentences; empty when it can."""
    return " ".join(_sentences(sheet, done, recorded=True))


def replay(
    api: GitHubApi, sheet: SheetDef, ident: Ident, changes: Sequence[FieldChange]
) -> SaveOutcome:
    """Send *changes* (each ``before`` what GitHub should have now) over a fresh read."""
    fresh = load(api, sheet, ident)
    choices = load_options(api, sheet, ident)
    expected = {change.key: change.before for change in changes}
    whole = [c for c in changes if not (c.key in sheet.writes and is_set(sheet.writes[c.key]))]
    found = tuple(
        FieldChange(c.key, c.label, fresh.values.get(c.key), c.after)
        for c in whole
        if not _same(c.before, fresh.values.get(c.key))
    )
    if found:
        return SaveOutcome(conflicts=found)
    return save(
        api,
        sheet,
        ident,
        changes,
        loaded={**fresh.values, **expected},  # type: ignore[dict-item]
        choices=choices,
        check_conflicts=False,
    )


def undo(api: GitHubApi, sheet: SheetDef, ident: Ident, done: Sequence[FieldChange]) -> SaveOutcome:
    """Put *done* back. Call :func:`undo_refusal` first: this assumes GitHub allows it."""
    back, _cannot = inverse(sheet, done)
    return replay(api, sheet, ident, back)


def redo_ident(sheet: SheetDef, ident: Ident, done: Sequence[FieldChange]) -> dict[str, str]:
    """Where the object is after *done* was undone (a renamed label is back at its old name)."""
    back, _cannot = inverse(sheet, done)
    return sheet.ident_after(ident, back)


def redo(api: GitHubApi, sheet: SheetDef, ident: Ident, done: Sequence[FieldChange]) -> SaveOutcome:
    """Make *done* again after an undo; *ident* is where the change first left the object."""
    return replay(api, sheet, redo_ident(sheet, ident, done), done)
