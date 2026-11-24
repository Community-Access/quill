"""What a Converter batch ends with: the actual result, said once and kept (FUX-04).

The family UX plan's FUX-04 names "Converter batch" as its first target, and a
batch used to end with "Converted 3 of 5 files. 2 skipped. cancelled." That
told nobody where the three went, what "skipped" meant after a Stop, or how to
finish the job without converting the three again -- pressing Convert a second
time made renamed copies of every file that had already worked.

So, from the same :class:`~quill.core.audio.convert.BatchResult`:

* **Where.** The folder, by its own name and its parent's
  (:func:`quill.core.action_feedback.place_of`); one file names the file too.
* **A Stop says what exists and what does not.** The converted files are kept;
  the file being encoded when Stop was pressed was removed, because FFmpeg
  writes to a temporary file that only a finished encode moves into place.
* **Retry keeps what worked.** The result is kept in Activity with Retry, and
  Retry converts only the files that failed or were not reached, to the same
  names, never the ones that already worked.
* **Names that collide say which.** Two failed ``track01.wav`` files from two
  folders are named with their folders.

wx-free apart from :func:`keep_batch`, which records into the shared Activity
log (:mod:`quill.core.activity`) through the shared action registry.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from quill.core import activity
from quill.core.action_feedback import place_of

__all__ = ["batch_sentence", "file_list", "keep_batch", "left_over", "outcome_of"]

#: How many failed files a spoken sentence names before it says "and N more".
_NAMED = 3


def file_list(paths: Sequence[Path]) -> list[str]:
    """Each file's name, with its folder when another file in the list shares the name."""
    counts = Counter(path.name.lower() for path in paths)
    return [place_of(path) if counts[path.name.lower()] > 1 else path.name for path in paths]


def left_over(result: Any) -> list[Any]:
    """The jobs that did not produce a file: failed, or not reached before a Stop."""
    return [item.job for item in result.results if not item.ok]


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _failed_clause(result: Any) -> str:
    names = file_list([item.job.source for item in result.failed])
    shown = ", ".join(names[:_NAMED])
    if len(names) > _NAMED:
        shown += f" and {len(names) - _NAMED} more"
    return f"{len(names)} failed: {shown}."


def batch_sentence(
    result: Any, total: int, dest: Path, *, notes: str = "", activity_key: str = ""
) -> str:
    """The one sentence a batch ends with. See the module docstring."""
    done = result.converted
    failed = len(result.failed)
    left = len(left_over(result))
    not_reached = left - failed
    folder = place_of(dest)
    if result.cancelled:
        head = (
            f"Stopped. Converted {done} of {total} files into the folder {folder}; they are kept."
            if done
            else "Stopped. No file was converted."
        )
    elif done == total == 1:
        job = next(item.job for item in result.results if item.ok)
        head = f"Converted {job.source.name} to {place_of(job.dest)}."
    elif done == total:
        head = f"Converted all {total} files into the folder {folder}."
    elif done:
        head = f"Converted {done} of {total} files into the folder {folder}."
    else:
        head = (
            "The file was not converted."
            if total == 1
            else f"None of the {total} files was converted."
        )
    parts = [head]
    if failed:
        parts.append(_failed_clause(result))
    if not_reached:
        verb = "was" if not_reached == 1 else "were"
        parts.append(
            f"{_plural(not_reached, 'file')} {verb} not converted, "
            "and nothing half-finished was left behind."
        )
    if notes:
        parts.append(notes)
    if left:
        where = f"Retry in Activity ({activity_key})" if activity_key else "Retry in Activity"
        parts.append(f"{where} converts only the {_plural(left, 'file')} left.")
    if failed:
        parts.append("Press Ctrl+R for the report.")
    return " ".join(parts)


def outcome_of(result: Any) -> str:
    """The Activity outcome: done, partly done, cancelled or failed."""
    if result.cancelled:
        return activity.PARTIAL if result.converted else activity.CANCELLED
    if not left_over(result):
        return activity.COMPLETED
    return activity.PARTIAL if result.converted else activity.FAILED


def keep_batch(
    summary: str,
    result: Any,
    dest: Path,
    *,
    retry: Callable[[], str | None] | None,
    open_folder: Callable[[], str | None],
) -> activity.ActionResult:
    """Keep the batch's result in Activity, with Open Folder and Retry where they apply.

    Already spoken by the caller (with ``force``), so it is recorded and not
    said again (GATE-13). Retry is offered only while something is left over.
    """
    from quill.ui.activity_window import register_actions

    actions: dict[str, Callable[[], str | None]] = {}
    next_actions: list[activity.NextAction] = []
    if left_over(result) and retry is not None:
        next_actions.append(activity.RETRY)
        actions[activity.RETRY.id] = retry
    if result.converted:
        next_actions.append(activity.OPEN_FOLDER)
        actions[activity.OPEN_FOLDER.id] = open_folder
    kept = activity.ActionResult(
        action="Convert",
        object_name=place_of(dest),
        outcome=outcome_of(result),
        summary=summary,
        next_actions=tuple(next_actions),
    )
    activity.LOG.record(kept)
    if actions:
        register_actions(kept, actions)
    return kept
