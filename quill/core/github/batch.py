"""Many objects at once: preview, a paced run, and a result per item (GitHub PRD 16.4, GH-R-043).

Select, then Alt+Enter: one sheet for every selected object, and saving it
changes only the fields you touched, on each of them. This module is that
save, wx-free:

- :func:`preview` is the sentence before anything changes: "Change 14
  issues: add bug, remove triage, set milestone 2027.1. 3 of them already
  have bug." (section 16.4);
- :func:`item_changes` turns the sheet's changes into one item's own: a
  three-state check list's added and removed rows applied to that item's
  list, and a field that is already so dropped, so it counts as Skipped;
- :func:`run` sends them one item at a time, paced for GitHub's secondary
  rate limits (a second between items by default), with a progress callback
  for the status bar and a :class:`BatchResult` per item: Done, Skipped
  (already so) or Failed and why;
- :func:`results_text` is Copy Results; failed items can be run again.

Removal and replacement are as available as adding (GH-R-041): the deltas
remove as readily as they add.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from quill.core.github.sheet_engine import SheetDef, save, sentence
from quill.core.github.workbench_api import GitHubApi
from quill.core.workbench.properties import FieldChange, ListDelta, Value, apply_delta

__all__ = [
    "BatchItem",
    "BatchResult",
    "DEFAULT_PACE_SECONDS",
    "item_changes",
    "preview",
    "results_text",
    "run",
]

DEFAULT_PACE_SECONDS = 1.0
"""GitHub asks for a second between content-creating requests (secondary rate limits)."""


@dataclass(frozen=True)
class BatchItem:
    name: str
    ident: Mapping[str, str]
    values: Mapping[str, Value]


@dataclass(frozen=True)
class BatchResult:
    name: str
    status: str
    detail: str = ""

    def row(self) -> str:
        return f"{self.name}: {self.status}" + (f", {self.detail}" if self.detail else "")


def _words(change: FieldChange) -> list[str]:
    after = change.after
    label = change.label.lower()
    if isinstance(after, ListDelta):
        parts = [f"add {', '.join(after.added)}"] if after.added else []
        parts += [f"remove {', '.join(after.removed)}"] if after.removed else []
        return parts
    if isinstance(after, bool):
        return [f"turn {label} {'on' if after else 'off'}"]
    if after in (None, ""):
        return [f"clear {label}"]
    if isinstance(after, tuple):
        return [f"set {label} to {', '.join(after) or 'none'}"]
    return [f"set {label} {after}"]


def _listed(item: BatchItem, key: str) -> tuple[str, ...]:
    found = item.values.get(key)
    return found if isinstance(found, tuple) else ()


def preview(noun: str, items: Sequence[BatchItem], changes: Sequence[FieldChange]) -> str:
    """The sentence before a batch: what changes, on how many, and what is already so."""
    parts: list[str] = []
    for change in changes:
        parts.extend(_words(change))
    said = f"Change {len(items)} {noun}: {', '.join(parts) or 'nothing'}."
    already: list[str] = []
    for change in changes:
        after = change.after
        if isinstance(after, ListDelta):
            for name in after.added:
                count = len([item for item in items if name in _listed(item, change.key)])
                if count:
                    already.append(f"{count} of them already have {name}")
        else:
            count = len([item for item in items if item.values.get(change.key) == after])
            if count:
                already.append(f"{count} of them already have that {change.label.lower()}")
    if already:
        said += " " + "; ".join(already).capitalize() + "."
    return said


def item_changes(changes: Sequence[FieldChange], values: Mapping[str, Value]) -> list[FieldChange]:
    """The changes for one item: deltas applied to its own lists, no-ops dropped."""
    found: list[FieldChange] = []
    for change in changes:
        before = values.get(change.key)
        after: Value = change.after
        if isinstance(after, ListDelta):
            current = before if isinstance(before, tuple) else ()
            after = apply_delta(current, after)
            if sorted(after) == sorted(current):
                continue
        elif after == before:
            continue
        found.append(FieldChange(change.key, change.label, before, after))
    return found


def run(
    api: GitHubApi,
    sheet: SheetDef,
    items: Sequence[BatchItem],
    changes: Sequence[FieldChange],
    *,
    choices: Mapping[str, Mapping[str, object]] | None = None,
    pace: float = DEFAULT_PACE_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    progress: Callable[[int, int], None] | None = None,
    done: Callable[[BatchItem, list[FieldChange]], None] | None = None,
) -> list[BatchResult]:
    """Change each item in turn and say what happened to each.

    *done* is told each item's proven changes, so the caller can record them
    in Change History. Each item's save checks for conflicts and verifies
    with a re-read, as a single sheet does.
    """
    results: list[BatchResult] = []
    for index, item in enumerate(items, start=1):
        if progress is not None:
            progress(index, len(items))
        own = item_changes(changes, item.values)
        if not own:
            results.append(BatchResult(item.name, "Skipped", "already so"))
            continue
        if index > 1 and pace > 0:
            sleep(pace)
        try:
            outcome = save(api, sheet, item.ident, own, loaded=item.values, choices=choices)
        except Exception as exc:  # noqa: BLE001 - one failure never stops the rest
            results.append(BatchResult(item.name, "Failed", str(exc)))
            continue
        if outcome.conflicts:
            names = ", ".join(c.label.lower() for c in outcome.conflicts)
            results.append(
                BatchResult(item.name, "Failed", f"changed on GitHub meanwhile: {names}")
            )
            continue
        if done is not None and outcome.done:
            done(item, outcome.done)
        if outcome.ok:
            results.append(BatchResult(item.name, "Done", sentence(item.name, outcome)))
        else:
            results.append(BatchResult(item.name, "Failed", sentence(item.name, outcome)))
    return results


def results_text(results: Sequence[BatchResult]) -> str:
    """Copy Results: one line per item, then the totals."""
    lines = [result.row() for result in results]
    totals = {
        status: sum(1 for r in results if r.status == status)
        for status in ("Done", "Skipped", "Failed")
    }
    lines.append(", ".join(f"{count} {status.lower()}" for status, count in totals.items()))
    return "\n".join(lines)
