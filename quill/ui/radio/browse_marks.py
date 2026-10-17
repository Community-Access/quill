"""Marks in Browse Stations: remove many rows with one question.

The Favorites marking keys (:mod:`quill.ui.radio.marks_shared`), in the Browse
tree. A row can be marked when Delete could remove it: a saved YouTube video
or playlist, a followed channel, a server you added, or a station that is one
of your favorites (wherever in the tree it appears). Any other row says what
can be marked instead of doing nothing.

Delete with rows marked removes **every** marked row after one question
("Delete 4 items?"), the same question Browse's own Delete asks -- so a
listener who checked "Don't ask me again" there is not asked here either --
and then reloads each branch that lost a row. Each removal runs the code the
single-row Delete runs (:mod:`quill.ui.radio.browse_delete`); nothing here is
a second implementation of "remove".

Marks are keyed by the row's node id, so a branch that reloads keeps its
marks and its rows still read "(marked)".
"""

from __future__ import annotations

from typing import Any

from quill.core.radio.browse_nodes import split_id
from quill.core.radio.row_marks import (
    MARK_SUFFIX,
    delete_question,
    deleted_sentence,
    marked_label,
)
from quill.ui.radio.marks_shared import (
    ACT,
    CLEAR,
    TOGGLE,
    clear_marks,
    mark_action,
    marks_on,
    say_ignored,
)

__all__ = [
    "CANNOT_MARK",
    "handle_key",
    "label",
    "remove_marked",
    "row_text",
    "toggle_selected",
]

_NOUN = "item"

CANNOT_MARK = (
    "Only rows Delete can remove can be marked: a saved YouTube video or "
    "playlist, a followed channel, a server you added, or a favorite station."
)


def label(dialog: Any, node_id: str, text: str) -> str:
    """A row's text, with "(marked)" when its node carries a mark."""
    marks = getattr(dialog, "_row_marks", None)
    return _with_mark(text, marks is not None and node_id in marks)


def row_text(dialog: Any, child: Any) -> str:
    """The Browse window's ``_row_label``: the row's text
    (:func:`quill.core.radio.browse_helpers.row_label`), marked when marked."""
    from quill.core.radio.browse_helpers import row_label

    return label(dialog, child.node_id, row_label(child))


def _with_mark(text: str, marked: bool) -> str:
    """*text* with "(marked)" set or taken off, placed after the row's name
    and before the "  (3 items)" note the tree adds, so the name is still
    what the row starts with."""
    head, sep, tail = text.partition("  (")
    return f"{marked_label(head.removesuffix(MARK_SUFFIX), marked)}{sep}{tail}"


def _what(dialog: Any, data: dict | None) -> tuple[str, Any] | None:
    """How a row would be removed: ("stored", (kind, args)) or ("favorite",
    station); ``None`` when Delete has nothing to remove on it."""
    from quill.ui.radio.browse_delete import _REMOVABLE

    if data is None:
        return None
    kind, args = split_id(str(data.get("node_id") or ""))
    if kind in _REMOVABLE and args and args[0]:
        return ("stored", (kind, list(args)))
    station = data.get("station")
    if station is not None and dialog._favorites.contains(station):
        return ("favorite", station)
    return None


def _rows(dialog: Any) -> dict[str, tuple[str, Any]]:
    rows = getattr(dialog, "_marked_rows", None)
    if rows is None:
        rows = {}
        dialog._marked_rows = rows
    return rows


def toggle_selected(dialog: Any) -> None:
    """Mark or unmark the selected row, saying the running count."""
    tree = dialog._tree
    node = tree.GetSelection()
    data = dialog._node_data(node) if node is not None else None
    what = _what(dialog, data)
    if what is None or data is None:
        dialog._announce(CANNOT_MARK)
        return
    node_id = str(data.get("node_id") or "")
    marks = marks_on(dialog)
    now_marked = marks.toggle(node_id)
    rows = _rows(dialog)
    if now_marked:
        rows[node_id] = what
    else:
        rows.pop(node_id, None)
    tree.SetItemText(node, _with_mark(str(tree.GetItemText(node)), now_marked))
    dialog._announce(marks.toggle_sentence(now_marked))


def remove_marked(dialog: Any) -> bool:
    """Ask once, then remove every marked row. Returns whether any went."""
    from quill.ui.radio import browse_delete

    marks = marks_on(dialog)
    rows = _rows(dialog)
    doomed = [(node_id, rows[node_id]) for node_id in marks.keys if node_id in rows]
    if not doomed:
        return False
    if not browse_delete.confirm(dialog, delete_question(len(doomed), _NOUN)):
        dialog._announce("Nothing was deleted.")
        return False
    roots: set[str] = set()
    done_favorites: set[str] = set()
    removed = failed = 0
    for _node_id, (how, target) in doomed:
        try:
            if how == "stored":
                roots.add(browse_delete.remove_stored_now(*target))
            else:
                key = str(getattr(target, "station_uuid", "") or getattr(target, "stream_url", ""))
                if key not in done_favorites:  # one station, shown in two branches
                    done_favorites.add(key)
                    browse_delete.unfavorite_now(dialog, target)
            removed += 1
        except Exception:  # noqa: BLE001 - one failed row must not stop the rest
            failed += 1
    marks.clear()
    rows.clear()
    for root in sorted(roots):
        browse_delete.reload_branch(dialog, root)
    dialog._announce(deleted_sentence(removed, _NOUN, failed=failed))
    return removed > 0


def handle_key(dialog: Any, event: Any) -> bool:
    """The tree's marking keys. True when the key was used.

    Plain Delete with nothing marked is left to the single-row Delete
    (``browse_delete``), exactly as before.
    """
    action = mark_action(dialog._wx, event)
    if action == TOGGLE:
        toggle_selected(dialog)
        return True
    if action == CLEAR:
        clear_marks(marks_on(dialog), announce=dialog._announce)
        _rows(dialog).clear()
        _unmark_all_rows(dialog)
        return True
    if action == ACT and marks_on(dialog):
        remove_marked(dialog)
        return True
    wx = dialog._wx
    if event.GetKeyCode() in (getattr(wx, "WXK_RETURN", -1), getattr(wx, "WXK_NUMPAD_ENTER", -1)):
        # Enter plays or opens the selected row only. While rows are marked it
        # says so once, after the row's own answer, and still does its job.
        dialog._wx.CallAfter(say_ignored, dialog)
    return False


def _unmark_all_rows(dialog: Any) -> None:
    """Take "(marked)" off every row on screen after Clear Marks."""
    tree = dialog._tree

    def walk(parent: Any) -> None:
        child, cookie = tree.GetFirstChild(parent)
        while child.IsOk():
            text = str(tree.GetItemText(child))
            if MARK_SUFFIX in text:
                tree.SetItemText(child, _with_mark(text, False))
            walk(child)
            child, cookie = tree.GetNextChild(parent, cookie)

    root = tree.GetRootItem()
    if root.IsOk():
        walk(root)
