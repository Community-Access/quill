"""Marks in the Schedule Recording list: remove many schedules at once.

The Favorites marking keys (:mod:`quill.ui.radio.marks_shared`), on the list of
scheduled recordings. ``.`` marks the selected schedule and says how many are
marked; the row reads "(marked)". Delete then removes every marked schedule
after one question ("Delete 3 schedules?", default No) -- where a single
Delete removes the selected one straight away, as it always has, because one
schedule is quickly added back and twelve are not.

Edit, Duplicate and Enable or Disable work on the selected schedule only;
while schedules are marked, the first of them to run says so, once, and that
the marks are still there.

This module also owns the list's key handler and its context menu, which moved
here from ``schedule_recording_dialog`` under GATE-11 when marking arrived.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio.row_marks import (
    delete_question,
    deleted_sentence,
    landing_after,
    marked_label,
)
from quill.ui.radio.marks_shared import (
    ACT,
    CLEAR,
    TOGGLE,
    clear_marks,
    mark_action,
    mark_menu_entries,
    marks_on,
    yes_no_asker,
)

__all__ = ["on_list_context_menu", "on_list_key", "remove_marked", "row_text", "toggle_selected"]

_NOUN = "schedule"


def row_text(dialog: Any, entry: Any, summary: str) -> str:
    """A schedule row's text, with "(marked)" when it carries a mark."""
    marks = getattr(dialog, "_row_marks", None)
    return marked_label(summary, marks is not None and entry.id in marks)


def toggle_selected(dialog: Any) -> None:
    """Mark or unmark the selected schedule, saying the running count."""
    index = dialog._list.GetSelection()
    if not (0 <= index < len(dialog._entries)):
        return
    entry = dialog._entries[index]
    marks = marks_on(dialog)
    now_marked = marks.toggle(entry.id)
    text = dialog._list.GetString(index)
    base = text[: -len(" (marked)")] if text.endswith(" (marked)") else text
    dialog._list.SetString(index, marked_label(base, now_marked))
    dialog._announce(marks.toggle_sentence(now_marked))


def remove_marked(dialog: Any, *, ask: Callable[[str], bool] | None = None) -> bool:
    """Ask once, then remove every marked schedule. Returns whether any went."""
    marks = marks_on(dialog)
    marks.keep_only(entry.id for entry in dialog._entries)
    doomed = [entry.id for entry in dialog._entries if entry.id in marks]
    if not doomed:
        return False
    asker = ask or yes_no_asker(dialog._win, "Delete Marked Schedules")
    if not asker(delete_question(len(doomed), _NOUN)):
        dialog._announce("Nothing was deleted.")
        return False
    order = [entry.id for entry in dialog._entries]
    index = dialog._list.GetSelection()
    current = order[index] if 0 <= index < len(order) else None
    landing = landing_after(order, current, doomed)
    removed = [entry_id for entry_id in doomed if dialog._on_remove(entry_id)]
    dialog._entries = [entry for entry in dialog._entries if entry.id not in removed]
    if dialog._editing_id in removed:
        dialog._reset_form()
    marks.clear()
    keep = landing if landing not in removed else None
    dialog._refresh_list(keep_id=keep)
    failed = len(doomed) - len(removed)
    dialog._announce(deleted_sentence(len(removed), _NOUN, failed=failed))
    if not dialog._entries:
        dialog._name_ctrl.SetFocus()  # the list is empty; never leave focus on a dead button
    return bool(removed)


def on_list_key(dialog: Any, event: Any) -> None:
    """The list's keys: mark, delete (marked, or the selected one), clear."""
    action = mark_action(dialog._wx, event)
    if action == TOGGLE:
        toggle_selected(dialog)
    elif action == ACT:
        if marks_on(dialog):
            remove_marked(dialog)
        else:
            dialog._on_remove_click(None)
    elif action == CLEAR:
        clear_marks(marks_on(dialog), announce=dialog._announce)
        dialog._refresh_list(keep_id=_selected_id(dialog))
    else:
        event.Skip()


def _selected_id(dialog: Any) -> str | None:
    entry = dialog._selected_entry()
    return entry.id if entry is not None else None


def on_list_context_menu(dialog: Any) -> None:
    """Shift+F10 on a schedule: its actions, then the marking rows."""
    wx = dialog._wx
    index = dialog._list.GetSelection()
    if not (0 <= index < len(dialog._entries)):
        return
    entry = dialog._entries[index]
    marks = marks_on(dialog)
    entries: list[tuple[str, Callable[[], None]]] = [
        ("&Edit", lambda: dialog._on_edit_click(None)),
        ("D&uplicate", lambda: dialog._on_duplicate_click(None)),
        ("Enab&le" if not entry.enabled else "Disab&le", lambda: dialog._on_toggle_click(None)),
    ]
    if not marks:
        # While schedules are marked, Delete removes them all, so the one-row
        # delete gives the key up to the marked row (one claimant per key).
        entries.append((
            f"&Delete {entry.station_name}\tDelete",
            lambda: dialog._on_remove_click(None),
        ))

    def clear() -> None:
        clear_marks(marks, announce=dialog._announce)
        dialog._refresh_list(keep_id=entry.id)

    entries += mark_menu_entries(
        marks,
        toggle=lambda: toggle_selected(dialog),
        remove=lambda: remove_marked(dialog),
        clear=clear,
    )
    menu = wx.Menu()
    id_refs = []
    for label, handler in entries:
        item_id = wx.NewIdRef()
        id_refs.append(item_id)
        menu.Append(item_id, label)
        menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), id=item_id)
    dialog._context_menu_id_refs = id_refs  # pinned while the popup can fire
    dialog._list.PopupMenu(menu)
    menu.Destroy()
