"""Insert > Markdown Tag, which is on the menu only in a Markdown document.

Reported from both editors: "in either a Rich Text or Plain Text document, the
item for inserting a Markdown tag in the Insert menu is unavailable." It was
dimmed there, which a reader announces as unavailable and then leaves somebody
wondering what they did wrong. The owner's decision (2026-10-04) is that the row
is simply **not there** outside Markdown, in QUILL and QUILL Lite alike: a rich
document has real formatting and a plain one has none, so neither has any use
for a picker of Markdown syntax.

Hidden, not deleted. The row keeps its id, its handler and its key, so pressing
the key in a document of the wrong kind still reaches the command -- which then
says why nothing happened, in the one sentence below, rather than doing nothing.
A dimmed row could not even do that: Windows does not deliver an accelerator
whose menu item is disabled.

Both editors read the rule and the sentence from here, so they cannot disagree
about either. Takes the wx objects it acts on rather than importing wx, so the
module costs nothing to import where wx is not wanted.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = [
    "MARKDOWN_TAG_REFUSAL",
    "HideableMenuRow",
    "markdown_tag_row_shown",
    "markdown_tags_apply",
    "sync_menu_row",
]

#: What the key says in a document that is not Markdown. Plain on purpose: the
#: person pressing it knows which key they pressed, and what they do not know is
#: why this document is different from the last one.
MARKDOWN_TAG_REFUSAL = "Markdown tags are for Markdown documents."


def markdown_tag_row_shown(kind: str) -> bool:
    """Whether Insert > Markdown Tag belongs on the menu for a *kind* of document.

    *kind* is ``"markdown"``, ``"html"``, ``"plain"`` or ``"rich"``. Only the
    first answers yes: HTML has its own tag picker, and rich and plain text have
    no Markdown to write.
    """
    return kind == "markdown"


def markdown_tags_apply(kind: str, say: Callable[[str], object]) -> bool:
    """True for a Markdown document; otherwise *say* the sentence and False.

    What the command does when its key is pressed, or it is chosen from the
    palette, in a document whose menu does not carry the row.
    """
    if markdown_tag_row_shown(kind):
        return True
    say(MARKDOWN_TAG_REFUSAL)
    return False


class HideableMenuRow:
    """One menu row that can leave its menu and come back to the same place.

    ``wx.Menu.Remove`` detaches the item without destroying it, so its id, its
    label and every ``EVT_MENU`` binding survive the absence; this object holds
    the only reference while the row is away. The place it returns to is
    remembered as "so many rows after a named neighbour" rather than as a fixed
    index, because the rows around it can change while it is gone (Open Recent
    and the Window list are rebuilt) -- and a separator has no id worth naming,
    so the neighbour is the nearest real row above, with the separators between
    counted.
    """

    def __init__(self, menu: Any, item: Any) -> None:
        self.menu = menu
        self.item = item
        self.shown = True
        #: The row's own key, read while it is still on the menu, so a caller can
        #: keep the key alive in an accelerator table while the row is hidden.
        #: ``None`` when the label carries no key wx can parse.
        self.accel = item.GetAccel()
        rows = list(menu.GetMenuItems())
        position = next(
            (index for index, row in enumerate(rows) if row.GetId() == item.GetId()), len(rows)
        )
        self._anchor_id: int | None = None
        self._gap = 0
        for row in reversed(rows[:position]):
            if row.IsSeparator():
                self._gap += 1
                continue
            self._anchor_id = row.GetId()
            break

    def set_shown(self, shown: bool) -> None:
        """Put the row on its menu or take it off. Nothing happens if it is
        already where it was asked to be."""
        shown = bool(shown)
        if shown == self.shown:
            return
        if shown:
            self.menu.Insert(self._home(), self.item)
        else:
            self.menu.Remove(self.item)
        self.shown = shown

    def _home(self) -> int:
        """The index the row goes back to: just after its neighbour and gap."""
        count = int(self.menu.GetMenuItemCount())
        if self._anchor_id is None:
            return min(self._gap, count)
        for index, row in enumerate(self.menu.GetMenuItems()):
            if row.GetId() == self._anchor_id:
                return min(index + 1 + self._gap, count)
        return count


def sync_menu_row(owner: Any, attr: str, menu_bar: Any, item_id: int, shown: bool) -> None:
    """Show or hide the row *item_id* on *menu_bar*, remembering it on *owner*.

    For a menu bar that can be rebuilt (QUILL's is, when features or the keymap
    change): a row found on the bar is always the current one and is adopted
    afresh, and a row not found is the one this owner hid earlier -- from this
    same bar. A bar that never had the row (a profile with the area switched
    off) is left alone.
    """
    item = menu_bar.FindItemById(item_id)
    if item is not None:
        menu = item.GetMenu()
        if menu is None:
            return
        row = HideableMenuRow(menu, item)
        setattr(owner, attr, (menu_bar, row))
    else:
        remembered = getattr(owner, attr, None)
        # A row hidden from an earlier bar is never put back into it: that bar
        # has been replaced, and its menus may already be gone.
        if remembered is None or remembered[0] is not menu_bar:
            return
        row = remembered[1]
    row.set_shown(shown)
