"""AI Document Q&A dialog for QUILL.

Supports both the current open document and external PDF/text files.
Multi-turn: the user can ask follow-up questions without starting over.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from quill.ui.dialog_contract import apply_modal_ids


class AIDocumentQADialog:
    """Ask questions about a document and get AI answers grounded in the text.

    Operates as a persistent (non-modal) dialog:
    - Document source: current editor content or a file chosen by Browse.
    - Multi-turn: each answer is added to the history list.
    - Source excerpt: shown below the answer when one was found.
    - Copy/Insert buttons for the selected answer.
    """

    def __init__(
        self,
        parent: object,
        initial_document_text: str,
        document_title: str,
        show_modal_dialog: Callable,
        connection: object,
        api_key: str,
        on_insert_text: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._connection = connection
        self._api_key = api_key
        self._on_insert = on_insert_text
        self._show_modal = show_modal_dialog
        self._working = False

        from quill.core.ai.document_qa import ConversationContext

        self._context = ConversationContext(document_text=initial_document_text)
        self._document_title = document_title

        self.dialog = wx.Dialog(
            parent,
            title=f"Document Q&A - {document_title}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(820, 660))
        self._build_ui()

    def _build_ui(self) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        # Document source row
        src_box = wx.StaticBox(self.dialog, label="Document source")
        src_sizer = wx.StaticBoxSizer(src_box, wx.HORIZONTAL)
        self._doc_path_ctrl = wx.TextCtrl(
            self.dialog,
            value=self._document_title,
        )
        self._doc_path_ctrl.SetName("Document path or title")
        browse_btn = wx.Button(self.dialog, label="&Browse File...")
        use_editor_btn = wx.Button(self.dialog, label="Use &Current Document")
        src_sizer.Add(self._doc_path_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        src_sizer.Add(browse_btn, 0, wx.RIGHT, 4)
        src_sizer.Add(use_editor_btn, 0)
        root.Add(src_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Truncation notice
        char_count = len(self._context.document_text)
        if char_count > 80_000:
            notice = wx.StaticText(
                self.dialog,
                label=(
                    f"Document is {char_count:,} characters. Only the first 80,000 "
                    "characters will be analysed. Answers may not cover the full document."
                ),
            )
            notice.Wrap(760)
            root.Add(notice, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Q&A history list
        history_label = wx.StaticText(self.dialog, label="Conversation history:")
        root.Add(history_label, 0, wx.LEFT | wx.TOP, 8)
        self._history = wx.ListCtrl(
            self.dialog,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SIMPLE,
        )
        self._history.SetName("Q&A history")
        self._history.InsertColumn(0, "#", width=36)
        self._history.InsertColumn(1, "Question", width=280)
        self._history.InsertColumn(2, "Answer (preview)", width=360)
        root.Add(self._history, 1, wx.EXPAND | wx.ALL, 8)

        # Answer detail panel
        detail_box = wx.StaticBox(self.dialog, label="Answer")
        detail_sizer = wx.StaticBoxSizer(detail_box, wx.VERTICAL)
        self._answer_ctrl = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_NONE,
        )
        self._answer_ctrl.SetName("Answer text")
        self._excerpt_label = wx.StaticText(self.dialog, label="")
        self._excerpt_label.Wrap(760)
        detail_sizer.Add(self._answer_ctrl, 1, wx.EXPAND | wx.ALL, 4)
        detail_sizer.Add(self._excerpt_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 4)
        root.Add(detail_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Question entry
        q_row = wx.BoxSizer(wx.HORIZONTAL)
        q_label = wx.StaticText(self.dialog, label="Ask a question:")
        self._question_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self._question_ctrl.SetName("Question")
        self._ask_btn = wx.Button(self.dialog, label="&Ask (Enter)")
        q_row.Add(q_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        q_row.Add(self._question_ctrl, 1, wx.RIGHT, 6)
        q_row.Add(self._ask_btn, 0)
        root.Add(q_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Status
        self._status_label = wx.StaticText(self.dialog, label="Ready.")
        root.Add(self._status_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Action buttons
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._copy_btn = wx.Button(self.dialog, label="&Copy Answer")
        self._insert_btn = wx.Button(self.dialog, label="&Insert at Cursor")
        self._clear_btn = wx.Button(self.dialog, label="C&lear History")
        self._close_btn = wx.Button(self.dialog, label="C&lose")
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._close_btn.GetId(),
            escape_id=self._close_btn.GetId(),
        )
        self._copy_btn.Enable(False)
        if self._on_insert is None:
            self._insert_btn.Enable(False)
        else:
            self._insert_btn.Enable(False)
        for b in (self._copy_btn, self._insert_btn, self._clear_btn, self._close_btn):
            btn_row.Add(b, 0, wx.RIGHT, 6)
        root.Add(btn_row, 0, wx.ALL, 8)

        self.dialog.SetSizer(root)
        self._bind_events(browse_btn, use_editor_btn)
        wx.CallAfter(self._question_ctrl.SetFocus)

    def _bind_events(self, browse_btn: object, use_editor_btn: object) -> None:
        wx = self._wx
        browse_btn.Bind(wx.EVT_BUTTON, self._on_browse)
        use_editor_btn.Bind(wx.EVT_BUTTON, self._on_use_editor)
        self._question_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_ask)
        self._ask_btn.Bind(wx.EVT_BUTTON, self._on_ask)
        self._history.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_history_select)
        self._copy_btn.Bind(wx.EVT_BUTTON, self._on_copy)
        self._insert_btn.Bind(wx.EVT_BUTTON, self._on_insert_clicked)
        self._clear_btn.Bind(wx.EVT_BUTTON, self._on_clear)
        self._close_btn.Bind(
            wx.EVT_BUTTON,
            lambda _e: self.dialog.Destroy(),
        )

    def _on_browse(self, event: object) -> None:
        wx = self._wx
        wildcard = (
            "Documents and PDFs (*.pdf;*.txt;*.md;*.docx)|*.pdf;*.txt;*.md;*.docx"
            "|All files (*.*)|*.*"
        )
        with wx.FileDialog(
            self.dialog,
            message="Select document to ask questions about",
            wildcard=wildcard,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            path = Path(dlg.GetPath())
        self._load_file(path)

    def _load_file(self, path: Path) -> None:
        try:
            if path.suffix.lower() == ".pdf":
                from quill.io.pdf import format_pdf_document

                text = format_pdf_document(path)
            else:
                text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            self._status_label.SetLabel(f"Could not open file: {exc}")
            return

        from quill.core.ai.document_qa import ConversationContext

        self._context = ConversationContext(document_text=text)
        self._document_title = path.name
        self.dialog.SetTitle(f"Document Q&A - {path.name}")
        self._doc_path_ctrl.SetValue(str(path))
        self._history.DeleteAllItems()
        self._answer_ctrl.SetValue("")
        self._status_label.SetLabel(
            f"Loaded {path.name} ({len(text):,} characters). Ask your first question."
        )

    def _on_use_editor(self, event: object) -> None:
        # Caller must have passed document text at construction time.
        # This button signals intent to re-confirm that source.
        self._status_label.SetLabel(
            f"Using current document ({len(self._context.document_text):,} characters)."
        )

    def _on_ask(self, event: object) -> None:
        if self._working:
            return
        question = self._question_ctrl.GetValue().strip()
        if not question:
            self._status_label.SetLabel("Type a question first.")
            return
        if not self._context.document_text.strip():
            self._status_label.SetLabel("No document loaded. Browse or use current document.")
            return

        self._working = True
        self._ask_btn.Enable(False)
        self._status_label.SetLabel("Asking AI...")

        def _run() -> None:
            import wx as _wx

            try:
                answer = self._context.ask(question, self._connection, self._api_key)
                _wx.CallAfter(self._on_answer_done, question, answer)
            except Exception as exc:  # noqa: BLE001
                _wx.CallAfter(self._on_answer_error, str(exc))

        threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: AI bg thread

    def _on_answer_done(self, question: str, answer: object) -> None:
        row = self._history.GetItemCount()
        self._history.InsertItem(row, str(row + 1))
        self._history.SetItem(row, 1, question[:60])
        self._history.SetItem(row, 2, answer.answer[:80])
        self._history.SetItemState(
            row,
            self._wx.LIST_STATE_SELECTED | self._wx.LIST_STATE_FOCUSED,
            self._wx.LIST_STATE_SELECTED | self._wx.LIST_STATE_FOCUSED,
        )
        self._answer_ctrl.SetValue(answer.answer)
        if answer.source_excerpt:
            self._excerpt_label.SetLabel(f"Source: {answer.source_excerpt}")
        else:
            self._excerpt_label.SetLabel("")
        truncation = " (document was truncated at 80,000 chars)" if answer.truncated else ""
        self._status_label.SetLabel(f"Answer received{truncation}.")
        self._copy_btn.Enable(True)
        if self._on_insert is not None:
            self._insert_btn.Enable(True)
        self._question_ctrl.SetValue("")
        self._working = False
        self._ask_btn.Enable(True)
        self._wx.CallAfter(self._question_ctrl.SetFocus)

    def _on_answer_error(self, message: str) -> None:
        self._status_label.SetLabel(f"Error: {message}")
        self._working = False
        self._ask_btn.Enable(True)

    def _on_history_select(self, event: object) -> None:
        row = self._history.GetFirstSelected()
        if row < 0 or row >= len(self._context.turns):
            return
        q, a = self._context.turns[row]
        self._answer_ctrl.SetValue(a)
        self._copy_btn.Enable(True)
        if self._on_insert is not None:
            self._insert_btn.Enable(True)

    def _on_copy(self, event: object) -> None:
        wx = self._wx
        text = self._answer_ctrl.GetValue()
        if text and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()
        self._status_label.SetLabel("Answer copied to clipboard.")

    def _on_insert_clicked(self, event: object) -> None:
        if self._on_insert is not None:
            text = self._answer_ctrl.GetValue()
            if text:
                self._on_insert(text)

    def _on_clear(self, event: object) -> None:
        self._context.clear_history()
        self._history.DeleteAllItems()
        self._answer_ctrl.SetValue("")
        self._excerpt_label.SetLabel("")
        self._status_label.SetLabel("History cleared. Ask a new question.")
        self._copy_btn.Enable(False)
        self._insert_btn.Enable(False)

    def show(self) -> None:
        self.dialog.Show()
        self._wx.CallAfter(self._question_ctrl.SetFocus)
