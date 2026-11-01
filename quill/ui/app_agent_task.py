"""An agent task's window side in the QuillVille apps (codex.md 6, Phase 4c).

The agent window (:mod:`quill.ui.agent_window`) is the editors' Do a Document
Task, and the apps reuse it as it is: one conversation, a status line, the
instruction, Send, Stop and Close, the same approval question and the same
closing summary, spoken and brailled once. What changes per app is what the
task's tools touch, so this module holds the two things every app's tools need
from the window and nothing else:

* :class:`AppTaskContext` -- the worker-safe host (``AppTaskHost``): run a
  callable on the UI thread and wait, add a line to the transcript, and
  **preview a change as text** before it is made.
* :class:`ProposedChangeDialog` / :func:`preview_text` -- the preview: the whole
  proposed change as read-only text, then Apply or Don't Apply (Escape). A
  write that an app task makes -- sections into a transcript, abbreviations
  into the library, tags on a saved item -- is shown here first (decision 13:
  every edit is reviewed as text).

The commands that open a task live with each app's features; the opener they
share is :meth:`quill.ui.hosted_ai_task_commands.AgentTaskMixin._open_app_task`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.ai.approvals import UiThreadBridge
from quill.ui.accessible_names import set_accessible_name
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size

__all__ = ["PREVIEW_TITLE", "AppTaskContext", "ProposedChangeDialog", "preview_text"]

PREVIEW_TITLE = "Review Proposed Change"
_PAD = 8


class ProposedChangeDialog(wx.Dialog):
    """The proposed change as text, then Apply or Don't Apply."""

    def __init__(self, parent: Any, heading: str, text: str) -> None:
        super().__init__(
            parent, title=PREVIEW_TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        label = wx.StaticText(self, label=heading or "Proposed change")
        self.text = wx.TextCtrl(self, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(self.text, heading or "Proposed change")
        self.text.SetHelpText(
            "The change the task wants to make, as text. Read it with the arrow keys. "
            "Enter applies it; Escape does not."
        )
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, _PAD)
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.AddStretchSpacer(1)
        # No access keys: Enter and Escape already press these (GATE-14).
        self.apply = wx.Button(self, wx.ID_OK, "Apply")
        self.apply.SetHelpText("Makes this change. The task then carries on.")
        self.skip = wx.Button(self, wx.ID_CANCEL, "Don't Apply")
        self.skip.SetHelpText("Leaves things as they are. The task carries on without it.")
        row.Add(self.apply, 0, wx.LEFT, _PAD)
        row.Add(self.skip, 0, wx.LEFT, _PAD)
        sizer.Add(row, 0, wx.EXPAND | wx.ALL, _PAD)
        self.apply.SetDefault()
        apply_modal_ids(
            self,
            affirmative_id=wx.ID_OK,
            affirmative_label="Apply",
            cancel_id=wx.ID_CANCEL,
            cancel_label="Don't Apply",
        )
        self.SetInitialSize(dip_size(self, 600, 420))
        self.Centre()
        self.text.SetFocus()


def preview_text(parent: Any, heading: str, text: str) -> bool:
    """Show :class:`ProposedChangeDialog`; True when the person chose Apply."""
    dialog = ProposedChangeDialog(parent, heading, text)
    try:
        return bool(show_modal_dialog(dialog, PREVIEW_TITLE) == wx.ID_OK)
    finally:
        dialog.Destroy()


class AppTaskContext:
    """What an app task's tools may ask of the window, safely from a worker."""

    def __init__(
        self,
        bridge: UiThreadBridge,
        note: Callable[[str], None],
        parent: Callable[[], Any],
    ) -> None:
        self._bridge = bridge
        self._note = note
        self._parent = parent

    @property
    def bridge(self) -> UiThreadBridge:
        return self._bridge

    def on_ui(self, fn: Callable[[], Any], default: Any = None) -> Any:
        """Run *fn* on the UI thread and return its value; *default* after a Stop."""
        return self._bridge.call(fn, default=default)

    def note(self, text: str) -> None:
        """A step's outcome, into the transcript, silently (GATE-13)."""
        self._bridge.call(lambda: self._note(text), default=None)

    def preview(self, title: str, text: str) -> bool:
        """The change as text first; True when the person applied it (decision 13)."""

        def on_ui() -> bool:
            # Over the agent window when it is the active one, so focus goes
            # back to the conversation when the preview closes.
            parent = wx.GetActiveWindow() or self._parent()
            return preview_text(parent, title, text)

        return bool(self._bridge.call(on_ui, default=False))
