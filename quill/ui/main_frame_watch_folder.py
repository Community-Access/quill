"""The watch-folder runtime on QUILL's main window (qc.md F-08, extracted 2026-10-03).

Everything that lives as long as watch-folder monitoring does: starting and
stopping it, its status page and queue monitor, its settings window, and the
built-in actions the watch service calls back into -- convert, run a macro, run
AI -- with their consent and resource-cap answers. It was a contiguous block of
``MainFrame``; the host contract is unchanged (``self._watch_service``,
``self.settings``, ``self._wx``, ``self._announce``), and the profile editor
beside it stays in ``main_frame_watch_profile.py``.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from quill.core.settings import save_settings
from quill.core.watch_actions import WatchActionOutcome
from quill.core.watch_default import launch_plan
from quill.core.watch_profiles import WatchProfile, iter_matching_files
from quill.core.watch_queue import (
    STATE_DONE,
    STATE_FAILED,
    STATE_PROCESSING,
    STATE_QUEUED,
    STATE_SKIPPED,
    QueueItem,
)
from quill.io.pandoc import convert_document_with_pandoc
from quill.ui.dialog_contract import apply_modal_ids


class WatchFolderRuntimeMixin:
    """Watch-folder monitoring, status and actions; mixed into ``MainFrame``."""

    def _apply_watch_folder_menu_state(self) -> None:
        # Watch folder toggle is now in Settings; no menu state to sync
        pass

    def _maybe_start_watch_folder(self) -> None:
        # H-SAFE-1: safe mode must not start the watcher; the banner is a
        # contract. The WatchService can still be constructed so other
        # surfaces (settings UI, diagnostics) can inspect profiles, but
        # ``start()`` is the side effect we are refusing.
        #
        # Two switches decide what launch starts (watch_default.launch_plan):
        # "Enable folder watching by default" starts the enabled profiles,
        # "Start watching automatically" starts the page's default folder.
        profiles, default_folder = launch_plan(self.settings, safe_mode=bool(self._safe_mode))
        if profiles:
            self._start_watch_folder_monitoring(announce=False)
            return
        if default_folder and self._feature_enabled("core.watch_folder"):
            # The default folder alone: deliberately not recorded as
            # watch_folder_enabled, which would start every profile next time.
            self._watch_service.start(profiles=False)
        self._apply_watch_folder_menu_state()

    def _start_watch_folder_monitoring(self, *, announce: bool = True) -> bool:
        if not self._feature_enabled("core.watch_folder"):
            if announce:
                self._set_status("Watch folder is unavailable in this profile")
            return False
        started = self._watch_service.start()
        self.settings.watch_folder_enabled = True
        save_settings(self.settings)
        self._apply_watch_folder_menu_state()
        if announce:
            if started:
                count = len(started)
                noun = "profile" if count == 1 else "profiles"
                self._set_status(f"Watch folder monitoring started ({count} {noun})")
                self._record_notification("Watch folder monitoring started", "speech")
            else:
                self._set_status("Watch folder is on, but no profiles are enabled")
                self._record_notification(
                    "Watch folder monitoring is on, but no profiles are enabled",
                    "speech",
                )
        return True

    def _stop_watch_folder_monitoring(self, *, announce: bool = True) -> None:
        self._watch_service.stop()
        self._apply_watch_folder_menu_state()
        if announce:
            self._set_status("Watch folder monitoring stopped")
            self._record_notification("Watch folder monitoring stopped", "speech")

    def toggle_watch_folder_monitoring(self) -> None:
        """Open Settings at the Watch Folders tab where monitoring can be toggled."""
        self.open_general_preferences()
        self._set_status("Watch folder monitoring setting is in Settings > Watch Folders")

    def show_watch_folder_status(self) -> None:
        """Open the accessible Watch Queue Monitor (WATCH-4)."""
        if not self._feature_enabled("core.watch_folder"):
            # #10: this early return left focus in the editor with only a silent
            # status, so the command looked like it "did nothing". Speak it.
            self._announce_result("Watch folder is unavailable in this profile")
            return
        existing = self._watch_queue_monitor
        if existing is not None:
            try:
                existing.Raise()
                existing.SetFocus()
                self._refresh_watch_queue_monitor()
                return
            except Exception:
                self._watch_queue_monitor = None
                self._watch_queue_listbox = None
        wx = self._wx
        dialog = wx.Dialog(
            self.frame,
            title="Watch Queue Monitor",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        root = wx.BoxSizer(wx.VERTICAL)

        summary = wx.StaticText(dialog, label="Watch queue")
        summary.SetName("Watch queue summary")
        root.Add(summary, 0, wx.ALL, 8)

        listbox = wx.ListBox(dialog, style=wx.LB_SINGLE)
        listbox.SetName("Watch queue items")
        root.Add(listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        button_row = wx.BoxSizer(wx.HORIZONTAL)
        pause_button = wx.Button(dialog, label="&Pause")
        pause_button.SetName("Pause or resume the watch queue")
        retry_button = wx.Button(dialog, label="&Retry")
        retry_button.SetName("Retry selected item")
        open_button = wx.Button(dialog, label="&Open Result")
        open_button.SetName("Open the result of the selected item")
        clear_button = wx.Button(dialog, label="&Clear Finished")
        clear_button.SetName("Clear finished items")
        refresh_button = wx.Button(dialog, label="Re&fresh")
        refresh_button.SetName("Refresh the watch queue")
        for button in (pause_button, retry_button, open_button, clear_button, refresh_button):
            button_row.Add(button, 0, wx.RIGHT, 6)
        root.Add(button_row, 0, wx.ALL, 8)

        buttons = dialog.CreateButtonSizer(wx.CLOSE)
        if buttons is not None:
            root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        dialog.SetSizerAndFit(root)
        dialog.SetSize((640, 460))

        def _selected_item() -> QueueItem | None:
            index = listbox.GetSelection()
            if index == wx.NOT_FOUND:
                return None
            items = self._watch_queue_items_cache
            if 0 <= index < len(items):
                return items[index]
            return None

        def _on_pause(_event: object) -> None:
            if self._watch_service.queue.is_paused():
                self._watch_service.resume()
                self._set_status("Watch queue resumed")
            else:
                self._watch_service.pause()
                self._set_status("Watch queue paused")
            self._refresh_watch_queue_monitor()

        def _on_retry(_event: object) -> None:
            item = _selected_item()
            if item is None:
                self._set_status("Select a queue item to retry")
                return
            if self._watch_service.retry_item(item.item_id):
                self._set_status(f"Retrying {Path(item.source_path).name}")
            else:
                self._set_status("That item cannot be retried")
            self._refresh_watch_queue_monitor()

        def _on_open(_event: object) -> None:
            item = _selected_item()
            if item is None:
                self._set_status("Select a queue item to open")
                return
            target = item.result_path or item.source_path
            if not target:
                self._set_status("That item has no file to open")
                return
            self.open_file(Path(target), record_recent=True, refresh_existing=False)

        def _on_clear(_event: object) -> None:
            removed = self._watch_service.clear_finished()
            self._set_status(f"Cleared {removed} finished item{'s' if removed != 1 else ''}")
            self._refresh_watch_queue_monitor()

        def _on_refresh(_event: object) -> None:
            self._refresh_watch_queue_monitor()

        def _on_close(_event: object) -> None:
            self._watch_queue_monitor = None
            self._watch_queue_listbox = None
            self._watch_queue_pause_button = None
            dialog.Destroy()

        pause_button.Bind(wx.EVT_BUTTON, _on_pause)
        retry_button.Bind(wx.EVT_BUTTON, _on_retry)
        open_button.Bind(wx.EVT_BUTTON, _on_open)
        clear_button.Bind(wx.EVT_BUTTON, _on_clear)
        refresh_button.Bind(wx.EVT_BUTTON, _on_refresh)
        dialog.Bind(wx.EVT_BUTTON, _on_close, id=wx.ID_CLOSE)
        dialog.Bind(wx.EVT_CLOSE, _on_close)

        self._watch_queue_monitor = dialog
        self._watch_queue_listbox = listbox
        self._watch_queue_summary = summary
        self._watch_queue_pause_button = pause_button
        self._watch_queue_items_cache = []
        apply_modal_ids(dialog, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)
        self._refresh_watch_queue_monitor()
        dialog.Show()
        listbox.SetFocus()

    def _refresh_watch_queue_monitor(self) -> None:
        dialog = self._watch_queue_monitor
        listbox = self._watch_queue_listbox
        if dialog is None or listbox is None:
            return
        try:
            items = self._watch_service.queue_items()
        except Exception:
            items = []
        self._watch_queue_items_cache = items
        previous = listbox.GetSelection()
        listbox.Clear()
        for item in items:
            name = Path(item.source_path).name if item.source_path else "(unknown)"
            label = f"{item.state.title()} - {name}"
            if item.attempts:
                label += f" (attempt {item.attempts})"
            if item.message:
                label += f" - {item.message}"
            listbox.Append(label)
        if items:
            target = previous if 0 <= previous < len(items) else 0
            listbox.SetSelection(target)
        counts = self._watch_service.queue_counts()
        summary = getattr(self, "_watch_queue_summary", None)
        if summary is not None:
            queued = counts.get(STATE_QUEUED, 0) + counts.get(STATE_PROCESSING, 0)
            done = counts.get(STATE_DONE, 0)
            failed = counts.get(STATE_FAILED, 0)
            skipped = counts.get(STATE_SKIPPED, 0)
            paused = " (paused)" if self._watch_service.queue.is_paused() else ""
            label = f"Pending {queued}, done {done}, failed {failed}, skipped {skipped}{paused}"
            # Explain an apparently-empty queue: profiles default to ignoring files
            # already present when the watch started (process_existing off), so only
            # newly-added files appear. Surface that so the monitor isn't confusing.
            if not items:
                try:
                    primed = self._watch_service.primed_count()
                except Exception:  # noqa: BLE001 - a hint must never break the monitor
                    primed = 0
                if primed:
                    label += (
                        f". {primed} existing file{'s' if primed != 1 else ''} ignored "
                        "(turn on 'Process existing files' on a profile, or add a new file)"
                    )
            summary.SetLabel(label)
        pause_button = getattr(self, "_watch_queue_pause_button", None)
        if pause_button is not None:
            pause_button.SetLabel("Resume" if self._watch_service.queue.is_paused() else "Pause")

    def open_watch_folder_settings(self) -> None:
        """Open the accessible Watch Profile Manager (WATCH-5)."""
        if not self._feature_enabled("core.watch_folder"):
            self._set_status("Watch folder is unavailable in this profile")
            return
        wx = self._wx
        with wx.Dialog(
            self.frame,
            title="Watch Folder Profiles",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        ) as dialog:
            root = wx.BoxSizer(wx.VERTICAL)

            heading = wx.StaticText(dialog, label="Watch folder profiles")
            heading.SetName("Watch folder profiles")
            root.Add(heading, 0, wx.ALL, 8)

            listbox = wx.ListBox(dialog, style=wx.LB_SINGLE)
            listbox.SetName("Watch folder profile list")
            root.Add(listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

            button_row = wx.BoxSizer(wx.HORIZONTAL)
            add_button = wx.Button(dialog, label="&Add...")
            edit_button = wx.Button(dialog, label="&Edit...")
            duplicate_button = wx.Button(dialog, label="D&uplicate")
            toggle_button = wx.Button(dialog, label="Ena&ble/Disable")
            delete_button = wx.Button(dialog, label="De&lete")
            for button in (add_button, edit_button, duplicate_button, toggle_button, delete_button):
                button_row.Add(button, 0, wx.RIGHT, 6)
            root.Add(button_row, 0, wx.ALL, 8)

            buttons = dialog.CreateButtonSizer(wx.CLOSE)
            if buttons is not None:
                root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
            dialog.SetSizerAndFit(root)
            dialog.SetSize((620, 440))

            def _refresh_list(select: int = -1) -> None:
                profiles = self._watch_service.profiles()
                listbox.Clear()
                for profile in profiles:
                    state = "enabled" if profile.enabled else "disabled"
                    folder = profile.folder_path or "(no folder)"
                    listbox.Append(f"{profile.name} - {state} - {folder}")
                if profiles:
                    index = select if 0 <= select < len(profiles) else 0
                    listbox.SetSelection(index)

            def _selected_profile() -> WatchProfile | None:
                index = listbox.GetSelection()
                if index == wx.NOT_FOUND:
                    return None
                profiles = self._watch_service.profiles()
                if 0 <= index < len(profiles):
                    return profiles[index]
                return None

            def _on_add(_event: object) -> None:
                profile = self._edit_watch_profile(None)
                if profile is not None:
                    self._watch_service.add_profile(profile)
                    _refresh_list()
                    self._set_status(f"Added watch profile {profile.name}")

            def _on_edit(_event: object) -> None:
                current = _selected_profile()
                if current is None:
                    self._set_status("Select a profile to edit")
                    return
                updated = self._edit_watch_profile(current)
                if updated is not None:
                    self._watch_service.update_profile(updated)
                    _refresh_list(listbox.GetSelection())
                    self._set_status(f"Updated watch profile {updated.name}")

            def _on_duplicate(_event: object) -> None:
                current = _selected_profile()
                if current is None:
                    self._set_status("Select a profile to duplicate")
                    return
                copy = self._watch_service.duplicate_profile(current.profile_id)
                if copy is not None:
                    _refresh_list()
                    self._set_status(f"Duplicated watch profile {current.name}")

            def _on_toggle(_event: object) -> None:
                current = _selected_profile()
                if current is None:
                    self._set_status("Select a profile to enable or disable")
                    return
                self._watch_service.set_profile_enabled(current.profile_id, not current.enabled)
                _refresh_list(listbox.GetSelection())
                state = "disabled" if current.enabled else "enabled"
                self._set_status(f"{current.name} {state}")

            def _on_delete(_event: object) -> None:
                current = _selected_profile()
                if current is None:
                    self._set_status("Select a profile to delete")
                    return
                response = self._show_message_box(
                    f"Delete watch profile '{current.name}'?",
                    "Delete Watch Profile",
                    wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT,
                )
                if response != wx.YES:
                    return
                self._watch_service.delete_profile(current.profile_id)
                _refresh_list()
                self._set_status(f"Deleted watch profile {current.name}")

            add_button.Bind(wx.EVT_BUTTON, _on_add)
            edit_button.Bind(wx.EVT_BUTTON, _on_edit)
            duplicate_button.Bind(wx.EVT_BUTTON, _on_duplicate)
            toggle_button.Bind(wx.EVT_BUTTON, _on_toggle)
            delete_button.Bind(wx.EVT_BUTTON, _on_delete)

            _refresh_list()
            apply_modal_ids(dialog, affirmative_id=wx.ID_CLOSE, escape_id=wx.ID_CLOSE)
            self._show_modal_dialog(dialog, "Watch Folder Profiles")

        if self._watch_service.is_running:
            self._watch_service.restart()
        self._apply_watch_folder_menu_state()
        self._set_status("Updated watch folder profiles")

    def _watch_ai_consent_detail(self) -> str:
        """Plain-language description of where AI watch actions send content (WATCH-6)."""
        try:
            from quill.core.ai.model_manager import load_model_choice, resolve_spec

            spec = resolve_spec(load_model_choice())
            return (
                f"AI actions send each file's text to your selected model "
                f"({spec.name}). This runs only when consent is checked."
            )
        except Exception:  # noqa: BLE001 - never block the dialog on this lookup
            return (
                "AI actions send each file's text to your selected AI model. "
                "This runs only when consent is checked."
            )

    def _watch_dry_run_sample(self, profile: WatchProfile) -> Path:
        """Pick a representative file for a dry-run preview without side effects."""
        folder = Path(profile.folder_path) if profile.folder_path else None
        if folder is not None and folder.is_dir():
            try:
                for candidate in iter_matching_files(profile):
                    return candidate
            except Exception:  # noqa: BLE001 - preview must never raise
                pass
            return folder / "example-file.txt"
        return Path("example-file.txt")

    def _on_watch_file_opened(self, path: Path) -> None:
        try:
            self.open_file(path, record_recent=True, refresh_existing=False)
        except Exception:
            self._set_status(f"Watch folder could not open {path.name}")
            return
        self._record_notification(f"Watch folder opened {path.name}", "speech")
        self._set_status(f"Watch folder opened {path.name}")

    def _on_watch_queue_event(self, event: str, item: object) -> None:
        if self._watch_queue_monitor is not None:
            self._refresh_watch_queue_monitor()
        if event == "failed" and item is not None:
            source = getattr(item, "source_path", "")
            name = Path(source).name if source else "a file"
            message = getattr(item, "message", "") or "unknown error"
            if self._watch_message_is_resource_cap(message):
                # WATCH-6: a runaway action that hit the shared SEC-9 wall-clock
                # cap is terminated; announce the termination distinctly so the
                # user understands the machine was protected, not that their
                # transform merely errored.
                self._record_notification(
                    f"Watch stopped {name}: it exceeded the time limit and was "
                    "terminated to protect your machine.",
                    "speech",
                )
                self._set_status(f"Watch stopped {name}: time limit exceeded")
                return
            self._record_notification(
                f"Watch failed for {name}: {message}",
                "speech",
            )
            self._set_status(f"Watch failed for {name}")

    @staticmethod
    def _watch_message_is_resource_cap(message: str) -> bool:
        """Return True when a failed watch item was terminated for a resource cap.

        The SEC-9 Python sandbox reports a wall-clock kill as "Execution timed
        out"; surface any timeout/limit phrasing as a resource-cap termination
        so WATCH-6 can announce it distinctly (WATCH-6).
        """
        lowered = (message or "").lower()
        return any(
            phrase in lowered
            for phrase in ("timed out", "timeout", "time limit", "exceeded", "resource cap")
        )

    # WATCH-7: built-in action handlers supplied to the watch action registry.
    # These run on the watch worker thread, so file I/O is done directly here
    # (the io layer is UI-agnostic) and any editor work is marshalled to the UI
    # thread via wx.CallAfter.
    _WATCH_CONVERT_KINDS: ClassVar[dict[str, tuple[str, str]]] = {
        "markdown": ("markdown", ".md"),
        "md": ("markdown", ".md"),
        "gfm": ("markdown", ".md"),
        "html": ("html", ".html"),
        "htm": ("html", ".html"),
        "plain": ("plain", ".txt"),
        "text": ("plain", ".txt"),
        "txt": ("plain", ".txt"),
    }

    def _watch_convert_file(self, path: Path, target_format: str) -> Path:
        """Convert a detected file to ``target_format`` via Pandoc (WATCH-7).

        Runs on the watch worker thread. Returns the written output path so the
        queue can report and optionally open the result.
        """
        key = (target_format or "").strip().lower()
        mapping = self._WATCH_CONVERT_KINDS.get(key)
        if mapping is None:
            raise ValueError(
                f"Unsupported convert target '{target_format}'. Use markdown, html, or plain text."
            )
        output_kind, suffix = mapping
        result = convert_document_with_pandoc(path, output_kind)
        target = path.with_suffix(suffix)
        if target == path:
            target = path.with_name(f"{path.stem}.converted{suffix}")
        target.write_text(result.text, encoding="utf-8")
        return target

    def _watch_run_macro(self, path: Path, macro_name: str) -> None:
        """Open a detected file and replay a saved macro over it (WATCH-7).

        Macro replay mutates the editor, so it must happen on the UI thread; the
        worker thread marshals it through wx.CallAfter and returns immediately.
        """
        call_after = getattr(self._wx, "CallAfter", None)
        if callable(call_after):
            call_after(self._watch_run_macro_ui, path, macro_name)
        else:  # pragma: no cover - fallback for headless test stubs
            self._watch_run_macro_ui(path, macro_name)

    def _watch_run_macro_ui(self, path: Path, macro_name: str) -> None:
        try:
            self.open_file(path, record_recent=True, refresh_existing=False)
        except Exception:
            self._set_status(f"Watch folder could not open {path.name}")
            return
        macros = getattr(self, "macros", None)
        if macros is None or macro_name not in getattr(macros, "macros", {}):
            self._set_status(f"Macro {macro_name} is no longer available")
            return
        try:
            macros.play_macro(macro_name, self.commands.run)
        except KeyError:
            self._set_status(f"Macro {macro_name} is no longer available")
            return
        self._set_status(f"Ran macro {macro_name} on {path.name}")

    def _watch_run_ai(self, path: Path, options: Mapping[str, object]) -> WatchActionOutcome:
        """Run a consented AI action over a detected file (WATCH-7, AI-5, WATCH-6).

        Runs on the watch worker thread. Honors the AI on/off switch and writes
        the result to a sidecar file so nothing in the editor is overwritten.
        """
        from quill.core.ai.model_manager import load_ai_enabled

        if not load_ai_enabled():
            return WatchActionOutcome.skipped(
                "AI is turned off. Enable it in Tools > AI Assistant to use this action."
            )
        mode = str(options.get("mode", "")).strip().lower()
        if mode not in {"summarize", "tag", "rewrite"}:
            return WatchActionOutcome.failed("Choose an AI mode: summarize, tag, or rewrite.")
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as error:
            return WatchActionOutcome.failed(f"Could not read file: {error}")
        assistant = self._get_assistant()
        try:
            if mode in {"summarize", "rewrite"}:
                result = assistant.transform(mode, text)
            else:  # tag
                result = assistant.ask(
                    "Read the following document and return a short, comma-separated "
                    "list of topical tags that describe it. Return only the tags:\n\n" + text
                )
        except Exception as error:  # surfaced as a failed outcome
            return WatchActionOutcome.failed(str(error))
        target = path.with_name(f"{path.stem}.{mode}.md")
        try:
            target.write_text(result, encoding="utf-8")
        except OSError as error:
            return WatchActionOutcome.failed(f"Could not write AI result: {error}")
        return WatchActionOutcome.done(f"AI {mode} written to {target.name}", result_path=target)
