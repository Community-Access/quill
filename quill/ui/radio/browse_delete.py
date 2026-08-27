"""Delete, in the browse tree: ask, remove, and show that it is gone.

Every removable row already had a verb -- **Remove from YouTube**, **Stop
Following This Channel**, **Remove from Favorites** -- and every one of them
was reachable only by opening a context menu and reading it. The key everybody
tries first did nothing at all, and the verbs that did work ended by *telling
the listener to refresh the list themselves*, so the row they had just removed
stayed on screen looking removed-and-not-removed ("pressing delete doesn't seem
to delete an item from the list and the user should be asked and doing so
should refresh the treeview to show that it is gone", 2026-08-23).

Three rules:

* **Delete runs the row's own verb.** There is no second implementation of
  "remove" here; this module decides *which* removal a row means and then calls
  the same code the menu item calls. A key and a menu item that could disagree
  is worse than a missing key.
* **It asks first, by name.** A tree is arrowed through quickly and Delete is
  next to keys people use for navigation; a destructive key with no question is
  a data-loss bug waiting for one mis-press. The question names the thing
  ("Remove Do schools kill creativity? from YouTube?") because "are you sure?"
  is not a question anybody can answer.
* **The branch reloads.** Removing a row and leaving it on screen reads as the
  removal having failed, which is exactly what was reported.

A row with nothing to remove says so, rather than swallowing the key -- the
same rule the whole tree follows.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.browse_nodes import split_id

#: Node kind -> (what it is called, which root branch to reload after).
#: A kind that is not here has no removal, and Delete says so out loud.
_REMOVABLE: dict[str, tuple[str, str]] = {
    "ytvideo": ("saved video", "youtube"),
    "ytplaylist": ("saved playlist", "youtube"),
    "youtubechannel": ("followed channel", "youtube"),
    "myservers": ("server", "myservers"),
}

NOTHING_TO_DELETE = (
    "There is nothing to delete on this row. Delete removes a saved YouTube "
    "video or playlist, a followed channel, a server you added, a favorite, "
    "or the Search Results branch."
)


def _label(dialog: Any, node: Any) -> str:
    """The row's own text, without the trailing "  (3 items)" the tree adds."""
    try:
        return str(dialog._tree.GetItemText(node)).split("  (")[0]
    except Exception:  # noqa: BLE001 - a label is never worth failing a key on
        return "this row"


#: The two remembered answers, as they are named on ``RadioHistory``.
CONFIRM_SETTING = "confirm_browse_delete"
EXPLAIN_SETTING = "explain_browse_delete"

DONT_ASK = "&Don't ask me again"
DONT_SHOW = "&Don't show this again"


def _history(dialog: Any) -> Any:
    """The radio history, reached through the frame behind this window."""
    frame = getattr(dialog, "_download_host", None) or dialog
    return getattr(frame, "_radio_history", None)


def _remembered(dialog: Any, setting: str) -> bool:
    """Whether this question is still wanted. Unknown hosts always ask."""
    history = _history(dialog)
    return bool(getattr(history, setting, True))


def _remember(dialog: Any, setting: str) -> None:
    """Stop asking, and persist that -- a preference set once must survive.

    Written through the frame's own saver where there is one; a window with no
    frame behind it (a test) simply keeps the answer for this session.
    """
    history = _history(dialog)
    if history is None:
        return
    setattr(history, setting, False)
    frame = getattr(dialog, "_download_host", None) or dialog
    save = getattr(frame, "_save_radio_history", None)
    if callable(save):
        try:
            save()
        except Exception:  # noqa: BLE001 - a failed save must not block the delete
            return


def _ask(dialog: Any, message: str, *, setting: str, question: bool, checkbox: str) -> bool:
    """One dialog with a "don't ask again" tick. True = go ahead / was shown.

    ``wx.RichMessageDialog`` because it is the platform's own message box
    *with* the checkbox -- the alternative is a bespoke dialog, which would be
    a new surface in the inventory, a new tab order to test with a screen
    reader, and no better for it. The checkbox starts **unticked** and the
    default button is **No**: a destructive key sitting beside the navigation
    keys must not be one mis-press from both deleting a row and switching the
    question off forever.
    """
    wx = dialog._wx
    style = wx.ICON_QUESTION | (
        wx.YES_NO | wx.NO_DEFAULT if question else wx.OK | wx.ICON_INFORMATION
    )
    box = wx.RichMessageDialog(  # dialog_button_contract: exempt
        getattr(dialog, "_win", None), message, "Delete", style
    )
    box.ShowCheckBox(checkbox, False)
    try:
        answer = box.ShowModal()
        if box.IsCheckBoxChecked():
            _remember(dialog, setting)
    finally:
        box.Destroy()
    return answer == wx.ID_YES if question else True


def confirm(dialog: Any, question: str) -> bool:
    """Ask before removing, defaulting to No, with a way to stop being asked.

    Somebody who deletes rows often should not be interrogated every time --
    and the place to turn that off is inside the question itself, which is the
    only place anybody would look. Once it is off, Delete removes without
    asking; the row is still named out loud afterwards, so the gesture is
    never silent.
    """
    if not _remembered(dialog, CONFIRM_SETTING):
        return True
    return _ask(dialog, question, setting=CONFIRM_SETTING, question=True, checkbox=DONT_ASK)


def explain_not_deletable(dialog: Any, label: str) -> None:
    """Delete landed on a row that has nothing to remove: say so, in a dialog.

    Spoken only, this was easy to miss on the key people press first -- and a
    key that appears to do nothing is indistinguishable from a broken one. It
    is said out loud as well, and it carries the same checkbox: the answer is
    useful once and noise forever after (2026-08-23).
    """
    dialog._announce(NOTHING_TO_DELETE)
    if not _remembered(dialog, EXPLAIN_SETTING):
        return
    _ask(
        dialog,
        f"{label} is part of Quill Radio's own list of sources, so there is "
        f"nothing here to delete.\n\n{NOTHING_TO_DELETE}\n\nTo take a whole "
        "branch out of the tree, use Hide This Source on its context menu.",
        setting=EXPLAIN_SETTING,
        question=False,
        checkbox=DONT_SHOW,
    )


def handle_key(dialog: Any, event: Any) -> bool:
    """The tree's Delete key. True when this module handled the press.

    Only while the **tree** has focus: Delete inside the Find box is an
    ordinary delete of a character, and stealing it there would make the search
    field unusable. Called from the window's char hook, which is the one place
    that sees a key before the tree does.
    """
    wx = dialog._wx
    if event.GetKeyCode() != wx.WXK_DELETE:
        return False
    if dialog._win.FindFocus() is not dialog._tree:
        return False
    delete_selected(dialog)
    return True


def delete_selected(dialog: Any) -> bool:
    """The Delete key on the selected row. True when something was removed."""
    node = dialog._tree.GetSelection()
    data = dialog._node_data(node) if node is not None else None
    if data is None:
        return False
    kind, args = split_id(str(data.get("node_id") or ""))
    station = data.get("station")

    if kind == "searchresults":
        return _close_search_results(dialog)
    if kind in _REMOVABLE and args and args[0]:
        return _remove_stored(dialog, node, kind, args)
    if station is not None and dialog._favorites.contains(station):
        return _remove_favorite(dialog, station)
    if kind in ("mypodcastshow", "mypodcastfolder"):
        return _remove_podcast(dialog, node, kind, args)
    explain_not_deletable(dialog, _label(dialog, node))
    return False


def _close_search_results(dialog: Any) -> bool:
    """Delete on the Search Results branch closes it.

    The one row where Delete does **not** ask first, and deliberately: this
    branch owns nothing. It is the answer to a search that has already
    happened, the query itself is still in Find, and running the search again
    rebuilds it -- so the confirmation this module insists on everywhere else
    would be a question about nothing. Asked for on 2026-08-26; the context
    menu's Close Search Results calls the same function.
    """
    from quill.ui.radio import browse_search_all

    if not browse_search_all.clear_results(dialog):
        return False
    dialog._announce("Search results closed.")
    return True


def _remove_stored(dialog: Any, node: Any, kind: str, args: list[str]) -> bool:
    """A saved YouTube link, a followed channel, or a server the listener added."""
    what, root = _REMOVABLE[kind]
    name = _label(dialog, node)
    where = "YouTube" if root == "youtube" else "My Servers"
    if not confirm(dialog, f"Remove {name} from {where}?"):
        dialog._announce("Nothing was removed.")
        return False

    url = args[0]
    if kind in ("ytvideo", "ytplaylist"):
        from quill.core.radio.youtube_saved import SavedStore

        SavedStore().remove(url)
    elif kind == "youtubechannel":
        from quill.core.radio.youtube_channels import ChannelStore

        ChannelStore().remove(url)
    else:
        from quill.core.radio.my_servers import ServerStore

        ServerStore().remove(url)

    reload_branch(dialog, root)
    dialog._announce(f"Removed {name}. That {what} is gone from {where}.")
    return True


def _remove_favorite(dialog: Any, station: Any) -> bool:
    """A row that is one of your favorites: Delete unfavorites it."""
    name = str(getattr(station, "display_name", "") or "") or "this station"
    if not confirm(dialog, f"Remove {name} from Favorites?"):
        dialog._announce("Nothing was removed.")
        return False
    key = str(getattr(station, "station_uuid", "") or "") or str(
        getattr(station, "stream_url", "") or ""
    )
    dialog._favorites.remove(key)
    changed = getattr(dialog, "_on_favorites_changed", None)
    if callable(changed):
        changed()
    refresh = getattr(dialog, "_refresh_favorites_branch", None)
    if callable(refresh):
        refresh()
    dialog._announce(f"Removed {name} from Favorites.")
    return True


def _remove_podcast(dialog: Any, node: Any, kind: str, args: list[str]) -> bool:
    """A subscribed show, or one of the folders they are filed in.

    These two already own confirmed, refreshing verbs (they are the podcast
    library's, shared with Quill Cast), so Delete hands straight over rather
    than asking a second question of its own.
    """
    from quill.ui.radio import browse_podcast_actions, browse_tree_menu

    if kind == "mypodcastfolder":
        browse_podcast_actions.delete_podcast_folder(dialog, args)
        return True
    browse_tree_menu.unsubscribe(dialog, node, kind, args)
    return True


def reload_branch(dialog: Any, node_id: str) -> None:
    """Re-fetch the branch that owned the removed row, so it disappears."""
    reload_source = getattr(dialog, "_reload_source_branch", None)
    if callable(reload_source):
        reload_source(node_id)
