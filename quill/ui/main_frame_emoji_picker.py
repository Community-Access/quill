"""Insert > Emoji... -- browse, search, and insert a standard Unicode emoji
with a rich spoken description of what it actually looks like
(docs/planning/emo.md, folded into the PRD's Accessible Emoji Picker section).

``EmojiPickerDialog`` is a plain custom dialog (every control named,
``show_modal_dialog`` + ``apply_modal_ids``, never raw ``ShowModal`` -- same
contract as ``local_git_dialogs.py``). ``EmojiPickerMixin`` is the thin
MainFrame-side command: check the catalog loaded, open the dialog, insert the
chosen character at the caret.

A visual emoji grid is exactly the pattern that is unusable for screen
readers, so this is a browse/search list, not a picture wall: a live-filtered
search box across every field the catalog carries (symbol, legacy emoticon,
name, keyword, and the rich description -- see quill.core.emoji_data.search),
a category list for open-ended browsing -- **Favorites** and **Recent**
(quill.core.emoji_usage's small per-user store) first, then Unicode's own
nine groupings -- a results list where arrowing through it reads like any
other accessible list (the glyph is spoken via its name in the row, not left
for the screen reader to guess at a bare character), and a description pane
that updates on every selection with the full picture: category, name,
keywords, legacy emoticon aliases, and the generated visual description.
Favorites and Recent never affect the underlying catalog -- un-favoriting or
clearing Recent only changes membership in those two lists; the emoji itself
stays exactly as findable by search or its Unicode category as before.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

_FAVORITES = "Favorites"
_RECENT = "Recent"


class EmojiPickerDialog:
    """Browse-or-search emoji picker. ``show()`` returns the chosen
    :class:`~quill.core.emoji_data.EmojiEntry`, or ``None`` on Cancel/Escape."""

    def __init__(
        self,
        parent: object,
        *,
        announce_cb: Callable[[str], None] | None = None,
    ) -> None:
        import wx

        from quill.core import emoji_data
        from quill.core.emoji_usage import EmojiUsage

        self._wx = wx
        self._emoji_data = emoji_data
        self._usage = EmojiUsage.load()
        self._announce = announce_cb or (lambda _m: None)
        self._categories = [_FAVORITES, _RECENT, *emoji_data.list_categories()]
        self._current_results: list[emoji_data.EmojiEntry] = []
        self._chosen: emoji_data.EmojiEntry | None = None

        self.dialog = wx.Dialog(
            parent,
            title="Insert Emoji",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((640, 480))
        self.dialog.SetSize((720, 560))
        panel = wx.Panel(self.dialog)
        root = wx.BoxSizer(wx.VERTICAL)

        search_row = wx.BoxSizer(wx.HORIZONTAL)
        search_row.Add(
            wx.StaticText(panel, label="&Search (name, keyword, or a typed smiley like :) ):"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._search_ctrl = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self._search_ctrl.SetName(
            "Search emoji by name, keyword, description, or a typed smiley like :) or <3; "
            "clear the search to browse by category instead"
        )
        search_row.Add(self._search_ctrl, 1, wx.EXPAND)
        root.Add(search_row, 0, wx.EXPAND | wx.ALL, 10)

        body = wx.BoxSizer(wx.HORIZONTAL)

        cat_col = wx.BoxSizer(wx.VERTICAL)
        cat_col.Add(wx.StaticText(panel, label="&Category"), 0, wx.BOTTOM, 4)
        self._category_list = wx.ListBox(panel, choices=self._categories)
        self._category_list.SetName("Emoji category; choose one to browse its emoji")
        if self._categories:
            self._category_list.SetSelection(0)
        cat_col.Add(self._category_list, 1, wx.EXPAND)
        body.Add(cat_col, 1, wx.EXPAND | wx.RIGHT, 10)

        results_col = wx.BoxSizer(wx.VERTICAL)
        results_col.Add(wx.StaticText(panel, label="&Emoji"), 0, wx.BOTTOM, 4)
        self._results = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._results.SetName("Emoji results; arrow through to hear the description of each")
        self._results.InsertColumn(0, "Symbol", width=70)
        self._results.InsertColumn(1, "Name", width=260)
        results_col.Add(self._results, 1, wx.EXPAND)
        body.Add(results_col, 2, wx.EXPAND)

        root.Add(body, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        root.Add(wx.StaticText(panel, label="Description"), 0, wx.LEFT | wx.TOP, 10)
        self._description = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP,
        )
        self._description.SetName("Description of the selected emoji")
        root.Add(self._description, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self._status = wx.StaticText(panel, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._favorite_btn = wx.Button(panel, label="Add to &Favorites")
        self._favorite_btn.SetName("Add or remove the selected emoji from Favorites")
        self._favorite_btn.Enable(False)
        self._insert_btn = wx.Button(panel, wx.ID_OK, "&Insert")
        self._insert_btn.SetName("Insert the selected emoji")
        self._insert_btn.Enable(False)
        cancel_btn = wx.Button(panel, wx.ID_CANCEL, "Cancel")
        cancel_btn.SetName("Cancel")
        btn_row.Add(self._favorite_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(self._insert_btn, 0, wx.RIGHT, 6)
        btn_row.Add(cancel_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.dialog.SetSizer(outer)

        self._search_ctrl.Bind(wx.EVT_TEXT, self._on_search_text)
        self._search_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_search_enter)
        self._category_list.Bind(wx.EVT_LISTBOX, self._on_category_selected)
        self._results.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_result_selected)
        self._results.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_activate)
        self._insert_btn.Bind(wx.EVT_BUTTON, self._on_insert)
        self._favorite_btn.Bind(wx.EVT_BUTTON, self._on_toggle_favorite)

        if not emoji_data.is_available():
            self._status.SetLabel(
                "The emoji catalog could not be loaded; browsing and search are unavailable."
            )
        elif self._categories:
            self._show_category(self._categories[0])

    # ------------------------------------------------------------------
    # Public entry point

    def show(self) -> object:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=wx.ID_OK,
            affirmative_label="Insert",
            cancel_id=wx.ID_CANCEL,
            escape_id=wx.ID_CANCEL,
        )
        try:
            answer = show_modal_dialog(self.dialog, "Insert Emoji")
            if answer == wx.ID_OK and self._chosen is not None:
                return self._chosen
            return None
        finally:
            self.dialog.Destroy()

    # ------------------------------------------------------------------
    # Results list population

    def _fill_results(self, entries: list, *, status: str) -> None:
        self._current_results = entries
        self._results.DeleteAllItems()
        for row, entry in enumerate(entries):
            self._results.InsertItem(row, entry.char)
            self._results.SetItem(row, 1, entry.name)
        self._status.SetLabel(status)
        self._insert_btn.Enable(False)
        self._favorite_btn.Enable(False)
        self._description.SetValue("")
        if entries:
            self._results.Select(0)
            self._results.Focus(0)

    def _show_category(self, category: str) -> None:
        if category == _FAVORITES:
            entries = self._emoji_data.entries_by_chars(self._usage.favorites)
            status = (
                f"{len(entries)} favorite emoji."
                if entries
                else "No favorites yet. Select an emoji and press Add to Favorites."
            )
            self._fill_results(entries, status=status)
            return
        if category == _RECENT:
            entries = self._emoji_data.entries_by_chars(self._usage.recent)
            status = (
                f"{len(entries)} recently used emoji."
                if entries
                else "No recently used emoji yet. Insert one and it will appear here."
            )
            self._fill_results(entries, status=status)
            return
        entries = self._emoji_data.list_by_category(category)
        self._fill_results(entries, status=f"{len(entries)} emoji in {category}.")

    def _show_search(self, query: str) -> None:
        entries = self._emoji_data.search(query)
        count = len(entries)
        noun = "result" if count == 1 else "results"
        self._fill_results(entries, status=f"{count} search {noun} for “{query}”.")

    # ------------------------------------------------------------------
    # Events

    def _on_search_text(self, _event: object) -> None:
        query = self._search_ctrl.GetValue().strip()
        if query:
            self._show_search(query)
        elif self._categories:
            selected = self._category_list.GetSelection()
            index = selected if selected != self._wx.NOT_FOUND else 0
            self._show_category(self._categories[index])

    def _on_search_enter(self, _event: object) -> None:
        if self._current_results:
            self._results.SetFocus()

    def _on_category_selected(self, _event: object) -> None:
        if self._search_ctrl.GetValue().strip():
            return  # a live search result stays in charge until cleared
        selection = self._category_list.GetSelection()
        if selection != self._wx.NOT_FOUND:
            self._show_category(self._categories[selection])

    def _on_result_selected(self, event: object) -> None:
        index = event.GetIndex()
        if 0 <= index < len(self._current_results):
            entry = self._current_results[index]
            described = self._emoji_data.describe(entry)
            self._description.SetValue(described.detail)
            self._insert_btn.Enable(True)
            self._favorite_btn.Enable(True)
            self._update_favorite_button_label(entry.char)

    def _update_favorite_button_label(self, char: str) -> None:
        if self._usage.is_favorite(char):
            self._favorite_btn.SetLabel("Remove from &Favorites")
        else:
            self._favorite_btn.SetLabel("Add to &Favorites")

    def _on_toggle_favorite(self, _event: object) -> None:
        index = self._results.GetFirstSelected()
        if not (0 <= index < len(self._current_results)):
            return
        entry = self._current_results[index]
        now_favorite = self._usage.toggle_favorite(entry.char)
        self._announce(
            f"Added {entry.name} to Favorites"
            if now_favorite
            else f"Removed {entry.name} from Favorites"
        )
        self._update_favorite_button_label(entry.char)
        # Un-favoriting while browsing the Favorites category removes the row
        # from view immediately, matching what just happened; every other
        # view just reflects the updated button label.
        if not self._search_ctrl.GetValue().strip():
            selection = self._category_list.GetSelection()
            if selection != self._wx.NOT_FOUND and self._categories[selection] == _FAVORITES:
                self._show_category(_FAVORITES)

    def _on_activate(self, _event: object) -> None:
        self._commit_selection()

    def _on_insert(self, _event: object) -> None:
        self._commit_selection()

    def _commit_selection(self) -> None:
        index = self._results.GetFirstSelected()
        if 0 <= index < len(self._current_results):
            self._chosen = self._current_results[index]
            self._usage.record_used(self._chosen.char)
            self.dialog.EndModal(self._wx.ID_OK)


class EmojiPickerMixin:
    """Adds Insert > Emoji... to ``MainFrame``."""

    def insert_emoji(self) -> None:
        from quill.core import emoji_data

        if not emoji_data.is_available():
            self._show_message_box(
                "The emoji catalog could not be loaded, so Insert Emoji is unavailable. "
                "This does not affect typing emoji directly with your system's own "
                "emoji input (Windows key + period).",
                "Insert Emoji",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            return
        chosen = EmojiPickerDialog(self.frame, announce_cb=self._announce).show()
        if chosen is None:
            return
        self.editor.WriteText(chosen.char)
        self._announce(f"Inserted {chosen.name}")

    # ------------------------------------------------------------------
    # Command palette registration

    def _register_emoji_picker_commands(self) -> None:
        self.commands.try_register(
            "edit.insert_emoji",
            "Insert Emoji...",
            self.insert_emoji,
            self._binding_for("edit.insert_emoji"),
        )
