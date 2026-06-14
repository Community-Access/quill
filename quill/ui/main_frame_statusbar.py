"""Status-bar construction, navigation, and rendering for ``MainFrame`` (CQ-1).

Extracted verbatim from ``main_frame.py`` into a cohesive mixin so the UI
monolith shrinks without any behaviour change. ``MainFrame`` inherits
``StatusBarMixin`` and every method resolves identically through the MRO; the
methods reference instance state and sibling methods via ``self`` exactly as
before. ``_StatusBarCell`` moves here with the methods that construct it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from quill.core.marks import line_column_for_position
from quill.core.metrics import compute_document_stats
from quill.core.palette import load_palette_usage, top_suggestion
from quill.core.settings import STATUS_BAR_ITEMS, Settings, save_settings
from quill.platform.windows.sr_announce import announce


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
        if getattr(self, "_active_notebook", None) is not None and "notebook_goal" not in visible:
            nb = self._active_notebook
            goal = getattr(nb, "goal", None)
            if goal is not None and getattr(goal, "enabled", False):
                visible.append("notebook_goal")
        if not visible:
            return ["message"]
        if "message" not in visible:
            visible.insert(0, "message")
        return visible

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
            line, column = line_column_for_position(
                editor.GetValue(),
                editor.GetInsertionPoint(),
            )
            return f"Ln {line}, Col {column}"
        if item == "word_count":
            editor = getattr(self, "editor", None)
            if editor is None:
                return ""
            stats = compute_document_stats(editor.GetValue())
            return f"{stats.words:,} words"
        if item == "mode":
            return "OVR" if getattr(self, "_overwrite_mode", False) else "INS"
        if item == "selection":
            editor = getattr(self, "editor", None)
            if editor is not None and hasattr(editor, "GetSelection"):
                start, end = editor.GetSelection()
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
            if profile is None:
                return "Plain text"
            return profile.name
        if item == "sr_name":
            # A11Y live indicator (§8.3): show the detected screen reader name.
            # Cache the result on the instance to avoid re-running tasklist on
            # every status-bar refresh.
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
        return ""

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
            "word_count": "Show document statistics",
            "mode": "Toggle overwrite mode",
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
            cell.button.SetLabel(self._statusbar_button_label(item))
            cell.button.SetHelpText(self._statusbar_help_text(item))
            cell.button.SetName(self._STATUS_BAR_LABELS.get(item, item))
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
        self._announce_statusbar_item(item)
        event.Skip()

    def _announce_statusbar_item(self, item: str) -> None:
        label = self._STATUS_BAR_LABELS.get(item, item)
        value = self._statusbar_text_for_item(item)
        if value:
            announce(f"Status bar, {label}, {value}")
        else:
            announce(f"Status bar, {label}")

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
        actions: dict[str, Callable[[], None]] = {
            "message": self.open_notifications,
            "line_column": self.go_to_line,
            "word_count": self.show_word_count,
            "mode": self.toggle_overwrite_mode,
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
