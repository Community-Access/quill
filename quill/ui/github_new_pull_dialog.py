"""New Pull Request: one form for the branches, title, description and Draft.

Opened by the GitHub Workbench (Ctrl+N on Pull Requests, or Create Pull
Request on a branch). The prefill, the kept draft and the existing-PR check
are :mod:`quill.core.github.pull_compose`'s; this is only the form. Nothing is
sent from here: OK returns the :class:`~quill.core.github.pull_compose.PullDraft`
and the Workbench sends it, says the result, and drops the kept draft.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from quill.core.github.pull_compose import PullDraft, describe_refusal, keep_draft
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size

__all__ = ["NewPullRequestDialog"]

_TITLE = "New Pull Request"


class NewPullRequestDialog:
    """Base, head, title, description and Draft, with the result in :attr:`draft`."""

    def __init__(
        self,
        parent: object,
        start: PullDraft,
        branches: Sequence[str],
        *,
        default_branch: str = "",
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce or (lambda _text: None)
        self._repository = start.repository
        self.draft: PullDraft | None = None
        names = list(dict.fromkeys([*branches, start.base, start.head]))
        names = [n for n in names if n]
        self.dialog = wx.Dialog(
            parent, title=_TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 560, 480))
        self.dialog.SetSize(dip_size(self.dialog, 700, 600))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            panel,
            label=(
                f"Propose merging one branch of {start.repository} into another. "
                "Create Pull Request is the only action here that sends anything to GitHub."
            ),
        )
        intro.Wrap(640)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        base_label = wx.StaticText(panel, label="Merge &into:")
        root.Add(base_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self._base = wx.Choice(panel, choices=names)
        self._base.SetName("Merge into")
        self._base.SetHelpText(
            "The branch that receives the changes, usually the default branch"
            + (f", {default_branch}." if default_branch else ".")
        )
        self._base.SetStringSelection(start.base or default_branch)
        root.Add(self._base, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        head_label = wx.StaticText(panel, label="Merge &from:")
        root.Add(head_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._head = wx.Choice(panel, choices=names)
        self._head.SetName("Merge from")
        self._head.SetHelpText("The branch with the changes you are proposing.")
        self._head.SetStringSelection(start.head)
        root.Add(self._head, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        title_label = wx.StaticText(panel, label="&Title:")
        root.Add(title_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._title = wx.TextCtrl(panel, value=start.title)
        self._title.SetName("Title")
        self._title.SetHelpText("Required. What the pull request does, in a line.")
        root.Add(self._title, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        body_label = wx.StaticText(panel, label="&Description:")
        root.Add(body_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._body = wx.TextCtrl(panel, value=start.body, style=wx.TE_MULTILINE | wx.TE_WORDWRAP)
        self._body.SetName("Description")
        self._body.SetHelpText(
            "Optional. Why, and what a reviewer should look at. Kept if you cancel."
        )
        root.Add(self._body, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._draft = wx.CheckBox(panel, label="Create as a dr&aft")
        self._draft.SetValue(start.draft)
        self._draft.SetHelpText(
            "A draft cannot be merged and asks nobody to review it until you mark it ready."
        )
        root.Add(self._draft, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._status = wx.StaticText(panel, label="")
        self._status.SetName("Why the pull request cannot be created yet")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.StdDialogButtonSizer()
        create = wx.Button(panel, wx.ID_OK, label="Create Pull Request")
        create.SetHelpText("Open the pull request on GitHub with these branches and text.")
        create.SetDefault()
        cancel = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
        cancel.SetHelpText("Close without sending. What you typed is kept for this session.")
        buttons.AddButton(create)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)
        create.Bind(wx.EVT_BUTTON, self._on_create)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)

    def _current(self) -> PullDraft:
        return PullDraft(
            self._repository,
            self._base.GetStringSelection(),
            self._head.GetStringSelection(),
            self._title.GetValue().strip(),
            self._body.GetValue().strip(),
            bool(self._draft.GetValue()),
        )

    def problem(self) -> str:
        """Why OK cannot send yet ("" when it can)."""
        current = self._current()
        reason = describe_refusal(current.base, current.head, ahead_by=None)
        if reason:
            return reason
        if not current.title:
            return "Type a title first."
        return ""

    def _on_create(self, event: object) -> None:
        problem = self.problem()
        if problem:
            # The status line is not focused, so say it (GATE-12); then focus
            # goes to the control that fixes it.
            self._status.SetLabel(problem)
            self._announce(problem)
            (self._title if "title" in problem else self._head).SetFocus()
            return
        self.draft = self._current()
        event.Skip()  # type: ignore[attr-defined]

    def show(self) -> bool:
        """Show the form; True with :attr:`draft` set when the person chose Create."""
        try:
            accepted = show_modal_dialog(self.dialog, _TITLE) == self._wx.ID_OK
            if not accepted:
                keep_draft(self._current())
            return accepted and self.draft is not None
        finally:
            self.dialog.Destroy()
