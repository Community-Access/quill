"""AI Thesaurus dialog for QUILL.

Looks up synonyms for the selected word (or a word typed in the search box)
and presents them with brief usage notes.  The user can double-click or press
Enter to replace the selected word in the editor.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids


class AIThesaurusDialog:
    """AI-powered thesaurus lookup.

    Parameters
    ----------
    parent:
        wx parent window.
    initial_word:
        Word pre-filled from the selection (may be empty).
    context_sentence:
        The sentence containing the word, for disambiguation.
    show_modal_dialog:
        MainFrame's _show_modal_dialog gate.
    on_lookup:
        Callable(word, context_sentence) -> list[ThesaurusEntry].
        Called in a background thread when the user clicks Look Up.
    on_replace:
        Optional callback(replacement: str) to insert the chosen synonym.
    """

    def __init__(
        self,
        parent: object,
        initial_word: str,
        context_sentence: str,
        show_modal_dialog: Callable,
        on_lookup: Callable,
        on_replace: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._on_lookup = on_lookup
        self._on_replace = on_replace
        self._show_modal = show_modal_dialog
        self._working = False
        self._entries: list = []
        self._context_sentence = context_sentence

        self.dialog = wx.Dialog(
            parent,
            title="AI Thesaurus",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize(wx.Size(600, 480))
        self._build_ui(initial_word)

    def _build_ui(self, initial_word: str) -> None:
        wx = self._wx
        root = wx.BoxSizer(wx.VERTICAL)

        # Search row
        search_row = wx.BoxSizer(wx.HORIZONTAL)
        word_label = wx.StaticText(self.dialog, label="Word:")
        self._word_ctrl = wx.TextCtrl(self.dialog, value=initial_word, style=wx.TE_PROCESS_ENTER)
        self._word_ctrl.SetName("Word to look up")
        self._lookup_btn = wx.Button(self.dialog, label="&Look Up")
        search_row.Add(word_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        search_row.Add(self._word_ctrl, 1, wx.RIGHT, 6)
        search_row.Add(self._lookup_btn, 0)
        root.Add(search_row, 0, wx.EXPAND | wx.ALL, 8)

        # Context hint
        if self._context_sentence:
            ctx_text = self._context_sentence[:80] + (
                "..." if len(self._context_sentence) > 80 else ""
            )
            ctx_label = wx.StaticText(self.dialog, label=f'Context: "{ctx_text}"')
            ctx_label.Wrap(560)
            root.Add(ctx_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Results list
        results_label = wx.StaticText(self.dialog, label="Synonyms:")
        root.Add(results_label, 0, wx.LEFT | wx.TOP, 8)
        self._list = wx.ListCtrl(
            self.dialog,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SIMPLE,
        )
        self._list.SetName("Synonyms")
        self._list.InsertColumn(0, "Synonym", width=160)
        self._list.InsertColumn(1, "Usage note", width=380)
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)

        # Status
        self._status_label = wx.StaticText(self.dialog, label="Enter a word and click Look Up.")
        root.Add(self._status_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Buttons
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._replace_btn = wx.Button(self.dialog, label="&Replace Word")
        self._copy_btn = wx.Button(self.dialog, label="&Copy Synonym")
        close_btn = wx.Button(self.dialog, wx.ID_CLOSE, label="C&lose")
        apply_modal_ids(
            self.dialog,
            affirmative_id=close_btn.GetId(),
            escape_id=close_btn.GetId(),
        )
        self._replace_btn.Enable(False)
        self._copy_btn.Enable(False)
        for b in (self._replace_btn, self._copy_btn, close_btn):
            btn_row.Add(b, 0, wx.RIGHT, 6)
        root.Add(btn_row, 0, wx.ALL, 8)

        self.dialog.SetSizer(root)
        self._bind_events(close_btn)
        wx.CallAfter(self._word_ctrl.SetFocus)

        # Auto-lookup if a word was pre-filled
        if initial_word.strip():
            wx.CallAfter(self._do_lookup)

    def _bind_events(self, close_btn: object) -> None:
        wx = self._wx
        self._word_ctrl.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._do_lookup())
        self._lookup_btn.Bind(wx.EVT_BUTTON, lambda _e: self._do_lookup())
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_item_activated)
        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_item_selected)
        self._replace_btn.Bind(wx.EVT_BUTTON, self._on_replace_clicked)
        self._copy_btn.Bind(wx.EVT_BUTTON, self._on_copy_clicked)
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(self._wx.ID_CLOSE))

    def _do_lookup(self) -> None:
        if self._working:
            return
        word = self._word_ctrl.GetValue().strip()
        if not word:
            self._status_label.SetLabel("Enter a word first.")
            return
        self._working = True
        self._lookup_btn.Enable(False)
        self._status_label.SetLabel("Looking up synonyms...")
        self._list.DeleteAllItems()
        self._replace_btn.Enable(False)
        self._copy_btn.Enable(False)

        import threading

        def _run() -> None:
            import wx as _wx

            try:
                entries = self._on_lookup(word, self._context_sentence)
                _wx.CallAfter(self._on_results, entries)
            except Exception as exc:  # noqa: BLE001
                _wx.CallAfter(self._on_error, str(exc))

        threading.Thread(target=_run, daemon=True).start()  # GATE-40-OK: AI bg thread

    def _on_results(self, entries: list) -> None:
        self._entries = entries
        self._list.DeleteAllItems()
        for i, entry in enumerate(entries):
            self._list.InsertItem(i, entry.synonym)
            self._list.SetItem(i, 1, entry.note)
        if entries:
            self._list.SetItemState(
                0,
                self._wx.LIST_STATE_SELECTED | self._wx.LIST_STATE_FOCUSED,
                self._wx.LIST_STATE_SELECTED | self._wx.LIST_STATE_FOCUSED,
            )
            self._replace_btn.Enable(self._on_replace is not None)
            self._copy_btn.Enable(True)
            self._status_label.SetLabel(f"{len(entries)} synonyms found.")
        else:
            self._status_label.SetLabel("No synonyms found.")
        self._working = False
        self._lookup_btn.Enable(True)

    def _on_error(self, message: str) -> None:
        self._status_label.SetLabel(f"Error: {message}")
        self._working = False
        self._lookup_btn.Enable(True)

    def _on_item_selected(self, event: object) -> None:
        self._replace_btn.Enable(bool(self._entries) and self._on_replace is not None)
        self._copy_btn.Enable(bool(self._entries))

    def _on_item_activated(self, event: object) -> None:
        # Double-click or Enter on an item replaces immediately
        self._replace_selected()

    def _selected_synonym(self) -> str:
        row = self._list.GetFirstSelected()
        if row < 0 or row >= len(self._entries):
            return ""
        return self._entries[row].synonym

    def _replace_selected(self) -> None:
        synonym = self._selected_synonym()
        if not synonym:
            return
        if self._on_replace:
            self._on_replace(synonym)
        self.dialog.EndModal(self._wx.ID_OK)

    def _on_replace_clicked(self, event: object) -> None:
        self._replace_selected()

    def _on_copy_clicked(self, event: object) -> None:
        wx = self._wx
        synonym = self._selected_synonym()
        if synonym and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(synonym))
            wx.TheClipboard.Close()
        self._status_label.SetLabel(f'Copied "{synonym}" to clipboard.')

    def show(self) -> None:
        self._show_modal(self.dialog)
        self.dialog.Destroy()
