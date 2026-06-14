from __future__ import annotations

from pathlib import Path

from quill.ui.main_frame import MainFrame

SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame.py").read_text(
    encoding="utf-8"
)


def test_main_frame_uses_watch_service_not_legacy_watcher() -> None:
    assert "from quill.core.watch_service import WatchService" in SOURCE
    assert "self._watch_service = WatchService(" in SOURCE
    # The legacy single-folder watcher must be fully removed.
    assert "WatchFolderService" not in SOURCE
    assert "WatchFolderConfig" not in SOURCE
    assert "_watch_folder_config" not in SOURCE


def test_watch_service_wiring_passes_engine_callbacks() -> None:
    assert "on_open=lambda path: self._wx.CallAfter(self._on_watch_file_opened, path)" in SOURCE
    assert "queue_listener=lambda event, item: self._wx.CallAfter(" in SOURCE
    assert "def _on_watch_file_opened(self, path: Path) -> None:" in SOURCE
    assert "def _on_watch_queue_event(self, event: str, item: object) -> None:" in SOURCE


def test_watch_service_wiring_passes_builtin_action_handlers() -> None:
    # WATCH-7: convert, macro, and AI handlers must be supplied to the registry.
    assert "on_convert=self._watch_convert_file," in SOURCE
    assert "on_run_macro=self._watch_run_macro," in SOURCE
    assert "on_ai=self._watch_run_ai," in SOURCE
    assert "def _watch_convert_file(self, path: Path, target_format: str) -> Path:" in SOURCE
    assert "def _watch_run_macro(self, path: Path, macro_name: str) -> None:" in SOURCE
    assert (
        "def _watch_run_ai(self, path: Path, options: Mapping[str, object]) -> WatchActionOutcome:"
        in SOURCE
    )


def test_watch_convert_handler_uses_pandoc() -> None:
    # WATCH-7: convert runs off the UI thread via the UI-agnostic pandoc helper.
    assert "result = convert_document_with_pandoc(path, output_kind)" in SOURCE
    assert "target.write_text(result.text, encoding=" in SOURCE


def test_watch_macro_handler_marshals_to_ui_thread() -> None:
    # WATCH-7: macro replay mutates the editor and must run on the UI thread.
    assert "call_after(self._watch_run_macro_ui, path, macro_name)" in SOURCE
    assert "macros.play_macro(macro_name, self.commands.run)" in SOURCE


def test_watch_ai_handler_honors_ai_switch_and_consent_gate() -> None:
    # WATCH-7/AI-5: the handler refuses to run when AI is off and writes a sidecar.
    assert "if not load_ai_enabled():" in SOURCE
    assert "return WatchActionOutcome.skipped(" in SOURCE
    assert 'target = path.with_name(f"{path.stem}.{mode}.md")' in SOURCE


def test_apply_watch_folder_menu_state_uses_service_running() -> None:
    # Method name preserved for accessibility tests that monkeypatch it.
    # MENU-1: the watch-folder toggle moved into Settings, so this method no
    # longer syncs a check item; it is a retained no-op for compatibility.
    assert "def _apply_watch_folder_menu_state(self) -> None:" in SOURCE
    assert "Watch folder toggle is now in Settings; no menu state to sync" in SOURCE


def test_watch_profile_manager_dialog_is_accessible() -> None:
    assert "def open_watch_folder_settings(self) -> None:" in SOURCE
    assert 'title="Watch Folder Profiles"' in SOURCE
    assert "panel = wx.Panel(dialog)" not in SOURCE
    assert 'listbox.SetName("Watch folder profile list")' in SOURCE
    assert "def _edit_watch_profile(self, profile: WatchProfile | None)" in SOURCE


def test_watch_queue_monitor_dialog_is_accessible() -> None:
    assert "def show_watch_folder_status(self) -> None:" in SOURCE
    assert 'title="Watch Queue Monitor"' in SOURCE
    assert "def _refresh_watch_queue_monitor(self) -> None:" in SOURCE
    assert "self._watch_service.retry_item(item.item_id)" in SOURCE
    assert "self._watch_service.clear_finished()" in SOURCE


def test_watch_profile_editor_uses_registry_actions() -> None:
    assert "self._watch_service.registry.available_actions()" in SOURCE
    assert 'options["destination"] = destination' in SOURCE
    assert "post_values = [POST_LEAVE, POST_MOVE, POST_DELETE]" in SOURCE


def test_watch_profile_editor_exposes_filters_and_schedule() -> None:
    # WATCH-5: per-profile suffix/name-pattern/min-size/min-age filters and schedule.
    assert 'suffix_input.SetName("File type suffixes, comma separated")' in SOURCE
    assert 'pattern_input.SetName("File name patterns, comma separated")' in SOURCE
    assert 'size_input.SetName("Minimum file size in bytes")' in SOURCE
    assert 'age_input.SetName("Minimum file age in seconds")' in SOURCE
    assert 'sched_choice.SetName("Schedule mode")' in SOURCE
    assert "sched_modes = [SCHED_ALWAYS, SCHED_WINDOW, SCHED_QUIET]" in SOURCE
    assert "name_patterns=name_patterns," in SOURCE
    assert "schedule_mode=schedule_mode," in SOURCE


def test_watch_profile_editor_exposes_per_action_options() -> None:
    # WATCH-7: per-action option controls for convert/macro/python/AI.
    assert 'convert_choice.SetName("Convert target format")' in SOURCE
    assert 'macro_input.SetName("Macro name to run")' in SOURCE
    assert 'python_code.SetName("Python transform code")' in SOURCE
    assert 'ai_choice.SetName("AI action mode")' in SOURCE
    assert 'options["target_format"]' in SOURCE
    assert 'options["macro_name"]' in SOURCE
    assert 'options["mode"]' in SOURCE


def test_watch_profile_editor_has_consent_and_dry_run_preview() -> None:
    # WATCH-6: per-profile AI consent control and a side-effect-free dry-run preview.
    assert 'consent.SetName("AI consent for this profile")' in SOURCE
    assert "def _watch_ai_consent_detail(self) -> str:" in SOURCE
    assert 'preview_button = wx.Button(dialog, label="Pre&view (dry run)")' in SOURCE
    assert "self._watch_service.registry.dry_run(" in SOURCE
    assert "def _watch_dry_run_sample(self, profile: WatchProfile) -> Path:" in SOURCE


def test_watch_resource_cap_classifier_flags_timeouts() -> None:
    # WATCH-6: sandbox wall-clock kills (SEC-9) must be recognised as cap kills.
    classify = MainFrame._watch_message_is_resource_cap
    assert classify("Execution timed out") is True
    assert classify("The transform hit the time limit") is True
    assert classify("resource cap reached") is True
    assert classify("Could not read file: missing") is False
    assert classify("") is False


def test_watch_queue_event_announces_resource_cap_termination_distinctly() -> None:
    # WATCH-6: a cap kill is announced as a protective termination, not a plain failure.
    frame = MainFrame.__new__(MainFrame)
    frame._watch_queue_monitor = None
    notifications: list[tuple[str, str]] = []
    statuses: list[str] = []
    frame._record_notification = lambda message, channel: notifications.append((message, channel))
    frame._set_status = lambda message: statuses.append(message)

    class _Item:
        source_path = Path("runaway.txt")
        message = "Execution timed out"

    frame._on_watch_queue_event("failed", _Item())

    assert notifications, "a cap termination must be announced"
    announced = notifications[0][0]
    assert "terminated to protect your machine" in announced
    assert statuses == ["Watch stopped runaway.txt: time limit exceeded"]


def test_watch_queue_event_announces_plain_failure_normally() -> None:
    frame = MainFrame.__new__(MainFrame)
    frame._watch_queue_monitor = None
    notifications: list[tuple[str, str]] = []
    statuses: list[str] = []
    frame._record_notification = lambda message, channel: notifications.append((message, channel))
    frame._set_status = lambda message: statuses.append(message)

    class _Item:
        source_path = Path("broken.txt")
        message = "Could not read file"

    frame._on_watch_queue_event("failed", _Item())

    assert notifications[0][0] == "Watch failed for broken.txt: Could not read file"
    assert statuses == ["Watch failed for broken.txt"]
