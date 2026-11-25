"""F1 on Quill Converter's queue: what happened to the selected file last time (FUX-10).

The queue keeps its rows after a run, but each file's result went only into
the Ctrl+R report, so a row read the same whether it converted, failed or was
skipped when you pressed Stop. The last run's results are now kept, and F1 on
the queue says the selected row's: converted to which file, failed and why,
or skipped. A folder row counts the files from inside it, and a file Split by
Chapters cut into parts says how many.

Registered on the queue when a run finishes, because before the first run
there is nothing to say; asked only when F1 is pressed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["describe_selected_row", "remember"]


def remember(host: Any, results: list[Any]) -> None:
    """Keep the last run's results by source file, and give the queue its F1 paragraph."""
    from quill.ui import app_context_help

    grouped: dict[Path, list[Any]] = {}
    for item in results:  # Split by Chapters makes many jobs from one source
        grouped.setdefault(Path(item.job.source), []).append(item)
    host._last_results = grouped
    app_context_help.set_selection_help(host._list, lambda: describe_selected_row(host))


def _sentence(text: str) -> str:
    """*text* ending in exactly one full stop, so the next sentence does not run on."""
    return text.strip().rstrip(".") + "."


def _file_sentence(item: Any) -> str:
    if item.skipped:
        return "Last time, this file was skipped, because the conversion was stopped."
    if item.ok:
        said = f"Last time, this file converted to {Path(item.job.dest).name}."
        return f"{said} {_sentence(item.error)}" if item.error else said  # a note
    reason = item.error.strip().rstrip(".") or "no reason was given"
    return f"Last time, this file failed: {reason}. Ctrl+R has the full report."


def _counts(items: list[Any]) -> tuple[str, str]:
    converted = sum(1 for item in items if item.ok and not item.skipped)
    skipped = sum(1 for item in items if item.skipped)
    failed = len(items) - converted - skipped
    counts = [f"{converted} converted"]
    if failed:
        counts.append(f"{failed} failed")
    if skipped:
        counts.append(f"{skipped} skipped")
    return ", ".join(counts), " Ctrl+R has the full report." if failed else ""


def _folder_sentence(items: list[Any]) -> str:
    counts, tail = _counts(items)
    return f"Last time, of the files in this folder: {counts}.{tail}"


def _split_sentence(items: list[Any]) -> str:
    counts, tail = _counts(items)
    return f"Last time, this file was split into {len(items)} parts: {counts}.{tail}"


def describe_selected_row(host: Any) -> str:
    """The selected queue row's last result, or "" when it was not in the last run."""
    from quill.core import converter_queue

    results: dict[Path, list[Any]] = getattr(host, "_last_results", {}) or {}
    index = host._list.GetSelection()
    if not 0 <= index < len(host._entries):
        return ""
    raw = host._entries[index]
    row = converter_queue.as_entry(raw)
    entry = row.source
    inside = [
        item for source, items in results.items() if entry in source.parents for item in items
    ]
    if inside:
        return _folder_sentence(inside)
    own = results.get(entry, [])
    if len(own) > 1:
        return _split_sentence(own)
    if own:
        return _file_sentence(own[0])
    if isinstance(raw, converter_queue.ConverterQueueEntry) and not row.available:
        reason = "is missing" if row.missing else "is no longer the same kind of item"
        kind = "folder" if row.is_folder else "file"
        return (
            f"This queued {kind} {reason}. It remains in the queue; remove it or "
            "make the drive or file available again."
        )
    return ""
