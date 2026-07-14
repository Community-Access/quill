"""AI Agent Result dialog for QUILL.

Shows the output of a completed agent run, with a step log, the final text,
insert/copy actions, and a re-run button.  This dialog is modal.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids


class AIAgentResultDialog:
    """Display the result of an agent session run.

    Parameters
    ----------
    parent:
        wx parent window.
    result:
        Completed AgentResult from agent_session.run_agent().
    title:
        Dialog title, e.g. "Rewrite Agent Result".
    show_modal_dialog:
        MainFrame's _show_modal_dialog gate.
    on_insert_text:
        Optional callback to insert the final text at the cursor.
    on_replace_selection:
        Optional callback to replace the current selection with the final text.
    on_rerun:
        Optional callback invoked when the user clicks Re-Run (no args).
    """

    def __init__(
        self,
        parent: object,
        result: object,
        title: str,
        show_modal_dialog: Callable,
        on_insert_text: Callable[[str], None] | None = None,
        on_replace_selection: Callable[[str], None] | None = None,
        on_rerun: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._result = result
        self._on_insert = on_insert_text
        self._on_replace = on_replace_selection
        self._on_rerun = on_rerun
        self._show_modal = show_modal_dialog

        self.dialog = wx.Dialog(
            parent,
            title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(760, 620))
        self._build_ui()

    def _build_ui(self) -> None:
        wx = self._wx
        result = self._result
        root = wx.BoxSizer(wx.VERTICAL)

        # Step log
        if result.steps:
            log_box = wx.StaticBox(self.dialog, label="Steps")
            log_sizer = wx.StaticBoxSizer(log_box, wx.VERTICAL)
            self._step_list = wx.ListCtrl(
                self.dialog,
                style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SIMPLE,
            )
            self._step_list.SetName("Agent steps")
            self._step_list.InsertColumn(0, "#", width=36)
            self._step_list.InsertColumn(1, "Step", width=200)
            self._step_list.InsertColumn(2, "Output preview", width=440)
            for i, step in enumerate(result.steps):
                self._step_list.InsertItem(i, str(i + 1))
                self._step_list.SetItem(i, 1, step.label)
                self._step_list.SetItem(i, 2, step.output[:80].replace("\n", " "))
            self._step_list.SetMinSize(wx.Size(-1, 100))
            log_sizer.Add(self._step_list, 1, wx.EXPAND | wx.ALL, 4)
            root.Add(log_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Final output
        out_box = wx.StaticBox(self.dialog, label="Final output")
        out_sizer = wx.StaticBoxSizer(out_box, wx.VERTICAL)
        self._output_ctrl = wx.TextCtrl(
            self.dialog,
            value=result.final_output,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
        )
        self._output_ctrl.SetName("Agent output")
        out_sizer.Add(self._output_ctrl, 1, wx.EXPAND | wx.ALL, 4)
        root.Add(out_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Char count
        char_label = wx.StaticText(
            self.dialog,
            label=f"{len(result.final_output):,} characters",
        )
        root.Add(char_label, 0, wx.LEFT | wx.BOTTOM, 8)

        # Action buttons
        btn_row = wx.BoxSizer(wx.HORIZONTAL)

        self._insert_btn = wx.Button(self.dialog, label="&Insert at Cursor")
        self._replace_btn = wx.Button(self.dialog, label="&Replace Selection")
        self._copy_btn = wx.Button(self.dialog, label="&Copy")
        self._rerun_btn = wx.Button(self.dialog, label="Re-&Run")
        close_btn = wx.Button(self.dialog, wx.ID_CLOSE, label="C&lose")

        apply_modal_ids(
            self.dialog,
            affirmative_id=close_btn.GetId(),
            escape_id=close_btn.GetId(),
        )

        has_output = bool(result.final_output)
        self._insert_btn.Enable(has_output and self._on_insert is not None)
        self._replace_btn.Enable(has_output and self._on_replace is not None)
        self._copy_btn.Enable(has_output)
        self._rerun_btn.Enable(self._on_rerun is not None)

        for b in (self._insert_btn, self._replace_btn, self._copy_btn, self._rerun_btn, close_btn):
            btn_row.Add(b, 0, wx.RIGHT, 6)
        root.Add(btn_row, 0, wx.ALL, 8)

        self.dialog.SetSizer(root)
        self._bind_events(close_btn)
        wx.CallAfter(self._output_ctrl.SetFocus)

    def _bind_events(self, close_btn: object) -> None:
        wx = self._wx
        self._insert_btn.Bind(wx.EVT_BUTTON, self._on_insert_clicked)
        self._replace_btn.Bind(wx.EVT_BUTTON, self._on_replace_clicked)
        self._copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        self._rerun_btn.Bind(wx.EVT_BUTTON, self._on_rerun_clicked)
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))

    def _on_insert_clicked(self, event: object) -> None:
        if self._on_insert:
            self._on_insert(self._result.final_output)
        self.dialog.EndModal(self._wx.ID_OK)

    def _on_replace_clicked(self, event: object) -> None:
        if self._on_replace:
            self._on_replace(self._result.final_output)
        self.dialog.EndModal(self._wx.ID_OK)

    def _on_copy(self, event: object) -> None:
        wx = self._wx
        text = self._result.final_output
        if text and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()

    def _on_rerun_clicked(self, event: object) -> None:
        self.dialog.EndModal(self._wx.ID_RETRY)
        if self._on_rerun:
            self._on_rerun()

    def show(self) -> int:
        result = self._show_modal(self.dialog)
        self.dialog.Destroy()
        return result
