"""Is this row already saved on disk, and where?

:mod:`download_prefs` decides where a download *goes* and
:mod:`download_cleanup` removes a whole show's worth. Between them sat a
question nothing could answer: **is this one episode already downloaded?**
Without it the menu offered *Download...* on a file that was already there,
had no way to remove just that one, and could not tell a listener that the
copy in front of them is local -- so a saved episode looked exactly like an
unsaved one right up until it was downloaded twice.

The answer comes from the disk, not from a database. There is no index and no
scan on startup: the folder **is** the record, exactly as
:mod:`downloaded_books` reads a book back. Somebody who deletes a file by hand
has un-downloaded that episode, and the next menu agrees with them.

The path is rebuilt through the same ``download_prefs`` planning that wrote it,
so this cannot drift from where downloads actually land. The one place it can
disagree -- an author-grouped book folder, whose name depends on how many works
that author had *at the time* -- is covered by also looking for the file under
the show/work folder directly.

wx-free, strict-typed. Reads directory entries; never writes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _candidate_folders(data_dir: Path, station: Any, *, group: str, author: str) -> list[Path]:
    """Every folder this row's file could reasonably be in, best guess first."""
    from quill.core.radio import download_prefs

    prefs = download_prefs.load(data_dir)
    planned = download_prefs.plan_destination(
        prefs,
        source=str(getattr(station, "source", "") or ""),
        work=group,
        author=author,
        existing_authors={},
    )
    folders = [planned]
    if author:
        # The author-grouping decision depends on how many works that author
        # already had when the file was written, so the ungrouped shape is a
        # real second home rather than a hypothetical one.
        root = download_prefs.resolved_root(prefs)
        folders.append(root / download_prefs.FOLDER_BOOKS / download_prefs.safe_segment(group))
    return folders


def downloaded_path(
    data_dir: Path,
    station: Any,
    *,
    group: str = "",
    author: str = "",
) -> Path | None:
    """The saved copy of *station*, or ``None`` when there is not one.

    *group* is the show or book the row belongs to -- the same value the
    download was filed under, so the lookup and the write agree.
    """
    from quill.core.radio import downloadable

    if not str(getattr(station, "stream_url", "") or "").strip():
        return None
    name = downloadable.suggested_filename(station)
    for folder in _candidate_folders(data_dir, station, group=group, author=author):
        try:
            candidate = folder / name
            if candidate.is_file():
                return candidate
        except OSError:  # an unreadable or impossible path is simply not a hit
            continue
    return None


def is_downloaded(data_dir: Path, station: Any, *, group: str = "", author: str = "") -> bool:
    """Whether this row has a saved copy. Never raises."""
    try:
        return downloaded_path(data_dir, station, group=group, author=author) is not None
    except Exception:  # noqa: BLE001 - a menu must never fail on a disk probe
        return False


def remove_download(
    data_dir: Path,
    station: Any,
    *,
    group: str = "",
    author: str = "",
) -> str:
    """Delete this row's saved copy and say what happened.

    The sidecar licence note goes with it -- a licence file for audio that is
    no longer there is litter that outlives what it describes. The folder is
    left standing: the rest of the show is still in it, and an empty one is
    where the next download goes.
    """
    path = downloaded_path(data_dir, station, group=group, author=author)
    if path is None:
        return "That is not downloaded, so there is nothing to remove."
    name = str(getattr(station, "name", "") or path.name)
    try:
        path.unlink()
    except OSError as error:
        return f"{name} could not be removed. {error}"
    sidecar = path.with_suffix(path.suffix + ".licence.txt")
    try:
        if sidecar.is_file():
            sidecar.unlink()
    except OSError:  # the audio is gone, which is what was asked for
        pass
    return f"Removed the download of {name}. It can be played from its source again."
