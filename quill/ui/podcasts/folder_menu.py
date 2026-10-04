"""The folder row's own menu: play it, queue it, move it, export it, set it.

Cast had a folder tree with nothing on it. Every item here is new, and every one
of them is an action *on the folder* rather than on something inside it.

Its own module because ``manager_dialog`` is at its GATE-11 ceiling, and because
the ordering decision belongs beside the items: **the listening verbs come
first**. A context menu is read from the top, and Play All is what somebody
opening a folder menu wants far more often than Rename.

Mnemonics are chosen against the whole popup this joins, which already carries
Rename (m), Delete (D) and New Folder (N) below.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["append_folder_items", "folder_items"]


def folder_items(
    dialog: Any, folder_id: str, *, settings: bool = True
) -> list[tuple[str, Callable[[], None]]]:
    """The label and handler for each folder action, in menu order.

    *dialog* is QUILL's Podcast Manager or QUILL Cast's one window -- both
    answer the names :mod:`folder_commands` reads. ``settings=False`` leaves
    out Folder Settings, which Cast does not offer: there a podcast's settings
    are set one podcast at a time.
    """
    from quill.ui.podcasts import folder_commands

    items: list[tuple[str, Callable[[], None]]] = [
        ("&Play All Unheard", lambda: folder_commands.play_folder(dialog, folder_id)),
        ("Add All to &Queue", lambda: folder_commands.add_folder_to_queue(dialog, folder_id)),
        ("Move &Up", lambda: folder_commands.reorder(dialog, folder_id, -1)),
        ("Move Dow&n", lambda: folder_commands.reorder(dialog, folder_id, 1)),
    ]
    if settings:
        items.append((
            "Folder &Settings...",
            lambda: folder_commands.open_folder_settings(dialog, folder_id),
        ))
    items.append((
        "&Export This Folder as OPML...",
        lambda: folder_commands.export_folder_opml(dialog, folder_id),
    ))
    return items


def append_folder_items(dialog: Any, menu: Any, folder_id: str) -> None:
    """Add the folder actions to *menu*, followed by a separator."""
    import wx

    for label, handler in folder_items(dialog, folder_id):
        item = menu.Append(wx.ID_ANY, label)
        menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), item)
    menu.AppendSeparator()
