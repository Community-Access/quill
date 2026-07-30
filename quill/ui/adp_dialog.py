"""Ask ADP -- the Audio Description Project assistant dialog.

Chat with the ADP catalog brain: type (or route a spoken question into) a
natural-language question about described films, series, and TV; the short,
speakable answer lands in a focus-managed read-only region (per ADP's
accessibility contract, NOT a live region), and the structured results
render as a navigable table. Multi-turn context works by round-tripping the
opaque ``history`` list; New Conversation clears it. Answers can be spoken
automatically through QUILL's own announcement engine -- voice always lives
on this device.

Pre-release feature: reachable only when ``future.adp_assistant`` is
unlocked by a signed code. Deliberately absent from user documentation.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.adp.models import TABLE_COLUMNS, AdpDataset, AskResponse, row_cell
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name


class AdpAskDialog:
    """Question in, spoken answer + accessible results table out."""

    def __init__(
        self,
        parent: object,
        *,
        ask: Callable[..., AskResponse],
        task_manager: object,
        speak_answers: bool = True,
        initial_question: str = "",
        auto_ask: bool = False,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._ask = ask
        self._task_manager = task_manager
        self._announce = announce_cb or (lambda _m: None)
        self._history: list[object] = []
        self._busy = False

        self.dialog = wx.Dialog(
            parent,
            title="Ask ADP — Audio Description Search",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((760, 560))
        root = wx.BoxSizer(wx.VERTICAL)

        question_label = wx.StaticText(self.dialog, label="&Question:")
        root.Add(question_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        ask_row = wx.BoxSizer(wx.HORIZONTAL)
        self._question = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        set_accessible_name(
            self._question,
            "Question for the ADP assistant, like what described comedies are on Netflix",
        )
        self._ask_btn = wx.Button(self.dialog, label="&Ask")
        set_accessible_name(self._ask_btn, "Ask the ADP assistant")
        new_btn = wx.Button(self.dialog, label="&New Conversation")
        set_accessible_name(new_btn, "Start a fresh conversation; context is cleared")
        ask_row.Add(self._question, 1, wx.EXPAND | wx.RIGHT, 6)
        ask_row.Add(self._ask_btn, 0, wx.RIGHT, 6)
        ask_row.Add(new_btn, 0)
        root.Add(ask_row, 0, wx.EXPAND | wx.ALL, 8)

        answer_label = wx.StaticText(self.dialog, label="A&nswer:")
        root.Add(answer_label, 0, wx.LEFT | wx.RIGHT, 8)
        self._answer = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE | wx.TE_READONLY)
        set_accessible_name(self._answer, "The assistant's answer, read-only")
        self._answer.SetMinSize((-1, 90))
        root.Add(self._answer, 0, wx.EXPAND | wx.ALL, 8)

        results_label = wx.StaticText(self.dialog, label="&Results:")
        root.Add(results_label, 0, wx.LEFT | wx.RIGHT, 8)
        self._results = wx.ListCtrl(self.dialog, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        set_accessible_name(
            self._results, "Structured results behind the answer; arrow through rows"
        )
        for index, (heading, _keys) in enumerate(TABLE_COLUMNS):
            self._results.InsertColumn(index, heading, width=140 if index == 0 else 100)
        root.Add(self._results, 1, wx.EXPAND | wx.ALL, 8)

        options_row = wx.BoxSizer(wx.HORIZONTAL)
        self._speak_check = wx.CheckBox(self.dialog, label="&Speak answers")
        set_accessible_name(self._speak_check, "Speak each answer aloud through Quill's own voice")
        self._speak_check.SetValue(speak_answers)
        self._status = wx.StaticText(self.dialog, label="Ready.")
        set_accessible_name(self._status, "Status")
        close_btn = wx.Button(self.dialog, id=wx.ID_CANCEL, label="&Close")
        options_row.Add(self._speak_check, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
        options_row.Add(self._status, 1, wx.ALIGN_CENTER_VERTICAL)
        options_row.Add(close_btn, 0)
        root.Add(options_row, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self._question.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._on_ask())
        self._ask_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_ask())
        new_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_new_conversation())

        if initial_question:
            self._question.SetValue(initial_question)
            if auto_ask:
                wx.CallAfter(self._on_ask)

    # -- asking -----------------------------------------------------------------

    def _on_ask(self) -> None:
        question = self._question.GetValue().strip()
        if not question or self._busy:
            return
        self._busy = True
        self._ask_btn.Enable(False)
        self._status.SetLabel("Asking ADP...")
        self._announce("Asking ADP...")
        history = list(self._history)

        def _do_ask(**_kwargs: object) -> AskResponse:
            return self._ask(question, history=history or None)

        def _on_success(_op: str, response: AskResponse) -> None:
            # Already on the UI thread: the task manager marshals its callbacks
            # here via call_ui_safely (which also guards them). Apply directly --
            # a second raw CallAfter would run outside that guard, so an Escape
            # that destroys the dialog first would raise an uncaught RuntimeError
            # on the dead widgets.
            self._apply_response(response)

        def _on_failure(_op: str, error: object) -> None:
            self._apply_failure(str(error))

        self._task_manager.submit(
            "adp-ask", _do_ask, on_success=_on_success, on_failure=_on_failure
        )

    def _apply_response(self, response: AskResponse) -> None:
        self._busy = False
        self._ask_btn.Enable(True)
        self._history = list(response.history)
        self._answer.SetValue(response.answer)
        rows = self._fill_results(response.datasets)
        self._status.SetLabel(f"{rows} result row(s)." if rows else "Answered.")
        # Focus-managed answer region per the ADP accessibility contract --
        # focus moves to the answer, which the screen reader then reads;
        # never an ARIA-live-style unsolicited announcement region.
        self._answer.SetFocus()
        if self._speak_check.GetValue():
            self._announce(response.answer)
        # Clear the box after a successful ask so the next question starts fresh
        # (the answer already has focus). On failure the text is left in place
        # (see _apply_failure) so it's recoverable.
        self._question.SetValue("")

    def _apply_failure(self, message: str) -> None:
        self._busy = False
        self._ask_btn.Enable(True)
        self._status.SetLabel(message)
        self._announce(message)

    def _fill_results(self, datasets: list[AdpDataset]) -> int:
        self._results.DeleteAllItems()
        row_index = 0
        for dataset in datasets:
            for row in dataset.rows:
                self._results.InsertItem(row_index, row_cell(row, TABLE_COLUMNS[0][1]))
                for col, (_heading, keys) in enumerate(TABLE_COLUMNS[1:], start=1):
                    self._results.SetItem(row_index, col, row_cell(row, keys))
                row_index += 1
        return row_index

    def _on_new_conversation(self) -> None:
        self._history = []
        self._answer.SetValue("")
        self._results.DeleteAllItems()
        self._status.SetLabel("New conversation.")
        self._announce("New conversation; context cleared.")
        self._question.SetValue("")
        self._question.SetFocus()

    # -- lifecycle ------------------------------------------------------------

    def show(self) -> None:
        from quill.ui.dialog_contract import show_modal_dialog

        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)
        self._question.SetFocus()
        # Pass the label + announce hook so the screen-reader enter/exit region
        # cues fire like every other modal (NowPlayingDialog, the radio
        # dialogs); Destroy in finally so a show-time failure never leaks it.
        try:
            show_modal_dialog(self.dialog, "Ask ADP", announce=self._announce)
        finally:
            self.dialog.Destroy()
