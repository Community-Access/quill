"""Compare Configuration: what differs from the source, read before proposing (PRD 22.11).

A check box for each file that can be updated -- missing here, or
different, each with lines added and removed -- all checked to start; the
differences of the selected file as a unified diff to read line by line; and
one line for the rest (the same, or only here and kept). Propose Update
hands back the checked files; the Workbench asks once more and opens one
pull request. Nothing is sent from here.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from quill.ui.change_walk_keys import bind_change_walk
from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog
from quill.ui.dpi import dip_size

__all__ = ["ConfigCompareDialog"]


class ConfigCompareDialog:
    title = "Compare Configuration"

    def __init__(
        self,
        parent: object,
        repository: str,
        source: str,
        diffs: Sequence[Any],
        *,
        announce: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._announce = announce or (lambda _text: None)
        self.updatable = [d for d in diffs if d.can_update]
        rest = [d for d in diffs if not d.can_update]
        self.chosen: list[Any] = []
        self.dialog = wx.Dialog(
            parent, title="Compare Configuration", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 640, 520))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(self.dialog, label=f"Files in {repository} to update from {source}:"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        # One real check box per file (A11Y-SR-1); the one with focus is the one
        # whose differences show below.
        panel = wx.ScrolledWindow(self.dialog)
        panel.SetScrollRate(0, 10)
        column = wx.BoxSizer(wx.VERTICAL)
        self.files: list[Any] = []
        self.current = 0
        for index, found in enumerate(self.updatable):
            box = wx.CheckBox(panel, label=found.sentence())
            box.SetValue(True)
            box.SetHelpText(
                "Checked files go into one pull request. Its differences show below while "
                "it has focus."
            )
            box.Bind(wx.EVT_SET_FOCUS, lambda e, i=index: (self.show_diff(i), e.Skip()))
            column.Add(box, 0, wx.ALL, 2)
            self.files.append(box)
        panel.SetSizer(column)
        root.Add(panel, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        root.Add(
            wx.StaticText(self.dialog, label="&Differences in the selected file:"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8,
        )
        self.diff = wx.TextCtrl(
            self.dialog, value="", style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP
        )
        self.diff.SetName("Differences")
        self.diff.SetHelpText(
            "Each change in the selected file: where it is, then its lines, each marked in "
            "your Diff Line Marks style. Added lines come from the source; removed lines are "
            "what this repository has now. F8 and Shift+F8 move to the next and previous change."
        )
        # F8 / Shift+F8 and words for the marks, as every other diff (FUX-12).
        bind_change_walk(self.diff, self._announce)
        root.Add(self.diff, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        same = sum(1 for d in rest if d.state == "same")
        only = sum(1 for d in rest if d.state == "only_here")
        self.others = wx.StaticText(
            self.dialog,
            label=f"Also: {same} file{'s' if same != 1 else ''} the same, and {only} only in "
            f"{repository}, which {'are' if only != 1 else 'is'} kept.",
        )
        self.others.SetName("The other files")
        root.Add(self.others, 0, wx.EXPAND | wx.ALL, 8)
        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self.dialog, wx.ID_OK, "Propose Update")
        ok.SetHelpText("Ask, then open one pull request with the checked files.")
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, "Cancel")
        cancel.SetHelpText("Close without changing anything.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        ok.Bind(wx.EVT_BUTTON, self._on_ok)
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        if self.updatable:
            self.show_diff(0)

    def show_diff(self, index: int) -> None:
        """Show file *index*'s differences in the box below (nothing is said)."""
        if not 0 <= index < len(self.updatable):
            return
        self.current = index
        found = self.updatable[index]
        if found.state == "missing":
            self.diff.SetValue(found.source_text)
        else:
            from quill.core.diff_marks import render_texts
            from quill.core.github.review_preferences import load_line_marks

            self.diff.SetValue(
                render_texts(
                    found.target_text,
                    found.source_text,
                    "this repository's copy",
                    "the source",
                    style=load_line_marks(),
                )
            )

    def checked(self) -> list[Any]:
        return [d for d, box in zip(self.updatable, self.files, strict=True) if box.GetValue()]

    def _on_ok(self, event: Any) -> None:
        chosen = self.checked()
        if not chosen:
            self._announce("Check at least one file, or press Cancel.")
            return
        self.chosen = chosen
        event.Skip()

    def show(self) -> list[Any]:
        try:
            if show_modal_dialog(self.dialog, self.title) != self._wx.ID_OK:
                return []
            return self.chosen
        finally:
            self.dialog.Destroy()
