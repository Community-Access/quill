"""Every key the Browse Stations window answers before its tree does.

Extracted from ``browse_tree_dialog`` under GATE-11 (extract, never
rebaseline) when Delete arrived and that module hit its ceiling -- and it reads
better out here anyway, because these four keys are one subject: **what a key
means depends on where focus is**, which is a policy, not a widget detail.

* **Ctrl+F** is the find box, from anywhere in the window.
* **Delete** removes what the selected row's own menu removes -- but only while
  the *tree* has focus, because Delete in the find box is a delete.
* **Escape** clears an active search when the find box has focus, and closes
  the window otherwise.
* **Ctrl+F4** closes, because a frame gets no automatic Escape-to-Cancel and
  this is the document-window close key a family of windows owes people.

Order matters and is the reason they live together: Escape has two meanings and
the narrower one has to be tried first.
"""

from __future__ import annotations

from typing import Any


def handle(dialog: Any, event: Any) -> bool:
    """Answer *event* if this window owns that key. True when it did.

    The caller skips the event when this returns False, which is what leaves
    every other key to the tree.
    """
    wx = dialog._wx
    key = event.GetKeyCode()
    focus = dialog._win.FindFocus()

    # Ctrl+F: straight to the Find box, from wherever focus is.
    if event.ControlDown() and not event.ShiftDown() and not event.AltDown() and key == ord("F"):
        dialog._find_ctrl.SetFocus()
        dialog._find_ctrl.SelectAll()
        dialog._announce("Find in this folder.")
        return True

    if key == wx.WXK_DELETE and focus is dialog._tree:
        from quill.ui.radio import browse_delete

        browse_delete.delete_selected(dialog)
        return True

    # Escape in the Find box clears the search (the old Clear button).
    if key == wx.WXK_ESCAPE and focus is dialog._find_ctrl:
        if dialog._find_active or dialog._find_ctrl.GetValue():
            dialog._clear_find()
            return True

    if dialog._modeless and (key == wx.WXK_ESCAPE or (key == wx.WXK_F4 and event.ControlDown())):
        dialog._win.Close()
        return True
    return False
