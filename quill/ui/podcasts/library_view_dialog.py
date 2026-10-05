"""View > Rearrange Library and Inbox... (Ctrl+Shift+R).

Every way to lay out the library and the Inbox.

One small window of choices that take effect as you make them -- the library
behind it redraws on each change, so a listener can try "Folders only", hear
the tree, and try something else without closing anything. Close keeps what
is chosen; there is nothing to save. The same settings are in Preferences >
The library and The Inbox.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.podcasts import library_view
from quill.core.podcasts.settings_defs_views import (
    FOLDER_SORTS,
    FOLDERS_OPEN,
    INBOX_LAYOUTS,
    LIBRARY_COUNTS,
    LIBRARY_LAYOUTS,
)

__all__ = ["TITLE", "SHOW_SORTS", "open_library_view"]

TITLE = "Rearrange Library and Inbox"

#: The podcast orders, worded as Preferences words them.
SHOW_SORTS = (
    ("title_az", "Title, A to Z"),
    ("title_za", "Title, Z to A"),
    ("unheard_first", "Most unheard first"),
    ("recently_updated", "Recently updated first"),
    ("custom", "My own order"),
)

#: (setting id, label with its access key, choices, help).
_CHOICES: tuple[tuple[str, str, tuple[tuple[str, str], ...], str], ...] = (
    (
        "library_layout",
        "Show the &library as:",
        LIBRARY_LAYOUTS,
        "Folders first, folders only, podcasts without folders, or folders and "
        "podcasts together by name. No podcast is ever hidden.",
    ),
    (
        "show_sort_mode",
        "Sort &podcasts by:",
        SHOW_SORTS,
        "The order podcasts are listed in, inside each folder and at the top level.",
    ),
    (
        "folder_sort_mode",
        "Sort &folders by:",
        FOLDER_SORTS,
        "The order folders are listed in, in the library and in the Inbox.",
    ),
    (
        "library_folders_open",
        "Folders &start:",
        FOLDERS_OPEN,
        "Whether folders show their podcasts straight away, or stay closed until "
        "you open one with the Right arrow.",
    ),
    (
        "library_counts",
        "&Counts say:",
        LIBRARY_COUNTS,
        "What the number beside each folder and podcast tells you.",
    ),
    (
        "inbox_layout",
        "Show the &Inbox as:",
        INBOX_LAYOUTS,
        "Every episode in one list, folders first and then the rest, or folders "
        "only. Enter on a folder shows its episodes; Backspace comes back.",
    ),
)


def _index(table: tuple[tuple[str, str], ...], value: object) -> int:
    for index, (item, _label) in enumerate(table):
        if item == value:
            return index
    return 0


def current(library: Any, setting_id: str) -> object:
    if setting_id == "show_sort_mode":
        return library.settings.show_sort_mode
    return library_view.setting(library, setting_id)


def open_library_view(host: Any) -> None:
    """Show the window; each change is stored and drawn at once."""
    import wx

    from quill.ui.dialog_contract import apply_modal_ids

    library = host._podcast_library
    dialog = wx.Dialog(host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE)
    root = wx.BoxSizer(wx.VERTICAL)
    grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
    grid.AddGrowableCol(1, 1)
    first: Any = None

    def on_choice(setting_id: str, table: tuple[tuple[str, str], ...]) -> Callable[[Any], None]:
        def handler(event: Any) -> None:
            value = table[max(0, event.GetEventObject().GetSelection())][0]
            apply(host, setting_id, value)

        return handler

    for setting_id, label, table, help_text in _CHOICES:
        grid.Add(wx.StaticText(dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
        choice = wx.Choice(dialog, choices=[words for _value, words in table])
        choice.SetSelection(_index(table, current(library, setting_id)))
        choice.SetHelpText(help_text)
        choice.Bind(wx.EVT_CHOICE, on_choice(setting_id, table))
        grid.Add(choice, 1, wx.EXPAND)
        first = first or choice
    root.Add(grid, 0, wx.EXPAND | wx.ALL, 10)

    empty = wx.CheckBox(dialog, label="Leave out folders with &nothing in them")
    empty.SetValue(bool(library_view.setting(library, "library_hide_empty_folders")))
    empty.SetHelpText(
        "Empty folders are still there, and come back the moment a podcast is filed in one."
    )
    empty.Bind(
        wx.EVT_CHECKBOX,
        lambda _e: apply(host, "library_hide_empty_folders", bool(empty.GetValue())),
    )
    root.Add(empty, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    buttons.AddStretchSpacer(1)
    close = wx.Button(dialog, wx.ID_CANCEL, label="Close")
    close.SetHelpText("Closes this window. Every choice above is already in effect.")
    buttons.Add(close, 0)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
    dialog.SetSizer(root)
    dialog.Fit()
    apply_modal_ids(dialog, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
    if first is not None:
        first.SetFocus()
    try:
        host._show_modal_dialog(dialog, TITLE)
    finally:
        dialog.Destroy()


def apply(host: Any, setting_id: str, value: object) -> bool:
    """Store one view choice, save, and redraw what is showing."""
    library = host._podcast_library
    if setting_id == "show_sort_mode":
        if library.settings.show_sort_mode == value:
            return False
        host._set_show_sort_mode(str(value), announce=False)
    elif not library_view.set_setting(library, setting_id, value):
        return False
    host._save_podcast_library()
    refresh = getattr(host, "_refresh_view_layout_menu", None)
    if callable(refresh):
        refresh()
    host._refresh_place(keep=True)
    return True
