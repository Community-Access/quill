"""Marks in the Schedule Recording list: remove, enable or disable many at once.

The Favorites marking keys (:mod:`quill.ui.radio.marks_shared`), on the list of
scheduled recordings. ``.`` marks the selected schedule and says how many are
marked; the row reads "(marked)". Delete then removes every marked schedule
after one question ("Delete 3 schedules?", default No) -- where a single
Delete removes the selected one straight away, as it always has, because one
schedule is quickly added back and twelve are not.

**Enable** or **Disable** while schedules are marked works on every marked
one. The button then reads "Enable 3 Marked" when any of them is off (so one
press switches them all on) and "Disable 3 Marked" when all of them are on;
the list's Shift+F10 menu offers both, so either can be chosen outright. It
asks nothing -- switching a schedule off loses nothing and is switched back the
same way -- says one sentence with the count, and clears the marks.

Edit and Duplicate work on the selected schedule only; while schedules are
marked, the first of them to run says so, once, and that the marks are still
there.

This module also owns the list's key handler and its context menu, which moved
here from ``schedule_recording_dialog`` under GATE-11 when marking arrived.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from quill.core.counted import plural
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

__all__ = [
    "on_list_context_menu",
    "on_list_key",
    "refresh_buttons",
    "remove_marked",
    "row_text",
    "set_marked_enabled",
    "toggle_button",
    "toggle_selected",
]

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
    refresh_buttons(dialog)
    dialog._announce(marks.toggle_sentence(now_marked))


def _marked_entries(dialog: Any) -> list[Any]:
    marks = marks_on(dialog)
    marks.keep_only(entry.id for entry in dialog._entries)
    return [entry for entry in dialog._entries if entry.id in marks]


def refresh_buttons(dialog: Any) -> None:
    """Name the list's buttons for what they act on: the selected schedule,
    or -- for Enable or Disable -- every marked one while any are marked.

    Nothing is spoken; the marking key already said the count.
    """
    dialog._refresh_remove_button()
    marked = _marked_entries(dialog)
    if not marked:
        return
    count = len(marked)
    button = dialog._toggle_btn
    if any(not entry.enabled for entry in marked):
        button.SetLabel(f"Enab&le {count} Marked")
        button.SetName(f"Enable the {plural(count, 'marked schedule')}")
    else:
        button.SetLabel(f"Disab&le {count} Marked")
        button.SetName(f"Disable the {plural(count, 'marked schedule')}")
    button.Enable(True)


def toggle_button(dialog: Any, event: Any = None) -> None:
    """The Enable or Disable button: every marked schedule while any are
    marked (on when any is off, otherwise off), else the selected one."""
    marked = _marked_entries(dialog)
    if not marked:
        dialog._on_toggle_click(event)
        return
    set_marked_enabled(dialog, any(not entry.enabled for entry in marked))


def set_marked_enabled(dialog: Any, enabled: bool) -> bool:
    """Switch every marked schedule on (*enabled*) or off. Returns whether
    any changed. One sentence, every clause a number (GATE-BULK-COUNT)."""
    marked = _marked_entries(dialog)
    if not marked:
        return False
    changed = failed = 0
    for entry in marked:
        if entry.enabled == enabled:
            continue
        updated = replace(entry, enabled=enabled)
        if dialog._on_update(updated):
            dialog._entries = [updated if e.id == updated.id else e for e in dialog._entries]
            changed += 1
        else:
            failed += 1
    already = len(marked) - changed - failed
    state = "enabled" if enabled else "disabled"
    said = f"{state.capitalize()} {plural(changed, _NOUN)}."
    if already:
        said += f" {already} {'was' if already == 1 else 'were'} already {state}."
    if failed:
        said += f" {failed} could not be changed."
    marks_on(dialog).clear()
    dialog._refresh_list(keep_id=_selected_id(dialog))
    dialog._announce(said)
    return changed > 0


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
    ]
    if marks:
        # Both, so either can be chosen outright; the button picks for you.
        entries += [
            (f"Enab&le {len(marks)} Marked", lambda: set_marked_enabled(dialog, True)),
            (f"Disa&ble {len(marks)} Marked", lambda: set_marked_enabled(dialog, False)),
        ]
    else:
        entries.append((
            "Enab&le" if not entry.enabled else "Disab&le",
            lambda: dialog._on_toggle_click(None),
        ))
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
