"""F1 on Quill Inkwell's Abbreviations list: why the selected entry will not expand (FUX-10).

The list marks an entry that is turned off with "(disabled)", but nothing said
what that means or where to turn it back on. F1 on the list now says so for
the selected entry, and nothing for one that is on. Asked only when F1 is
pressed.
"""

from __future__ import annotations

from typing import Any

__all__ = ["DISABLED", "describe_selected_row", "install"]

DISABLED = (
    "This abbreviation is disabled, so typing it does not expand it. To turn it "
    "back on, press Ctrl+M for Manage Abbreviations, select it, and press "
    "Enable/Disable (Alt+B), or check Enabled in its Edit dialog."
)


def describe_selected_row(host: Any) -> str:
    """The selected entry's paragraph: :data:`DISABLED`, or "" when it is on."""
    index = host._list.GetFirstSelected()
    entries = host._library.abbreviations
    if not 0 <= index < len(entries):
        return ""
    return "" if entries[index].enabled else DISABLED


def install(host: Any) -> None:
    """Give the Abbreviations list its F1 paragraph about the selected entry."""
    from quill.ui import app_context_help

    app_context_help.set_selection_help(host._list, lambda: describe_selected_row(host))


def fill_list(host: Any) -> None:
    """Fill Inkwell's abbreviation list, and keep F1 on a row saying its situation."""
    install(host)  # F1 says why a disabled entry will not expand
    host._list.DeleteAllItems()
    for i, entry in enumerate(host._library.abbreviations):
        label = entry.abbreviation if entry.enabled else f"{entry.abbreviation} (disabled)"
        host._list.InsertItem(i, label)
        host._list.SetItem(i, 1, entry.expansion.replace("\n", " ")[:60])
        host._list.SetItem(i, 2, entry.category)
