"""What QUILL's multi-file document jobs end with: Save All and Batch Conversion.

The family's "actual result, said once" (FUX-04, ``docs/design/fux-04-adoption.md``).
A single save already ends with :func:`quill.core.action_feedback.saved_result`;
this module builds the sentences for the two jobs that write many files at once,
from the same pieces, so they say what is now true rather than what was tried:

* **Save All** said "Saved all documents" when nothing needed saving, and "Save
  all cancelled" when it stopped part way -- which left out the only facts
  anybody could act on: which documents were saved, which one it stopped at,
  and how many are still unsaved.
* **Batch Conversion** said how many files converted and then opened the
  Application Status window over whatever was being written. The sentence now
  says where the converted files are and which files failed; the full list goes
  to Activity (Shift+F9), not to a window that takes focus.

Two files with the same name are told apart by their folders
(:func:`distinct_names`), because "Saved notes.md and notes.md" is no answer.
wx-free and pure.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from pathlib import PurePath
from typing import TYPE_CHECKING

from quill.core.action_feedback import place_of, saved_result

if TYPE_CHECKING:
    from quill.core.batch_convert import BatchReport

__all__ = [
    "batch_conversion_details",
    "batch_conversion_folder",
    "batch_conversion_result",
    "distinct_names",
    "joined",
    "save_all_result",
]

#: How many file names a spoken sentence lists before saying "and N more".
NAMED_LIMIT = 3


def distinct_names(paths: Sequence[PurePath]) -> list[str]:
    """Each file's name, with its folder when another file has the same name."""
    counts = Counter(path.name.lower() for path in paths)
    return [place_of(path) if counts[path.name.lower()] > 1 else path.name for path in paths]


def joined(names: Sequence[str], *, limit: int = NAMED_LIMIT) -> str:
    """``a, b and c``; past *limit* names, ``a, b, c and 2 more``."""
    shown = list(names[:limit])
    rest = len(names) - len(shown)
    if rest > 0:
        return ", ".join(shown) + f" and {rest} more"
    if len(shown) <= 1:
        return "".join(shown)
    return ", ".join(shown[:-1]) + f" and {shown[-1]}"


def _documents(count: int) -> str:
    return "1 document" if count == 1 else f"{count} documents"


def save_all_result(saved: Sequence[PurePath], *, stopped_at: str = "", left: int = 0) -> str:
    """What Save All ends with: what it saved, and where it stopped if it did.

    *stopped_at* names the document whose save was cancelled or failed (its own
    failure has already been said); *left* counts the unsaved documents after it
    that Save All never reached.
    """
    if not saved and not stopped_at:
        return "Nothing needed saving."
    parts: list[str] = []
    if len(saved) == 1:
        parts.append(saved_result(saved[0]))
    elif saved:
        parts.append(f"Saved {_documents(len(saved))}: {joined(distinct_names(saved))}.")
    if stopped_at:
        parts.append(f"Stopped at {stopped_at}, which is not saved.")
        if left:
            verb = "is" if left == 1 else "are"
            parts.append(f"{left} more {verb} not saved.")
    return " ".join(parts)


def _files(count: int) -> str:
    return "1 file" if count == 1 else f"{count} files"


def batch_conversion_folder(report: BatchReport) -> PurePath:
    """The one folder that holds the converted files, else the folder converted."""
    folders = {entry.output.parent for entry in report.entries if entry.success and entry.output}
    if len(folders) == 1:
        return next(iter(folders))
    return report.plan.root


#: The reasons :func:`quill.core.batch_convert.run_batch` gives a skipped file.
_SKIPPED_REASONS = frozenset({
    "Output already exists; overwrite policy is 'never'.",
    "User declined to overwrite existing file.",
})


def _failed_sources(report: BatchReport) -> list[PurePath]:
    """The files that failed: not skipped, and not the one a cancel stopped in."""
    failed = [e for e in report.entries if not e.success and e.error not in _SKIPPED_REASONS]
    if report.cancelled and len(failed) > report.failed:
        failed = failed[: report.failed]
    return [entry.source for entry in failed]


def batch_conversion_result(report: BatchReport) -> str:
    """One sentence for a finished (or stopped) batch: what converted, where, what did not."""
    total = report.total
    if total <= 0:
        return f"Batch conversion found no files to convert in {report.plan.root.name}."
    converted = report.converted
    if converted == 0:
        head = f"Converted none of the {_files(total)}."
    elif converted == total:
        head = f"Converted {_files(total)}."
    else:
        head = f"Converted {converted} of {total} files."
    parts = [head]
    folders = {e.output.parent for e in report.entries if e.success and e.output}
    if len(folders) == 1:
        pronoun = "It is" if converted == 1 else "They are"
        parts.append(f"{pronoun} in {place_of(next(iter(folders)))}.")
    elif folders:
        parts.append(f"They are in {len(folders)} folders under {report.plan.root.name}.")
    failed = _failed_sources(report)
    if failed:
        parts.append(f"{report.failed} failed: {joined(distinct_names(failed))}.")
    if report.skipped:
        noun = "file was" if report.skipped == 1 else "files were"
        parts.append(f"{report.skipped} skipped, because the converted {noun} already there.")
    if report.cancelled:
        remaining = max(0, total - converted - report.failed - report.skipped)
        parts.append(f"Stopped before the last {_files(remaining)}; they were not converted.")
    return " ".join(parts)


def batch_conversion_details(report: BatchReport) -> str:
    """Every file and what happened to it, with full paths, for Activity's details."""
    lines: list[str] = []
    for entry in report.entries:
        if entry.success and entry.output is not None:
            lines.append(f"Converted: {entry.source} to {entry.output}")
        else:
            lines.append(f"Not converted: {entry.source}: {entry.error or 'no reason given'}")
    return "\n".join(lines)
