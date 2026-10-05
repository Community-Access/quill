"""The Local Media window's menus and keys, as one table.

Every command the window has is a row here -- ``(verb, label, key, help)`` --
and the same row builds the menu bar item, labels the context-menu item with
its key, and answers the key itself. One table is what keeps the three from
drifting: a key the menu advertises is a key that works, and a key that works
is one the menu shows (the house rule: every menu item shows its keyboard
route, and no two items in a menu bar claim the same key).

**Why the keys are answered here as well as by the menu bar.** Embedded in
QUILL the window is a modal dialog with no menu bar at all, and Alt+Shift+Up
is the kind of chord Windows likes to hand to a menu bar before any control
sees it. So the window's char hook answers every key in :data:`MENUS` itself,
in both shapes, and the menu bar's accelerators are the advertisement. A key
consumed by the hook never reaches an accelerator, so nothing fires twice.

Keys were chosen to stay clear of everything else a Quill Radio window
answers to: the transport keys (Ctrl+P, Ctrl+., Ctrl+Up/Down, Ctrl+Shift
plus Left, Right, Up, Down, 0, 9, comma, period, C, W, G, P, O), the media keys
(Ctrl+Shift+V, K, T, A, I and Ctrl+Alt+D), the Station menu (Ctrl+B, Ctrl+F,
Ctrl+Shift+M, Ctrl+Shift+R, Ctrl+Comma) and window switching (Ctrl+Tab,
Ctrl+1 to 9). ``tests/unit/ui/radio/test_local_media_window.py`` checks it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = [
    "CHECK_VERBS",
    "MENUS",
    "canonical",
    "chord_of_event",
    "install_menu_bar",
    "key_table",
    "popup",
]

#: ``(menu title, [(verb, label, key, help), ...])`` in menu-bar order. A verb
#: of ``""`` is a separator. The window answers each verb with ``cmd_<verb>``.
MENUS: tuple[tuple[str, tuple[tuple[str, str, str, str], ...]], ...] = (
    (
        "&Local Media",
        (
            ("new_playlist", "&New Playlist...", "Ctrl+N", "Make an empty playlist."),
            ("add_files", "Add &Media Files...", "Ctrl+O", "Pick files to add to this playlist."),
            ("add_folder", "Add a &Folder...", "Ctrl+Alt+O", "Add every file in a folder."),
            ("insert_before", "&Insert Files Here...", "Insert", "Add files before the item."),
            ("insert_after", "Insert Files &After...", "Shift+Insert", "Add files after it."),
            ("", "", "", ""),
            ("import_playlist", "Im&port a Playlist...", "Ctrl+I", "Read an M3U or PLS."),
            ("export_playlist", "&Export as M3U...", "Ctrl+Shift+X", "Save for other players."),
            ("", "", "", ""),
            ("rename", "&Rename Playlist...", "F2", "Give the playlist a new name."),
            ("save_opened", "Sa&ve as Playlist...", "Ctrl+S", "Keep the Opened files list."),
            ("duplicate", "D&uplicate Playlist", "Ctrl+D", "Make a copy of the playlist."),
            ("delete_playlist", "&Delete Playlist...", "Shift+Delete", "Asks first."),
            ("follow_folder", "F&ollow the Folder", "Ctrl+Alt+F", "Add new files as they appear."),
            ("rescan", "Chec&k the Folder Now", "F5", "Look for new files in it now."),
            ("", "", "", ""),
            ("columns", "Choose &Columns...", "Ctrl+Alt+Shift+C", "What each row says."),
            ("close", "Clo&se", "Ctrl+W", "Close this window. Playing carries on."),
        ),
    ),
    (
        "&Edit",
        (
            ("undo", "&Undo", "Ctrl+Z", "Take back the last change."),
            ("", "", "", ""),
            ("cut", "Cu&t", "Ctrl+X", "Mark items to move; Paste puts them."),
            ("copy", "&Copy", "Ctrl+C", "Copy items, and their paths as text."),
            ("paste_before", "&Paste Before", "Ctrl+V", "Put them before the item."),
            ("paste_after", "Paste &After", "Ctrl+Alt+V", "Put them after the item."),
            ("", "", "", ""),
            ("remove", "&Remove from Playlist", "Delete", "The file stays on your computer."),
            ("remove_missing", "Remove &Missing Items", "Ctrl+Shift+Delete", "Tidy up."),
            ("select_all", "Select A&ll", "Ctrl+A", "Select every item."),
            ("", "", "", ""),
            ("properties", "Propert&ies...", "Alt+Enter", "Tags, length and path."),
            ("show_in_folder", "Show in File &Explorer", "Ctrl+Shift+E", "Open its folder."),
            ("locate", "Locate Missing &File...", "Ctrl+Shift+L", "Find a moved file."),
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
            ("", "", "", ""),
            ("sort", "&Sort Playlist...", "Ctrl+Shift+S", "Sort once; undoable."),
        ),
    ),
    (
        "&Play",
        (
            ("play", "&Play", "Ctrl+Enter", "Play the selected item, then carry on."),
            ("pause", "Pause or &Resume", "Ctrl+Space", "Hold or continue what plays."),
            ("next", "&Next Item", "Ctrl+Right", "The next item in the playlist."),
            ("previous", "Pre&vious Item", "Ctrl+Left", "The item before."),
            ("", "", "", ""),
            ("play_playlist", "Play This Play&list", "Ctrl+Alt+P", "From the start."),
            ("continue", "C&ontinue Where I Left Off", "Ctrl+Alt+C", "Where you stopped."),
            ("play_next", "Play Ne&xt", "Ctrl+Shift+Enter", "Right after this one."),
            ("up_next", "Add to &Up Next", "Ctrl+Alt+Enter", "After anything queued."),
            ("", "", "", ""),
            ("shuffle", "&Shuffle", "Ctrl+H", "Play in a shuffled order."),
            ("reshuffle", "Shuffle &Again", "Ctrl+Shift+H", "A new shuffled order."),
            ("repeat", "Repea&t", "Ctrl+R", "Off, the whole playlist, or this item."),
            ("stop_after", "Stop After This &Item", "Ctrl+Alt+S", "Once."),
            ("", "", "", ""),
            ("summary", "Playlist Su&mmary", "Ctrl+T", "What plays, and the playlist in a breath."),
        ),
    ),
)

#: Verbs whose menu item is a check item, ticked when the state is on.
CHECK_VERBS = frozenset({"shuffle", "stop_after", "follow_folder"})

#: Only the modeless window has a Close item: the modal dialog closes with
#: its own Close button and Escape.
_MODELESS_ONLY = frozenset({"close"})

_KEY_NAMES = {
    "UP": "Up",
    "DOWN": "Down",
    "LEFT": "Left",
    "RIGHT": "Right",
    "HOME": "Home",
    "END": "End",
    "DELETE": "Delete",
    "DEL": "Delete",
    "INSERT": "Insert",
    "INS": "Insert",
    "ENTER": "Enter",
    "RETURN": "Enter",
    "SPACE": "Space",
}


def canonical(chord: str) -> str:
    """``"shift+alt+up"`` -> ``"Alt+Shift+Up"``: one spelling per chord."""
    parts = [part.strip() for part in chord.split("+") if part.strip()]
    if not parts:
        return ""
    key = parts[-1].upper()
    mods = {part.upper() for part in parts[:-1]}
    name = _KEY_NAMES.get(key, key if len(key) > 1 else key.upper())
    if name.startswith("F") and name[1:].isdigit():
        name = name.upper()
    ordered = [label for label in ("Ctrl", "Alt", "Shift") if label.upper() in mods]
    return "+".join([*ordered, name])


def chord_of_event(event: Any, wx: Any) -> str:
    """The canonical chord a key event is, or ``""`` for keys nobody names."""
    code = event.GetKeyCode()
    named = {
        wx.WXK_UP: "Up",
        wx.WXK_DOWN: "Down",
        wx.WXK_LEFT: "Left",
        wx.WXK_RIGHT: "Right",
        wx.WXK_HOME: "Home",
        wx.WXK_END: "End",
        wx.WXK_DELETE: "Delete",
        wx.WXK_NUMPAD_DELETE: "Delete",
        wx.WXK_INSERT: "Insert",
        wx.WXK_NUMPAD_INSERT: "Insert",
        wx.WXK_RETURN: "Enter",
        wx.WXK_NUMPAD_ENTER: "Enter",
        wx.WXK_SPACE: "Space",
    }
    if code in named:
        key = named[code]
    elif wx.WXK_F1 <= code <= wx.WXK_F12:
        key = f"F{code - wx.WXK_F1 + 1}"
    elif 32 < code < 127:
        key = chr(code).upper()
    else:
        return ""
    mods = []
    if event.ControlDown():
        mods.append("Ctrl")
    if event.AltDown():
        mods.append("Alt")
    if event.ShiftDown():
        mods.append("Shift")
    return canonical("+".join([*mods, key]))


def key_table(*, modeless: bool) -> dict[str, str]:
    """Canonical chord -> verb, for every keyed row this window shape has."""
    table: dict[str, str] = {}
    for _title, rows in MENUS:
        for verb, _label, key, _help in rows:
            if verb and key and (modeless or verb not in _MODELESS_ONLY):
                table[canonical(key)] = verb
    return table


def install_menu_bar(window: Any, wx: Any, run: Callable[[str], None]) -> dict[str, Any]:
    """Build the window's menu bar. Returns verb -> menu item, for check marks.

    The Station and Window menus are the app's own (``surface_app_menu`` and
    the window manager), so Alt+S and Alt+W mean here what they mean everywhere.
    """
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
    from quill.ui.radio import surface_app_menu

    refs.extend(
        surface_app_menu.install(
            win=window._win,
            host=window._host,
            menu_bar=menu_bar,
            wx=wx,
            skip=("open_local_media",),  # Ctrl+O is Add Media Files in here
        )
    )
    window._windows.install(window._win, menu_bar)
    window._win.SetMenuBar(menu_bar)
    return items


def _row(verb: str) -> tuple[str, str]:
    for _title, rows in MENUS:
        for candidate, label, key, _help in rows:
            if candidate == verb:
                return label, key
    return verb, ""


#: The item context menu: ``(verb, label)``; the key comes from :data:`MENUS`
#: where the menu bar has the same verb. Access keys are unique in this menu.
ITEM_POPUP: tuple[tuple[str, str], ...] = (
    ("play", "&Play"),
    ("pause", "Pau&se or Resume"),
    ("play_next", "Play Ne&xt"),
    ("up_next", "Add to &Up Next"),
    ("", ""),
    ("move", "&Move"),
    ("cut", "Cu&t"),
    ("copy", "&Copy"),
    ("paste_before", "Paste &Before"),
    ("paste_after", "Paste &After"),
    ("insert_before", "&Insert Files Here..."),
    ("insert_after", "I&nsert Files After..."),
    ("", ""),
    ("remove", "&Remove from Playlist"),
    ("locate", "Locate &File..."),
    ("show_in_folder", "Show in Fi&le Explorer"),
    ("properties", "Prop&erties..."),
)

MOVE_POPUP: tuple[tuple[str, str], ...] = (
    ("move_up", "Move &Up"),
    ("move_down", "Move &Down"),
    ("move_top", "Move to &Top"),
    ("move_bottom", "Move to &Bottom"),
    ("move_to", "Move to &Position..."),
)


def popup(
    window: Any,
    wx: Any,
    rows: list[tuple[str, str]],
    run: Callable[[str], None],
    *,
    keys: dict[str, str] | None = None,
) -> Any:
    """A context menu of *rows*, each label carrying its key where it has one.

    The key text after the tab is what a screen reader reads with the item; a
    popup menu binds nothing by it, so it only ever *says* the key the window
    already answers to. *keys* overrides a verb's key (Enter, rather than the
    menu bar's Ctrl+Enter, on the row the cursor is in).
    """
    menu = wx.Menu()
    refs = []
    for verb, label in rows:
        if not verb:
            if menu.GetMenuItemCount():
                menu.AppendSeparator()
            continue
        if verb == "move":
            sub = popup(window, wx, list(MOVE_POPUP), run)
            menu.AppendSubMenu(sub, label)
            continue
        key = (keys or {}).get(verb, _row(verb)[1])
        item_id = wx.NewIdRef()
        refs.append(item_id)
        menu.Append(item_id, f"{label}\t{key}" if key else label)
        menu.Bind(wx.EVT_MENU, lambda _e, v=verb: run(v), id=item_id)
    window._context_id_refs = [*getattr(window, "_context_id_refs", []), *refs]
    return menu
