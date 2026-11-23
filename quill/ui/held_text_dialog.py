"""Text Not Typed: Insert or Copy, for text kept back from the wrong place (FUX-07).

When Quill Inkwell cannot confirm that the place in front is the one the text
was meant for (:mod:`quill.core.expansion.destination`), the text is kept and
this small window offers what to do with it:

* **Insert** -- go back to that place and type it there, after the same
  checks again. Offered only where trying again can work.
* **Copy** -- put it on the clipboard, to paste wherever you choose.
* **Cancel** (Escape) -- let it go.

The window's one sentence is the whole explanation, and the screen reader
reads it with the title when the window opens, so nothing else announces it
(GATE-13). The sentence never contains the text itself: the text is private
and is not read aloud unless the person pastes it somewhere and reads it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.expansion.destination import HeldOffer

__all__ = ["COPY", "INSERT", "TITLE", "ask_held_text"]

TITLE = "Text Not Typed"
INSERT = "insert"
COPY = "copy"


def ask_held_text(
    parent: Any,
    offer: HeldOffer,
    run_modal: Callable[[Any, str], int],
) -> str | None:
    """Ask what to do with held text: :data:`INSERT`, :data:`COPY`, or ``None``.

    *run_modal* is the app's modal contract, ``run_modal(dialog, title)``.
    """
    import wx

    from quill.ui.dialog_contract import apply_modal_ids
    from quill.ui.dpi import dip

    dialog = wx.Dialog(parent, title=TITLE)
    try:
        dialog.SetName("held_text_dialog")  # F1 finds its purpose by the title
        sizer = wx.BoxSizer(wx.VERTICAL)
        message = wx.StaticText(dialog, label=offer.sentence)
        message.Wrap(dip(dialog, 420))
        sizer.Add(message, 0, wx.ALL, dip(dialog, 12))
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        insert_id = wx.NewIdRef()
        copy_id = wx.NewIdRef()
        insert = None
        if offer.can_insert:
            insert = wx.Button(dialog, insert_id, "&Insert")
            buttons.Add(insert, 0, wx.RIGHT, dip(dialog, 8))
        copy = wx.Button(dialog, copy_id, "&Copy")
        buttons.Add(copy, 0, wx.RIGHT, dip(dialog, 8))
        buttons.Add(wx.Button(dialog, wx.ID_CANCEL, "Cancel"))
        sizer.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, dip(dialog, 12))
        dialog.SetSizerAndFit(sizer)

        def finish(code: int) -> Callable[[Any], None]:
            return lambda _event: dialog.EndModal(code)

        if insert is not None:
            insert.Bind(wx.EVT_BUTTON, finish(int(insert_id)))
        copy.Bind(wx.EVT_BUTTON, finish(int(copy_id)))
        first = insert if insert is not None else copy
        first.SetDefault()
        first.SetFocus()
        apply_modal_ids(dialog, cancel_id=wx.ID_CANCEL)
        # Opened just after the focus was handed to another program, so
        # Windows' foreground lock may leave it flashing on the taskbar,
        # unheard: bring it forward once it is showing.
        wx.CallAfter(_to_front, dialog)
        answer = run_modal(dialog, TITLE)
    finally:
        dialog.Destroy()
    if offer.can_insert and answer == int(insert_id):
        return INSERT
    if answer == int(copy_id):
        return COPY
    return None


def _to_front(dialog: Any) -> None:
    try:
        from quill.platform.windows.foreground import force_foreground_window

        if dialog.IsShown():
            force_foreground_window(int(dialog.GetHandle()))
    except Exception:  # noqa: BLE001 - not Windows, or already closed
        pass
