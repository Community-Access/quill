"""Status-bar construction, navigation, and rendering for ``MainFrame`` (CQ-1).

Extracted verbatim from ``main_frame.py`` into a cohesive mixin so the UI
monolith shrinks without any behaviour change. ``MainFrame`` inherits
``StatusBarMixin`` and every method resolves identically through the MRO; the
methods reference instance state and sibling methods via ``self`` exactly as
before. ``_StatusBarCell`` moves here with the methods that construct it.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from quill.core.braille_statusbar import short_form_from_resolver
from quill.core.links import infer_markup_kind
from quill.core.markdown_sections import current_section_at, parse_heading_blocks
from quill.core.marks import line_column_for_position
from quill.core.metrics import compute_document_stats
from quill.core.navigation import estimate_page_count, estimate_page_for_position, page_starts
from quill.core.palette import load_palette_usage, top_suggestion
from quill.core.settings import STATUS_BAR_ITEMS, Settings, save_settings
from quill.platform.sr_announce import announce
from quill.ui.dialog_contract import apply_modal_ids


@dataclass(slots=True)
class _StatusBarCell:
    item: str
    button: object


class StatusBarMixin:
    def _statusbar_items(self) -> list[str]:
        allowed = set(STATUS_BAR_ITEMS)
        ordered = [item for item in self.settings.status_bar_order if item in allowed]
        hidden = {item for item in self.settings.status_bar_hidden if item in allowed}
        visible = [item for item in ordered if item not in hidden]
        # Hide cells whose governing feature is disabled so the bar reflects
        # the active feature profile rather than showing "Unavailable" cells.
        feature_manager = getattr(self, "features", None)
        if feature_manager is not None:
            status_bar_features = getattr(self, "_STATUS_BAR_FEATURES", {}) or {}
            visible = [
                item
                for item in visible
                if item not in status_bar_features
                or feature_manager.is_enabled(status_bar_features[item])
            ]
        if (
            getattr(self.settings, "title_bar_path_mode", "name") == "full_path"
            and "file_path" in visible
        ):
            visible = [item for item in visible if item != "file_path"]
        document = getattr(self, "document", None)
        if document is not None and document.path is not None:
            for item in ("encoding", "line_endings"):
                if item not in visible:
                    visible.append(item)
        last_find_query = getattr(self, "_last_find_query", "")
        if last_find_query and "search_term" not in visible:
            visible.append("search_term")
        notifications = getattr(self, "_notifications", [])
        if notifications and "notifications" not in visible:
            visible.append("notifications")
        read_aloud = getattr(self, "_read_aloud", None)
        read_aloud_state = getattr(read_aloud, "state", "idle")
        if read_aloud_state != "idle" and "read_aloud" not in visible:
            visible.append("read_aloud")
        if read_aloud_state != "idle" and "background_tasks" not in visible:
            visible.append("background_tasks")
        if getattr(self.settings, "spellcheck_as_you_type", False) and "spell_check" not in visible:
            visible.append("spell_check")
        quill_key_active = getattr(self, "_quill_key_mode_active", False) or getattr(
            self, "_quill_key_prefix_pending", False
        )
        if quill_key_active and "quill_key_mode" not in visible:
            visible.append("quill_key_mode")
        if getattr(self, "_extend_selection_mode", False) and "extend_mode" not in visible:
            visible.append("extend_mode")
        editor = getattr(self, "editor", None)
        if editor is None:
            return visible or ["message"]
        selection_start, selection_end = editor.GetSelection()
        if selection_end > selection_start and "selection" not in visible:
            visible.append("selection")
        # §8.2 Annisuggestion: surface the most-used recent command when the
        # threshold is met, but only if the item is not already configured in
        # the user's status bar order.
        if "suggestion" not in visible and self._get_action_suggestion() is not None:
            visible.append("suggestion")
        if "braille" not in visible and self._statusbar_braille_text():
            visible.append("braille")
        if "page" in visible and self._statusbar_braille_text():
            visible = [item for item in visible if item != "page"]
        # Auto-surface the AI engine cell once the user has chosen a non-Native
        # agentic engine, so the active engine is always visible while in use
        # without permanently occupying the bar for everyone else.
        if "ai_engine" not in visible and self._ai_engine_should_autoshow():
            visible.append("ai_engine")
        if not visible:
            return ["message"]
        if "message" not in visible:
            visible.insert(0, "message")
        # The generic Message cell has nothing left to say once another
        # visible cell already shows the exact same text -- saying it twice
        # through two different cells is confusing noise, not information.
        # ``any()`` short-circuits on the first match, so this only computes
        # every other cell's text in the (rare) case nothing matches.
        if "message" in visible:
            message_text = self._statusbar_text_for_item("message")
            if message_text and any(
                self._statusbar_text_for_item(item) == message_text
                for item in visible
                if item != "message"
            ):
                visible = [item for item in visible if item != "message"]
        return visible

    def _statusbar_document_stats(self) -> object | None:
        """Return DocumentStats for the live buffer, or None if unavailable.

        Shared by the word/char/line/reading-time cells. The dead-widget guard
        (#269) mirrors the other cells: a queued caret event can fire after the
        editor's C++ TextCtrl is destroyed.
        """
        editor = getattr(self, "editor", None)
        if editor is None:
            return None
        try:
            return compute_document_stats(editor.GetValue())
        except RuntimeError:
            return None

    def _statusbar_text_for_item(self, item: str) -> str:
        feature_id = self._STATUS_BAR_FEATURES.get(item)
        feature_manager = getattr(self, "features", None)
        if (
            feature_id is not None
            and feature_manager is not None
            and not feature_manager.is_enabled(feature_id)
        ):
            # Return empty string rather than "Unavailable in current profile".
            # _statusbar_items() already filters disabled-feature cells out of
            # the layout, so this path is a defensive fallback. If a cell
            # somehow escapes the filter, broadcasting "unavailable" in its
            # button label causes JAWS and NVDA to read the word "unavailable"
            # as part of the window announcement (#176). The help text (set by
            # _statusbar_help_text) still carries the unavailable reason for
            # sighted users who inspect the cell.
            return ""
        read_aloud = getattr(self, "_read_aloud", None)
        read_aloud_state = getattr(read_aloud, "state", "idle")
        notifications = getattr(self, "_notifications", [])
        autosave_interval = getattr(self, "_autosave_interval", timedelta(seconds=30))
        if item == "message":
            message = getattr(self, "_status_message", "Ready")
            if message == "Modified" and self._dirty_title_suffix():
                return "Ready"
            return message
        if item == "file_path":
            document = getattr(self, "document", None)
            if document is None or document.path is None:
                return "Unsaved"
            return document.path.name
        if item == "line_column":
            editor = getattr(self, "editor", None)
            document = getattr(self, "document", None)
            if editor is None or document is None:
                return ""
            # #269: ctrl+F4 can leave self.editor pointing at a destroyed
            # C++ TextCtrl. Treat the dead-widget condition as "no editor"
            # so a queued caret event does not crash the statusbar refresh.
            try:
                line, column = line_column_for_position(
                    editor.GetValue(),
                    editor.GetInsertionPoint(),
                )
            except RuntimeError:
                return ""
            return f"Ln {line}, Col {column}"
        if item in ("word_count", "char_count", "line_count", "reading_time"):
            stats = self._statusbar_document_stats()
            if stats is None:
                return ""
            if item == "word_count":
                return f"{stats.words:,} words"
            if item == "char_count":
                return f"{stats.characters:,} chars"
            if item == "line_count":
                return f"{stats.lines:,} lines"
            # reading_time: ~200 words per minute, rounded up to a whole minute.
            if stats.words == 0:
                return "0 min read"
            minutes = (stats.words + 199) // 200
            return "<1 min read" if stats.words < 200 else f"{minutes} min read"
        if item == "document_progress":
            editor = getattr(self, "editor", None)
            if editor is None:
                return ""
            try:
                total = len(editor.GetValue())
                caret = editor.GetInsertionPoint()
            except RuntimeError:
                return ""
            if total <= 0:
                return "0%"
            percent = round(min(caret, total) / total * 100)
            return f"{percent}%"
        if item == "mode":
            return "Overwrite" if getattr(self, "_overwrite_mode", False) else "Insert"
        if item == "tab_mode":
            return "Tab char" if getattr(self, "_tab_inserts_literal", False) else "Indent"
        if item == "document_format":
            try:
                return self._document_format_status_text()
            except Exception:  # noqa: BLE001 - a status cell must never raise
                return ""
        if item == "selection":
            editor = getattr(self, "editor", None)
            if editor is not None and hasattr(editor, "GetSelection"):
                try:
                    start, end = editor.GetSelection()
                except RuntimeError:
                    return "Sel 0"
                length = max(0, end - start)
                return f"Sel {length}"
            return "Sel 0"
        if item == "encoding":
            document = getattr(self, "document", None)
            return getattr(document, "encoding", "")
        if item == "line_endings":
            document = getattr(self, "document", None)
            if getattr(document, "line_ending", "\n") == "\r\n":
                return "CRLF"
            return "LF"
        if item == "spell_check":
            return "On" if getattr(self.settings, "spellcheck_as_you_type", False) else "Off"
        if item == "background_tasks":
            count = getattr(self, "_background_task_count", 0)
            if count > 0:
                return f"{count} active"
            if read_aloud_state == "speaking":
                return "Read aloud"
            if notifications:
                return "Notifications"
            return "Idle"
        if item == "notifications":
            count = len(notifications)
            if count == 0:
                return "No new messages"
            return f"{count} message(s)"
        if item == "read_aloud":
            if read_aloud_state == "paused":
                return "Paused"
            if read_aloud_state == "speaking":
                return "Speaking"
            return "Stopped"
        if item == "autosave":
            seconds = int(autosave_interval.total_seconds())
            if seconds <= 0:
                return "Autosave off"
            if seconds % 60 == 0:
                minutes = seconds // 60
                return f"Autosave: {minutes} min"
            return f"Autosave: {seconds} s"
        if item == "search_term":
            last_find_query = getattr(self, "_last_find_query", "")
            if last_find_query:
                return f'Find: "{last_find_query}"'
            return "No search term"
        if item == "quill_key_mode":
            if getattr(self, "_quill_key_mode_sticky", False):
                return "Locked"
            if getattr(self, "_quill_key_mode_active", False):
                return "Browse"
            if getattr(self, "_quill_key_prefix_pending", False):
                return "Prefix"
            return "Off"
        if item == "extend_mode":
            return "EXT" if getattr(self, "_extend_selection_mode", False) else "Off"
        if item == "abbreviations":
            enabled = getattr(self.settings, "abbreviation_expansion", True)
            return "ABR: On" if enabled else "ABR: Off"
        if item == "copy_tray_slots":
            if not hasattr(self, "_copy_tray_instance"):
                return "Slots: ?/12"
            count = sum(1 for _, s in self._tray().all_slots() if not s.is_empty())
            return f"Slots: {count}/12"
        if item == "language_profile":
            tab = getattr(self, "_current_tab", None)
            profile = getattr(tab, "_language_profile", None)
            name = profile.name if profile is not None else "Plain text"
            # Distinguish a user-pinned override ("(set)") from auto-detection, so
            # it is clear the choice came from the user and not the file name.
            if getattr(tab, "_language_profile_pinned", False):
                return f"{name} (set)"
            return name
        if item == "ai_engine":
            return self.ai_engine_status_text()
        if item == "braille":
            return self._statusbar_braille_text()
        if item == "page":
            return self._statusbar_page_text()
        if item == "sr_name":
            # A11Y live indicator (§8.3): show the detected screen reader name.
            # Cache the result on the instance to avoid re-running the process
            # snapshot on every status-bar refresh.
            if not hasattr(self, "_sr_name_cache"):
                try:
                    from quill.platform.windows.sr_detect import detect_screen_reader

                    result = detect_screen_reader()
                    self._sr_name_cache = result.name if result.detected else "None detected"
                except Exception:  # noqa: BLE001
                    self._sr_name_cache = "Unknown"
            return self._sr_name_cache
        if item == "suggestion":
            # §8.2 Annisuggestion: show most-used recent command.
            suggestion = self._get_action_suggestion()
            if suggestion is None:
                return ""
            binding = getattr(suggestion, "keybinding", "") or ""
            if binding:
                return f"{suggestion.title} ({binding})"
            return suggestion.title
        if item == "notebook_goal":
            nb = getattr(self, "_active_notebook", None)
            if nb is None:
                return ""
            goal = getattr(nb, "goal", None)
            if goal is None or not getattr(goal, "enabled", False):
                return ""
            count = getattr(goal, "today_count", 0)
            target = getattr(goal, "daily_target", 500)
            unit = getattr(goal, "unit", "words")
            if count >= target:
                return f"Goal reached: {count:,} {unit}"
            return f"{count:,} / {target:,} {unit}"
        if item == "section_heading":
            # EdSharp port: "Section: Heading N of M" when the caret is on
            # a heading in a Markdown or HTML document. Hidden by default
            # (see _default_status_bar_hidden); the cell silently returns
            # "" for plain-text documents and for carets not on a heading.
            return self._statusbar_section_heading_text()
        if item == "radio_player":
            return self._radio_status_text()
        if item == "podcast_player":
            return self._podcast_status_text()
        return ""

    def _statusbar_section_heading_text(self) -> str:
        """Return "Section: Heading N of M" or "" for the status-bar cell.

        EdSharp port. Returns "" when the editor or document is missing,
        when the active surface is not Markdown or HTML, when there are no
        headings at the caret's level, or when the underlying widget has
        been destroyed (the same dead-widget guard as the other cells).
        """
        editor = getattr(self, "editor", None)
        document = getattr(self, "document", None)
        if editor is None or document is None:
            return ""
        try:
            surface = infer_markup_kind(document.path)
        except Exception:  # noqa: BLE001
            return ""
        if surface not in {"markdown", "html"}:
            return ""
        try:
            text = editor.GetValue()
            caret = editor.GetInsertionPoint()
        except RuntimeError:
            return ""
        try:
            blocks = parse_heading_blocks(text, surface)
        except Exception:  # noqa: BLE001
            return ""
        if not blocks:
            return ""
        section = current_section_at(text, caret, markup_kind=surface)
        if section is None:
            return ""
        if section.level <= 0:
            return ""
        same_level = [b for b in blocks if b.level == section.level]
        if not same_level:
            return ""
        ordinal = 0
        for _index, block in enumerate(blocks):
            if block.level == section.level:
                ordinal += 1
            if block.section_start == section.start:
                break
        else:
            ordinal = 1
        total = len(same_level)
        return f"Section: Heading {section.level} ({ordinal} of {total})"

    def _statusbar_braille_text(self) -> str:
        """Return the short-form braille cell text, or "" if not active.

        Hidden for non-BRF documents. For a BRF document the resolver is
        built from the document's braille metadata and cached on the frame
        (keyed by document identity + text length) so a caret move reuses
        it; an edit that changes the length rebuilds it.
        """
        resolver = self._active_brf_resolver()
        if resolver is None:
            return ""
        editor = getattr(self, "editor", None)
        if editor is None:
            return ""
        try:
            char_offset = editor.GetCurrentPos()
        except Exception:  # noqa: BLE001
            return ""
        try:
            return short_form_from_resolver(resolver, char_offset)
        except (ValueError, TypeError):
            return ""

    def _statusbar_page_text(self) -> str:
        """Return the page cell's text: exact "N of M" or "~N of ~M (estimated)".

        Exact when the document's text contains at least one form-feed
        (real page boundaries, e.g. from PDF import); otherwise estimated
        from word count via ``page_estimate_words_per_page``. Never
        returns one style's punctuation for the other -- the tilde and the
        word "estimated" always travel together.
        """
        editor = getattr(self, "editor", None)
        if editor is None:
            return ""
        try:
            text = editor.GetValue()
            position = editor.GetInsertionPoint()
        except RuntimeError:
            return ""
        starts = page_starts(text)
        if len(starts) > 1:
            current = sum(1 for start in starts if start <= position)
            current = max(1, min(current, len(starts)))
            return f"{current} of {len(starts)}"
        words_per_page = getattr(self.settings, "page_estimate_words_per_page", 300)
        total = estimate_page_count(text, words_per_page)
        current = estimate_page_for_position(text, position, words_per_page)
        return f"~{current} of ~{total} (estimated)"

    def _active_brf_resolver(self) -> object | None:
        """Return a BraillePositionResolver for the active BRF document, or None.

        ``Document`` is a slots dataclass, so the resolver cannot be attached
        to it; it is cached on the frame instead. Returns None for any
        non-BRF document.
        """
        document = getattr(self, "document", None)
        if document is None:
            return None
        meta = getattr(document, "source_metadata", None) or {}
        if meta.get("source_kind") != "brf":
            return None
        text = getattr(document, "text", "") or ""
        key = (id(document), len(text))
        cache = getattr(self, "_brf_resolver_cache", None)
        if cache is not None and cache[0] == key:
            return cache[1]
        from quill.core.braille_position import BraillePositionResolver
        from quill.core.brf_document import BRFDocument

        brf_doc = BRFDocument.from_text_and_suffix(
            text,
            str(meta.get("brf_suffix", "")),
            had_bom=bool(meta.get("brf_had_bom", False)),
            non_ascii_offsets=list(meta.get("brf_non_ascii_offsets", []) or []),
            cell_width=int(meta.get("brf_cell_width", 40) or 40),
            line_height=int(meta.get("brf_line_height", 25) or 25),
            profile=str(meta.get("brf_profile", "ueb_english")),
        )
        resolver = BraillePositionResolver(brf_doc)
        self._brf_resolver_cache = (key, resolver)
        return resolver

    def _get_action_suggestion(self) -> object | None:
        """Return the Annisuggestion for the current session, or None."""
        commands_obj = getattr(self, "commands", None)
        if commands_obj is None:
            return None
        try:
            usage = load_palette_usage()
            commands = commands_obj.list(feature_manager=getattr(self, "features", None))
            return top_suggestion(usage, commands)
        except Exception:  # noqa: BLE001
            return None

    def _statusbar_button_label(self, item: str) -> str:
        label = self._STATUS_BAR_LABELS.get(item, item)
        value = self._statusbar_text_for_item(item)
        if item == "message":
            return value or label
        # These cells show only the value — the label is carried by SetName / announce,
        # not repeated in the visible button text.
        if item in {"line_column", "mode", "radio_player", "podcast_player"}:
            return value or label
        if value:
            return f"{label}: {value}"
        return label

    def _statusbar_help_text(self, item: str) -> str:
        feature_id = self._STATUS_BAR_FEATURES.get(item)
        feature_manager = getattr(self, "features", None)
        if (
            feature_id is not None
            and feature_manager is not None
            and not feature_manager.is_enabled(feature_id)
        ):
            return (
                f"{self._STATUS_BAR_LABELS.get(item, item)} is unavailable in the current profile"
            )
        labels = {
            "message": "Open notifications",
            "line_column": "Go to line",
            "page": "Page position. Press Enter for Go To Page.",
            "word_count": "Show document statistics",
            "mode": "Toggle overwrite mode",
            "tab_mode": "Toggle Tab key mode (QUILL Key + U). Indent or insert a tab character.",
            "document_format": (
                "Current document format. Press Enter to switch between Plain "
                "text, Markdown, HTML, and Rich Text."
            ),
            "selection": "Show selection statistics",
            "encoding": "Choose document encoding",
            "line_endings": "Toggle line endings",
            "spell_check": "Open spell check dialog",
            "background_tasks": "Open notifications",
            "notifications": "Open notifications",
            "read_aloud": "Start or pause read aloud",
            "autosave": "Cycle autosave interval",
            "search_term": "Reopen Find",
            "file_path": "Open containing folder",
            "quill_key_mode": "QUILL key mode state",
            "extend_mode": "Extend selection mode active. Press F7 to toggle.",
            "abbreviations": "Abbreviation expansion. Press Enter to toggle on/off.",
            "copy_tray_slots": "Copy tray slots in use. Press Enter to open Copy Tray.",
            "language_profile": "Active language profile. Press Enter to change language.",
            "sr_name": "Detected screen reader. Press Enter to re-detect.",
            "suggestion": "Frequently used command. Press Enter to run it.",
            "braille": "Braille position. Press Enter for Read Braille Status.",
            "ai_engine": "Active AI engine. Press Enter to switch engines.",
            "radio_player": (
                "Internet Radio. Press Enter to play or pause; right-click for "
                "Stop, Mute, and Favorite Stations."
            ),
            "podcast_player": (
                "Podcasts. Press Enter to play or pause; right-click for Stop "
                "and download controls."
            ),
        }
        return labels.get(item, self._STATUS_BAR_LABELS.get(item, item))

    def _build_statusbar_cells(self) -> None:
        if not hasattr(self, "_wx") or not hasattr(self, "statusbar"):
            return
        wx = self._wx
        context_menu_event = getattr(wx, "EVT_CONTEXT_MENU", None)
        self._statusbar_sizer.Clear(delete_windows=True)
        self._statusbar_cells = []
        items = self._statusbar_items()
        if "message" not in items:
            items = ["message"] + items
        for item in items:
            button = wx.Button(
                self.statusbar,
                label=self._statusbar_button_label(item),
                style=wx.BU_EXACTFIT,
            )
            button.SetName(self._STATUS_BAR_LABELS.get(item, item))
            button.SetHelpText(self._statusbar_help_text(item))
            button.Bind(wx.EVT_BUTTON, lambda _e, cell=item: self._activate_statusbar_cell(cell))
            button.Bind(
                wx.EVT_KEY_DOWN, lambda event, cell=item: self._on_statusbar_key_down(event, cell)
            )
            button.Bind(
                wx.EVT_SET_FOCUS,
                lambda event, cell=item: self._on_statusbar_cell_focus(event, cell),
            )
            if context_menu_event is not None:
                button.Bind(
                    context_menu_event,
                    lambda event, cell=item: self._on_statusbar_cell_context_menu(event, cell),
                )
            self._statusbar_sizer.Add(
                button,
                1 if item == "message" else 0,
                wx.EXPAND | wx.ALL,
                2,
            )
            self._statusbar_cells.append(_StatusBarCell(item=item, button=button))
        self.statusbar.Layout()

    def _apply_statusbar_layout(self) -> None:
        if not hasattr(self, "_wx") or not hasattr(self, "statusbar"):
            self._refresh_legacy_statusbar()
            return
        self._build_statusbar_cells()
        if self._statusbar_cells:
            self._active_statusbar_cell_index = min(
                self._active_statusbar_cell_index,
                len(self._statusbar_cells) - 1,
            )
            self._refresh_statusbar()

    def _refresh_statusbar(self) -> None:
        if not hasattr(self, "_statusbar_cells") or not hasattr(self, "_wx"):
            self._refresh_legacy_statusbar()
            return
        if not self._statusbar_cells:
            self._build_statusbar_cells()
        for cell in self._statusbar_cells:
            item = cell.item
            try:
                # The button itself can also be a dead C++ wrapper if the
                # statusbar was torn down mid-refresh. Treat the dead-widget
                # condition as a transient skip and let the next refresh
                # try again (#269).
                cell.button.SetLabel(self._statusbar_button_label(item))
                cell.button.SetHelpText(self._statusbar_help_text(item))
                cell.button.SetName(self._STATUS_BAR_LABELS.get(item, item))
            except RuntimeError:
                continue
            try:
                cell.button.SetMinSize((-1, -1))
                if item != "message":
                    width = self._STATUS_BAR_WIDTHS.get(item, 120)
                    cell.button.SetMinSize((width, -1))
            except Exception:
                pass
        self.statusbar.Layout()

    def _refresh_legacy_statusbar(self) -> None:
        if not hasattr(self, "statusbar"):
            return
        items = self._statusbar_items()
        # #269: _statusbar_text_for_item returns safe fallbacks if the live
        # editor's C++ wrapper has been destroyed, so this list comprehension
        # is now safe even when a tab was just closed.
        texts = [self._statusbar_text_for_item(item) for item in items]
        if hasattr(self.statusbar, "SetFieldsCount"):
            self.statusbar.SetFieldsCount(len(items))
        if hasattr(self.statusbar, "SetStatusWidths"):
            widths = [self._STATUS_BAR_WIDTHS.get(item, 120) for item in items]
            self.statusbar.SetStatusWidths(widths)
        if hasattr(self.statusbar, "SetStatusText"):
            for index, text in enumerate(texts):
                self.statusbar.SetStatusText(text, index)

    def _statusbar_cell_index(self, item: str) -> int:
        for index, cell in enumerate(self._statusbar_cells):
            if cell.item == item:
                return index
        return 0

    def _focus_statusbar_cell(self, index: int | None = None) -> None:
        if not self._statusbar_cells:
            return
        target_index = self._active_statusbar_cell_index if index is None else index
        target_index = max(0, min(target_index, len(self._statusbar_cells) - 1))
        self._active_statusbar_cell_index = target_index
        self._statusbar_cells[target_index].button.SetFocus()

    def _on_statusbar_cell_focus(self, event: object, item: str) -> None:
        index = self._statusbar_cell_index(item)
        self._active_statusbar_cell_index = index
        # The "Status bar" region name is announced only on the F6 landing into
        # the bar (flagged by _focus_region). Arrowing between cells is
        # intra-region navigation and clears the flag, so the region name is not
        # repeated on every keystroke -- the user already heard it on landing.
        entering = getattr(self, "_statusbar_entry_pending", False)
        self._statusbar_entry_pending = False
        self._announce_statusbar_item(item, with_region_prefix=entering)
        event.Skip()

    def _announce_statusbar_item(self, item: str, *, with_region_prefix: bool = True) -> None:
        label = self._STATUS_BAR_LABELS.get(item, item)
        value = self._statusbar_text_for_item(item)
        prefix = "Status bar, " if with_region_prefix else ""
        if value:
            announce(f"{prefix}{label}, {value}")
        else:
            announce(f"{prefix}{label}")

    def _on_statusbar_key_down(self, event: object, item: str) -> None:
        wx = self._wx
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_LEFT:
            self._focus_statusbar_cell(self._statusbar_cell_index(item) - 1)
            return
        if key_code == wx.WXK_RIGHT:
            self._focus_statusbar_cell(self._statusbar_cell_index(item) + 1)
            return
        if key_code == wx.WXK_HOME:
            self._focus_statusbar_cell(0)
            return
        if key_code == wx.WXK_END:
            self._focus_statusbar_cell(len(self._statusbar_cells) - 1)
            return
        if key_code == wx.WXK_ESCAPE:
            self.editor.SetFocus()
            self._set_active_region("Editor")
            announce("Returned to editor")
            return
        if key_code == wx.WXK_TAB:
            step = -1 if event.ShiftDown() else 1
            self._focus_statusbar_cell(self._statusbar_cell_index(item) + step)
            return
        if key_code in {wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_SPACE}:
            self._activate_statusbar_cell(item)
            return
        event.Skip()

    def _activate_statusbar_cell(self, item: str) -> None:
        feature_id = self._STATUS_BAR_FEATURES.get(item)
        feature_manager = getattr(self, "features", None)
        if (
            feature_id is not None
            and feature_manager is not None
            and not feature_manager.is_enabled(feature_id)
        ):
            self._set_status(
                f"{self._STATUS_BAR_LABELS.get(item, item)} is unavailable in this profile"
            )
            return
        if item == "abbreviations":
            self.toggle_abbreviation_expansion()
            return
        if item == "copy_tray_slots":
            self.open_copy_tray()
            return
        if item == "radio_player":
            self.radio_toggle_play_pause()
            return
        if item == "podcast_player":
            self.podcast_toggle_play_pause()
            return
        actions: dict[str, Callable[[], None]] = {
            "message": self.open_notifications,
            "line_column": self.go_to_line,
            "page": self.go_to_page,
            "word_count": self.show_word_count,
            "mode": self.toggle_overwrite_mode,
            "tab_mode": self.toggle_tab_insert_mode,
            "document_format": self.switch_document_format,
            "selection": self.show_word_count,
            "encoding": self.choose_document_encoding,
            "line_endings": self.toggle_line_endings,
            "spell_check": self.open_spell_check_dialog,
            "background_tasks": self.open_notifications,
            "notifications": self.open_notifications,
            "read_aloud": self.toggle_read_aloud,
            "autosave": self.cycle_autosave_interval,
            "search_term": self.find_text,
            "file_path": self.open_containing_folder,
        }
        if item == "ai_engine":
            self.open_ai_engine_switcher()
            return
        if item == "language_profile":
            self.set_document_language()
            return
        # §8.3: A11Y indicator re-detection.
        if item == "sr_name":
            if hasattr(self, "_sr_name_cache"):
                del self._sr_name_cache
            self._refresh_statusbar()
            return
        # §8.2 Annisuggestion: run the suggested command.
        if item == "suggestion":
            suggestion = self._get_action_suggestion()
            if suggestion is not None:
                try:
                    self.commands.run(suggestion.id)
                except Exception:  # noqa: BLE001
                    self._set_status(f"Could not run suggestion: {suggestion.title}")
            return
        action = actions.get(item)
        if action is None:
            self._set_status(self._statusbar_text_for_item(item))
            return
        action()

    def _hide_statusbar_cell(self, item: str) -> None:
        if item == "message":
            self._set_status("Status Message cannot be hidden")
            return
        hidden = set(getattr(self.settings, "status_bar_hidden", []))
        hidden.add(item)
        ordered_hidden = [entry for entry in self.settings.status_bar_order if entry in hidden]
        self.settings.status_bar_hidden = ordered_hidden
        save_settings(self.settings)
        self._apply_statusbar_layout()
        label = self._STATUS_BAR_LABELS.get(item, item)
        self._set_status(f"Hid {label} from status bar")

    def _restore_default_statusbar_layout(self) -> None:
        defaults = Settings()
        self.settings.status_bar_order = list(defaults.status_bar_order)
        self.settings.status_bar_hidden = list(defaults.status_bar_hidden)

    def _on_statusbar_cell_context_menu(self, event: object, item: str) -> None:
        wx = self._wx
        menu = wx.Menu()
        activate_id = wx.NewIdRef()
        hide_id = wx.NewIdRef()
        settings_id = wx.NewIdRef()
        menu.Append(activate_id, "Activate")
        if item in ("notifications", "background_tasks"):
            clear_notifications_id = wx.NewIdRef()
            menu.Append(clear_notifications_id, "Clear All Notifications")
            menu.Bind(
                wx.EVT_MENU,
                lambda _e: self.clear_all_notifications(),
                id=clear_notifications_id,
            )
        if item == "radio_player":
            self._build_radio_status_bar_menu(menu)
        if item == "podcast_player":
            self._build_podcast_status_bar_menu(menu)
        menu.Append(hide_id, "Hide this item")
        menu.Append(settings_id, "Status bar settings...")
        menu.Bind(wx.EVT_MENU, lambda _e: self._activate_statusbar_cell(item), id=activate_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self._hide_statusbar_cell(item), id=hide_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_status_bar_settings(), id=settings_id)
        if item == "message":
            hide_item = menu.FindItemById(hide_id)
            if hide_item is not None:
                hide_item.Enable(False)
        popup_target = None
        for cell in self._statusbar_cells:
            if cell.item == item:
                popup_target = cell.button
                break
        if popup_target is None:
            popup_target = self.statusbar
        self._popup_context_menu(popup_target, menu, event)

    def _set_status(self, message: str) -> None:
        self._status_message = message
        self._record_spoken(message)
        self._refresh_statusbar()
        throttle_ms = int(getattr(self.settings, "announcement_throttle_ms", 0) or 0)
        if throttle_ms > 0:
            now = time.monotonic()
            last = getattr(self, "_last_status_announce_at", 0.0)
            if (now - last) * 1000.0 < throttle_ms:
                return
            self._last_status_announce_at = now
        announce(message)

    def _set_status_quiet(self, message: str) -> None:
        """Update the status bar text WITHOUT speaking it. Used for per-keystroke
        states like "Modified" so the screen reader doesn't repeat it on every
        character (it already echoes what you type)."""
        self._status_message = message
        self._refresh_statusbar()

    def _on_statusbar_context_menu(self, event: object) -> None:
        wx = self._wx
        menu = wx.Menu()
        dark_id = wx.NewIdRef()
        wrap_id = wx.NewIdRef()
        spell_id = wx.NewIdRef()
        layout_id = wx.NewIdRef()
        menu.AppendCheckItem(dark_id, "Dark Mode")
        menu.Check(dark_id, self.settings.theme == "dark")
        menu.AppendCheckItem(wrap_id, "Soft Wrap")
        menu.Check(wrap_id, self.settings.soft_wrap)
        menu.AppendCheckItem(spell_id, "Spell Check As You Type")
        menu.Check(spell_id, self.settings.spellcheck_as_you_type)
        menu.AppendSeparator()
        menu.Append(layout_id, "Status Bar Layout...")
        menu.Bind(wx.EVT_MENU, lambda _e: self.toggle_dark_mode(), id=dark_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.toggle_soft_wrap(), id=wrap_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.toggle_spellcheck_as_you_type(), id=spell_id)
        menu.Bind(wx.EVT_MENU, lambda _e: self.open_status_bar_settings(), id=layout_id)
        self._popup_context_menu(self.statusbar, menu, event)

    def open_status_bar_settings(self) -> None:
        wx = self._wx
        item_order = list(self.settings.status_bar_order)
        hidden = set(self.settings.status_bar_hidden)
        dialog = wx.Dialog(self.frame, title="Status Bar Layout", size=(560, 420))
        # Parent every control directly to the dialog and lay them out in one
        # sizer (issue #119 pattern). The previous build parented controls to an
        # inner wx.Panel but added dialog.CreateButtonSizer()'s buttons (children
        # of the dialog) to the panel's sizer. That parent/sizer mismatch
        # mislaid the OK/Cancel buttons, and because SetEscapeId(wx.ID_CANCEL)
        # needs a realized Cancel button, neither the buttons nor Escape could
        # dismiss the dialog. This matches the working Keymap Editor and search
        # dialogs.
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(
                dialog,
                label=(
                    "Choose visible status items and order. "
                    "Use Move Up/Down, or right-click for Move Left/Right and Hide/Show."
                ),
            ),
            0,
            wx.ALL | wx.EXPAND,
            8,
        )

        def state_label(item: str, shown: bool) -> str:
            # Spell out the visibility in the item text so it is obvious without
            # relying solely on the checkbox state (which some screen readers
            # announce only on focus, not at a glance).
            base = self._STATUS_BAR_LABELS.get(item, item)
            return f"{base} (shown)" if shown else f"{base} (hidden)"

        chooser = wx.CheckListBox(  # A11Y-SR-1-OK: state in label text; pending CheckBox conversion
            dialog,
            choices=[state_label(item, item not in hidden) for item in item_order],
        )
        for index, item in enumerate(item_order):
            chooser.Check(index, item not in hidden)
        root.Add(chooser, 1, wx.ALL | wx.EXPAND, 8)

        def refresh_label(index: int) -> None:
            if 0 <= index < len(item_order):
                chooser.SetString(index, state_label(item_order[index], chooser.IsChecked(index)))

        def announce_state(index: int) -> None:
            if not (0 <= index < len(item_order)):
                return
            base = self._STATUS_BAR_LABELS.get(item_order[index], item_order[index])
            self._set_status(f"{base} {'shown' if chooser.IsChecked(index) else 'hidden'}")

        def toggle_item(index: int) -> None:
            # Programmatic toggle (context menu) — Check() does not fire
            # EVT_CHECKLISTBOX, so refresh the label and announce here.
            if not (0 <= index < len(item_order)):
                return
            chooser.Check(index, not chooser.IsChecked(index))
            refresh_label(index)
            announce_state(index)

        def on_toggle(event: object) -> None:
            # Fired by the native checkbox toggle, including the Spacebar.
            index = event.GetInt() if hasattr(event, "GetInt") else chooser.GetSelection()
            refresh_label(index)
            announce_state(index)

        chooser.Bind(wx.EVT_CHECKLISTBOX, on_toggle)
        controls = wx.BoxSizer(wx.HORIZONTAL)
        move_up = wx.Button(dialog, label="Move Up")
        move_down = wx.Button(dialog, label="Move Down")
        restore_defaults = wx.Button(dialog, label="Restore Defaults")
        controls.Add(move_up, 0, wx.RIGHT, 8)
        controls.Add(move_down, 0, wx.RIGHT, 8)
        controls.Add(restore_defaults, 0, wx.RIGHT, 8)
        root.Add(controls, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
        if buttons is not None:
            ok_button = dialog.FindWindowById(wx.ID_OK)
            if ok_button is not None:
                ok_button.SetDefault()
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        dialog.SetSizer(root)
        restore_defaults_selected = False

        def swap_items(first: int, second: int) -> None:
            if first < 0 or second < 0:
                return
            if first >= len(item_order) or second >= len(item_order):
                return
            item_order[first], item_order[second] = item_order[second], item_order[first]
            first_checked = chooser.IsChecked(first)
            second_checked = chooser.IsChecked(second)
            chooser.Check(first, second_checked)
            chooser.Check(second, first_checked)
            chooser.SetString(first, state_label(item_order[first], second_checked))
            chooser.SetString(second, state_label(item_order[second], first_checked))
            chooser.SetSelection(second)

        def move_selected(offset: int) -> None:
            selected = chooser.GetSelection()
            if selected == wx.NOT_FOUND:
                return
            target = selected + offset
            if target < 0 or target >= len(item_order):
                return
            swap_items(selected, target)

        def on_move_up(_event: object) -> None:
            move_selected(-1)

        def on_move_down(_event: object) -> None:
            move_selected(1)

        def on_context_menu(event: object) -> None:
            selected = chooser.GetSelection()
            if selected == wx.NOT_FOUND:
                return
            menu = wx.Menu()
            move_left_id = wx.NewIdRef()
            move_right_id = wx.NewIdRef()
            toggle_id = wx.NewIdRef()
            menu.Append(move_left_id, "Move Left")
            menu.Append(move_right_id, "Move Right")
            menu.AppendSeparator()
            toggle_label = "Hide Item" if chooser.IsChecked(selected) else "Show Item"
            menu.Append(toggle_id, toggle_label)
            menu.Bind(wx.EVT_MENU, lambda _e: move_selected(-1), id=move_left_id)
            menu.Bind(wx.EVT_MENU, lambda _e: move_selected(1), id=move_right_id)
            menu.Bind(
                wx.EVT_MENU,
                lambda _e: toggle_item(selected),
                id=toggle_id,
            )
            self._popup_context_menu(chooser, menu, event)

        def on_restore_defaults(_event: object) -> None:
            nonlocal restore_defaults_selected
            restore_defaults_selected = True
            self._set_status("Status bar defaults selected")

        move_up.Bind(wx.EVT_BUTTON, on_move_up)
        move_down.Bind(wx.EVT_BUTTON, on_move_down)
        restore_defaults.Bind(wx.EVT_BUTTON, on_restore_defaults)
        chooser.Bind(wx.EVT_CONTEXT_MENU, on_context_menu)

        # The dialog must be destroyed on every exit path; ``_show_modal_dialog``
        # only shows it modally and does not own its lifetime. (The pre-extraction
        # copy in main_frame.py leaked it — the module-level Destroy gate missed it
        # only because hundreds of sibling dialogs there call .Destroy().)
        try:
            if self._show_modal_dialog(dialog, "Status Bar Layout") != wx.ID_OK:
                return
            if restore_defaults_selected:
                self._restore_default_statusbar_layout()
            else:
                self.settings.status_bar_order = list(item_order)
                self.settings.status_bar_hidden = [
                    item for index, item in enumerate(item_order) if not chooser.IsChecked(index)
                ]
            save_settings(self.settings)
            self._apply_statusbar_layout()
            self._set_status("Status bar layout updated")
        finally:
            dialog.Destroy()
