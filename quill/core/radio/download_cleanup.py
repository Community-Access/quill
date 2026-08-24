"""Removing a show's downloaded episode files. The one place that deletes.

Quill Radio files a podcast episode's download under
``<root>\\Podcasts\\<Show>\\`` (see :mod:`download_prefs`); this module is the
symmetric verb -- count what is there, and take it away on request. Deliberate
rules:

* **Only inside the show's own folder**, resolved through the same
  ``download_prefs`` path logic that wrote the files -- never a caller-supplied
  path, so a bug upstream cannot aim the delete anywhere else.
* **Files only, then the folder if it emptied.** A subfolder someone made by
  hand inside the show's folder is not ours and is left standing (and keeps
  the folder alive), on the never-assume rule.
* **The library is untouched.** Subscription, played state, positions --
  removing the copies changes what is on disk, not what was heard.

wx-free, strict-typed. Never raises: a half-finished cleanup reports what it
did, because "Removed 12 files" and silence are different answers.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.radio import download_prefs


def show_download_dir(data_dir: Path, show_title: str) -> Path:
    """Where this show's episode downloads live (existing or not)."""
    prefs = download_prefs.load(data_dir)
    return (
        download_prefs.resolved_root(prefs)
        / download_prefs.FOLDER_PODCASTS
        / download_prefs.safe_segment(show_title)
    )


def downloaded_file_count(data_dir: Path, show_title: str) -> int:
    """Files in the show's downloads folder (a local read; 0 when absent).

    Counts every regular file including ``.part`` remnants and licence
    sidecars -- Remove All Downloads takes all of them, so the count and the
    verb agree.
    """
    if not (show_title or "").strip():
        return 0
    try:
        folder = show_download_dir(data_dir, show_title)
        return sum(1 for entry in folder.iterdir() if entry.is_file())
    except OSError:
        return 0


def remove_show_downloads(
    data_dir: Path,
    show_title: str,
    *,
    take: Callable[[list[Path]], int] | None = None,
) -> str:
    """Delete every downloaded file for *show_title*. Returns the sentence.

    The folder itself is removed only when the delete emptied it.

    *take* is how the files leave: given the whole list, it returns how many
    it took responsibility for. It exists so one step of undo can move them
    aside instead of unlinking them (:func:`quill.ui.undo_last_ui.hold_or_delete`)
    without this module learning what an undo is. Default: unlink, exactly as
    before.
    """
    if not (show_title or "").strip():
        return "There is nothing downloaded for that show."
    folder = show_download_dir(data_dir, show_title)
    removed = failed = 0
    try:
        entries = list(folder.iterdir())
    except OSError:
        return "There is nothing downloaded for that show."
    files = [entry for entry in entries if entry.is_file()]
    if take is not None:
        removed = take(files)
        failed = len(files) - removed
    else:
        for entry in files:
            try:
                entry.unlink()
                removed += 1
            except OSError:
                failed += 1
    try:
        if not any(folder.iterdir()):
            folder.rmdir()
    except OSError:
        pass
    if not removed and not failed:
        return "There is nothing downloaded for that show."
    spoken = f"Removed {removed} downloaded file{'s' if removed != 1 else ''}."
    if failed:
        spoken += f" {failed} could not be removed (a file may be open in another program)."
    return spoken
