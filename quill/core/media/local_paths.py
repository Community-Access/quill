"""Where a remembered file actually is, on *this* machine.

:mod:`quill.core.media.positions` keys a saved place on the file's **contents**,
so your place survives moving, renaming, and a different operating system --
which is exactly right, and is why it deliberately stores no path. A path is a
fact about one machine, and putting one in a record that syncs would leak
somebody's folder layout to every other device they own.

But *Continue Listening* needs a path. Knowing you are two hours into something
called ``Middlemarch, chapter 4`` is no use if nothing can open it.

So: a **local-only sidecar**, never synced, mapping a content id to the last
place that file was seen. It is a hint and it is treated as one -- a stale entry
is simply dropped when the file is no longer there, because a resume list
offering things that cannot be opened is worse than a shorter list.

Why not just add a path field to the position record? Because the position
record travels. This file does not, will not, and is not merged: two machines
disagreeing about where a file lives is not a conflict to resolve, it is two
correct answers.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
from pathlib import Path

from quill.core.storage import write_json_atomic

_FILENAME = "media_paths.json"

#: A cap, because this grows with every file ever played and is only a hint.
#: Oldest entries fall off first; losing one costs a row in a list, nothing more.
MAX_ENTRIES = 2000


def sidecar_path(data_dir: Path | str) -> Path:
    return Path(data_dir) / _FILENAME


def _read(data_dir: Path | str) -> dict[str, str]:
    try:
        raw = json.loads(sidecar_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}


def remember(data_dir: Path | str, media_id: str, path: Path | str) -> None:
    """Note where *media_id* was last seen. Best effort; never raises."""
    if not media_id:
        return
    entries = _read(data_dir)
    entries[media_id] = str(path)
    if len(entries) > MAX_ENTRIES:
        # dicts keep insertion order, so the oldest are simply the first.
        entries = dict(list(entries.items())[-MAX_ENTRIES:])
    try:
        write_json_atomic(sidecar_path(data_dir), entries)
    except (OSError, TypeError, ValueError):
        return


def path_for(data_dir: Path | str, media_id: str) -> Path | None:
    """Where that file was last seen, if it is still there.

    A path that no longer exists returns ``None`` rather than being offered and
    then failing -- the file may have been moved, and the *position* is still
    perfectly good; it will be found again the next time the file is played.
    """
    if not media_id:
        return None
    raw = _read(data_dir).get(media_id, "")
    if not raw:
        return None
    path = Path(raw)
    try:
        return path if path.is_file() else None
    except OSError:
        return None


def forget(data_dir: Path | str, media_id: str) -> bool:
    """Drop one hint, when its file has gone for good."""
    entries = _read(data_dir)
    if entries.pop(media_id, None) is None:
        return False
    try:
        write_json_atomic(sidecar_path(data_dir), entries)
    except (OSError, TypeError, ValueError):
        return False
    return True
