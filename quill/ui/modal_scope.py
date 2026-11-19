"""Scoped modality: a window whose dialogs block only it (GH-R-002).

wx's ShowModal disables every top-level window of the app. A window that marks
itself ``_quill_modal_scope = True`` -- the Workbench -- promises that its
dialogs block only it, so the editor stays usable. ``show_modal_dialog`` calls
:func:`keep_bystanders_usable` just before ShowModal.
"""

from __future__ import annotations

from collections.abc import Iterable

from quill.ui.dialog_contract import dialog_alive


def _top_level_chain(window: object) -> list[object]:
    """Every top-level window from *window* up through its parents."""
    chain: list[object] = []
    current = window
    while current is not None:
        try:
            if current.IsTopLevel():  # type: ignore[attr-defined]
                chain.append(current)
            current = current.GetParent()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - a dead window ends the walk
            break
    return chain


def scoped_modal_bystanders(dialog: object, top_levels: Iterable[object]) -> list[object]:
    """The windows a modal *dialog* must leave usable, or [] for an ordinary one.

    wx's ShowModal disables every top-level window of the app. A window that
    marks itself ``_quill_modal_scope = True`` -- the Workbench -- promises
    that its dialogs block only it (GH-R-002): the editor, and any other window
    outside the dialog's own parent chain, stays usable. Returned are those
    other windows that are enabled now, so they can be enabled again once the
    modal loop has disabled them; windows already disabled stay as they were.
    """
    chain = _top_level_chain(dialog)
    if not any(getattr(w, "_quill_modal_scope", False) for w in chain):
        return []
    kept: list[object] = []
    for window in top_levels:
        if any(window is w for w in chain):
            continue
        try:
            if window.IsEnabled():  # type: ignore[attr-defined]
                kept.append(window)
        except Exception:  # noqa: BLE001 - a dead window is skipped
            continue
    return kept


def _enable_again(windows: Iterable[object]) -> None:
    for window in windows:
        try:
            if dialog_alive(window) and not window.IsEnabled():  # type: ignore[attr-defined]
                window.Enable(True)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - a closed window needs nothing
            continue


def keep_bystanders_usable(dialog: object) -> None:
    """Schedule the re-enabling of a scoped modal's bystanders (GH-R-002).

    The CallAfter runs inside the dialog's own modal loop, after ShowModal has
    disabled everything; when the dialog ends, wx re-enables what it disabled,
    and enabling a window that is already enabled changes nothing.
    """
    try:
        import wx

        bystanders = scoped_modal_bystanders(dialog, wx.GetTopLevelWindows())
        if bystanders:
            wx.CallAfter(_enable_again, bystanders)
    except Exception:  # noqa: BLE001 - never stop a dialog from opening
        return
