"""Marks in Browse Stations: add many stations to Favorites, or remove many rows.

The Favorites marking keys (:mod:`quill.ui.radio.marks_shared`), in the Browse
tree. A row can be marked when it is a station, or when Delete could remove it:
a saved YouTube video or playlist, a followed channel, a server you added, or a
station that is one of your favorites (wherever in the tree it appears). Any
other row says what can be marked instead of doing nothing.

**Add to Favorites** with stations marked -- the window's Add to Favorites
button, which then reads "Add 3 Marked to Favorites" and is Alt+O from
anywhere in the window, the tree included -- adds every marked station that is
not already a favorite, says how many were added and how many were there
already, and clears the marks. It asks nothing: adding is undone by removing,
and nothing is lost. A station that only resolves when played (TuneIn) has no
stream to save until then, so it cannot be marked; the button on it alone still
resolves and adds it, as before.

No chord of its own, on purpose: every Ctrl+Alt and Ctrl+Shift letter is
already a command somewhere in Quill Radio (Ctrl+Alt+F, the obvious one, is
Repair FFmpeg), and the button's access key was already the way to add a
favorite here. The button's labels keep the one access key, O, in every
state; they used to switch to F, which Refresh also claims (GATE-14).

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

from quill.core.counted import plural
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
    "add_marked_to_favorites",
    "favorite_button",
    "handle_key",
    "label",
    "remove_marked",
    "row_text",
    "sync_favorite_button",
    "toggle_selected",
]

_NOUN = "item"

CANNOT_MARK = (
    "Only stations, and rows Delete can remove, can be marked: a saved YouTube "
    "video or playlist, a followed channel, or a server you added."
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


def _stations(dialog: Any) -> dict[str, Any]:
    """Node id -> the station on a marked row, for Add to Favorites."""
    stations = getattr(dialog, "_marked_stations", None)
    if stations is None:
        stations = {}
        dialog._marked_stations = stations
    return stations


def toggle_selected(dialog: Any) -> None:
    """Mark or unmark the selected row, saying the running count."""
    tree = dialog._tree
    node = tree.GetSelection()
    data = dialog._node_data(node) if node is not None else None
    what = _what(dialog, data)
    station = data.get("station") if data is not None else None
    if data is None or (what is None and station is None):
        dialog._announce(CANNOT_MARK)
        return
    node_id = str(data.get("node_id") or "")
    marks = marks_on(dialog)
    now_marked = marks.toggle(node_id)
    rows, stations = _rows(dialog), _stations(dialog)
    rows.pop(node_id, None)
    stations.pop(node_id, None)
    if now_marked and what is not None:
        rows[node_id] = what
    if now_marked and station is not None:
        stations[node_id] = station
    tree.SetItemText(node, _with_mark(str(tree.GetItemText(node)), now_marked))
    sync_favorite_button(dialog)
    dialog._announce(marks.toggle_sentence(now_marked))


def _forget_marks(dialog: Any) -> None:
    """Every mark gone: the set, what it pointed at, and the rows' "(marked)"."""
    marks_on(dialog).clear()
    _rows(dialog).clear()
    _stations(dialog).clear()
    _unmark_all_rows(dialog)
    sync_favorite_button(dialog)


def _addable(dialog: Any) -> list[Any]:
    """The marked stations, in the order marked, each once."""
    stations = _stations(dialog)
    seen: set[str] = set()
    found: list[Any] = []
    for node_id in marks_on(dialog).keys:
        station = stations.get(node_id)
        if station is None:
            continue
        key = str(getattr(station, "station_uuid", "") or getattr(station, "stream_url", ""))
        if key and key not in seen:
            seen.add(key)
            found.append(station)
    return found


def add_marked_to_favorites(dialog: Any) -> bool:
    """Add every marked station to Favorites. Returns whether any was added.

    One sentence, every clause a number (GATE-BULK-COUNT): how many were added
    and how many were favorites already. The marks are cleared afterwards --
    the job they were made for is done.
    """
    stations = _addable(dialog)
    marked = len(marks_on(dialog))
    if not stations:
        dialog._announce(
            f"None of the {plural(marked, 'marked row')} is a station to add to Favorites."
        )
        return False
    added = sum(1 for station in stations if dialog._favorites.add(station))
    already = len(stations) - added
    said = f"Added {plural(added, 'station')} to Favorites."
    if already:
        verb = "was" if already == 1 else "were"
        said += f" {already} {verb} already there."
    _forget_marks(dialog)
    if added:
        dialog._on_favorites_changed()
        dialog._refresh_favorites_branch()
    dialog._announce(said)
    return added > 0


def favorite_button(dialog: Any) -> None:
    """The Add to Favorites button: every marked station while any are marked,
    otherwise the highlighted row's add-or-remove, as it always was."""
    if _addable(dialog):
        add_marked_to_favorites(dialog)
        return
    dialog._toggle_favorite()


def sync_favorite_button(dialog: Any) -> None:
    """While stations are marked, the button says it adds them and can be
    pressed from any row. Nothing is spoken: the marking key said the count."""
    count = len(_addable(dialog))
    button = dialog._favorite_btn
    if count:
        button.SetLabel(f"Add {count} Marked t&o Favorites")
        button.Enable(True)
        return
    if "Marked" in str(button.GetLabel()):
        # Put back what the highlighted row's own button says. The label is
        # reset first, so describe_selection's own call back here stops.
        from quill.ui.radio.browse_details import describe_selection

        button.SetLabel("Add t&o Favorites")
        describe_selection(dialog, dialog._selected_data())


def remove_marked(dialog: Any) -> bool:
    """Ask once, then remove every marked row. Returns whether any went."""
    from quill.ui.radio import browse_delete

    marks = marks_on(dialog)
    rows = _rows(dialog)
    doomed = [(node_id, rows[node_id]) for node_id in marks.keys if node_id in rows]
    if not doomed:
        count = plural(len(marks), "marked row")
        dialog._announce(f"None of the {count} can be deleted. Alt+O adds them to Favorites.")
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
    _forget_marks(dialog)
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
        _forget_marks(dialog)
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
