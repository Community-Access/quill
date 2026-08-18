"""Subscription-library verbs on the browse tree's podcast rows.

Extracted from ``browse_tree_menu`` under GATE-11 the day they were written:
folders, OPML import, and Mark All as Played are one concern -- the shared
podcast library, edited from Radio -- and the menu module stays what it was,
a map from action ids to handlers.

Every confirmation goes through :func:`quill.ui.dialog_contract.show_message_box`
so the question is announced and parented correctly (GATE-16), and every
outcome is spoken in the words the wx-free core helpers return -- the same
sentences the unit tests pin.
"""

from __future__ import annotations

from typing import Any


def new_podcast_folder(dialog: Any, kind: str, args: list[str]) -> None:
    """New Folder... on the Subscriptions root, or inside a library folder."""
    wx = dialog._wx
    parent_id = args[0] if kind == "mypodcastfolder" and args else None
    with wx.TextEntryDialog(  # dialog_button_contract: exempt
        dialog._win, "Folder name:", "New Folder"
    ) as entry:
        if entry.ShowModal() != wx.ID_OK:
            return
        name = entry.GetValue()
    from quill.core.paths import app_data_dir
    from quill.core.radio.podcast_follow import create_podcast_folder

    dialog._announce(create_podcast_folder(app_data_dir(), name, parent_folder_id=parent_id))
    dialog._refresh_selected()


def rename_podcast_folder(dialog: Any, args: list[str]) -> None:
    wx = dialog._wx
    if not args:
        return
    current = dialog._tree.GetItemText(dialog._tree.GetSelection()).split(" (")[0]
    with wx.TextEntryDialog(  # dialog_button_contract: exempt
        dialog._win, "New name:", "Rename Folder", value=current
    ) as entry:
        if entry.ShowModal() != wx.ID_OK:
            return
        name = entry.GetValue()
    from quill.core.paths import app_data_dir
    from quill.core.radio.podcast_follow import rename_podcast_folder as rename_op

    dialog._announce(rename_op(app_data_dir(), args[0], name) + " Refresh Podcasts to update.")


def delete_podcast_folder(dialog: Any, args: list[str]) -> None:
    wx = dialog._wx
    if not args:
        return
    from quill.ui.dialog_contract import show_message_box

    name = dialog._tree.GetItemText(dialog._tree.GetSelection()).split(" (")[0]
    answer = show_message_box(
        f"Delete the folder {name}? Its podcasts and subfolders move up a "
        "level; nothing is unsubscribed.",
        "Delete Folder",
        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        dialog._win,
        announce=dialog._announce,
    )
    if answer != wx.YES:
        return
    from quill.core.paths import app_data_dir
    from quill.core.radio.podcast_follow import delete_podcast_folder as delete_op

    dialog._announce(delete_op(app_data_dir(), args[0]) + " Refresh Podcasts to update.")


def move_show_to_folder(dialog: Any, args: list[str]) -> None:
    """Move to Folder... -- Quill Cast's own picker over the same library."""
    if not args:
        return
    from quill.core.paths import app_data_dir
    from quill.core.podcasts.subscriptions import load_library
    from quill.core.radio.podcast_follow import move_show_to_folder as move_op
    from quill.ui.podcasts.folder_picker_dialog import FolderPickerDialog

    library = load_library(app_data_dir())
    show = library.find_show_by_feed_url(args[0])
    title = show.title if show is not None else "this show"
    picker = FolderPickerDialog(
        dialog._win,
        library=library,
        title=f"Move {title} to Folder",
        announce_cb=dialog._announce,
    )
    result = picker.show()
    if not result.confirmed:
        return
    dialog._announce(
        move_op(app_data_dir(), args[0], result.folder_id) + " Refresh Podcasts to update."
    )


def mark_all_played(dialog: Any, args: list[str]) -> None:
    """Mark All as Played..., confirmed -- the same verb and the same shared
    state as Quill Cast's Episode menu, so the badge clears in both apps."""
    wx = dialog._wx
    if not args:
        return
    from quill.core.paths import app_data_dir
    from quill.core.radio.podcast_follow import mark_show_played, unheard_for_feed
    from quill.ui.dialog_contract import show_message_box

    count = unheard_for_feed(app_data_dir(), args[0])
    name = dialog._tree.GetItemText(dialog._tree.GetSelection()).split(" (")[0]
    answer = show_message_box(
        f"Mark all {count} unplayed episode(s) of {name} as played?",
        "Mark All as Played",
        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        dialog._win,
        announce=dialog._announce,
    )
    if answer != wx.YES:
        return
    dialog._announce(mark_show_played(app_data_dir(), args[0]) + " Refresh Podcasts to update.")


def import_opml(dialog: Any) -> None:
    """Import Podcasts from OPML... on the Podcasts branch itself.

    The parse/plan/apply runs off the UI thread -- a two-thousand-line file
    must not freeze the tree -- and the outcome is spoken in full.
    """
    wx = dialog._wx
    if dialog._safe_mode:
        dialog._announce("Importing is disabled in Safe Mode. Restart Quill Radio normally.")
        return
    with wx.FileDialog(  # dialog_button_contract: exempt
        dialog._win,
        "Import Podcasts from OPML",
        wildcard="OPML files (*.opml;*.xml)|*.opml;*.xml|All files (*.*)|*.*",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as chooser:
        if chooser.ShowModal() != wx.ID_OK:
            return
        path = chooser.GetPath()
    dialog._announce("Importing podcasts...")

    def _work(**_kwargs: Any) -> str:
        from quill.core.paths import app_data_dir
        from quill.core.podcasts.opml_import import import_opml_file

        return import_opml_file(app_data_dir(), path).spoken

    def _ok(_op: str, spoken: object) -> None:
        dialog._announce(f"{spoken} Refresh Podcasts to see them.")

    def _failed(_op: str, error: object) -> None:
        dialog._announce(f"That file could not be imported. {error}")

    dialog._task_manager.submit("radio-opml-import", _work, on_success=_ok, on_failure=_failed)
