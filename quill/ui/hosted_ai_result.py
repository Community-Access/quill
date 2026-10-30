"""The AI Result window: what came back, and what you can do with it.

Shared by both editors, like the pad it comes from. Split out of
:mod:`quill.ui.hosted_ai_pad` under GATE-11 on 2026-10-15, when it gained
**Review Changes** -- QUILL's word-level review (:mod:`quill.ui.ai_diff_review_dialog`)
for an answer that would replace the selection -- and the pad gained the answer
delivery choice. ``hosted_ai_pad`` still exports :class:`AiResultFrame`, and the
shared commands look it up there, so nothing that opens it moved.

Every rule of the pad applies: a modeless frame, Close bound by hand, nothing
put into the document without a button press, and every edit one undo step.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.ai.writing_tools import ACTION_TITLES
from quill.ui.dpi import dip_size
from quill.ui.hosted_ai_dialogs import _close_row, _read_only, focus_on

__all__ = ["AiResultFrame"]


class AiResultFrame(wx.Frame):
    """What came back, and the things you can do with it.

    Read-only, because an AI answer is a proposal. Editing happens in the
    document, through the ordinary undo stack, and nothing here changes a
    document without a keystroke saying so -- not on a timer, not on close.
    """

    def __init__(
        self,
        parent: wx.Window,
        *,
        action: str,
        text: str,
        used: str,
        on_replace: Callable[[str], None] | None,
        on_insert: Callable[[str], None] | None,
        on_again: Callable[[], None] | None,
        announce: Callable[[str], None],
        on_follow_up: Callable[[], None] | None = None,
        on_review: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, title=ACTION_TITLES.get(action, "AI Result"))
        self._text = text
        self._announce = announce

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)

        body = _read_only(
            panel,
            sizer,
            "The answer",
            text,
            "What the AI sent back. Read-only -- use Replace My Selection or "
            "Insert Below to put it into your document.",
        )

        extra: list[wx.Button] = []
        if on_replace is not None:
            replace = wx.Button(panel, label="&Replace My Selection")
            replace.SetHelpText(
                "Puts this in place of the text you had selected. Control Z takes it back."
            )
            replace.Bind(wx.EVT_BUTTON, lambda _e: self._apply(on_replace, "Replaced."))
            extra.append(replace)
        if on_review is not None:
            review = wx.Button(panel, label="Re&view Changes...")
            review.SetHelpText(
                "Compares this with the text you had selected, change by change and "
                "word by word, so you can keep some changes and leave the rest. "
                "Nothing changes until you apply."
            )

            def _review(_event: wx.CommandEvent) -> None:
                on_review(self._text)

            review.Bind(wx.EVT_BUTTON, _review)
            extra.append(review)
        if on_insert is not None:
            insert = wx.Button(panel, label="Insert &Below")
            insert.SetHelpText(
                "Puts this into your document underneath the current paragraph. "
                "Control Z takes it back."
            )
            insert.Bind(wx.EVT_BUTTON, lambda _e: self._apply(on_insert, "Inserted."))
            extra.append(insert)

        copy = wx.Button(panel, label="&Copy")
        copy.SetHelpText("Puts the answer on the clipboard.")
        copy.Bind(wx.EVT_BUTTON, self._on_copy)
        extra.append(copy)

        if on_again is not None:
            again = wx.Button(panel, label="Try &Again")
            again.SetHelpText(
                "Sends the same text again. This uses one more of your free requests."
            )

            def _retry(_event: wx.CommandEvent) -> None:
                self.Close()
                on_again()

            again.Bind(wx.EVT_BUTTON, _retry)
            extra.append(again)

        if on_follow_up is not None:
            follow = wx.Button(panel, label="Follow &Up")
            follow.SetHelpText(
                "Carries on from this answer in a conversation: ask for it shorter, "
                "ask about one part of it, or ask something new. Each message uses "
                "one request."
            )

            def _follow(_event: wx.CommandEvent) -> None:
                self.Close()
                on_follow_up()

            follow.Bind(wx.EVT_BUTTON, _follow)
            extra.append(follow)

        _close_row(self, sizer, *extra)

        if used:
            _read_only(
                panel,
                sizer,
                "Requests",
                used,
                "How much of your free allowance this answer used, and what is left.",
                grow=False,
            )

        self.SetInitialSize(dip_size(self, 620, 460))
        self.Centre()
        # Focus lands on the answer, so the reader reads it. Nothing is
        # announced on top of that (GATE-13): the window title and the focused
        # field are both things it already says.
        focus_on(self, body)

    def _apply(self, action: Callable[[str], None], said: str) -> None:
        action(self._text)
        self._announce(f"{said} Press Control Z to undo.")

    def _on_copy(self, _event: wx.CommandEvent) -> None:
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(self._text))
            finally:
                wx.TheClipboard.Close()
            self._announce("Copied.")
