"""What a folder row can do: play it, queue it, reorder it, export it, set it.

The UI half of :mod:`quill.core.podcasts.folder_actions`. The rules are there
and pure; here are the queue writes, the file dialog, and the sentences.

**Nothing starts silently.** Play All says how many it queued and what is
playing; a reorder says the new position ("News, 2 of 5"); an export says how
many shows went and to what file. A folder action that happened invisibly is one
somebody has to go and verify.

**Folder settings apply at save time, not at read time.** Choosing a queue-age
limit for a folder writes that value into every member show's own override, and
then the folder forgets it. One inheritance chain, not two: the effective
setting for a show is what ``PodcastLibrary.effective_settings`` has always
said it is, and nothing anywhere has to ask a folder what it thinks.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts import folder_actions

__all__ = [
    "add_folder_to_queue",
    "export_folder_opml",
    "open_folder_settings",
    "play_folder",
    "reorder",
]


def play_folder(dialog: Any, folder_id: str) -> None:
    """Queue one round of what is new in this folder, and start it."""
    library = dialog._library
    pairs = folder_actions.latest_unplayed_per_show(library, folder_id)
    if not pairs:
        dialog._announce("Nothing in that folder is unplayed.")
        return
    from quill.core.podcasts import queue as queue_module

    added = 0
    for show, episode in pairs:
        if queue_module.add_to_queue(library, str(show.id), str(episode.guid)):
            added += 1
    dialog._on_library_changed()
    first_show, first_episode = pairs[0]
    dialog._announce(
        f"Queued {added} episode{'' if added == 1 else 's'}, one from each podcast. "
        f"Playing {first_episode.title} from {first_show.title}."
    )
    play = getattr(dialog, "_play_episode", None)
    if callable(play):
        play(first_show, first_episode)


def add_folder_to_queue(dialog: Any, folder_id: str) -> None:
    """Every unplayed episode in the folder, appended to the queue.

    The whole folder rather than one per show: this is the deliberate version
    of Play All, chosen by somebody who meant it.
    """
    library = dialog._library
    from quill.core.podcasts import queue as queue_module

    added = 0
    for show, episode in folder_actions.unplayed_in_folder(library, folder_id):
        if queue_module.add_to_queue(library, str(show.id), str(episode.guid)):
            added += 1
    if not added:
        dialog._announce("Nothing in that folder is unplayed.")
        return
    dialog._on_library_changed()
    dialog._announce(f"Added {added} episode{'' if added == 1 else 's'} to the queue.")


def reorder(dialog: Any, folder_id: str, delta: int) -> None:
    """Move a folder among its siblings, and say where it now is."""
    library = dialog._library
    position = folder_actions.reorder_folder(library, folder_id, delta)
    folder = library.find_folder(folder_id)
    name = folder.name if folder is not None else "That folder"
    if position < 0:
        dialog._announce(f"{name} is already at the {'end' if delta > 0 else 'start'}.")
        return
    siblings = sum(
        1
        for row in library.folders
        if row.parent_folder_id == (folder.parent_folder_id if folder else None)
    )
    dialog._on_library_changed()
    dialog.refresh_tree()
    dialog._announce(f"{name}, {position + 1} of {siblings}.")


def export_folder_opml(dialog: Any, folder_id: str) -> None:
    """Write this folder and its children out as an OPML file."""
    import wx

    from quill.core.podcasts.opml import export_subtree

    text = export_subtree(dialog._library, folder_id)
    if not text:
        dialog._announce("There is nothing in that folder to export.")
        return
    folder = dialog._library.find_folder(folder_id)
    name = folder.name if folder is not None else "podcasts"
    safe = "".join(c for c in name if c.isalnum() or c in " -_").strip() or "podcasts"
    with wx.FileDialog(
        dialog.dialog,
        f"Export {name} as OPML",
        defaultFile=f"{safe}.opml",
        wildcard="OPML file (*.opml)|*.opml|All files (*.*)|*.*",
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as file_dialog:
        if file_dialog.ShowModal() != wx.ID_OK:
            return
        destination = file_dialog.GetPath()
    from pathlib import Path

    try:
        Path(destination).write_text(text, encoding="utf-8")
    except OSError as error:
        dialog._announce(f"Could not write that file: {error}.")
        return
    count = len(folder_actions.subtree_show_ids(dialog._library, folder_id))
    dialog._announce(
        f"Exported {count} podcast{'' if count == 1 else 's'} to {Path(destination).name}."
    )


def open_folder_settings(dialog: Any, folder_id: str) -> None:
    """Apply a few settings to every show in the folder, once."""
    from quill.ui.podcasts.folder_settings_dialog import FolderSettingsDialog

    library = dialog._library
    folder = library.find_folder(folder_id)
    if folder is None:
        return
    shows = folder_actions.shows_in_folder(library, folder_id)
    if not shows:
        dialog._announce("That folder has no podcasts in it yet.")
        return
    chosen = FolderSettingsDialog(
        dialog.dialog,
        folder_name=folder.name,
        show_count=len(shows),
        announce_cb=dialog._announce,
    ).show()
    if not chosen:
        return
    # Two homes, because the three settings genuinely live in two places:
    # queue expiry and speed are PodcastSettings fields and go through
    # apply_show_override (which clones from whatever is currently effective,
    # so a folder setting never resets the other overrides a show carries);
    # Inbox routing is a field on the show itself.
    routing = chosen.pop("route_to_inbox", None)
    for show in shows:
        if chosen:
            library.apply_show_override(show, **chosen)
        if routing is not None:
            show.route_to_inbox = bool(routing)
    dialog._on_library_changed()
    dialog._announce(f"Applied to {len(shows)} podcast{'' if len(shows) == 1 else 's'}.")
