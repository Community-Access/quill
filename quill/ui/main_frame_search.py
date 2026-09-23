"""Find, replace, and search-in-files for MainFrame (CQ-1 decomposition).

``SearchCommandsMixin`` owns the search surface: the accessible find/replace
prompt and the native wx.FindReplaceDialog wiring, find next/previous with
wrap handling, find-all-matches, replace one/all, and the multi-file
search/replace flow (``_prompt_file_search`` / ``search_in_files`` /
``replace_in_files`` with its ``_FileSearchRequest`` model and background
worker). Extracted verbatim from ``main_frame.py``; runs on ``MainFrame``
(``self``).

The **dialog** the last two open moved to
:mod:`quill.ui.main_frame_file_search_prompt` on 2026-09-10 (GATE-11). It was a
hundred and fifty lines of form building in a file of one-screen command
handlers, and it is the only thing here that is a window rather than a search.
``SearchCommandsMixin`` inherits it, so every caller and every composed frame is
unchanged.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.search import SearchOptions, SearchPatternError, find_matches, replace_all
from quill.core.search_history import add_search_term
from quill.ui.main_frame_file_search_prompt import (
    FileSearchPromptMixin,
)
from quill.ui.main_frame_file_search_prompt import (
    FileSearchRequest as _FileSearchRequest,
)


class SearchCommandsMixin(FileSearchPromptMixin):
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
        if getattr(self.settings, "find_use_quill_dialog", False):
            self._open_quill_find_dialog(replace)
            return
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

    def _open_quill_find_dialog(self, replace: bool) -> None:
        """Open (or refocus) QUILL's own Find dialog (#1327 F1, opt-in setting).

        The host wiring lives with the dialog (find_dialog.open_for_main_frame)
        so this mixin stays a thin dispatcher.
        """
        from quill.ui.find_dialog import open_for_main_frame

        open_for_main_frame(self, replace=replace)

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
            self._report_search_missed("No matches found")
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
            # Wrapping is off and the search has run out of document in the
            # direction it was going. Not the same fact as "there is no such text":
            # the fix is to go to the other end, not to change the pattern, so the
            # sentence names the end it stopped at.
            edge = "start" if reverse else "end"
            self._report_search_missed(
                f"No more matches. Reached the {edge} of the document, and wrapping is off."
            )
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
        # A match ends the run of misses: the next one is a fresh question and
        # gets a spoken answer rather than another tone.
        self._last_search_miss = None
        self._set_status(f"Found {direction} at position {start + 1}{wrap_suffix}")
        from quill.core.sound_events import SoundEvent
        from quill.ui.sound_manager import post_sound

        post_sound(SoundEvent.SEARCH_WRAPPED if wrapped else SoundEvent.SEARCH_FOUND)

    def _report_search_missed(self, message: str) -> None:
        """A search found nothing, reported in the channel the user chose.

        ``settings.find_not_found_feedback`` -- sound (the default), speech, both
        or neither -- resolved through the shared rule in
        :mod:`quill.core.action_feedback` so QuillLite cannot answer this
        differently.

        The **first** miss speaks whatever the mode says, and a repeat of the
        same miss does not: see
        :func:`~quill.core.action_feedback.resolve_failure` for why those are
        two different presses. A miss counts as a repeat only while the wording
        is unchanged, so changing what you are looking for gets you an answer
        again rather than another unexplained tone.

        The status bar is set either way: ``_set_status`` speaks what it is given,
        so the quiet path uses ``_set_status_quiet`` and the bar still carries the
        record for anyone who goes and reads it.
        """
        from quill.core.action_feedback import resolve_failure
        from quill.core.sound_events import SoundEvent
        from quill.ui.sound_manager import has_sound_for, post_sound

        repeated = getattr(self, "_last_search_miss", None) == message
        self._last_search_miss = message
        try:
            play, speak = resolve_failure(
                getattr(self.settings, "find_not_found_feedback", "sound"),
                has_sound=has_sound_for(SoundEvent.SEARCH_NOT_FOUND),
                repeated=repeated,
            )
        except Exception:  # noqa: BLE001 - feedback must never break a search
            play, speak = True, False
        if play:
            post_sound(SoundEvent.SEARCH_NOT_FOUND)
        if speak:
            self._set_status(message)
        else:
            self._set_status_quiet(message)

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
