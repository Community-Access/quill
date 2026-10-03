"""What you can do to a search result: follow it, stop following it, look at it.

Split out of ``add_podcast_dialog`` because it is a separate job from building the
window, and because all four things in here arrived together out of one session of
using the dialog (2026-09-30):

* **Preview had never worked.** ``preview_command`` called
  ``feed_reader.load_feed``, and there is no such function -- there is
  ``fetch_and_parse_feed``. Every press raised ``AttributeError`` inside the
  background task, landed in the failure handler, and set a status label. The
  button looked dead because it was.
* **The action button did not know whether you already followed the show.** It
  said Subscribe on every row, and pressing it on one you already had produced a
  refusal. The refusal was well written; being told no is still worse than being
  offered the thing that would help.
* **A row did not say whether you follow it.** That is the more important half of
  the same problem: a dimmed or relabelled button tells you about the row you are
  on, and a listener wants to know while arrowing *past* it. So the list carries
  a Following column, and the button follows the list rather than replacing it.
* **There was no context menu**, which on a list is where a keyboard user looks
  for everything a row can do.

The vocabulary is **Follow**, not Subscribe. Every podcast app a listener has used
in the last five years says Follow, and "subscribe" now reads as something with a
price attached -- which is exactly the wrong thing to suggest about a free app
adding a free feed.

One rule that shapes the whole module: **unfollowing from here always asks
first.** This window is where somebody is exploring, arrowing quickly through
results, and a one-press destructive action beside a one-press additive action on
the same key is how a library loses a podcast. What is at stake is named in the
question, because "are you sure" answers nothing.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "FOLLOW_LABEL",
    "UNFOLLOW_LABEL",
    "action_label",
    "already_following",
    "follow_action",
    "following_cell",
    "open_context_menu",
    "refresh_follow_button",
    "refresh_row_following",
    "unfollow_confirm",
]

#: The two labels the action button alternates between. Access keys chosen
#: against every other mnemonic in the window (Search, Preview, Add, Import
#: OPML, Podcast name, Feed address, Directory), so neither collides -- GATE-14,
#: where a duplicate advertises a key that may silently not work.
# Alt+O, not Alt+F: the Add Podcast window's "&Feed address:" owns F (GATE-14).
FOLLOW_LABEL = "F&ollow"
UNFOLLOW_LABEL = "Unf&ollow"


def already_following(library: Any, feed_url: str) -> Any:
    """The show already in the library for *feed_url*, or ``None``.

    By feed address rather than by title: two shows share a name far more often
    than they share a feed, and the address is what actually decides whether
    following this row would add anything.
    """
    if not feed_url:
        return None
    try:
        return library.find_show_by_feed_url(feed_url)
    except Exception:  # noqa: BLE001 - a library that cannot answer is not a crash
        return None


def following_cell(library: Any, feed_url: str) -> str:
    """What the Following column says for this row: ``"Following"`` or ``""``.

    Empty rather than "Not following", because the column is read out on every
    row and the interesting state is the rare one. A column that says something
    on all forty rows costs forty words and carries no information.
    """
    return "Following" if already_following(library, feed_url) is not None else ""


def action_label(library: Any, feed_url: str) -> str:
    """Which of the two labels the action button should be showing."""
    return UNFOLLOW_LABEL if already_following(library, feed_url) is not None else FOLLOW_LABEL


def unfollow_confirm(show: Any) -> str:
    """The question, naming the show and what survives it.

    Both halves matter. The title, because a listener arrowing through results has
    no other way to be sure which row the question is about. And what survives,
    because "stop following" sounds like it might delete the episodes, and
    somebody who would have been happy to unfollow will cancel rather than find
    out.
    """
    title = str(getattr(show, "title", "") or "that podcast")
    return (
        f"Stop following {title}?\n\n"
        "It is removed from your library, along with your place in its episodes. "
        "Any episodes you have downloaded stay on this computer until you delete "
        "them, and you can follow it again from here at any time."
    )


def open_context_menu(dialog: Any, index: int) -> None:
    """The result row's own menu, at the row rather than at the pointer.

    Positioned on the **list control** rather than at a mouse position, because
    the menu has to appear in the same place whether it was opened with the
    Applications key, with Shift+F10, or with a right-click -- and the first two
    are how it will usually be opened here.

    Every row carries the same five items, and the ones that cannot work on this
    row are *disabled rather than absent*: a menu whose shape changes between
    rows is one a listener has to re-read every time, and a disabled item at
    least says the capability exists.
    """
    wx = dialog._wx
    results = getattr(dialog, "_search_results", [])
    if not (0 <= index < len(results)):
        return
    result = results[index]
    following = already_following(dialog._library, result.feed_url)

    menu = wx.Menu()
    follow_id = wx.NewIdRef()
    menu.Append(follow_id, "Stop &Following" if following is not None else "&Follow")
    preview_id = wx.NewIdRef()
    menu.Append(preview_id, "&Preview...")
    menu.AppendSeparator()
    copy_feed_id, copy_site_id, open_site_id = wx.NewIdRef(), wx.NewIdRef(), wx.NewIdRef()
    menu.Append(copy_feed_id, "Copy Feed &Address")
    menu.Append(copy_site_id, "Copy &Website Address")
    menu.Append(open_site_id, "&Open Website in Your Browser")
    homepage = str(getattr(result, "homepage", "") or "")
    menu.Enable(copy_site_id, bool(homepage))
    menu.Enable(open_site_id, bool(homepage))

    dialog.dialog.Bind(wx.EVT_MENU, lambda _e: dialog._on_follow_action(), id=follow_id)
    dialog.dialog.Bind(wx.EVT_MENU, lambda _e: dialog._on_preview_selected(), id=preview_id)
    dialog.dialog.Bind(
        wx.EVT_MENU,
        lambda _e: _copy(dialog, result.feed_url, "Feed address copied"),
        id=copy_feed_id,
    )
    dialog.dialog.Bind(
        wx.EVT_MENU, lambda _e: _copy(dialog, homepage, "Website address copied"), id=copy_site_id
    )
    dialog.dialog.Bind(wx.EVT_MENU, lambda _e: _open_site(dialog, homepage), id=open_site_id)

    try:
        dialog._results.PopupMenu(menu)
    finally:
        menu.Destroy()


def _copy(dialog: Any, text: str, said: str) -> None:
    """Put *text* on the clipboard and say so.

    Announced, because a clipboard write is the textbook case of something the
    screen reader cannot report: nothing on screen changed, and the only way to
    find out whether it worked would be to paste it somewhere.
    """
    if not text:
        dialog._announce("There is no address to copy for that podcast.")
        return
    wx = dialog._wx
    clipboard = wx.TheClipboard
    if not clipboard.Open():
        dialog._announce("The clipboard could not be opened, so nothing was copied.")
        return
    try:
        clipboard.SetData(wx.TextDataObject(text))
    finally:
        clipboard.Close()
    dialog._announce(said)


def _open_site(dialog: Any, homepage: str) -> None:
    """Open the show's own page in the listener's browser.

    Refused in Safe Mode along with everything else that leaves the app, and
    announced either way -- a browser opening behind a modal dialog is not
    something a screen-reader user will necessarily notice.
    """
    if not homepage:
        dialog._announce("That podcast did not give a website address.")
        return
    if getattr(dialog, "_safe_mode", False):
        dialog._announce("Opening a website is disabled in Safe Mode.")
        return
    import webbrowser

    try:
        webbrowser.open(homepage)
    except Exception:  # noqa: BLE001 - a browser that will not start is not a crash
        dialog._announce("That website could not be opened.")
        return
    dialog._announce("Opened in your browser.")


def refresh_follow_button(dialog: Any) -> None:
    """Make the action button offer the verb that applies to the current row.

    The label is set rather than the button being dimmed, because a dimmed
    button answers "no" and a relabelled one answers "here is what you can do
    instead" -- and on a row you already follow, the thing somebody usually
    wants is to stop.
    """
    result = dialog._selected_result()
    label = action_label(dialog._library, result.feed_url) if result is not None else FOLLOW_LABEL
    if dialog._subscribe_btn.GetLabel() != label:
        dialog._subscribe_btn.SetLabel(label)


def refresh_row_following(dialog: Any, index: int, feed_url: str) -> None:
    """Bring one row's Following cell and the action button back into step.

    One row rather than a redraw of the list: a redraw would move the cursor,
    and the cursor is where the listener is.
    """
    for column, definition in enumerate(dialog._columns):
        if definition.id == "following":
            dialog._results.SetItem(index, column, following_cell(dialog._library, feed_url))
            break
    refresh_follow_button(dialog)


def follow_action(dialog: Any) -> None:
    """Follow the selected row, or -- if it is already followed -- offer to stop.

    Asking is not optional here. This window is where somebody explores,
    arrowing quickly through results, and a one-press destructive action on the
    same key as a one-press additive one is how a library loses a podcast.

    Unfollowing goes through the **shared** prompt rather than removing the show
    here: that one asks, honours the show's delete-files-on-remove policy,
    deletes the stored private-feed password so no secret is orphaned, and --
    the part a local implementation would silently have lost -- registers the
    whole thing as one undoable step, so Ctrl+Z puts the subscription back.
    """
    index = dialog._results.GetFirstSelected()
    if not (0 <= index < len(dialog._search_results)):
        return
    result = dialog._search_results[index]
    existing = already_following(dialog._library, result.feed_url)
    if existing is None:
        dialog._subscribe_to_feed(result.feed_url, title_hint=result.title, result_index=index)
        refresh_row_following(dialog, index, result.feed_url)
        return
    from quill.ui.podcasts.show_actions import unsubscribe_show_prompt

    if not unsubscribe_show_prompt(
        dialog.dialog,
        dialog._library,
        existing,
        announce=dialog._announce,
        on_change=dialog._on_library_changed,
    ):
        return
    title = str(getattr(existing, "title", "") or "that podcast")
    dialog._status.SetLabel(f"No longer following {title}.")
    refresh_row_following(dialog, index, result.feed_url)
