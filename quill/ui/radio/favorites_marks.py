"""Mark many favourites, then remove them with one question (xradio2 4.10).

Shared by the two favourites trees -- the main window's and Manage Favorites
-- so the key, the words and the confirmation cannot drift between them. The
rule itself (what a mark is, what is said) is wx-free in
:mod:`quill.core.radio.row_marks`; this module is the tree half: the key, the
row text, and the one confirmation.

* ``.`` (period, or the keypad's decimal point) marks or unmarks the selected
  station and says how many are marked. The row's text gains "(marked)", so
  arrowing back over it says so without anything being announced.
* Delete, while anything is marked, removes **every** marked station after one
  question that says how many: "Delete 5 stations?". With nothing marked it
  removes the selected row exactly as before.
* Ctrl+Shift+Delete clears every mark (also Clear Marks on the context menu).
  Escape is not taken: it already closes Manage Favorites.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio.favorites import RadioFavoritesStore
from quill.core.radio.row_marks import (
    RowMarks,
    delete_question,
    deleted_sentence,
    landing_after,
    marked_label,
)

__all__ = [
    "clear_marks",
    "dialog_marks",
    "dialog_menu_entries",
    "handle_dialog_key",
    "handle_key",
    "is_mark_key",
    "label_for",
    "mark_menu_entries",
    "remove_and_land",
    "remove_marked",
    "selected_key",
    "station_keys",
    "toggle_selected",
]

_NOUN = "station"


def is_mark_key(wx: Any, event: Any) -> bool:
    """Plain ``.`` or the keypad's decimal point, with no modifier held."""
    if event.ControlDown() or event.AltDown() or event.ShiftDown():
        return False
    return event.GetKeyCode() in (ord("."), getattr(wx, "WXK_NUMPAD_DECIMAL", -1))


def label_for(marks: RowMarks | None, key: str, label: str) -> str:
    """The row text for a station, with "(marked)" when it carries a mark."""
    return marked_label(label, marks is not None and key in marks)


def toggle_selected(
    tree: Any,
    marks: RowMarks,
    store: RadioFavoritesStore,
    *,
    announce: Callable[[str], None],
) -> bool:
    """Mark or unmark the selected station row. Returns whether it acted.

    The row's text is rewritten in place rather than the tree rebuilt, so the
    cursor stays exactly where it was. A folder is not marked: deleting a
    folder is a different question (its stations are kept), and mixing the two
    in one count would make the count a lie.
    """
    item = tree.GetSelection()
    if not item.IsOk():
        return False
    data = tree.GetItemData(item)
    if not (isinstance(data, tuple) and len(data) == 2 and data[0] == "station"):
        announce("Only stations can be marked.")
        return True
    favorite = store.find(data[1])
    if favorite is None:
        return False
    now_marked = marks.toggle(favorite.key)
    tree.SetItemText(item, marked_label(favorite.display_label, now_marked))
    announce(marks.toggle_sentence(now_marked))
    return True


def remove_marked(
    parent: Any,
    store: RadioFavoritesStore,
    marks: RowMarks,
    *,
    announce: Callable[[str], None],
    ask: Callable[[str], bool] | None = None,
) -> bool:
    """Ask once, then remove every marked station. Returns whether any went.

    *ask* is the yes/no question (a ``wx.MessageBox`` by default); the tests
    pass a fake. The answer defaults to No, because the question is about many
    rows at once and Enter pressed by habit should cost nothing.
    """
    marks.keep_only(favorite.key for favorite in store.favorites)
    count = len(marks)
    if count == 0:
        return False
    question = delete_question(count, _NOUN)
    if not (ask or _ask_with_message_box(parent))(question):
        announce("Nothing was deleted.")
        return False
    removed = sum(1 for key in marks.keys if store.remove(key))
    marks.clear()
    announce(deleted_sentence(removed, _NOUN, failed=count - removed))
    return removed > 0


def mark_menu_entries(
    marks: RowMarks | None,
    *,
    toggle: Callable[[], None],
    remove: Callable[[], None],
    clear: Callable[[], None],
) -> list[tuple[str, Callable[[], None]]]:
    """The context-menu rows for marking, each showing its key.

    While anything is marked, Delete means "remove the marked stations", so the
    row that says so is the one carrying the Delete key -- the caller drops its
    single-row Remove... entry then, keeping one claimant per key.
    """
    entries: list[tuple[str, Callable[[], None]]] = [("Mark &for Deleting\t.", toggle)]
    if marks:
        entries.append((f"&Remove {len(marks)} Marked...\tDelete", remove))
        entries.append(("&Clear Marks\tCtrl+Shift+Delete", clear))
    return entries


def clear_marks(marks: RowMarks, *, announce: Callable[[str], None]) -> int:
    """Unmark everything and say how many were unmarked."""
    count = marks.clear()
    announce(f"Cleared {count} mark{'' if count == 1 else 's'}." if count else "Nothing marked.")
    return count


def handle_key(
    wx: Any,
    event: Any,
    *,
    tree: Any,
    marks: RowMarks,
    store: RadioFavoritesStore,
    parent: Any,
    announce: Callable[[str], None],
    changed: Callable[[str | None], None],
) -> bool:
    """The tree's marking keys. Returns True when the key was used.

    ``.`` toggles a mark; Delete removes the marked stations when there are
    any (otherwise it is left to the tree's own single-row Delete); and
    Ctrl+Shift+Delete clears every mark. *changed* runs after stations were
    removed or marks cleared, with the station key the cursor should land on,
    so the caller saves and redraws without dropping the listener at the top.
    """
    if is_mark_key(wx, event):
        toggle_selected(tree, marks, store, announce=announce)
        return True
    code = event.GetKeyCode()
    if code not in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
        return False
    if event.ControlDown() and event.ShiftDown() and not event.AltDown():
        clear_marks(marks, announce=announce)
        changed(selected_key(tree))
        return True
    if event.ControlDown() or event.AltDown() or event.ShiftDown():
        return False
    marks.keep_only(favorite.key for favorite in store.favorites)
    if not marks:
        return False
    remove_and_land(tree, parent, store, marks, announce=announce, changed=changed)
    return True


def remove_and_land(
    tree: Any,
    parent: Any,
    store: RadioFavoritesStore,
    marks: RowMarks,
    *,
    announce: Callable[[str], None],
    changed: Callable[[str | None], None],
) -> None:
    """:func:`remove_marked`, then redraw with the cursor on a surviving row."""
    order = station_keys(tree)
    doomed = marks.keys
    landing = landing_after(order, selected_key(tree), doomed)
    if remove_marked(parent, store, marks, announce=announce):
        changed(landing)
        if landing is None:
            announce("No favorites left.")


def selected_key(tree: Any) -> str | None:
    """The selected station's key, or ``None`` on a folder or nothing."""
    item = tree.GetSelection()
    if not item.IsOk():
        return None
    data = tree.GetItemData(item)
    if isinstance(data, tuple) and len(data) == 2 and data[0] == "station":
        return str(data[1])
    return None


def station_keys(tree: Any) -> list[str]:
    """Every station key in the order the tree shows them, folders walked."""
    keys: list[str] = []

    def walk(parent: Any) -> None:
        child, cookie = tree.GetFirstChild(parent)
        while child.IsOk():
            data = tree.GetItemData(child)
            if isinstance(data, tuple) and len(data) == 2 and data[0] == "station":
                keys.append(str(data[1]))
            walk(child)
            child, cookie = tree.GetNextChild(parent, cookie)

    root = tree.GetRootItem()
    if root.IsOk():
        walk(root)
    return keys


def dialog_marks(dialog: Any) -> RowMarks:
    """Manage Favorites' marks, made on first use (kept off its constructor,
    which GATE-11 holds at its budget)."""
    marks = getattr(dialog, "_delete_marks", None)
    if marks is None:
        marks = RowMarks()
        dialog._delete_marks = marks
    return marks


def handle_dialog_key(dialog: Any, event: Any) -> bool:
    """:func:`handle_key` for the Manage Favorites window."""
    return handle_key(
        dialog._wx,
        event,
        tree=dialog._tree,
        marks=dialog_marks(dialog),
        store=dialog._store,
        parent=dialog.dialog,
        announce=dialog._announce,
        changed=dialog._changed,
    )


def dialog_menu_entries(
    dialog: Any, entries: list[tuple[str, Callable[[], None]]]
) -> list[tuple[str, Callable[[], None]]]:
    """Manage Favorites' station menu with the marking rows added."""
    marks = dialog_marks(dialog)
    if marks:
        entries = [entry for entry in entries if not entry[0].startswith("&Remove...")]

    def remove() -> None:
        remove_and_land(
            dialog._tree,
            dialog.dialog,
            dialog._store,
            marks,
            announce=dialog._announce,
            changed=dialog._changed,
        )

    def clear() -> None:
        clear_marks(marks, announce=dialog._announce)
        dialog._refresh_tree(selected_key(dialog._tree))

    return entries + mark_menu_entries(
        marks,
        toggle=lambda: toggle_selected(
            dialog._tree, marks, dialog._store, announce=dialog._announce
        ),
        remove=remove,
        clear=clear,
    )


def _ask_with_message_box(parent: Any) -> Callable[[str], bool]:
    def ask(question: str) -> bool:
        import wx

        answer = wx.MessageBox(  # MSGBOX-OK: parented confirmation for a shared action
            question,
            "Delete Marked Stations",
            wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
            parent,
        )
        return bool(answer == wx.YES)

    return ask
