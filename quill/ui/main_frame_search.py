"""Find, replace, and search-in-files for MainFrame (CQ-1 decomposition).

``SearchCommandsMixin`` owns the search surface: the accessible find/replace
prompt and the native wx.FindReplaceDialog wiring, find next/previous with
wrap handling, find-all-matches, replace one/all, and the multi-file
search/replace flow (``_prompt_file_search`` / ``search_in_files`` /
``replace_in_files`` with its ``_FileSearchRequest`` model and background
worker). Extracted verbatim from ``main_frame.py``; runs on ``MainFrame``
(``self``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from quill.core.search import SearchOptions, SearchPatternError, find_matches, replace_all
from quill.core.search_history import add_search_term
from quill.ui.dialog_contract import (
    apply_modal_ids,
)


@dataclass(slots=True)
class _FileSearchRequest:
    root: Path
    pattern: str
    query: str
    replacement: str | None
    options: SearchOptions
    output_mode: str
    preview_before_replace: bool


class SearchCommandsMixin:
    def _prompt_search(
        self, title: str, replacement: bool = False
    ) -> tuple[str, str | None, SearchOptions] | None:
        from quill.ui.web_form import show_web_form

        default_query = self._last_find_query or (
            self._search_history[0] if self._search_history else ""
        )
        mode_labels = ["Plain text", "Whole word", "Regular expression", "Wildcard"]
        fields = [
            {
                "name": "query",
                "label": "Find text",
                "type": "text",
                "value": default_query,
            },
        ]
        if replacement:
            fields.append({
                "name": "replacement",
                "label": "Replace with",
                "type": "text",
                "value": "",
            })
        fields.extend([
            {
                "name": "mode",
                "label": "Search mode",
                "type": "select",
                "value": "Plain text",
                "options": [(label, label) for label in mode_labels],
            },
            {
                "name": "case_sensitive",
                "label": "Case sensitive",
                "type": "checkbox",
                "value": False,
            },
        ])
        values = show_web_form(
            self.frame,
            self._wx,
            title=title,
            fields=fields,
        )
        if values is None:
            return None
        query = str(values.get("query", "")).strip()
        if not query:
            return None
        mode = str(values.get("mode", "Plain text"))
        options = SearchOptions(
            case_sensitive=bool(values.get("case_sensitive", False)),
            whole_word=mode == "Whole word",
            use_regex=mode == "Regular expression",
            wildcard=mode == "Wildcard",
        )
        replacement_value = str(values.get("replacement", "")) if replacement else None
        return query, replacement_value, options

    def find_text(self) -> None:
        self._open_find_replace(replace=False)

    def _open_find_replace(self, replace: bool) -> None:
        """Open the native (modeless) wx.FindReplaceDialog for Find / Replace.

        Native dialog = reliable buttons, read directly by VoiceOver/NVDA, and
        the standard Find Next / Replace / Replace All flow. It carries
        case-sensitive + whole-word + direction; regex and wildcard searches
        stay available via Find All Matches / Search in Files.
        """
        wx = self._wx
        existing = getattr(self, "_find_replace_dialog", None)
        if existing is not None:
            # Recreate so toggling Find<->Replace works and it returns to front.
            existing.Destroy()
            self._find_replace_dialog = None
        flags = wx.FR_DOWN
        options = getattr(self, "_last_search_options", None)
        if options is not None:
            if getattr(options, "case_sensitive", False):
                flags |= wx.FR_MATCHCASE
            if getattr(options, "whole_word", False):
                flags |= wx.FR_WHOLEWORD
        data = wx.FindReplaceData(flags)
        seed = getattr(self, "_last_find_query", "") or (
            self._search_history[0] if self._search_history else ""
        )
        if seed:
            data.SetFindString(seed)
        self._find_replace_data = data  # keep a reference alive for the dialog
        style = wx.FR_REPLACEDIALOG if replace else 0
        dialog = wx.FindReplaceDialog(self.frame, data, "Replace" if replace else "Find", style)
        dialog.Bind(wx.EVT_FIND, self._on_find_event)
        dialog.Bind(wx.EVT_FIND_NEXT, self._on_find_event)
        dialog.Bind(wx.EVT_FIND_REPLACE, self._on_find_replace_event)
        dialog.Bind(wx.EVT_FIND_REPLACE_ALL, self._on_find_replace_all_event)
        dialog.Bind(wx.EVT_FIND_CLOSE, self._on_find_close_event)
        self._find_replace_dialog = dialog
        dialog.Show(True)
        dialog.Raise()

    def _search_options_from_flags(self, flags: int) -> SearchOptions:
        wx = self._wx
        return SearchOptions(
            case_sensitive=bool(flags & wx.FR_MATCHCASE),
            whole_word=bool(flags & wx.FR_WHOLEWORD),
            use_regex=False,
            wildcard=False,
        )

    def _on_find_event(self, event: object) -> None:
        query = event.GetFindString()
        if not query:
            return
        self._last_find_query = query
        self._last_search_options = self._search_options_from_flags(event.GetFlags())
        self._search_history = add_search_term(query)
        reverse = not bool(event.GetFlags() & self._wx.FR_DOWN)
        self._find_relative(reverse=reverse)

    def _on_find_replace_event(self, event: object) -> None:
        query = event.GetFindString()
        if not query:
            return
        options = self._search_options_from_flags(event.GetFlags())
        self._last_find_query = query
        self._last_search_options = options
        self._replace_current_match(query, event.GetReplaceString(), options)

    def _on_find_replace_all_event(self, event: object) -> None:
        wx = self._wx
        query = event.GetFindString()
        if not query:
            return
        options = self._search_options_from_flags(event.GetFlags())
        self._last_find_query = query
        self._last_search_options = options
        text = self.editor.GetValue()
        try:
            updated_text, replacements = replace_all(text, query, event.GetReplaceString(), options)
        except SearchPatternError as error:
            self._show_message_box(str(error), "Replace All", wx.ICON_ERROR | wx.OK)
            return
        if replacements == 0:
            self._set_status("No replacements made")
            return
        self._replace_document_text(updated_text)
        self.document.set_text(updated_text)
        self._set_status(f"Replaced {replacements} occurrence(s)")

    def _on_find_close_event(self, _event: object) -> None:
        dialog = getattr(self, "_find_replace_dialog", None)
        if dialog is not None:
            dialog.Destroy()
        self._find_replace_dialog = None
        self._find_replace_data = None

    def _replace_current_match(self, query: str, replacement: str, options: SearchOptions) -> None:
        wx = self._wx
        text = self.editor.GetValue()
        try:
            matches = find_matches(text, query, options)
        except SearchPatternError as error:
            self._show_message_box(str(error), "Replace", wx.ICON_ERROR | wx.OK)
            return
        if not matches:
            self._set_status("No replacements made")
            return
        sel_start, sel_end = self.editor.GetSelection()
        chosen: tuple[int, int] | None = None
        wrapped = False
        if sel_start != sel_end and (sel_start, sel_end) in matches:
            chosen = (sel_start, sel_end)
        else:
            cursor = sel_end if sel_start != sel_end else self.editor.GetInsertionPoint()
            for start, end in matches:
                if start >= cursor:
                    chosen = (start, end)
                    break
            if chosen is None and self.settings.wrap_find:
                chosen = matches[0]
                wrapped = True
        if chosen is None:
            self._set_status("No replacements made from the current position")
            return
        start, end = chosen
        updated_text = text[:start] + replacement + text[end:]
        self._replace_document_text(updated_text)
        self.document.set_text(updated_text)
        replaced_end = start + len(replacement)
        self.editor.SetSelection(start, replaced_end)
        self.editor.SetInsertionPoint(replaced_end)
        self._last_match = (start, replaced_end)
        wrap_suffix = (
            " (wrapped)" if wrapped and getattr(self.settings, "announce_wrap", True) else ""
        )
        self._set_status(f"Replaced at position {start + 1}{wrap_suffix}")

    def find_next(self) -> None:
        self._find_relative(reverse=False)

    def find_previous(self) -> None:
        self._find_relative(reverse=True)

    def _find_relative(self, reverse: bool) -> None:
        if not self._last_find_query:
            self.find_text()
            return

        text = self.editor.GetValue()
        try:
            matches = find_matches(text, self._last_find_query, self._last_search_options)
        except SearchPatternError as error:
            self._show_message_box(str(error), "Find", self._wx.ICON_ERROR | self._wx.OK)
            self._set_status("Find error")
            return
        if not matches:
            self._set_status("No matches found")
            from quill.core.sound_events import SoundEvent
            from quill.ui.sound_manager import post_sound

            post_sound(SoundEvent.SEARCH_NOT_FOUND)
            return

        cursor = self.editor.GetInsertionPoint()
        selected_start, selected_end = self.editor.GetSelection()
        if selected_start != selected_end:
            cursor = selected_start if reverse else selected_end

        chosen: tuple[int, int] | None = None
        wrapped = False
        if reverse:
            for start, end in reversed(matches):
                if end <= cursor:
                    chosen = (start, end)
                    break
            if chosen is None and self.settings.wrap_find:
                chosen = matches[-1]
                wrapped = True
        else:
            for start, end in matches:
                if start >= cursor:
                    chosen = (start, end)
                    break
            if chosen is None and self.settings.wrap_find:
                chosen = matches[0]
                wrapped = True

        if chosen is None:
            self._set_status("No matches found from the current position")
            from quill.core.sound_events import SoundEvent
            from quill.ui.sound_manager import post_sound

            post_sound(SoundEvent.SEARCH_NOT_FOUND)
            return

        start, end = chosen
        self.editor.SetFocus()
        self._ensure_extend_selection_anchor()
        if self._extend_selection_mode and self._extend_selection_anchor is not None:
            self._move_point(start if reverse else end)
        else:
            self.editor.SetSelection(start, end)
            self.editor.SetInsertionPoint(end)
        self._last_match = chosen
        direction = "previous" if reverse else "next"
        wrap_suffix = (
            " (wrapped)" if wrapped and getattr(self.settings, "announce_wrap", True) else ""
        )
        self._set_status(f"Found {direction} at position {start + 1}{wrap_suffix}")
        from quill.core.sound_events import SoundEvent
        from quill.ui.sound_manager import post_sound

        post_sound(SoundEvent.SEARCH_WRAPPED if wrapped else SoundEvent.SEARCH_FOUND)

    def _ensure_extend_selection_anchor(self) -> None:
        if not self._extend_selection_mode or self._extend_selection_anchor is not None:
            return
        selection_start, selection_end = self.editor.GetSelection()
        if selection_start != selection_end:
            self._extend_selection_anchor = selection_start
            return
        self._extend_selection_anchor = self.editor.GetInsertionPoint()

    def find_all_matches(self) -> None:
        wx = self._wx
        if not self._last_find_query:
            # Rich modal prompt here keeps regex / wildcard search available
            # (the native Find dialog only does case / whole-word / direction).
            prompt = self._prompt_search("Find All Matches")
            if prompt is None:
                return
            query, _replacement, options = prompt
            if not query:
                return
            self._last_find_query = query
            self._last_search_options = options
            self._search_history = add_search_term(query)

        text = self.editor.GetValue()
        try:
            matches = find_matches(text, self._last_find_query, self._last_search_options)
        except SearchPatternError as error:
            self._show_message_box(str(error), "Find All Matches", wx.ICON_ERROR | wx.OK)
            self._set_status("Find error")
            return
        if not matches:
            self._show_message_box(
                "No matches found.",
                "Find All Matches",
                wx.ICON_INFORMATION | wx.OK,
            )
            self._set_status("No matches found")
            return

        lines = text.splitlines(keepends=True)
        starts = [0]
        for line in lines:
            starts.append(starts[-1] + len(line))

        def locate(position: int) -> tuple[int, int]:
            line_number = 1
            for index in range(1, len(starts)):
                if starts[index] > position:
                    line_number = index
                    break
            else:
                line_number = max(1, len(starts) - 1)
            column = position - starts[line_number - 1] + 1
            return line_number, column

        details: list[str] = []
        for idx, (start, _end) in enumerate(matches[:25], start=1):
            line_number, column = locate(start)
            details.append(f"{idx}. Line {line_number}, Column {column}")
        more = ""
        if len(matches) > 25:
            more = f"\n...and {len(matches) - 25} more"

        self._show_message_box(
            f'Matches for "{self._last_find_query}": {len(matches)}\n\n'
            + "\n".join(details)
            + more,
            "Find All Matches",
            wx.ICON_INFORMATION | wx.OK,
        )
        self._set_status(f"Found {len(matches)} match(es)")

    def replace_text(self) -> None:
        self._open_find_replace(replace=True)

    def replace_all_text(self) -> None:
        # The native Replace dialog has its own Replace All button.
        self._open_find_replace(replace=True)

    def _prompt_file_search(self, *, replace: bool) -> _FileSearchRequest | None:
        wx = self._wx
        default_root = self.document.path.parent if self.document.path is not None else Path.cwd()
        dialog_label = "Replace Across Files" if replace else "Search in Files"
        dialog = wx.Dialog(
            self.frame,
            title=dialog_label,
            size=(700, 0),
        )
        root = wx.BoxSizer(wx.VERTICAL)
        form = wx.FlexGridSizer(0, 3, 8, 8)
        form.AddGrowableCol(1, 1)

        def add_row(label: str, make_ctrl, button: object | None = None) -> object:
            form.Add(wx.StaticText(dialog, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = make_ctrl()
            form.Add(ctrl, 1, wx.EXPAND)
            if button is None:
                form.AddSpacer(1)
            else:
                form.Add(button, 0)
            return ctrl

        folder_picker = add_row(
            "Starting folder", lambda: wx.DirPickerCtrl(dialog, path=str(default_root))
        )
        file_pattern_ctrl = add_row("File pattern", lambda: wx.TextCtrl(dialog, value="*"))
        query_ctrl = add_row(
            "Search text", lambda: wx.TextCtrl(dialog, value="", style=wx.TE_PROCESS_ENTER)
        )

        replacement_ctrl = None
        if replace:
            replacement_ctrl = add_row(
                "Replacement",
                lambda: wx.TextCtrl(dialog, value="", style=wx.TE_PROCESS_ENTER),
            )

        mode_choice = add_row(
            "Match mode",
            lambda: wx.Choice(dialog, choices=["Plain text", "Wildcard", "Regular expression"]),
        )
        mode_choice.SetSelection(0)

        output_choice = add_row(
            "Output format",
            lambda: wx.Choice(
                dialog,
                choices=[
                    "Filenames only",
                    "Filenames with line numbers and counts",
                    "Counts only",
                    "Filename with line context",
                ],
            ),
        )
        output_choice.SetSelection(3)

        case_sensitive = wx.CheckBox(dialog, label="Case sensitive")
        whole_word = wx.CheckBox(dialog, label="Whole word")
        root.Add(form, 0, wx.ALL | wx.EXPAND, 8)
        root.Add(case_sensitive, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        root.Add(whole_word, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        preview_before_replace = None
        if replace:
            preview_before_replace = wx.CheckBox(dialog, label="Preview before replacing")
            preview_before_replace.SetValue(True)
            root.Add(preview_before_replace, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            # Mirror the proven single-document search dialog (_prompt_search):
            # a StdDialogButtonSizer must be added with wx.EXPAND, not
            # wx.ALIGN_RIGHT. Adding it right-aligned left the OK/Cancel buttons
            # unrealized on Windows, so the Cancel button could not be clicked
            # and the dialog trapped the user (#84). EXPAND plus an explicit
            # default button restores reliable, keyboard-accessible dismissal.
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetDefault()
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.SetSizerAndFit(root)

        def submit(_event: object) -> None:
            dialog.EndModal(wx.ID_OK)

        query_ctrl.Bind(wx.EVT_TEXT_ENTER, submit)
        if replacement_ctrl is not None:
            replacement_ctrl.Bind(wx.EVT_TEXT_ENTER, submit)

        def focus_query() -> None:
            query_ctrl.SetFocus()

        if hasattr(wx, "CallAfter"):
            wx.CallAfter(focus_query)
        else:
            focus_query()

        try:
            if self._show_modal_dialog(dialog, dialog_label) != wx.ID_OK:
                return None
            query = query_ctrl.GetValue().strip()
            if not query:
                self._show_message_box(
                    "Search text cannot be blank.",
                    dialog_label,
                    wx.ICON_ERROR | wx.OK,
                )
                return None
            mode = mode_choice.GetStringSelection()
            options = SearchOptions(
                case_sensitive=bool(case_sensitive.GetValue()),
                whole_word=bool(whole_word.GetValue()),
                use_regex=mode == "Regular expression",
                wildcard=mode == "Wildcard",
            )
            replacement_value = (
                replacement_ctrl.GetValue() if replacement_ctrl is not None else None
            )
            preview = (
                bool(preview_before_replace.GetValue())
                if preview_before_replace is not None
                else False
            )
            output_modes = (
                "filenames",
                "filenames_lines_counts",
                "counts",
                "context",
            )
            return _FileSearchRequest(
                root=Path(folder_picker.GetPath()),
                pattern=file_pattern_ctrl.GetValue().strip() or "*",
                query=query,
                replacement=replacement_value,
                options=options,
                output_mode=output_modes[
                    max(0, min(output_choice.GetSelection(), len(output_modes) - 1))
                ],
                preview_before_replace=preview,
            )
        finally:
            dialog.Destroy()

    def search_in_files(self) -> None:
        from quill.core.file_search import FileSearchReport, render_search_report, search_files

        request = self._prompt_file_search(replace=False)
        if request is None:
            self._set_status("Search in files cancelled")
            return

        def work(progress: Callable[[str, int, int], None]) -> FileSearchReport:
            return search_files(
                request.root,
                request.pattern,
                request.query,
                request.options,
                progress=progress,
            )

        def on_success(result: object) -> None:
            report = result if isinstance(result, FileSearchReport) else None
            if report is None:
                return
            text = render_search_report(report, request.output_mode)
            self._open_generated_tab(f"Search - {request.pattern}", text)
            match_count = report.total_matches
            file_count = len(report.entries)
            self._set_status(f"Search complete: {match_count} match(es) in {file_count} file(s)")

        self._run_background_task("Searching files", work, on_success)

    def replace_in_files(self) -> None:
        from quill.core.file_search import FileSearchReport, render_replace_preview, search_files

        request = self._prompt_file_search(replace=True)
        if request is None:
            self._set_status("Replace across files cancelled")
            return
        replacement = request.replacement or ""

        if not request.preview_before_replace:
            self._start_replace_files(request, replacement)
            return

        def preview_work(progress: Callable[[str, int, int], None]) -> FileSearchReport:
            return search_files(
                request.root,
                request.pattern,
                request.query,
                request.options,
                progress=progress,
            )

        def preview_done(result: object) -> None:
            report = result if isinstance(result, FileSearchReport) else None
            if report is None:
                return
            text = render_replace_preview(report, replacement)
            self._open_generated_tab(f"Replace Preview - {request.pattern}", text)
            if report.total_matches == 0:
                self._set_status("No matches found")
                return
            confirm = self._show_message_box(
                "Apply these replacements across files?",
                "Replace Across Files",
                self._wx.ICON_QUESTION | self._wx.YES_NO | self._wx.NO_DEFAULT,
            )
            if confirm == self._wx.YES:
                self._start_replace_files(request, replacement)
                return
            self._set_status("Replace across files cancelled")

        self._run_background_task("Previewing file replacements", preview_work, preview_done)

    def _start_replace_files(self, request: _FileSearchRequest, replacement: str) -> None:
        from quill.core.file_search import FileReplaceReport, render_replace_report, replace_files

        def work(progress: Callable[[str, int, int], None]) -> FileReplaceReport:
            return replace_files(
                request.root,
                request.pattern,
                request.query,
                replacement,
                request.options,
                progress=progress,
            )

        def on_success(result: object) -> None:
            report = result if isinstance(result, FileReplaceReport) else None
            if report is None:
                return
            text = render_replace_report(report)
            self._open_generated_tab(f"Replace Results - {request.pattern}", text)
            replacement_count = report.total_replacements
            file_count = len(report.entries)
            self._set_status(f"Replaced {replacement_count} occurrence(s) in {file_count} file(s)")

        self._run_background_task("Replacing files", work, on_success)
