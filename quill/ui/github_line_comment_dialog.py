"""Write a comment on one line, or a run of lines, of a pull request's diff.

The comment can go into the review you are putting together (kept on this
device until Compose Review submits it) or be posted on its own now. Suggest a
Change writes a ```suggestion block holding the lines' current text, so you
edit the code itself rather than describing the edit.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from quill.core.github.diff_lines import (
    DiffLine,
    LineCommentAnchor,
    render_line,
    strip_suggestion_block,
    suggestion_block,
)
from quill.core.github.review_errors import GitHubReviewError
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size

ADD_TO_REVIEW = "review"
POST_NOW = "post"


@dataclass(frozen=True, slots=True)
class LineCommentChoice:
    """What the person chose: add to the review or post now, and the text."""

    action: str
    body: str


class GitHubLineCommentDialog:
    """Modal composer for one line comment; returns a choice, or None on Cancel."""

    def __init__(
        self,
        parent: object,
        *,
        anchor: LineCommentAnchor,
        lines: Sequence[DiffLine],
        style: str,
        body: str = "",
        can_post_now: bool = True,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._lines = tuple(lines)
        self._announce = announce_cb or (lambda _message: None)
        self._result: LineCommentChoice | None = None
        where = anchor.describe()
        self.dialog = wx.Dialog(
            parent,
            title=f"Comment on {where}"[:120],
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 560, 420))
        self.dialog.SetSize(dip_size(self.dialog, 720, 560))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        quoted_label = wx.StaticText(panel, label="Lines you are commenting on:")
        root.Add(quoted_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._quoted = wx.TextCtrl(
            panel,
            value="\n".join(render_line(line, style) for line in self._lines),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
        )
        self._quoted.SetName("Lines you are commenting on")
        self._quoted.SetHelpText("The diff lines this comment is attached to, read-only.")
        root.Add(self._quoted, 1, wx.EXPAND | wx.ALL, 10)

        self._suggest = wx.CheckBox(panel, label="&Suggest a change")
        self._suggest.SetHelpText(
            "Writes a suggestion block holding these lines' current text into the comment. "
            "Edit the code inside it; the author can accept it on GitHub with one click."
        )
        root.Add(self._suggest, 0, wx.LEFT | wx.RIGHT, 10)

        body_label = wx.StaticText(panel, label="&Comment:")
        root.Add(body_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._body = wx.TextCtrl(panel, value=body, style=wx.TE_MULTILINE | wx.TE_WORDWRAP)
        self._body.SetName("Comment")
        self._body.SetHelpText("What you want to say about these lines. Markdown works.")
        root.Add(self._body, 2, wx.EXPAND | wx.ALL, 10)

        self._status = wx.StaticText(panel, label="")
        self._status.SetName("Comment status")
        self._status.SetHelpText("Says why the comment could not be used yet.")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._add_btn = wx.Button(panel, wx.ID_OK, label="&Add to Review")
        self._add_btn.SetDefault()
        self._add_btn.SetHelpText(
            "Keep this comment on this device. It goes to GitHub with your review when you "
            "submit it from Compose Review."
        )
        self._post_btn = wx.Button(panel, wx.ID_ANY, label="&Post Now")
        self._post_btn.SetHelpText("Post this one comment to GitHub now, outside a review.")
        self._post_btn.Enable(can_post_now)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
        cancel_btn.SetHelpText("Close without keeping this comment.")
        buttons.Add(self._add_btn, 0, wx.RIGHT, 6)
        buttons.Add(self._post_btn, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(cancel_btn)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        self._suggest.Bind(wx.EVT_CHECKBOX, self._on_suggest)
        self._add_btn.Bind(wx.EVT_BUTTON, lambda _event: self._finish(ADD_TO_REVIEW))
        self._post_btn.Bind(wx.EVT_BUTTON, lambda _event: self._finish(POST_NOW))

    def _say(self, message: str) -> None:
        # The status line is not focused, so the reader would not say it (GATE-12).
        self._status.SetLabel(message)
        self._announce(message)

    def _on_suggest(self, _event: object) -> None:
        if not self._suggest.GetValue():
            self._body.SetValue(strip_suggestion_block(self._body.GetValue()))
            return
        try:
            block = suggestion_block(self._lines)
        except GitHubReviewError as exc:
            self._suggest.SetValue(False)
            self._say(str(exc))
            return
        text = self._body.GetValue().rstrip("\n")
        start = len(text) + (2 if text else 0) + len("```suggestion\n")
        self._body.SetValue(f"{text}\n\n{block}" if text else block)
        self._body.SetFocus()
        self._body.SetInsertionPoint(start)

    def _finish(self, action: str) -> None:
        body = self._body.GetValue().strip()
        if not body:
            self._say("Write a comment first.")
            self._body.SetFocus()
            return
        self._result = LineCommentChoice(action, body)
        self.dialog.EndModal(self._wx.ID_OK)

    def show(self) -> LineCommentChoice | None:
        wx = self._wx
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        self._body.SetFocus()
        try:
            if show_modal_dialog(self.dialog, "Line Comment", announce=self._announce) != wx.ID_OK:
                return None
            return self._result
        finally:
            self.dialog.Destroy()


__all__ = ["ADD_TO_REVIEW", "POST_NOW", "GitHubLineCommentDialog", "LineCommentChoice"]
