"""Where the playing episode came from, as one line (ear.md R6).

A listener who cannot see the window has no way to tell whether "next" means the
rest of the queue, the rest of a folder, or nothing at all -- and those are three
different evenings. The Player Information report gains one line that says it:

    Playing from: News > Mornings
    Playing from: the queue
    Playing from: the Inbox

**It is a line in a report, never an announcement.** Speaking it on every
episode start would be the textbook GATE-13 violation: the source did not change
between episode four and episode five of the same folder run, so saying it again
tells the listener nothing they did not already know and costs them a sentence
they cannot skip.

The folder path is built from the folder tree rather than stored, so it cannot go
stale when a folder is renamed or moved.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from typing import Any

__all__ = ["QUEUE", "folder_path", "playing_from"]

#: What the queue is called in this line. Lower case and with the article,
#: because the line reads as a sentence: "Playing from: the queue".
QUEUE = "the queue"
INBOX = "the Inbox"


def folder_path(library: Any, folder_id: str, *, separator: str = " > ") -> str:
    """``"News > Mornings"`` for a nested folder, or ``""`` when there is none.

    Walks up ``parent_folder_id`` and stops at the first missing link, so a
    folder whose parent was deleted still names itself rather than returning
    nothing. A cycle -- which a hand-edited file could contain -- is bounded by
    the number of folders, never by recursion.
    """
    names: list[str] = []
    seen: set[str] = set()
    current = folder_id
    limit = len(getattr(library, "folders", []) or []) + 1
    while current and current not in seen and len(names) <= limit:
        seen.add(current)
        folder = library.find_folder(current)
        if folder is None:
            break
        names.append(folder.name)
        current = getattr(folder, "parent_folder_id", "") or ""
    return separator.join(reversed(names))


def playing_from(library: Any, show: Any, *, from_queue: bool = False) -> str:
    """The source line's value, or ``""`` when there is nothing useful to say.

    *from_queue* wins over the folder, because it is the more specific answer to
    the question the line exists for: an episode reached through the queue
    continues through the queue whatever folder its show happens to live in.

    Returns ``""`` rather than "nowhere" when the show is unfiled and the queue
    is not involved -- a report line that says nothing should not be printed at
    all, and the caller drops an empty string.
    """
    if from_queue:
        return QUEUE
    if show is None:
        return ""
    if getattr(show, "route_to_inbox", False):
        return INBOX
    return folder_path(library, getattr(show, "folder_id", "") or "")
