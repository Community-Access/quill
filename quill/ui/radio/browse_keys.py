"""Every key the Browse Stations window answers before its tree does.

Extracted from ``browse_tree_dialog`` under GATE-11 (extract, never
rebaseline) when Delete arrived and that module hit its ceiling -- and it reads
better out here anyway, because these four keys are one subject: **what a key
means depends on where focus is**, which is a policy, not a widget detail.

* **Ctrl+F** is the find box, from anywhere in the window.
* **Delete** removes what the selected row's own menu removes -- but only while
  the *tree* has focus, because Delete in the find box is a delete. With rows
  marked (``.``, see ``browse_marks``) it removes every marked row instead.
* **Escape** clears an active search when the find box has focus; in the tree,
  inside a category (a country, a language, a genre), it goes back to that
  category's row and folds it -- one level per press, the way Enter opened
  it -- and only at the top level does it close the window.
* **Ctrl+F4** closes, because a frame gets no automatic Escape-to-Cancel and
  this is the document-window close key a family of windows owes people.

Order matters and is the reason they live together: Escape has two meanings and
the narrower one has to be tried first.
"""

from __future__ import annotations

from typing import Any

from quill.ui.radio import browse_marks


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

    # ., Delete with rows marked, Ctrl+Shift+Delete: the marking keys.
    if focus is dialog._tree and browse_marks.handle_key(dialog, event):
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

    # Escape inside a category goes back to the category's own row, folded,
    # one level per press; only at the top level does it close (item 43). The
    # Find box keeps its text and the player keeps playing.
    plain = not getattr(event, "HasAnyModifiers", lambda: False)()
    if key == wx.WXK_ESCAPE and focus is dialog._tree and plain:
        if back_to_category(dialog._tree):
            return True

    if dialog._modeless and (key == wx.WXK_ESCAPE or (key == wx.WXK_F4 and event.ControlDown())):
        dialog._win.Close()
        return True
    return False


def back_to_category(tree: Any) -> bool:
    """Select the highlighted row's category and fold it. False at the top level.

    The tree's root is hidden, so a top-level source's parent is the root and
    there is nowhere further back to go: Escape then means close, as it always
    has. Nothing is spoken; the selection change is the reader's to read.
    """
    try:
        item = tree.GetSelection()
        if not item or not item.IsOk():
            return False
        parent = tree.GetItemParent(item)
        if not parent.IsOk() or parent == tree.GetRootItem():
            return False
    except (AttributeError, RuntimeError):  # no tree yet, or one being torn down
        return False
    tree.SelectItem(parent)
    tree.Collapse(parent)
    tree.EnsureVisible(parent)
    return True
