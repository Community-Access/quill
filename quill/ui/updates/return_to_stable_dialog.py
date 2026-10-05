"""Go back to Stable? -- the safe, safe-with-losses and not-safe versions (plan 7.6).

One window, three shapes, decided before it opens
(:func:`quill.core.updater.going_back.assess_return`):

* **safe** (and safe with losses): "Go back to 3.2.0 now" is the default, with
  "Wait for Stable" beside it;
* **not safe**: "Wait for Stable" is the default, with "Use the copy from
  3 October" when that copy exists.

Close changes nothing and carries no access key (GATE-14). Focus starts on
the explanation, so the screen reader reads why the window opened; the risk is
in the words and the button names, never in colour.
"""

from __future__ import annotations

from typing import Any, Literal

import wx

from quill.core.updater.going_back import ReturnAssessment
from quill.core.updater.wording import RETURN_SAFE_TITLE, RETURN_UNSAFE_TITLE, return_text
from quill.core.versioning import ReleaseVersion
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button

__all__ = ["ReturnAnswer", "ReturnToStableDialog"]

ReturnAnswer = Literal["now", "wait", "restore", "close"]

_WAIT = 5201
_RESTORE = 5202


def _shown(version: str) -> str:
    parsed = ReleaseVersion.try_parse(version)
    return parsed.display() if parsed is not None else version


class ReturnToStableDialog(wx.Dialog):  # type: ignore[misc]
    """Ask how to come back to Stable. :meth:`answer` after the modal returns."""

    def __init__(
        self, parent: Any, assessment: ReturnAssessment, *, app_name: str, channel: str
    ) -> None:
        safe = assessment.verdict is not None and assessment.verdict.safe
        super().__init__(
            parent,
            title=RETURN_SAFE_TITLE if safe else RETURN_UNSAFE_TITLE,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._answer: ReturnAnswer = "close"
        sizer = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(self, label="What going back &means:")
        sizer.Add(heading, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self._text = wx.TextCtrl(
            self,
            value=return_text(assessment, app_name, channel),
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(-1, 240),
        )
        self._text.SetName("What going back means")
        self._text.SetHelpText(
            "Whether Stable can read everything you have saved, and the ways back "
            "that are safe. Read-only; arrow through it like a document."
        )
        sizer.Add(self._text, 1, wx.EXPAND | wx.ALL, 12)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer()
        default: wx.Button
        if safe and assessment.stable is not None:
            target = _shown(assessment.stable.version)
            now = wx.Button(self, wx.ID_OK, label=f"&Go back to {target} now")
            now.SetHelpText(
                f"Install {target}, the Stable version. Your settings stay as they are."
            )
            now.Bind(wx.EVT_BUTTON, lambda _e: self._finish("now"))
            buttons.Add(now, 0, wx.RIGHT, 6)
            default = now
        wait = wx.Button(self, _WAIT, label="&Wait for Stable")
        wait.SetHelpText(
            "Keep the version you have, stop taking test versions, and move to Stable "
            "by itself when Stable catches up. Nothing is installed."
        )
        wait.Bind(wx.EVT_BUTTON, lambda _e: self._finish("wait"))
        buttons.Add(wait, 0, wx.RIGHT, 6)
        if not safe:
            default = wait
            if assessment.snapshot is not None and assessment.stable is not None:
                day = assessment.snapshot_date or "the day you joined"
                restore = wx.Button(self, _RESTORE, label=f"&Use the copy from {day}")
                restore.SetHelpText(
                    "Put back the copy of your settings saved when you joined, then install "
                    "Stable. A copy of how things are now is saved first."
                )
                restore.Bind(wx.EVT_BUTTON, lambda _e: self._finish("restore"))
                buttons.Add(restore, 0, wx.RIGHT, 6)
        close = wx.Button(self, wx.ID_CANCEL, label="Close")
        close.SetHelpText("Close this and change nothing.")
        bind_close_button(self, close, modeless=False)
        buttons.Add(close, 0)
        default.SetDefault()
        sizer.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        self.SetSizerAndFit(sizer)
        self.SetSize((600, -1))
        apply_modal_ids(self, escape_id=wx.ID_CANCEL)
        self._text.SetFocus()

    def answer(self) -> ReturnAnswer:
        return self._answer

    def _finish(self, answer: ReturnAnswer) -> None:
        self._answer = answer
        self.EndModal(wx.ID_OK if answer == "now" else wx.ID_CANCEL)
