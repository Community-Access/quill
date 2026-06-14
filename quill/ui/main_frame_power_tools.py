"""Editor power-tool conveniences, mixed into :class:`MainFrame` (EDS-1..20).

This module gathers the editor power-tool commands behind one mixin
so they do not bloat ``main_frame.py`` (the same structural pattern used by
``BrowseModeMixin`` for CQ-1). Every method resolves through ``MainFrame`` and
relies on its helpers: ``self.editor``, ``self.document``, ``self.settings``,
``self._wx``, ``self.frame``, ``self._set_status``, ``self._announce``,
``self._replace_document_text``, ``self._move_point``, ``self._show_message_box``,
``self._create_document_tab`` and the ``_apply_*`` mutation helpers.

The wx-free logic lives in dedicated ``quill/core`` modules (unicode_insert,
datetime_insert, wrap_ops, set_ops, regex_ops, cursor_address, indent_infer,
clipboard_collector, key_describer, run_target) and ``quill/core/line_ops``; this
layer only wires those into the editor, dialogs, and announcements.
"""

from __future__ import annotations

import os
import webbrowser
from datetime import datetime
from pathlib import Path

from quill.core import format_ops as _fmt
from quill.core.clipboard_collector import append_collected
from quill.core.cursor_address import (
    describe_cursor_address,
    describe_document_status,
    describe_selection_length,
    offset_for_percent,
)
from quill.core.datetime_insert import (
    DEFAULT_DATETIME_FORMAT,
    calculate_date,
    format_datetime,
    parse_weekday,
)
from quill.core.document import Document
from quill.core.html_to_markdown import extract_cf_html_fragment, html_to_markdown
from quill.core.indent_infer import (
    describe_indent_change,
    describe_indent_unit,
    indent_columns,
    infer_indent_unit,
)
from quill.core.key_describer import command_for_accelerator
from quill.core.line_ops import (
    delete_paragraph,
    delete_to_document_end,
    delete_to_document_start,
    delete_to_line_end,
    delete_to_line_start,
    first_non_blank_position,
    last_non_blank_position,
)
from quill.core.paths import app_data_dir
from quill.core.regex_ops import RegexError, count_matches, extract_matches
from quill.core.run_target import classify_target, is_dangerous_executable, target_at_cursor
from quill.core.set_ops import format_lines, lines_common_to_both, lines_in_first_not_second
from quill.core.storage import read_json, write_json_atomic
from quill.core.unicode_insert import CodepointError, parse_codepoint

_DATE_INSERT_FORMAT = "%Y-%m-%d"


class PowerToolsActionsMixin:
    """Editor power-tool conveniences mixed into :class:`MainFrame`."""

    # ------------------------------------------------------------------ shared
    def _power_tools_text_cursor(self) -> tuple[str, int]:
        return self.editor.GetValue(), self.editor.GetInsertionPoint()

    def _power_tools_insert_at_cursor(self, snippet: str, status: str) -> None:
        if self._document_is_read_only():
            self._set_status("Document is read-only")
            return
        text, pos = self._power_tools_text_cursor()
        updated = text[:pos] + snippet + text[pos:]
        self._replace_document_text(updated)
        self.document.set_text(updated)
        new_pos = pos + len(snippet)
        self.editor.SetInsertionPoint(new_pos)
        self.editor.SetSelection(new_pos, new_pos)
        self._set_status(status)

    def _power_tools_transform_selection_or_document(self, transform, status: str) -> None:
        if self._document_is_read_only():
            self._set_status("Document is read-only")
            return
        text = self.editor.GetValue()
        start, end = self.editor.GetSelection()
        if start == end:
            start, end = 0, len(text)
        block = transform(text[start:end])
        updated = text[:start] + block + text[end:]
        self._replace_document_text(updated)
        self.document.set_text(updated)
        self.editor.SetSelection(start, start + len(block))
        self._set_status(status)

    def _power_tools_open_text_in_new_buffer(self, text: str, status: str) -> None:
        self._clear_empty_workspace_state()
        self._create_document_tab(Document(text=text), select=True)
        self._set_status(status)

    def _power_tools_prompt_single(self, title: str, label: str, value: str = "") -> str | None:
        # A single text field must be a native dialog, not a WebView form: a
        # WebView forces the screen reader into virtual-cursor mode for a trivial
        # prompt such as Number Lines ("Start numbering at:"). wx.TextEntryDialog
        # is a plain, focus-managed control with no virtual cursor.
        wx = self._wx
        with wx.TextEntryDialog(self.frame, label, title, value) as dialog:
            if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                return None
            return str(dialog.GetValue())

    def _power_tools_clipboard_text(self) -> str:
        wx = self._wx
        clipboard = getattr(wx, "TheClipboard", None)
        if clipboard is None or not clipboard.Open():
            return ""
        try:
            data = wx.TextDataObject()
            if clipboard.GetData(data):
                return str(data.GetText())
            return ""
        finally:
            clipboard.Close()

    def _power_tools_clipboard_html(self) -> str:
        """Return the clipboard's HTML payload, if any.

        Prefers the Windows ``HTML Format`` (CF_HTML) clipboard flavour and
        unwraps its fragment; returns an empty string when no HTML is present so
        callers can fall back to plain text.
        """
        wx = self._wx
        clipboard = getattr(wx, "TheClipboard", None)
        if clipboard is None or not clipboard.Open():
            return ""
        try:
            data_format = wx.DataFormat("HTML Format")
            if not clipboard.IsSupported(data_format):
                return ""
            data = wx.CustomDataObject(data_format)
            if not clipboard.GetData(data):
                return ""
            raw = data.GetData()
            try:
                payload = bytes(raw).decode("utf-8", errors="replace")
            except (TypeError, ValueError):
                payload = str(raw)
            return extract_cf_html_fragment(payload)
        except Exception:
            return ""
        finally:
            clipboard.Close()

    # ------------------------------------------- HTML clipboard -> Markdown
    def paste_html_as_markdown(self) -> None:
        """Convert HTML on the clipboard to Markdown and insert it at the cursor.

        Bound to the QUILL key, then ``M``. Uses the clipboard's CF_HTML payload
        when available, otherwise treats the plain-text clipboard as HTML. The
        read-only guard is honoured via ``_power_tools_insert_at_cursor``.
        """
        html = self._power_tools_clipboard_html()
        if not html.strip():
            html = self._power_tools_clipboard_text()
        if not html.strip():
            self._set_status("Clipboard is empty")
            return
        markdown = html_to_markdown(html)
        if not markdown.strip():
            self._set_status("No HTML content to convert")
            return
        self._power_tools_insert_at_cursor(markdown, "Pasted HTML as Markdown")

    # ----------------------------------------------------------- EDS-1 unicode
    def insert_special_character(self) -> None:
        raw = self._power_tools_prompt_single(
            "Insert Special Character",
            "Unicode code point (hex, d-prefix for decimal, or U+):",
        )
        if raw is None:
            return
        try:
            character = parse_codepoint(raw)
        except CodepointError as error:
            self._set_status(str(error))
            return
        self._power_tools_insert_at_cursor(character, f"Inserted U+{ord(character):04X}")

    # --------------------------------------------------------- EDS-2 date/time
    def insert_date_time(self) -> None:
        fmt = str(getattr(self.settings, "datetime_insert_format", "") or DEFAULT_DATETIME_FORMAT)
        rendered = format_datetime(datetime.now(), fmt)
        self._power_tools_insert_at_cursor(rendered, f"Inserted date and time: {rendered}")

    # ------------------------------------------------------- EDS-3 calc a date
    def calculate_and_insert_date(self) -> None:
        from quill.ui.web_form import show_web_form

        now = datetime.now()
        values = show_web_form(
            self.frame,
            self._wx,
            title="Calculate Date",
            intro=(
                "Enter a year and month, then either a fixed day, or a week and "
                "weekday (for example week 4, Thursday for the 4th Thursday)."
            ),
            fields=[
                {"name": "year", "label": "Year", "type": "text", "value": str(now.year)},
                {"name": "month", "label": "Month (1-12)", "type": "text", "value": str(now.month)},
                {"name": "day", "label": "Day of month (optional)", "type": "text", "value": ""},
                {
                    "name": "week",
                    "label": "Week (optional, -1 = last)",
                    "type": "text",
                    "value": "",
                },
                {
                    "name": "weekday",
                    "label": "Weekday name (optional)",
                    "type": "text",
                    "value": "",
                },
            ],
        )
        if values is None:
            return
        try:
            year = int(str(values.get("year", "")).strip())
            month = int(str(values.get("month", "")).strip())
            day_raw = str(values.get("day", "")).strip()
            week_raw = str(values.get("week", "")).strip()
            weekday_raw = str(values.get("weekday", "")).strip()
            day = int(day_raw) if day_raw else None
            week = int(week_raw) if week_raw else None
            weekday = parse_weekday(weekday_raw) if weekday_raw else None
            result = calculate_date(year, month, day=day, week=week, weekday=weekday)
        except ValueError as error:
            self._set_status(f"Could not calculate date: {error}")
            return
        rendered = result.strftime(_DATE_INSERT_FORMAT)
        self._power_tools_insert_at_cursor(rendered, f"Inserted date: {rendered}")

    # ----------------------------------- EDS-4/5 line transforms (migrated)
    # ``number_lines`` and ``hard_wrap_lines`` moved onto the contribution
    # grammar: their handlers now live in ``quill.ui.features.line_transforms``
    # and run through the first-party ``Host`` facade (migration plan Wave 2 /
    # §9). The power-tools registration table resolves the ``power.number_lines`` and
    # ``power.hard_wrap_lines`` ids to those handlers, so no mixin method remains.

    # --------------------------------------------------- EDS-6 new from clipboard
    def new_document_from_clipboard(self) -> None:
        clip = self._power_tools_clipboard_text()
        self._power_tools_open_text_in_new_buffer(
            clip,
            "New document from clipboard" if clip else "New document (clipboard was empty)",
        )

    # -------------------------------------------------------- EDS-7 insert file
    def insert_file_content(self) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.frame,
            "Insert file content",
            wildcard="All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Insert File") != wx.ID_OK:
                return
            chosen = Path(dialog.GetPath())
        try:
            content = self._power_tools_read_text_with_detection(chosen)
        except OSError as error:
            self._set_status(f"Could not read file: {error}")
            return
        self._power_tools_insert_at_cursor(content, f"Inserted contents of {chosen.name}")

    @staticmethod
    def _power_tools_read_text_with_detection(path: Path) -> str:
        raw = path.read_bytes()
        for encoding in ("utf-8-sig", "utf-8", "utf-16"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("latin-1")

    # -------------------------------------------------- EDS-8 read-only guard
    def _read_only_store_path(self) -> Path:
        return app_data_dir() / "read-only-guards.json"

    def _read_only_paths(self) -> set[str]:
        cached = getattr(self, "_power_tools_read_only_paths", None)
        if cached is None:
            stored = read_json(self._read_only_store_path(), [])
            cached = {str(item) for item in stored} if isinstance(stored, list) else set()
            self._power_tools_read_only_paths = cached
        return cached

    def _document_is_read_only(self) -> bool:
        flag = self.document.source_metadata.get("read_only_guard")
        if flag is not None:
            return bool(flag)
        if self.document.path is not None:
            return str(self.document.path) in self._read_only_paths()
        return False

    def _refresh_read_only_state(self) -> None:
        """Re-apply the persisted read-only guard to the active editor."""
        read_only = self._document_is_read_only()
        self.document.source_metadata["read_only_guard"] = read_only
        getattr(self.editor, "SetEditable", lambda _v: None)(not read_only)

    def toggle_read_only_guard(self) -> None:
        read_only = not self._document_is_read_only()
        self.document.source_metadata["read_only_guard"] = read_only
        self.editor.SetEditable(not read_only)
        if self.document.path is not None:
            paths = self._read_only_paths()
            if read_only:
                paths.add(str(self.document.path))
            else:
                paths.discard(str(self.document.path))
            try:
                write_json_atomic(self._read_only_store_path(), sorted(paths))
            except OSError:
                pass
        self._announce("Document is read-only" if read_only else "Document is editable")

    # ------------------------------------------------ EDS-9 delete to bounds
    def delete_to_line_start(self) -> None:
        self._apply_line_operation(delete_to_line_start, "Deleted to start of line")

    def delete_to_line_end(self) -> None:
        self._apply_line_operation(delete_to_line_end, "Deleted to end of line")

    def delete_to_document_start(self) -> None:
        self._apply_line_operation(delete_to_document_start, "Deleted to top of document")

    def delete_to_document_end(self) -> None:
        self._apply_line_operation(delete_to_document_end, "Deleted to bottom of document")

    # ----------------------------------------------- EDS-10 delete paragraph
    def delete_paragraph(self) -> None:
        self._apply_line_operation(delete_paragraph, "Deleted paragraph")

    # -------------------------------------------- EDS-11 clipboard collector
    def toggle_clipboard_collector(self) -> None:
        active = not getattr(self, "_power_tools_clipboard_collector", False)
        self._power_tools_clipboard_collector = active
        copy_event = getattr(self._wx, "EVT_TEXT_COPY", None)
        previous = getattr(self, "_power_tools_collector_editor", None)
        if copy_event is not None and previous is not None:
            previous.Unbind(copy_event)
        self._power_tools_collector_editor = (
            self.editor if (copy_event is not None and active) else None
        )
        if copy_event is not None and active:
            self.editor.Bind(copy_event, self._on_power_tools_collect_copy)
        self._announce(
            "Clipboard collector on; copies append to this document"
            if active
            else "Clipboard collector off"
        )

    def _on_power_tools_collect_copy(self, event: object) -> None:
        event.Skip()
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after):
            call_after(self.collect_clipboard_now)
        else:
            self.collect_clipboard_now()

    def collect_clipboard_now(self) -> None:
        if self._document_is_read_only():
            return
        clip = self._power_tools_clipboard_text()
        if not clip:
            return
        updated = append_collected(self.editor.GetValue(), clip)
        self._replace_document_text(updated)
        self.document.set_text(updated)
        end = len(updated)
        self.editor.SetInsertionPoint(end)
        self.editor.SetSelection(end, end)
        if self.document.path is not None:
            self.save_file()
        self._set_status("Collected clipboard text")

    # ---------------------------------------------------- EDS-12 set operations
    def set_lines_first_not_second(self) -> None:
        text, cursor = self._power_tools_text_cursor()
        lines = lines_in_first_not_second(text, cursor)
        self._power_tools_open_text_in_new_buffer(
            format_lines(lines), f"{len(lines)} line(s) in first block only"
        )

    def set_lines_common(self) -> None:
        text, cursor = self._power_tools_text_cursor()
        lines = lines_common_to_both(text, cursor)
        self._power_tools_open_text_in_new_buffer(
            format_lines(lines), f"{len(lines)} line(s) common to both blocks"
        )

    # ---------------------------------------------- EDS-13 regex count/extract
    def count_regex_matches(self) -> None:
        pattern = self._power_tools_prompt_single("Count Matches", "Regular expression:")
        if pattern is None:
            return
        text = self.editor.GetValue()
        start, end = self.editor.GetSelection()
        scope = text if start == end else text[start:end]
        try:
            total = count_matches(scope, pattern)
        except RegexError as error:
            self._set_status(str(error))
            return
        self._announce(f"{total} match(es)")

    def extract_regex_matches(self) -> None:
        pattern = self._power_tools_prompt_single("Extract Matches", "Regular expression:")
        if pattern is None:
            return
        text = self.editor.GetValue()
        start, end = self.editor.GetSelection()
        scope = text if start == end else text[start:end]
        try:
            extracted = extract_matches(scope, pattern)
        except RegexError as error:
            self._set_status(str(error))
            return
        self._power_tools_open_text_in_new_buffer(extracted, "Extracted matches")

    # -------------------------------------------------- EDS-14 speech queries
    def speak_cursor_address(self) -> None:
        text, cursor = self._power_tools_text_cursor()
        self._announce(describe_cursor_address(text, cursor))

    def speak_document_status(self) -> None:
        self._announce(describe_document_status(self.document.modified, self.document.encoding))

    def speak_selection_length(self) -> None:
        start, end = self.editor.GetSelection()
        selection = self.editor.GetValue()[start:end]
        self._announce(describe_selection_length(selection))

    # ----------------------------------------------------- EDS-15 go to percent
    def go_to_percent(self) -> None:
        raw = self._power_tools_prompt_single("Go To Percent", "Document percentage (0-100):", "50")
        if raw is None:
            return
        try:
            percent = float(raw.strip())
        except ValueError:
            self._set_status("Percentage must be a number")
            return
        text = self.editor.GetValue()
        target = offset_for_percent(text, percent)
        self._record_location_before_jump()
        self._move_point(target)
        self.editor.SetFocus()
        self._location_ring.record(target)
        self._set_status(f"Moved to {round(max(0.0, min(100.0, percent)))}%")

    # ---------------------------------------------- EDS-16 non-blank navigation
    def move_to_first_non_blank(self) -> None:
        text, cursor = self._power_tools_text_cursor()
        position = first_non_blank_position(text, cursor)
        self._move_point(position)
        self._announce_character_at(text, position)

    def move_to_last_non_blank(self) -> None:
        text, cursor = self._power_tools_text_cursor()
        position = last_non_blank_position(text, cursor)
        self._move_point(position)
        self._announce_character_at(text, position)

    def _announce_character_at(self, text: str, position: int) -> None:
        if 0 <= position < len(text) and text[position] != "\n":
            self._announce(f"Character: {text[position]}")
        else:
            self._announce("End of line")

    # ------------------------------------------------- EDS-17 key describer
    def toggle_key_describer(self) -> None:
        active = not getattr(self, "_power_tools_key_describer", False)
        self._power_tools_key_describer = active
        self._announce(
            "Key Describer on; press a key to hear its action" if active else "Key Describer off"
        )

    def _maybe_describe_key(self, event: object) -> bool:
        """When Key Describer is on, speak the bound action and swallow the key.

        Returns ``True`` if the event was consumed.
        """
        if not getattr(self, "_power_tools_key_describer", False):
            return False
        accelerator = self._accelerator_from_event(event)
        if accelerator is None:
            return False
        command_id = command_for_accelerator(self.keymap, accelerator)
        if command_id is None:
            self._announce(f"{accelerator}: no action")
            return True
        command = self.commands.get(command_id) if hasattr(self.commands, "get") else None
        label = getattr(command, "label", None) or command_id
        self._announce(f"{accelerator}: {label}")
        return True

    def _accelerator_from_event(self, event: object) -> str | None:
        wx = self._wx
        key_code = event.GetKeyCode()
        modifier_keys = {
            getattr(wx, "WXK_CONTROL", -10),
            getattr(wx, "WXK_SHIFT", -11),
            getattr(wx, "WXK_ALT", -12),
            getattr(wx, "WXK_RAW_CONTROL", -13),
        }
        if key_code in modifier_keys:
            return None
        parts: list[str] = []
        if event.ControlDown():
            parts.append("Ctrl")
        if event.AltDown():
            parts.append("Alt")
        if event.ShiftDown():
            parts.append("Shift")
        name = self._key_name(key_code)
        if name is None:
            return None
        parts.append(name)
        return "+".join(parts)

    def _key_name(self, key_code: int) -> str | None:
        wx = self._wx
        specials = {
            getattr(wx, "WXK_F1", 340): "F1",
            getattr(wx, "WXK_F2", 341): "F2",
            getattr(wx, "WXK_F3", 342): "F3",
            getattr(wx, "WXK_F4", 343): "F4",
            getattr(wx, "WXK_F5", 344): "F5",
            getattr(wx, "WXK_RETURN", 13): "Enter",
            getattr(wx, "WXK_TAB", 9): "Tab",
            getattr(wx, "WXK_ESCAPE", 27): "Escape",
            getattr(wx, "WXK_HOME", 313): "Home",
            getattr(wx, "WXK_END", 312): "End",
        }
        if key_code in specials:
            return specials[key_code]
        if 32 <= key_code <= 126:
            return chr(key_code).upper()
        return None

    # ------------------------------------------- EDS-18 indent infer/announce
    def toggle_indent_announce(self) -> None:
        active = not getattr(self, "_power_tools_indent_announce", False)
        self._power_tools_indent_announce = active
        self._power_tools_last_indent_columns = self._current_indent_columns()
        self._announce(
            "Indentation announcements on" if active else "Indentation announcements off"
        )

    def _current_indent_columns(self) -> int:
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        line_start = text.rfind("\n", 0, cursor) + 1
        newline = text.find("\n", cursor)
        line_end = len(text) if newline == -1 else newline
        tab_width = int(getattr(self.settings, "tab_width", 4) or 4)
        return indent_columns(text[line_start:line_end], tab_width=tab_width)

    def _maybe_announce_indent(self) -> None:
        if not getattr(self, "_power_tools_indent_announce", False):
            return
        current = self._current_indent_columns()
        previous = getattr(self, "_power_tools_last_indent_columns", current)
        self._power_tools_last_indent_columns = current
        message = describe_indent_change(previous, current)
        if message is not None:
            self._announce(message)

    def _maybe_play_indent_tone(self) -> None:
        """Play a pitched tone when the caret moves to a new indent level.

        Off unless the user picks a scale in Preferences (``indent_tone_scale``).
        The level is ``indent columns // indent size`` clamped to 0-7, matching
        the 8 levels the tone packs ship. Blank / whitespace-only lines hold the
        previous level so cursoring through gaps stays silent.
        """
        scale = str(getattr(self.settings, "indent_tone_scale", "") or "")
        if not scale:
            return
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        line_start = text.rfind("\n", 0, cursor) + 1
        newline = text.find("\n", cursor)
        line_end = len(text) if newline == -1 else newline
        if not text[line_start:line_end].strip():
            return
        indent_size = int(getattr(self.settings, "indent_size", 4) or 4)
        level = max(0, min(7, self._current_indent_columns() // max(1, indent_size)))
        previous = getattr(self, "_indent_tone_last_level", None)
        self._indent_tone_last_level = level
        if previous is None or level == previous:
            return
        direction = "up" if level > previous else "down"
        from quill.ui.sound_manager import post_sound

        post_sound(f"indent_level_{level}_{direction}")

    def infer_indent(self) -> None:
        unit = infer_indent_unit(self.editor.GetValue())
        description = describe_indent_unit(unit)
        if unit is None:
            self._set_status(f"Inferred indentation: {description}")
            return
        wx = self._wx
        answer = self._show_message_box(
            f"Inferred indentation: {description}. Adopt it for this document?",
            "Infer Indent",
            wx.YES_NO | wx.ICON_QUESTION,
        )
        if answer == wx.ID_YES:
            if unit == "\t":
                self.settings.indent_with_tabs = True
            else:
                self.settings.indent_with_tabs = False
                self.settings.indent_size = len(unit)
            self._announce(f"Adopted indentation: {description}")
        else:
            self._announce(f"Inferred indentation: {description}")

    # ------------------------------------------------- EDS-19 run file/target
    def run_current_file(self) -> None:
        if self.document.path is None:
            self._set_status("Save the document before running it")
            return
        self.save_file()
        if self.document.modified:
            return
        path = self.document.path
        if is_dangerous_executable(str(path)):
            self._set_status("Refusing to launch an executable or script for safety")
            return
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]  # noqa: S606
        except OSError as error:
            self._set_status(f"Could not run file: {error}")
            return
        self._set_status(f"Running {path.name}")

    def run_target_at_cursor(self) -> None:
        text, cursor = self._power_tools_text_cursor()
        start, end = self.editor.GetSelection()
        selection = text[start:end] if start != end else ""
        token = target_at_cursor(text, cursor, selection)
        target = classify_target(token)
        if not target.safe:
            self._set_status(target.reason or "Nothing to run at the cursor")
            return
        if target.kind == "email":
            address = (
                target.value if target.value.startswith("mailto:") else f"mailto:{target.value}"
            )
            webbrowser.open(address)
            self._set_status(f"Opened email to {target.value}")
            return
        if target.kind == "url":
            webbrowser.open(target.value)
            self._set_status(f"Opened {target.value}")
            return
        path = Path(target.value)
        if not path.exists():
            self._set_status(f"Path does not exist: {target.value}")
            return
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]  # noqa: S606
        except OSError as error:
            self._set_status(f"Could not open path: {error}")
            return
        self._set_status(f"Opened {path.name}")

    # ------------------------------------------- EDS-20 rename/delete on disk
    def rename_current_file(self) -> None:
        if self.document.path is None:
            self._set_status("Save the document before renaming it")
            return
        current = self.document.path
        new_name = self._power_tools_prompt_single("Rename File", "New file name:", current.name)
        if new_name is None:
            return
        new_name = new_name.strip()
        if not new_name or new_name == current.name:
            return
        target = current.with_name(new_name)
        if target.exists():
            self._set_status(f"A file named {new_name} already exists")
            return
        try:
            current.rename(target)
        except OSError as error:
            self._set_status(f"Could not rename file: {error}")
            return
        self.document.path = target
        self._refresh_title()
        self._set_status(f"Renamed to {new_name}")

    def delete_current_file(self) -> None:
        if self.document.path is None:
            self._set_status("This document has not been saved to disk")
            return
        path = self.document.path
        wx = self._wx
        answer = self._show_message_box(
            f"Delete {path.name} from disk? This cannot be undone.",
            "Delete File",
            wx.YES_NO | wx.ICON_WARNING,
        )
        if answer != wx.ID_YES:
            return
        try:
            path.unlink()
        except OSError as error:
            self._set_status(f"Could not delete file: {error}")
            return
        index = self._current_tab_index()
        if index >= 0:
            self._close_tab(index)
        self._set_status(f"Deleted {path.name}")

    # ----------------------------------------- EDS-21 HTML / entity transforms
    def strip_html_tags(self) -> None:
        self._power_tools_transform_selection_or_document(
            _fmt.strip_html_tags, "Stripped HTML tags"
        )

    def decode_html_entities(self) -> None:
        self._power_tools_transform_selection_or_document(
            _fmt.decode_html_entities, "Decoded HTML entities"
        )

    def encode_html_entities(self) -> None:
        self._power_tools_transform_selection_or_document(
            _fmt.encode_html_entities, "Encoded HTML entities"
        )

    # ----------------------------------------- #197 encoding tools
    def show_non_ascii(self) -> None:
        """Open a read-only report of every non-ASCII character (#197)."""
        from quill.core import encoding_tools

        report = encoding_tools.summarize_non_ascii(self.editor.GetValue())
        self._power_tools_open_text_in_new_buffer(report, "Non-ASCII characters")

    def encode_all_non_ascii(self) -> None:
        """Replace every non-ASCII character with its HTML entity (#197)."""
        from quill.core import encoding_tools

        self._power_tools_transform_selection_or_document(
            encoding_tools.encode_non_ascii_to_entities,
            "Converted non-ASCII characters to HTML entities",
        )

    def reencode_file(self) -> None:
        """Save a copy of the document in a chosen text encoding (#197)."""
        from quill.core import encoding_tools

        wx = self._wx
        text = self.editor.GetValue()
        labels = [label for _codec, label in encoding_tools.ENCODING_CHOICES]
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose the target encoding for the saved copy:",
            "Re-encode As",
            labels,
        ) as chooser:
            if self._show_modal_dialog(chooser, "Re-encode As") != wx.ID_OK:
                self._set_status("Re-encode cancelled")
                return
            index = chooser.GetSelection()
        if index == wx.NOT_FOUND:
            self._set_status("Re-encode cancelled")
            return
        codec, label = encoding_tools.ENCODING_CHOICES[index]
        data = encoding_tools.reencode_text(text, codec)

        default_dir = ""
        if hasattr(self, "_file_dialog_default_dir"):
            default_dir = self._file_dialog_default_dir()
        with wx.FileDialog(
            self.frame,
            f"Save re-encoded copy ({label})",
            defaultDir=default_dir,
            wildcard="All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Save re-encoded copy") != wx.ID_OK:
                self._set_status("Re-encode cancelled")
                return
            target = Path(dialog.GetPath())
        try:
            target.write_bytes(data)
        except OSError as error:
            self._set_status(f"Could not write file: {error}")
            return
        self._set_status(f"Saved re-encoded copy ({label}) to {target}")

    # -------------------------------------- EDS-22 line-level TextMonkey transforms
    def trim_blank_lines(self) -> None:
        self._power_tools_transform_selection_or_document(
            _fmt.trim_blank_lines, "Trimmed blank lines"
        )

    def shuffle_lines(self) -> None:
        self._power_tools_transform_selection_or_document(_fmt.shuffle_lines, "Shuffled lines")

    def sort_lines_numeric(self) -> None:
        self._power_tools_transform_selection_or_document(
            _fmt.sort_lines_numeric, "Sorted lines numerically"
        )

    def sort_lines_by_length(self) -> None:
        self._power_tools_transform_selection_or_document(
            _fmt.sort_lines_by_length, "Sorted lines by length"
        )

    def keep_unique_lines(self) -> None:
        """Remove duplicate lines (case-sensitive); alias with a discoverable name."""
        self._power_tools_transform_selection_or_document(
            _fmt.remove_duplicate_lines, "Kept unique lines (removed duplicates)"
        )

    def delete_lines_containing(self) -> None:
        pattern = self._power_tools_prompt_single("Delete Lines Containing", "Regular expression:")
        if pattern is None:
            return
        try:
            self._power_tools_transform_selection_or_document(
                lambda text: _fmt.delete_lines_containing(text, pattern),
                "Deleted lines containing pattern",
            )
        except Exception as error:
            self._set_status(f"Invalid pattern: {error}")

    def delete_lines_not_containing(self) -> None:
        pattern = self._power_tools_prompt_single(
            "Delete Lines Not Containing", "Regular expression (keep matching lines):"
        )
        if pattern is None:
            return
        try:
            self._power_tools_transform_selection_or_document(
                lambda text: _fmt.delete_lines_not_containing(text, pattern),
                "Kept only lines containing pattern",
            )
        except Exception as error:
            self._set_status(f"Invalid pattern: {error}")
