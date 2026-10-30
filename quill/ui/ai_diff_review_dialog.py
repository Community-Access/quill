"""Review AI Changes: an AI edit, read change by change and word by word.

QUILL's review window for AI edits (AI-7), extracted from
:mod:`quill.ui.assistant_tools` on 2026-10-15 so the free hosted AI of both
editors could offer it -- the AI Result window's **Review Changes** button --
without QUILL Lite importing QUILL's whole assistant module. QUILL keeps
reaching it exactly as before (``MainFrame.open_ai_diff_review``, and
``assistant_tools`` re-exports the class), so there is one review window and
one engine (:mod:`quill.core.ai.diff_review`, which supplies the word-level
detail: "changed 'quick' to 'rapid'" with the sentence it happened in).

**Word by word (2026-10-17).** In prose a hunk is usually a whole paragraph,
so accepting or rejecting it whole meant taking a bad word to keep a good one.
When the change on focus holds two or more word groups, a second list --
**Words in this change**, Alt+W -- shows each one with the sentence it is in,
checked; Space drops a group and keeps the original words there. Dropping the
last group drops the change; checking one back takes the change again. Accept
All still takes everything, Reject All still takes nothing, and accepting
every group is byte-for-byte the AI's revision.

Every control carries its F1 sentence at construction (GATE-<APP>-HELP); QUILL
Lite's help audit scans this module now that QUILL Lite opens it.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_modal_dialog
from quill.ui.dpi import dip_size

__all__ = ["DiffReviewDialog"]


class DiffReviewDialog:
    """Accessible, line-by-line review of an AI edit (AI-7).

    Presents the diff between the current document text and a proposed revision
    as a navigable checklist of added / removed / changed hunks. Each hunk is
    pre-checked; the reader can read every change line by line in the detail
    pane, keep or drop single word groups inside a changed hunk, then apply
    all, some (partial apply), or none (reject). Applying is handed back to the
    caller as a single replacement text so the editor records it as one undo
    unit.
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
        #: Accepted word groups per hunk, for hunks with any word groups.
        self._word_choices: dict[int, set[int]] = {
            hunk.index: set(range(len(hunk.word_changes)))
            for hunk in self.review.hunks
            if hunk.word_changes
        }
        self._word_hunk = -1  # the hunk the word list is showing

        self.dialog = wx.Dialog(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(dip_size(self.dialog, 880, 680))

        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        hunks = self.review.hunks
        single = len(hunks) == 1 and len(hunks[0].word_changes) < 2
        intro = (
            "Review the proposed AI change below. Read it line by line in the "
            "details pane, then choose Accept to apply it or Reject to leave the "
            "document unchanged."
            if single
            else (
                "Review the proposed AI changes below. Checked changes will be "
                "applied; uncheck any you want to keep as-is. When a change holds "
                "several word edits, the Words list below it lets you keep or drop "
                "each one. Use Apply Checked for a partial apply, Accept All to "
                "take every change, or Reject All to leave the document unchanged."
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

        root.Add(wx.StaticText(panel, label="&Changes"), 0, wx.LEFT | wx.RIGHT, 8)
        self.hunk_list = wx.CheckListBox(  # A11Y-SR-1-OK: diff hunks; pending CheckBox conversion
            panel,
            choices=[hunk.describe() for hunk in hunks],
        )
        set_accessible_name(self.hunk_list, "Changes")
        self.hunk_list.SetHelpText(
            "Every change the AI proposes, one per line. A checked change will be "
            "applied; press Space to uncheck one you want to keep as it was. The "
            "details below say exactly what changed, word by word. Alt+C comes "
            "back here."
        )
        root.Add(self.hunk_list, 1, wx.EXPAND | wx.ALL, 8)
        for index in range(len(hunks)):
            self.hunk_list.Check(index, True)

        self.word_label = wx.StaticText(panel, label="&Words in this change")
        root.Add(self.word_label, 0, wx.LEFT | wx.RIGHT, 8)
        self.word_list = wx.CheckListBox(  # A11Y-SR-1-OK: word groups of one hunk
            panel,
            choices=[],
            size=dip_size(panel, -1, 120),
        )
        set_accessible_name(self.word_list, "Words in this change")
        self.word_list.SetHelpText(
            "Each word edit inside the change you are on, with the sentence it is "
            "in. A checked edit is applied; press Space to drop one and keep the "
            "original words there while the rest of the change still goes in. "
            "Dropping every edit drops the change. Shown only when a change holds "
            "two or more word edits; Alt+W reaches it."
        )
        root.Add(self.word_list, 0, wx.EXPAND | wx.ALL, 8)

        root.Add(wx.StaticText(panel, label="Change &details"), 0, wx.LEFT | wx.RIGHT, 8)
        self.details = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=dip_size(panel, -1, 150),
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
                "Applies only the checked changes, and inside them only the checked "
                "word edits, as one edit; Control Z takes it back."
            )
            accept_all_button.SetHelpText(
                "Applies every change and every word edit, checked or not, as one "
                "edit; Control Z takes it back."
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
        self._panel = panel
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        self.hunk_list.Bind(wx.EVT_LISTBOX, self._on_hunk_selected)
        self.hunk_list.Bind(wx.EVT_CHECKLISTBOX, self._on_hunk_checked)
        self.word_list.Bind(wx.EVT_LISTBOX, self._on_word_selected)
        self.word_list.Bind(wx.EVT_CHECKLISTBOX, self._on_word_checked)
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)

        if hunks:
            self.hunk_list.SetSelection(0)
            self._show_hunk_details(0)
        else:
            self._show_word_list(False)
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

    # ------------------------------------------------------------------ #
    # Moving through the changes
    # ------------------------------------------------------------------ #

    def _on_hunk_selected(self, _event: object) -> None:
        index = self.hunk_list.GetSelection()
        if index != self._wx.NOT_FOUND and 0 <= index < len(self.review.hunks):
            self._show_hunk_details(index)

    def _show_hunk_details(self, index: int) -> None:
        hunk = self.review.hunks[index]
        self.details.SetValue("\n".join(hunk.detail_lines()))
        self._fill_word_list(index)

    def _fill_word_list(self, index: int) -> None:
        """Show the word groups of hunk *index*, or hide the list for a hunk
        with fewer than two (where the change's own check box says it all)."""
        hunk = self.review.hunks[index]
        self._word_hunk = index
        if len(hunk.word_changes) < 2:
            self._show_word_list(False)
            return
        self.word_list.Set([change.choice_label() for change in hunk.word_changes])
        chosen = self._word_choices.get(index, set())
        hunk_on = self.hunk_list.IsChecked(index)
        for position in range(len(hunk.word_changes)):
            self.word_list.Check(position, hunk_on and position in chosen)
        self._show_word_list(True)

    def _show_word_list(self, show: bool) -> None:
        self.word_label.Show(show)
        self.word_list.Show(show)
        panel = getattr(self, "_panel", None)
        if panel is not None:
            panel.Layout()

    def _on_word_selected(self, _event: object) -> None:
        position = self.word_list.GetSelection()
        hunk_index = self._word_hunk
        if position == self._wx.NOT_FOUND or not 0 <= hunk_index < len(self.review.hunks):
            return
        changes = self.review.hunks[hunk_index].word_changes
        if not 0 <= position < len(changes):
            return
        change = changes[position]
        lines = [f"{change.action_phrase()}."]
        if change.old_sentence:
            lines.append(f"Sentence before: {change.old_sentence}")
        if change.new_sentence and change.new_sentence != change.old_sentence:
            lines.append(f"Sentence after: {change.new_sentence}")
        self.details.SetValue("\n".join(lines))

    # ------------------------------------------------------------------ #
    # Keeping the two lists in step
    # ------------------------------------------------------------------ #

    def _on_hunk_checked(self, event: object) -> None:
        """A change checked or unchecked whole: all its word groups follow."""
        index = int(event.GetInt()) if hasattr(event, "GetInt") else self._word_hunk
        if not 0 <= index < len(self.review.hunks):
            return
        hunk = self.review.hunks[index]
        if hunk.word_changes and self.hunk_list.IsChecked(index):
            self._word_choices[index] = set(range(len(hunk.word_changes)))
        if index == self._word_hunk:
            self._fill_word_list(index)

    def set_word_accepted(self, position: int, accepted: bool) -> None:
        """Keep or drop word group *position* of the change on show.

        The one path for a word decision, so the keyboard (Space in the Words
        list) and the tests reach the same rules: dropping the last group
        unchecks the change, and keeping one in an unchecked change checks it.
        Both of those happen to a control that does not have focus, so they
        are the only things said -- the check box under focus speaks for
        itself.
        """
        hunk_index = self._word_hunk
        if not 0 <= hunk_index < len(self.review.hunks):
            return
        count = len(self.review.hunks[hunk_index].word_changes)
        if not 0 <= position < count:
            return
        hunk_on = self.hunk_list.IsChecked(hunk_index)
        chosen = set(self._word_choices.get(hunk_index, set())) if hunk_on else set()
        if accepted:
            chosen.add(position)
        else:
            chosen.discard(position)
        self._word_choices[hunk_index] = chosen
        if not chosen and hunk_on:
            self.hunk_list.Check(hunk_index, False)
            self._announce("No word edits left in this change, so it will not be applied")
        elif chosen and not hunk_on:
            self.hunk_list.Check(hunk_index, True)
            self._announce("This change will be applied again, with the checked word edits")
        kept = len(chosen)
        self.status.SetLabel(
            f"{kept} of {count} word edits in this change will be applied."
            if chosen
            else "This change will not be applied."
        )

    def _on_word_checked(self, event: object) -> None:
        position = int(event.GetInt())
        self.set_word_accepted(position, bool(self.word_list.IsChecked(position)))

    # ------------------------------------------------------------------ #
    # Applying
    # ------------------------------------------------------------------ #

    def _on_accept_all_clicked(self, event: object) -> None:
        """Accept every hunk and every word group, in one step (also serves
        single Accept)."""
        for index in range(len(self.review.hunks)):
            self.hunk_list.Check(index, True)
        self._word_choices = {
            hunk.index: set(range(len(hunk.word_changes)))
            for hunk in self.review.hunks
            if hunk.word_changes
        }
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
        choices = getattr(self, "_word_choices", {})
        result_text = self.review.apply(accepted, choices)
        if result_text == self.review.original:
            self.status.SetLabel("No changes were applied; the document is unchanged.")
            self._announce("No changes were applied")
            return
        self.applied = True
        self._on_apply(result_text)
        count = len(accepted)
        partial = sum(
            1
            for index in accepted
            if len(choices.get(index, ())) < len(self.review.hunks[index].word_changes)
        )
        noun = "change" if count == 1 else "changes"
        if partial:
            self._announce(f"Applied {count} {noun}, {partial} of them in part, as one undo step")
        else:
            self._announce(f"Applied {count} {noun} as one undo step")
        self.dialog.EndModal(self._wx.ID_OK)
