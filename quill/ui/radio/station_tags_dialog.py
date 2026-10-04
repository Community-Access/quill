"""Edit Station Tags: your own words about a station, so a search can find it.

One labelled box for your tags, comma separated ("Detroit Tigers, MLB,
baseball"), and below it the directory's own tags, read-only, so you can see
what the station is already found by before adding to it. OK saves, Escape or
Cancel leaves everything as it was, and emptying the box removes your tags.

Reached from every place a station is: a Favorites row, a Browse or Search row,
a Find Stations result, and -- for the station you are listening to -- the
Command Palette's "Edit Tags for the Playing Station". Where the tags are kept
(with the favorite, or in a small map of their own) is
:mod:`quill.core.radio.station_tags`'s business; this module only asks.

The announcement says what happened to the tags, never the tags themselves:
the details panel reads them back on the next arrow key, and saying them here
too is the over-announcing GATE-13 exists to stop.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = [
    "TITLE",
    "ask_tags",
    "build_dialog",
    "details_for",
    "edit_playing",
    "edit_row_tags",
    "edit_station_tags",
]

TITLE = "Edit Station Tags"

#: ``ask(parent, station_name, your_tags_text, directory_tags_text)`` returns the
#: typed text, or ``None`` when cancelled. Injected by tests.
AskTags = Callable[[Any, str, str, str], "str | None"]


def build_dialog(parent: Any, station_name: str, current: str, directory: str) -> tuple[Any, Any]:
    """The dialog and its tags box, built but not shown."""
    import wx

    from quill.ui.dialog_contract import apply_modal_ids

    dialog = wx.Dialog(parent, title=TITLE)
    root = wx.BoxSizer(wx.VERTICAL)
    intro = wx.StaticText(
        dialog,
        label=(
            f"Your own tags for {station_name}. A search for any of them finds this "
            "station. Leave the box empty to remove your tags."
        ),
    )
    intro.Wrap(420)
    root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

    root.Add(
        wx.StaticText(dialog, label="&Your tags, separated by commas:"),
        0,
        wx.LEFT | wx.RIGHT,
        10,
    )
    tags_box = wx.TextCtrl(dialog, value=current, size=(420, -1))
    tags_box.SetName("Your tags, separated by commas")
    tags_box.SetHelpText(
        "Words you want to find this station by, separated by commas -- for "
        "example: Detroit Tigers, MLB, baseball. Search and the Favorites filter "
        "match them. Empty the box to remove your tags."
    )
    root.Add(tags_box, 0, wx.EXPAND | wx.ALL, 10)

    root.Add(
        wx.StaticText(dialog, label="&Directory tags (read-only):"),
        0,
        wx.LEFT | wx.RIGHT,
        10,
    )
    directory_box = wx.TextCtrl(
        dialog,
        value=directory or "The directory gave this station no tags.",
        style=wx.TE_READONLY | wx.TE_MULTILINE,
        size=(420, 60),
    )
    directory_box.SetName("Directory tags, read-only")
    directory_box.SetHelpText(
        "The tags the station directory already lists for this station. They are "
        "searched too, and cannot be changed here."
    )
    root.Add(directory_box, 0, wx.EXPAND | wx.ALL, 10)

    buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
    if buttons is not None:
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
    dialog.SetSizerAndFit(root)
    apply_modal_ids(
        dialog,
        affirmative_id=wx.ID_OK,
        affirmative_label="OK",
        cancel_id=wx.ID_CANCEL,
        cancel_label="Cancel",
        escape_id=wx.ID_CANCEL,
    )
    return dialog, tags_box


def ask_tags(parent: Any, station_name: str, current: str, directory: str) -> str | None:
    """Show the dialog. The typed text, or ``None`` when cancelled."""
    import wx

    from quill.ui.dialog_contract import show_modal_dialog

    dialog, tags_box = build_dialog(parent, station_name, current, directory)
    try:
        tags_box.SetFocus()
        tags_box.SetInsertionPointEnd()
        if show_modal_dialog(dialog, TITLE) != wx.ID_OK:
            return None
        return str(tags_box.GetValue() or "")
    finally:
        dialog.Destroy()


def _favorites_of(host: Any) -> Any:
    from quill.ui.radio.station_lookup_lane import favorites_of

    return favorites_of(host)


def edit_station_tags(
    host: Any,
    station: Any,
    *,
    ask: AskTags | None = None,
    data_dir: Any = None,
    announce: Callable[[str], None] | None = None,
) -> bool:
    """Ask for *station*'s tags and save them where they belong. Changed?

    False when there is no station, it has no stable identity, the listener
    cancelled, or the tags came back the same -- so a caller refreshes its row
    only when there is something new to show.
    """
    from quill.core.radio import station_tags as tags_mod

    say = announce or getattr(host, "_announce", None) or (lambda _m: None)
    if station is None or not tags_mod.station_key(station):
        say("Select a station to tag.")
        return False
    if data_dir is None:
        from quill.core.paths import app_data_dir

        data_dir = app_data_dir()
    favorites = _favorites_of(host)
    store = tags_mod.load_tag_store(data_dir)
    current = tags_mod.user_tags_for(station, favorites=favorites, store=store)
    asker = ask or ask_tags
    from quill.ui import modal_stack

    typed = asker(
        modal_stack.parent_window(host),
        str(getattr(station, "name", "") or "this station"),
        tags_mod.format_tags(current),
        tags_mod.format_tags(tuple(getattr(station, "tags", ()) or ())),
    )
    if typed is None:
        return False
    wanted = tags_mod.parse_tags(typed)
    if wanted == current:
        return False
    try:
        favorites_changed, store_changed = tags_mod.set_user_tags(
            station, wanted, favorites=favorites, store=store
        )
        if favorites_changed and favorites is not None:
            from quill.core.radio.favorites import save_favorites

            save_favorites(data_dir, favorites)
        if store_changed:
            tags_mod.save_tag_store(data_dir, store)
    except OSError:
        say("The tags could not be saved.")
        return False
    say("Tags saved." if wanted else "Tags removed.")
    return True


def edit_row_tags(dialog: Any, data: dict, station: Any) -> None:
    """The browse-row entry point: edit, then re-read the details pane so the
    next arrow key hears the new tags rather than the old ones."""
    if edit_station_tags(dialog, station):
        from quill.ui.radio import browse_details

        browse_details.describe_selection(dialog, data)


def edit_playing(host: Any) -> bool:
    """Edit Tags for the Playing Station: the same dialog, for what is on air."""
    controller = getattr(host, "_radio_controller", None)
    state = getattr(controller, "state", None)
    station = getattr(state, "station", None)
    if station is None:
        say = getattr(host, "_announce", None) or (lambda _m: None)
        say("Nothing is playing.")
        return False
    return edit_station_tags(host, station)


def details_for(host: Any, station: Any, details: str | None = None) -> str:
    """*station*'s details text with your tags in it. Never raises."""
    text = str(getattr(station, "details_text", "") or "") if details is None else details
    try:
        from quill.core.paths import app_data_dir
        from quill.core.radio import station_tags as tags_mod

        tags = tags_mod.user_tags_for(
            station, favorites=_favorites_of(host), store=tags_mod.load_tag_store(app_data_dir())
        )
        return tags_mod.details_with_tags(text, tags)
    except Exception:  # noqa: BLE001 - the details still describe the station
        return text
