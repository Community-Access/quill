"""Opening the episode-notes list, from either surface (x.md item 11).

Two surfaces reach the same list and they used to build it separately:

* the **Podcast Manager**, where you pick an episode and open its notes from
  a context menu -- the only route that existed;
* the **player**, acting on whatever is playing -- the route item 11 adds,
  because a note is a thing you make *while listening*, so needing to leave
  the player, find the episode in a tree and open a context menu to read your
  notes back was the wrong shape entirely.

Keeping both here means the two answer with the same wording, offer the same
Copy Note text, and cannot drift apart. It is also what GATE-11 asks for
rather than merely permits: the player route came to about fifty lines, and
``main_frame_podcasts.py`` and ``manager_phase4.py`` were both at their
budgets -- so the code went to a new module and both hosts got *smaller*.

The two differ in exactly one way, and it is a real difference rather than an
accident: from the Manager you may open the notes of an episode that is **not
playing**, so jumping to a note has to start that episode first. From the
player, the episode is by definition already playing, so it only seeks.
"""

from __future__ import annotations

from typing import Any


def _open(
    parent: Any,
    *,
    show_id: str,
    episode_guid: str,
    episode_title: str,
    show_title: str,
    audio_url: str,
    announce: Any,
) -> int | None:
    """Build and show the list. Returns the chosen position, or None."""
    from quill.core.podcasts.episode_notes import (
        delete_episode_note,
        load_episode_notes,
        notes_for_episode,
    )
    from quill.ui.podcasts.episode_notes_dialog import EpisodeNotesDialog

    notes = notes_for_episode(load_episode_notes(), show_id, episode_guid)
    dialog = EpisodeNotesDialog(
        parent,
        show_id=show_id,
        episode_guid=episode_guid,
        episode_title=episode_title,
        notes=notes,
        on_delete=delete_episode_note,
        announce_cb=announce,
        show_title=show_title,
        audio_url=audio_url,
    )
    return dialog.show()


def spoken_position(position_ms: int) -> str:
    """ "12 minutes 34 seconds" -- never "12:34".

    Read aloud, a colon-separated pair is ambiguous unless you already know it
    is a time. The written ``m:ss`` form is fine in the list and on the
    clipboard, where there are surrounding words; an announcement is not.
    """
    minutes, seconds = divmod(max(0, position_ms) // 1000, 60)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour{'' if hours == 1 else 's'}")
    if minutes:
        parts.append(f"{minutes} minute{'' if minutes == 1 else 's'}")
    parts.append(f"{seconds} second{'' if seconds == 1 else 's'}")
    return " ".join(parts)


def open_for_playing_episode(host: Any) -> None:
    """My Notes in This Episode..., for whatever is playing.

    Nothing playing means there is no episode to have notes about, and no
    notes yet means an empty list would tell the listener nothing -- both say
    so instead, and the second points at the command that makes one.
    """
    controller = host._podcast_controller
    state = controller.state
    if not state.show_id or not state.episode_guid:
        host._announce("Nothing is playing, so there are no episode notes to show.")
        return

    from quill.core.podcasts.episode_notes import load_episode_notes, notes_for_episode

    if not notes_for_episode(load_episode_notes(), state.show_id, state.episode_guid):
        host._announce("No notes in this episode yet. Add one with Podcasts: Add Episode Note.")
        return

    show = host._podcast_library.find_show(state.show_id)
    episode = show.find_episode(state.episode_guid) if show is not None else None
    jump_ms = _open(
        host.frame,
        show_id=state.show_id,
        episode_guid=state.episode_guid,
        episode_title=state.title or str(getattr(episode, "title", "")),
        show_title=str(getattr(show, "title", "")),
        audio_url=str(getattr(episode, "audio_url", "")),
        announce=host._announce,
    )
    if jump_ms is None:
        return
    controller.seek(jump_ms)
    host._announce(f"Jumped to your note at {spoken_position(jump_ms)}")


def open_for_episode(dialog: Any, show: Any, episode: Any) -> None:
    """The Manager's route: the notes of the episode you selected.

    The selected episode need not be the playing one, so a jump starts it
    before seeking -- otherwise the position would land in whatever else
    happened to be playing.
    """
    jump_ms = _open(
        dialog.dialog,
        show_id=show.id,
        episode_guid=episode.guid,
        episode_title=episode.title,
        show_title=show.title,
        audio_url=episode.audio_url,
        announce=dialog._announce,
    )
    if jump_ms is None:
        return
    if dialog._controller.state.episode_guid != episode.guid:
        dialog._play_pair(show, episode)
    dialog._controller.seek(jump_ms)
    dialog._announce(f"Jumped to note at {spoken_position(jump_ms)}")


__all__ = ["open_for_episode", "open_for_playing_episode", "spoken_position"]
