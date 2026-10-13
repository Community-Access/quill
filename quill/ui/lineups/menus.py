"""The Lineups window's menus and keys, as one table.

The same shape as Radio's Local Media window (``local_media_window_menu``): each
row ``(verb, label, key, help)`` builds the menu-bar item, labels the context
menu item with its key, and answers the key in the window's char hook. One
table is what keeps the three from drifting: every menu item shows its keyboard
route, and no two items in the menu bar claim the same key.

**Where Local Media has the same verb, the key is the same** -- Ctrl+Enter plays
and carries on, Ctrl+Alt+P plays the whole list, Alt+Shift and the arrows move,
Ctrl+J moves to a position, Alt+Enter is properties, F5 checks now, Ctrl+T is
the summary -- so a listener who knows one list knows the other.

Keys stay clear of what every Radio window already answers to (the transport
keys, the media keys, the Station menu and window switching; see
``local_media_window_menu``), checked by ``tests/unit/ui/lineups``. Ctrl+E is
Sound Enhancements and Ctrl+P is Play or Stop in Radio, so neither is used here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.ui.radio.local_media_window_menu import canonical, chord_of_event

__all__ = [
    "CHECK_VERBS",
    "ITEM_POPUP",
    "LINEUP_POPUP",
    "MENUS",
    "canonical",
    "chord_of_event",
    "install_menu_bar",
    "key_table",
    "popup",
]

Row = tuple[str, str, str, str]

#: ``(menu title, [(verb, label, key, help), ...])``; a verb of ``""`` is a
#: separator. The window answers each verb with ``cmd_<verb>``.
MENUS: tuple[tuple[str, tuple[Row, ...]], ...] = (
    (
        "Line&up",
        (
            ("new_lineup", "&New Lineup...", "Ctrl+N", "Name a new, empty lineup."),
            (
                "new_example",
                "New from an E&xample...",
                "Ctrl+Alt+N",
                "Start from a ready-made one.",
            ),
            ("duplicate", "Dupli&cate Lineup", "Ctrl+D", "A copy with the same rules and order."),
            ("rename", "&Rename Lineup...", "F2", "Give the lineup a new name."),
            (
                "delete_lineup",
                "&Delete Lineup...",
                "Shift+Delete",
                "Asks first; Undo brings it back.",
            ),
            ("", "", "", ""),
            ("edit_rules", "Edit R&ules...", "Ctrl+Alt+R", "What comes in, and when it goes."),
            ("start_here", "&Start Here", "Ctrl+Alt+H", "Open this lineup when the app starts."),
            ("", "", "", ""),
            (
                "removed_items",
                "Removed &Items...",
                "Ctrl+Alt+Z",
                "What you removed; bring it back.",
            ),
            ("recently_left", "Recently &Left...", "Ctrl+Alt+L", "What the rules let go, and why."),
            ("", "", "", ""),
            ("import_rules", "Im&port Rules...", "Ctrl+I", "Make a lineup from a rules file."),
            (
                "export_rules",
                "&Export Rules...",
                "Ctrl+Shift+X",
                "Save this lineup's rules to share.",
            ),
            ("", "", "", ""),
            ("close", "Cl&ose", "Ctrl+W", "Close this window. Playing carries on."),
        ),
    ),
    (
        "&Edit",
        (
            ("undo", "&Undo", "Ctrl+Z", "Take back the last change."),
            ("", "", "", ""),
            ("cut", "Cu&t", "Ctrl+X", "Mark items to move; Paste puts them."),
            ("paste_before", "&Paste Before", "Ctrl+V", "Put them before the item."),
            ("paste_after", "Paste &After", "Ctrl+Alt+V", "Put them after the item."),
            ("", "", "", ""),
            ("keep", "&Keep This Item", "Ctrl+K", "It stays whatever the rules say."),
            ("remove", "&Remove from Lineup", "Delete", "No rule brings it back."),
            ("remove_missing", "Remove &Missing Items", "Ctrl+Shift+Delete", "Tidy up."),
            ("select_all", "Select A&ll", "Ctrl+A", "Select every item."),
            ("", "", "", ""),
            ("why", "&Why Is This Here...", "Alt+Enter", "The rule, or your hand, and how long."),
            ("refresh", "Refresh &Now", "F5", "Run the rules now."),
        ),
    ),
    (
        "&Arrange",
        (
            ("move_up", "Move &Up", "Alt+Shift+Up", "One place up."),
            ("move_down", "Move &Down", "Alt+Shift+Down", "One place down."),
            ("move_top", "Move to &Top", "Alt+Shift+Home", "To the start."),
            ("move_bottom", "Move to &Bottom", "Alt+Shift+End", "To the end."),
            ("move_to", "Move to &Position...", "Ctrl+J", "Type the number to move to."),
        ),
    ),
    (
        "&Play",
        (
            ("play", "&Play", "Ctrl+Enter", "Play the selected item, then carry on."),
            ("pause", "Pause or &Resume", "Ctrl+Space", "Hold or continue what plays."),
            ("next", "&Next Item", "Ctrl+Right", "The next item in the lineup."),
            ("previous", "Pre&vious Item", "Ctrl+Left", "The item before."),
            ("", "", "", ""),
            ("play_all", "Play This &Lineup", "Ctrl+Alt+P", "From the start."),
            ("play_next", "Play Ne&xt", "Ctrl+Shift+Enter", "Right after what is playing."),
            ("up_next", "Add to &Up Next", "Ctrl+Alt+Enter", "After anything queued."),
            ("stop_after", "Stop After This &Item", "Ctrl+Alt+S", "Once."),
            ("", "", "", ""),
            ("skip_live", "S&kip Live Items", "Ctrl+Alt+K", "Leave out what never ends."),
            ("summary", "Lineup Su&mmary", "Ctrl+T", "How many, how long, when updated."),
        ),
    ),
)

#: Verbs whose menu item is a check item.
CHECK_VERBS = frozenset({"start_here", "keep", "skip_live"})

#: Keys a list answers itself only while it has focus (they edit text elsewhere).
LIST_ONLY_KEYS = frozenset({"Delete", "Shift+Delete", "Ctrl+A", "Ctrl+X", "Ctrl+V", "F2"})


def key_table() -> dict[str, str]:
    """Canonical chord -> verb, for every keyed row."""
    table: dict[str, str] = {}
    for _title, rows in MENUS:
        for verb, _label, key, _help in rows:
            if verb and key:
                table[canonical(key)] = verb
    return table


def install_menu_bar(window: Any, wx: Any, run: Callable[[str], None]) -> dict[str, Any]:
    """Build the menu bar; the app adds its own menus. Returns verb -> item."""
    menu_bar = wx.MenuBar()
    items: dict[str, Any] = {}
    refs = window._menu_id_refs
    for title, rows in MENUS:
        menu = wx.Menu()
        for verb, label, key, help_text in rows:
            if not verb:
                menu.AppendSeparator()
                continue
            item_id = wx.NewIdRef()
            refs.append(item_id)
            kind = wx.ITEM_CHECK if verb in CHECK_VERBS else wx.ITEM_NORMAL
            items[verb] = menu.Append(item_id, f"{label}\t{key}", help_text, kind)
            window._win.Bind(wx.EVT_MENU, lambda _e, v=verb: run(v), id=item_id)
        menu_bar.Append(menu, title)
    window._lineups_host.install_menus(window._win, menu_bar, refs)
    window._win.SetMenuBar(menu_bar)
    return items


def _key_of(verb: str) -> str:
    for _title, rows in MENUS:
        for candidate, _label, key, _help in rows:
            if candidate == verb:
                return key
    return ""


#: The Items list's context menu ``(verb, label)``; keys come from :data:`MENUS`.
ITEM_POPUP: tuple[tuple[str, str], ...] = (
    ("play", "&Play"),
    ("play_next", "Play Ne&xt"),
    ("up_next", "Add to &Up Next"),
    ("", ""),
    ("why", "&Why Is This Here..."),
    ("keep", "&Keep This Item"),
    ("", ""),
    ("move_up", "Mo&ve Up"),
    ("move_down", "Move &Down"),
    ("move_top", "Move to &Top"),
    ("move_bottom", "Move to &Bottom"),
    ("move_to", "Move to P&osition..."),
    ("cut", "&Cut"),
    ("paste_before", "Paste B&efore"),
    ("paste_after", "Paste &After"),
    ("", ""),
    ("remove", "&Remove from Lineup"),
)

#: The Lineups list's context menu.
LINEUP_POPUP: tuple[tuple[str, str], ...] = (
    ("play_all", "&Play This Lineup"),
    ("edit_rules", "Edit R&ules..."),
    ("start_here", "&Start Here"),
    ("", ""),
    ("rename", "&Rename..."),
    ("duplicate", "Dupli&cate"),
    ("delete_lineup", "&Delete..."),
    ("", ""),
    ("removed_items", "Removed &Items..."),
    ("recently_left", "Recently &Left..."),
    ("", ""),
    ("new_lineup", "&New Lineup..."),
)


def popup(
    window: Any,
    wx: Any,
    rows: list[tuple[str, str]],
    run: Callable[[str], None],
    *,
    keys: dict[str, str] | None = None,
    checked: frozenset[str] = frozenset(),
) -> Any:
    """A context menu of *rows*, each label carrying the key the window answers to."""
    menu = wx.Menu()
    refs = []
    for verb, label in rows:
        if not verb:
            if menu.GetMenuItemCount():
                menu.AppendSeparator()
            continue
        key = (keys or {}).get(verb, _key_of(verb))
        item_id = wx.NewIdRef()
        refs.append(item_id)
        kind = wx.ITEM_CHECK if verb in CHECK_VERBS else wx.ITEM_NORMAL
        item = menu.Append(item_id, f"{label}\t{key}" if key else label, "", kind)
        if verb in CHECK_VERBS:
            item.Check(verb in checked)
        menu.Bind(wx.EVT_MENU, lambda _e, v=verb: run(v), id=item_id)
    window._context_id_refs = [*getattr(window, "_context_id_refs", []), *refs]
    return menu
