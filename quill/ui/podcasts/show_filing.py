"""Move or copy a placement without creating a second subscription."""

from __future__ import annotations

from collections.abc import Callable

from quill.core.podcasts import folder_membership
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.folder_picker_dialog import FolderPickerDialog


def file_show(
    parent: object,
    library: PodcastLibrary,
    show: PodcastShow,
    *,
    source_folder_id: str | None,
    copy: bool = False,
    announce: Callable[[str], None],
    on_library_changed: Callable[[], None] | None = None,
) -> bool:
    action = "Copy" if copy else "Move"
    picker = FolderPickerDialog(
        parent,
        library=library,
        title=f"{action} {show.title} to Folder",
        action_label=f"&{action} Here",
        announce_cb=announce,
        on_library_changed=on_library_changed,
    )
    result = picker.show()
    if not result.confirmed:
        return False
    if library.find_show(show.id) is not show:
        announce("That podcast is no longer followed.")
        return False
    try:
        changed = (
            folder_membership.copy_to(library, show, result.folder_id)
            if copy
            else folder_membership.move_to(library, show, result.folder_id, source=source_folder_id)
        )
    except ValueError as error:
        announce(str(error))
        return False
    if not changed:
        announce("The podcast is already in that folder.")
        return False
    folder = library.find_folder(result.folder_id) if result.folder_id else None
    destination = folder.name if folder is not None else "the top level"
    announce(f"{'Copied' if copy else 'Moved'} {show.title} to {destination}.")
    return True
