"""The shared Help-menu items every listening app grew on 2026-08-24.

Recent Problems, Quiet Hours, Export / Import My Setup, and Bookmarks -- built
once here and appended by both Quill Radio and QUILL Cast, because every one of
them is a shared surface over a shared file and a second copy of the wiring is
a second place for the two apps to drift apart.

They sit together on Help rather than being scattered because they answer the
same family of question: *why is this app talking to me, why is it not, and
how do I take all of this with me?*

* **Recent Problems** (11.5) -- where a transient announcement goes, so a feed
  that failed while you were in another window is still findable an hour later.
* **Quiet Hours** (11.9) -- the window in which the app stops speaking on its
  own. Feeds are still checked; only the speech waits.
* **Export / Import My Setup** (11.10) -- one file carrying subscriptions,
  favorites, folders, places, settings and bookmarks. OPML moves subscriptions
  and nothing else.
* **Bookmarks** (4.4) -- everywhere you marked, in either app, in one list.
  Its companion verb, Bookmark This Moment, belongs on each app's playback
  menu instead: it is a thing you do while listening, not a thing you go and
  look for.

Every label goes through the host's ``_menu_label`` so it shows the key that
is *actually* bound and follows the listener when they rebind it -- the house
rule the menu-accelerator gate enforces.
"""

from __future__ import annotations

from typing import Any


def append_support_items(host: Any, help_menu: Any, wx: Any) -> tuple[Any, ...]:
    """Append the shared items to *help_menu*, bound to *host*.

    Returns every id ref it created. The caller must pin them (``_keep_menu_ids``):
    a menu id ref that is garbage-collected can be reissued to a different
    item, and the symptom is a random menu entry firing the wrong command.
    """
    problems_id = wx.NewIdRef()
    help_menu.Append(problems_id, host._menu_label("Recent &Problems...", "app.recent_problems"))
    host.frame.Bind(wx.EVT_MENU, lambda _e: host.open_recent_problems(), id=problems_id)

    quiet_id = wx.NewIdRef()
    help_menu.Append(quiet_id, host._menu_label("&Quiet Hours...", "app.quiet_hours"))
    host.frame.Bind(wx.EVT_MENU, lambda _e: host.open_quiet_hours(), id=quiet_id)

    bookmarks_id = wx.NewIdRef()
    help_menu.Append(bookmarks_id, host._menu_label("&Bookmarks...", "app.bookmarks"))
    host.frame.Bind(wx.EVT_MENU, lambda _e: host.open_bookmarks(), id=bookmarks_id)

    export_id, import_id = wx.NewIdRef(), wx.NewIdRef()
    help_menu.Append(export_id, host._menu_label("E&xport My Setup...", "app.export_setup"))
    help_menu.Append(import_id, host._menu_label("&Import My Setup...", "app.import_setup"))
    host.frame.Bind(wx.EVT_MENU, lambda _e: host.export_my_setup(), id=export_id)
    host.frame.Bind(wx.EVT_MENU, lambda _e: host.import_my_setup(), id=import_id)

    ids = (problems_id, quiet_id, bookmarks_id, export_id, import_id)
    host._keep_menu_ids(*ids)
    return ids


def insert_edit_menu(host: object, menu_bar: object, wx: object, *, position: int = 1) -> object:
    """Insert the one-item &Edit menu holding Undo Last Action (11.3).

    Where Windows apps keep it, and where a listener will press Alt+E looking
    for it. One step of undo is cheaper than a confirmation prompt on every
    destructive verb and kinder than either; both apps have no editor, so
    Ctrl+Z is free here in exactly the way it is not in QUILL.

    Returns the id ref, which the caller must pin.
    """
    edit_menu = wx.Menu()
    undo_id = wx.NewIdRef()
    host._keep_menu_ids(undo_id)
    edit_menu.Append(undo_id, host._menu_label("&Undo Last Action", "app.undo_last"))
    host.frame.Bind(wx.EVT_MENU, lambda _e: host.undo_last_action(), id=undo_id)
    menu_bar.Insert(position, edit_menu, "&Edit")
    return undo_id


def wire_support_surfaces(host: Any, menu_bar: Any, help_menu: Any, wx: Any) -> None:
    """Both halves at once: the &Edit menu, and the shared Help items.

    The one call an app frame makes. Keeping it one call is the point -- the
    four surfaces arrive together, are shared between the apps, and a frame
    that wired three of them would be a frame with a missing key nobody
    noticed until somebody pressed it.

    **Edit goes at index 1, not at the end** (2026-08-25). This used to pass
    ``position=menu_bar.GetMenuCount()``, which put Edit wherever the frame
    happened to have got to -- in Quill Radio that was between Community and
    QuillVille, in QUILL Cast between Quillins and Help. Both are places no
    Windows app has ever kept Edit, and a menu found by counting Alt+Right
    presses is a menu whose position is the whole of its discoverability.
    Index 1 is immediately after the app's own first menu (Station in Radio,
    Subscriptions in Cast), which is where File/Edit sits everywhere else.
    """
    insert_edit_menu(host, menu_bar, wx)
    append_support_items(host, help_menu, wx)
