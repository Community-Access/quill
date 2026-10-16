"""Review AI Changes: an AI edit, read change by change and word by word.

QUILL's review window for AI edits (AI-7), extracted from
:mod:`quill.ui.assistant_tools` on 2026-10-15 so the free hosted AI of both
editors could offer it -- the AI Result window's **Review Changes** button --
without QUILL Lite importing QUILL's whole assistant module. QUILL keeps
reaching it exactly as before (``MainFrame.open_ai_diff_review``, and
``assistant_tools`` re-exports the class), so there is one review window and
one engine (:mod:`quill.core.ai.diff_review`, which supplies the word-level
detail: "changed 'quick' to 'rapid'" with the sentence it happened in).

Every control carries its F1 sentence at construction (GATE-<APP>-HELP); QUILL
Lite's help audit scans this module now that QUILL Lite opens it.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_modal_dialog

__all__ = ["DiffReviewDialog"]


class DiffReviewDialog:
    """Accessible, line-by-line review of an AI edit (AI-7).

    Presents the diff between the current document text and a proposed revision
    as a navigable checklist of added / removed / changed hunks. Each hunk is
    pre-checked; the reader can read every change line by line in the detail
    pane, then apply all, some (partial apply), or none (reject). Applying is
    handed back to the caller as a single replacement text so the editor records
    it as one undo unit.
    """

    def __init__(
        self,
        parent: object,
        *,
        title: str,
        original_text: str,
        revised_text: str,
        on_apply: Callable[[str], None],
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        from quill.core.ai.diff_review import build_diff_review

        self._wx = wx
        self._on_apply = on_apply
        self._announce = announce or (lambda _message: None)
        self.review = build_diff_review(original_text, revised_text)
        self.applied = False

        self.dialog = wx.Dialog(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((880, 640))

        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        single = len(self.review.hunks) == 1
        intro = (
            "Review the proposed AI change below. Read it line by line in the "
            "details pane, then choose Accept to apply it or Reject to leave the "
            "document unchanged."
            if single
            else (
                "Review the proposed AI changes below. Checked hunks will be "
                "applied; uncheck any you want to keep as-is. Read each hunk "
                "line by line in the details pane. Use Apply Checked for a "
                "partial apply, Accept All to take every change, or Reject All "
                "to leave the document unchanged."
            )
        )
        root.Add(
            wx.StaticText(panel, label=intro),
            0,
            wx.EXPAND | wx.ALL,
            8,
        )

        self.summary = wx.StaticText(panel, label=self.review.summary())
        root.Add(self.summary, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        root.Add(wx.StaticText(panel, label="Changes"), 0, wx.LEFT | wx.RIGHT, 8)
        self.hunk_list = wx.CheckListBox(  # A11Y-SR-1-OK: diff hunks; pending CheckBox conversion
            panel,
            choices=[hunk.describe() for hunk in self.review.hunks],
        )
        set_accessible_name(self.hunk_list, "Changes")
        self.hunk_list.SetHelpText(
            "Every change the AI proposes, one per line. A checked change will be "
            "applied; press Space to uncheck one you want to keep as it was. The "
            "details below say exactly what changed, word by word."
        )
        root.Add(self.hunk_list, 1, wx.EXPAND | wx.ALL, 8)
        for index in range(len(self.review.hunks)):
            self.hunk_list.Check(index, True)

        root.Add(wx.StaticText(panel, label="Change details"), 0, wx.LEFT | wx.RIGHT, 8)
        self.details = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(-1, 170),
        )
        set_accessible_name(self.details, "Change details")
        self.details.SetHelpText(
            "The change you are on, line by line: what was there, what would replace "
            "it, and for a small change the words that differ and the sentence they "
            "are in. Read-only."
        )
        root.Add(self.details, 0, wx.EXPAND | wx.ALL, 8)

        self.status = wx.StaticText(panel, label="Ready to apply the checked changes.")
        root.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        action_buttons: list = []
        if single:
            # A single change needs no bulk controls or partial apply: Accept
            # applies it and closes; Reject closes and leaves the document as-is.
            self.apply_button = wx.Button(panel, id=wx.ID_OK, label="Accept")
            reject_button = wx.Button(panel, id=wx.ID_CANCEL, label="Reject")
            self.apply_button.SetHelpText(
                "Applies the change as one edit; Control Z takes it back."
            )
            reject_button.SetHelpText("Closes this window and leaves your document unchanged.")
            buttons.Add(self.apply_button, 0, wx.RIGHT, 8)
            buttons.AddStretchSpacer(1)
            buttons.Add(reject_button, 0)
            self.apply_button.Bind(wx.EVT_BUTTON, self._on_accept_all_clicked)
            reject_button.Bind(wx.EVT_BUTTON, self._on_reject_clicked)
            action_buttons.append(self.apply_button)
        else:
            self.apply_button = wx.Button(panel, label="Apply Checked")
            accept_all_button = wx.Button(panel, label="Accept All")
            reject_all_button = wx.Button(panel, id=wx.ID_CANCEL, label="Reject All")
            self.apply_button.SetHelpText(
                "Applies only the checked changes, as one edit; Control Z takes it back."
            )
            accept_all_button.SetHelpText(
                "Applies every change, checked or not, as one edit; Control Z takes it back."
            )
            reject_all_button.SetHelpText("Closes this window and leaves your document unchanged.")
            buttons.Add(self.apply_button, 0, wx.RIGHT, 8)
            buttons.Add(accept_all_button, 0, wx.RIGHT, 8)
            buttons.AddStretchSpacer(1)
            buttons.Add(reject_all_button, 0)
            self.apply_button.Bind(wx.EVT_BUTTON, self._on_apply_clicked)
            accept_all_button.Bind(wx.EVT_BUTTON, self._on_accept_all_clicked)
            reject_all_button.Bind(wx.EVT_BUTTON, self._on_reject_clicked)
            action_buttons.extend([self.apply_button, accept_all_button, reject_all_button])
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        self.hunk_list.Bind(wx.EVT_LISTBOX, self._on_hunk_selected)
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)

        if self.review.hunks:
            self.hunk_list.SetSelection(0)
            self._show_hunk_details(0)
        else:
            for button in action_buttons:
                button.Enable(False)
            self.details.SetValue(
                "The proposed revision is identical to the current document. "
                "There is nothing to apply."
            )

    def show_modal(self) -> None:
        self.dialog.CentreOnParent()
        try:
            show_modal_dialog(self.dialog, self.dialog.GetTitle())
        finally:
            self.dialog.Destroy()

    def _on_hunk_selected(self, _event: object) -> None:
        index = self.hunk_list.GetSelection()
        if index != self._wx.NOT_FOUND and 0 <= index < len(self.review.hunks):
            self._show_hunk_details(index)

    def _show_hunk_details(self, index: int) -> None:
        hunk = self.review.hunks[index]
        self.details.SetValue("\n".join(hunk.detail_lines()))

    def _on_accept_all_clicked(self, event: object) -> None:
        """Accept every hunk and apply in one step (also serves single Accept)."""
        for index in range(len(self.review.hunks)):
            self.hunk_list.Check(index, True)
        self._on_apply_clicked(event)

    def _on_reject_clicked(self, _event: object) -> None:
        """Reject everything and dismiss the dialog without touching the document."""
        self.applied = False
        count = len(self.review.hunks)
        label = "Rejected the change" if count == 1 else "Rejected all changes"
        self._announce(f"{label}; the document is unchanged")
        self.dialog.EndModal(self._wx.ID_CANCEL)

    def _on_apply_clicked(self, _event: object) -> None:
        accepted = {
            index for index in range(len(self.review.hunks)) if self.hunk_list.IsChecked(index)
        }
        result_text = self.review.apply(accepted)
        if result_text == self.review.original:
            self.status.SetLabel("No changes were applied; the document is unchanged.")
            self._announce("No changes were applied")
            return
        self.applied = True
        self._on_apply(result_text)
        count = len(accepted)
        self._announce(f"Applied {count} {'change' if count == 1 else 'changes'} as one undo step")
        self.dialog.EndModal(self._wx.ID_OK)
