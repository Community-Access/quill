"""Saying what a delete deletes, before it deletes it (ear.md R13).

Remove Downloaded Copy removes the file Cast fetched, keeps the episode, and can
fetch it again. That is easy to be relaxed about. For a **local** show it is the
same verb over very different ground: Cast *copied* the listener's file into its
own folder when they imported it, so "delete" there means deleting Cast's copy
while the original sits exactly where they left it -- and somebody who cannot see
a file manager to check has no way to know that unless the app says it.

So the message names the file and states what survives:

    Delete Cast's copy of "Interview with Ada"?
    The original file stays where it was.

versus, for a downloaded episode:

    Delete the downloaded copy of "Interview with Ada"?
    It stays in your library and can be downloaded again.

Two other things a delete must do and used to leave behind: **stop it if it is
playing** -- the file is about to vanish from under the player -- and **clear its
position**, because a resume point into a file that no longer exists is a promise
the app cannot keep. For a local file that position is the only record of where
the listener was, and leaving it would make the next import silently resume into
the middle.

wx-free, strict-typed, pure. Deleting the file itself stays in ``retention``; this
decides the words and the tidying.
"""

from __future__ import annotations

from typing import Any

__all__ = ["confirm_message", "forget_position", "is_cast_copy"]


def is_cast_copy(show: Any) -> bool:
    """Whether the file was copied in from the listener's own disk.

    A local show's audio came from somewhere else and still exists there; a
    subscribed show's came off the internet and can come again. The two need
    different sentences, and this is the only thing that distinguishes them.
    """
    return bool(getattr(show, "is_local", False))


def confirm_message(show: Any, episode: Any) -> str:
    """What to ask before deleting this episode's file.

    Names the episode, because a confirmation that says "this episode" is one the
    listener has to take on trust about which row they were on.
    """
    title = str(getattr(episode, "title", "") or "this episode").strip()
    if is_cast_copy(show):
        return (
            f'Delete Cast\'s copy of "{title}"?\n\n'
            "The original file stays where it was. Only the copy Cast made when "
            "you imported it is deleted."
        )
    return (
        f'Delete the downloaded copy of "{title}"?\n\n'
        "It stays in your library and can be downloaded again."
    )


def forget_position(episode: Any) -> bool:
    """Clear the resume point. Returns whether there was one.

    A position into a file that no longer exists is a promise the app cannot
    keep, and for a local file it is the *only* record of where the listener was
    -- leaving it would make a later re-import silently resume into the middle of
    something they thought they were starting.
    """
    had = int(getattr(episode, "position_ms", 0) or 0) > 0
    episode.position_ms = 0
    episode.position_updated_at = ""
    return had
