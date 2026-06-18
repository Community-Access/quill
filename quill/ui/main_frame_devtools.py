"""Developer Console mixin for ``MainFrame`` (QDC feature).

Wires the QUILL Developer Console (Python + TypeScript) into the running
editor.  Implements the ``ConsoleHost`` protocol so ``QuillScriptAPI`` can
reach editor state without importing wx.

Threading contract:
- Console UI runs on the wx UI thread.
- Python execution is synchronous on the UI thread (short commands only; long
  commands should be wrapped in a background task by the user via threading).
- TypeScript execution runs a Node subprocess; the result arrives via
  threading.Event and is posted back to the UI with wx.CallAfter.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from quill.core.scripting import QuillScriptAPI
from quill.devtools import history as _history
from quill.devtools.console_window import ConsoleWindow
from quill.devtools.python_console import PythonConsole
from quill.devtools.ts_console import TypeScriptConsole, TypeScriptConsoleError

_CONSENT_TEXT = (
    "Developer Console\n\n"
    "This console can run code inside QUILL and may change the current document.\n"
    "Only run commands you understand or received from a trusted source.\n\n"
    "Note: Python commands execute synchronously. A loop with no exit condition\n"
    "will freeze QUILL until it completes. Save your document before running\n"
    "document-wide commands.\n\n"
    "Recommended:\n"
    "- Use q.run_command(...) or documented q methods.\n"
    "- Do not paste code from unknown sources."
)


class DevToolsMixin:
    """Mixin that adds the QUILL Developer Console to ``MainFrame``."""

    # ------------------------------------------------------------------
    # Lazy-init state accessors

    def _dt_python_console(self) -> PythonConsole:
        if not hasattr(self, "_dev_python_console"):
            self._dev_python_console = PythonConsole(self._dt_make_namespace())
        return self._dev_python_console

    def _dt_ts_console(self) -> TypeScriptConsole:
        if not hasattr(self, "_dev_ts_console"):
            timeout = float(getattr(self.settings, "console_typescript_timeout", 30))
            self._dev_ts_console = TypeScriptConsole(
                host=self, timeout=timeout, ui_call=self._dt_marshal_to_ui
            )
        return self._dev_ts_console

    def _dt_window(self) -> ConsoleWindow:
        if not hasattr(self, "_dev_console_window"):
            self._dev_console_window = ConsoleWindow(
                wx=self._wx,
                parent=self.frame,
                on_execute_python=self._dt_on_execute_python,
                on_execute_ts=self._dt_on_execute_ts,
                announce_cb=self._announce,
                focus_editor_cb=self._dt_focus_editor,
            )
        return self._dev_console_window

    def _dt_focus_editor(self) -> None:
        try:
            self.editor.SetFocus()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # ConsoleHost protocol implementation

    def console_get_editor_text(self) -> str:
        try:
            return self.editor.GetValue()
        except Exception:
            return ""

    def console_set_editor_text(self, text: str) -> None:
        try:
            self.editor.SetValue(text)
            self._mark_document_modified()
        except Exception:
            pass

    def console_get_selected_text(self) -> str:
        try:
            return self.editor.GetStringSelection()
        except Exception:
            return ""

    def console_replace_selection(self, text: str) -> None:
        try:
            self.editor.WriteText(text)
            self._mark_document_modified()
        except Exception:
            pass

    def console_goto_line(self, line: int) -> None:
        try:
            idx = self.editor.XYToPosition(0, line - 1)
            self.editor.SetInsertionPoint(idx)
            self.editor.ShowPosition(idx)
        except Exception:
            pass

    def console_goto_offset(self, offset: int) -> None:
        try:
            self.editor.SetInsertionPoint(offset)
            self.editor.ShowPosition(offset)
        except Exception:
            pass

    def console_get_document_name(self) -> str:
        try:
            path = self._active_document_path()
            return path.name if path else ""
        except Exception:
            return ""

    def console_run_command(self, command_id: str) -> None:
        self.commands.run(command_id)

    def console_command_exists(self, command_id: str) -> bool:
        return self.commands.get(command_id) is not None

    def console_list_commands(self, query: str | None) -> list[tuple[str, str]]:
        cmds = self.commands.list()
        if query:
            q = query.lower()
            cmds = [c for c in cmds if q in c.id.lower() or q in c.title.lower()]
        return [(c.id, c.title) for c in cmds]

    def console_announce(self, text: str) -> None:
        self._announce(text)

    def console_get_last_announcements(self) -> list[str]:
        try:
            return list(getattr(self, "_announcement_log", []))
        except Exception:
            return []

    def console_document_stats(self) -> dict[str, int]:
        try:
            text = self.editor.GetValue()
            lines = text.count("\n") + (1 if text else 0)
            words = len(text.split()) if text else 0
            chars = len(text)
            paragraphs = len([p for p in text.split("\n\n") if p.strip()])
            return {"words": words, "lines": lines, "chars": chars, "paragraphs": paragraphs}
        except Exception:
            return {"words": 0, "lines": 0, "chars": 0, "paragraphs": 0}

    # ------------------------------------------------------------------
    # Subsystem surfaces for the q.* facades. All defensive: a console call
    # must never crash the editor, so every accessor degrades to a safe default.

    def console_get_setting(self, name: str) -> object:
        return getattr(getattr(self, "settings", None), name, None)

    def console_all_settings(self) -> dict[str, object]:
        from dataclasses import asdict, is_dataclass

        settings = getattr(self, "settings", None)
        try:
            if is_dataclass(settings) and not isinstance(settings, type):
                return dict(asdict(settings))
        except Exception:
            pass
        return {}

    def console_active_profile(self) -> tuple[str, str]:
        try:
            profile = self.features.active_profile()
            return (str(profile.id), str(profile.name))
        except Exception:
            return ("", "")

    def console_available_profiles(self) -> list[tuple[str, str]]:
        try:
            return [(str(p.id), str(p.name)) for p in self.features.available_profiles()]
        except Exception:
            return []

    def console_switch_profile(self, profile_id: str) -> None:
        try:
            self.features.switch_profile(profile_id)
        except Exception:
            pass

    def console_feature_enabled(self, feature_id: str) -> bool:
        try:
            return bool(self.features.is_enabled(feature_id))
        except Exception:
            return False

    def console_list_bookmarks(self) -> list[tuple[str, int]]:
        try:
            return [(str(name), int(pos)) for name, pos in self._bookmarks.items()]
        except Exception:
            return []

    def console_list_quillins(self) -> list[str]:
        names: list[str] = []
        try:
            for item in self._installed_quillins():
                name = (
                    getattr(getattr(item, "manifest", None), "name", None)
                    or getattr(item, "id", None)
                    or getattr(item, "name", None)
                )
                names.append(str(name) if name else str(item))
        except Exception:
            return []
        return names

    def console_start_macro(self, name: str) -> None:
        try:
            self.macros.start_recording(name)
        except Exception:
            pass

    def console_stop_macro(self) -> str | None:
        try:
            macro = self.macros.stop_recording()
            return getattr(macro, "name", None)
        except Exception:
            return None

    def console_play_last_macro(self) -> None:
        try:
            self.macros.play_last_macro(self.commands.run)
        except Exception:
            pass

    def console_recording_macro(self) -> str | None:
        try:
            return self.macros.recording_name
        except Exception:
            return None

    def console_spell_suggest(self, word: str) -> list[str]:
        try:
            from quill.core.spellcheck import suggest_words

            return list(suggest_words(word, self._spell_dictionary()))
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Public entry points

    def open_python_console(self) -> None:
        """Tools > Advanced > Developer Console > Open Python Console"""
        import os

        if os.environ.get("QUILL_SAFE_MODE") == "1":
            self._set_status("Developer Console is disabled in Safe Mode.")
            self._announce("Developer Console is disabled in Safe Mode.")
            return
        if not getattr(self.settings, "console_enabled", True):
            self._set_status("Developer Console is disabled in settings.")
            self._announce("Developer Console is disabled in settings.")
            return
        if not self._dt_consent_check():
            return
        win = self._dt_window()
        win.set_language("Python")
        py = self._dt_python_console()
        py.update_namespace(self._dt_snapshot_vars())
        entries = [e.source for e in _history.load(50, language="python")]
        win.load_history(entries)
        win.set_status(f"Ready - Python | {self.console_get_document_name() or 'no document'}")
        # #47: the TypeScript worker announces when it finishes starting; the
        # Python console had the same silence gap on first open.  Announce a
        # brief ready cue so screen-reader users hear that the window is
        # live before they type.
        first_open = not getattr(self, "_dt_python_opened", False)
        self._dt_python_opened = True
        win.show()
        if first_open:
            self._wx.CallAfter(
                self._announce,
                "Python console ready. Type q.help() for the scripting API reference.",
            )

    def open_typescript_console(self) -> None:
        """Tools > Advanced > Developer Console > Open TypeScript Console"""
        import os

        if os.environ.get("QUILL_SAFE_MODE") == "1":
            self._set_status("Developer Console is disabled in Safe Mode.")
            self._announce("Developer Console is disabled in Safe Mode.")
            return
        if not getattr(self.settings, "console_enabled", True):
            self._set_status("Developer Console is disabled in settings.")
            self._announce("Developer Console is disabled in settings.")
            return
        if not self._dt_consent_check():
            return
        win = self._dt_window()
        entries = [e.source for e in _history.load(50, language="typescript")]
        win.load_history(entries)
        win.set_language("TypeScript")
        win.set_status(f"Ready - TypeScript | {self.console_get_document_name() or 'no document'}")
        win.show()
        ts = self._dt_ts_console()
        if not ts.is_running():
            threading.Thread(  # GATE-40-OK: long-lived TS worker.
                target=self._dt_start_ts_worker, daemon=True
            ).start()

    def copy_diagnostic_summary(self) -> None:
        """Tools > Advanced > Developer Console > Copy Diagnostic Summary"""
        api = QuillScriptAPI(self)
        summary = api.support.diagnostic_summary()
        wx = self._wx
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(summary))
            finally:
                wx.TheClipboard.Close()
            self._announce("Diagnostic summary copied to clipboard.")
        else:
            self._announce("Could not open clipboard.")

    def restart_typescript_worker(self) -> None:
        if not hasattr(self, "_dev_console_window"):
            self._set_status("Open the TypeScript console first, then restart the worker.")
            self._announce("Open the TypeScript console first, then restart the worker.")
            return
        self._dt_ts_console()  # ensure created before thread starts
        threading.Thread(  # GATE-40-OK: TS worker restart.
            target=self._dt_restart_ts_worker, daemon=True
        ).start()

    # ------------------------------------------------------------------
    # Execution callbacks (called from ConsoleWindow on UI thread)

    def _dt_on_execute_python(self, source: str, prompt: str) -> None:
        win = self._dt_window()
        py = self._dt_python_console()
        py.update_namespace(self._dt_snapshot_vars())
        win.append_transcript(f"{prompt}{source}\n")
        result = py.execute(source)
        from quill.core.script_results import ScriptSuccess

        if isinstance(result, ScriptSuccess):
            if result.output:
                win.append_transcript(result.output)
                self._dt_announce_output(result.output)
            if result.value is not None:
                win.append_transcript(f"Result: {result.value!r}\n")
                self._announce(f"Result: {result.value!r}")
            elif not result.output:
                # Silent success — announce so SR user knows it ran
                self._announce("Done.")
            _history.add_entry("python", source, success=True)
        else:
            win.append_transcript(f"Error: {result.message}\n")
            if result.suggestion:
                win.append_transcript(f"Suggestion: {result.suggestion}\n")
            if result.detail:
                win.append_transcript(f"Details:\n{result.detail}\n")
            self._announce(f"Error: {result.message}")
            _history.add_entry("python", source, success=False)

    def _dt_on_execute_ts(self, source: str, prompt: str) -> None:
        win = self._dt_window()
        win.append_transcript(f"{prompt}{source}\n")
        win.set_status("Running TypeScript...")
        self._announce("Running TypeScript.")
        ts = self._dt_ts_console()
        threading.Thread(  # GATE-40-OK: TS execute thread; bounded by source.
            target=self._dt_ts_execute_thread,
            args=(ts, source, win),
            daemon=True,
        ).start()

    def _dt_ts_execute_thread(self, ts: TypeScriptConsole, source: str, win: ConsoleWindow) -> None:
        result = ts.execute(source)
        self._wx.CallAfter(self._dt_ts_done, result, source, win)

    def _dt_ts_done(self, result: Any, source: str, win: ConsoleWindow) -> None:
        from quill.core.script_results import ScriptSuccess

        if isinstance(result, ScriptSuccess):
            if result.output:
                win.append_transcript(result.output + "\n")
                self._dt_announce_output(result.output)
            if result.value is not None:
                win.append_transcript(f"Result: {result.value!r}\n")
                self._announce(f"Result: {result.value!r}")
            elif not result.output:
                self._announce("Done.")
            _history.add_entry("typescript", source, success=True)
        else:
            win.append_transcript(f"Error: {result.message}\n")
            if result.detail:
                win.append_transcript(f"Details:\n{result.detail}\n")
            self._announce(f"Error: {result.message}")
            _history.add_entry("typescript", source, success=False)
        win.set_status(f"Ready - TypeScript | {self.console_get_document_name() or 'no document'}")

    # ------------------------------------------------------------------
    # Internal helpers

    def _dt_consent_check(self) -> bool:
        """Show first-run safety warning; return True if user accepted."""
        from quill.core.settings import save_settings

        if getattr(self.settings, "dev_console_consent_accepted", False):
            return True
        result = self._show_message_box(
            _CONSENT_TEXT,
            "Developer Console",
            self._wx.OK | self._wx.CANCEL | self._wx.ICON_INFORMATION,
        )
        if result == self._wx.OK:
            self.settings.dev_console_consent_accepted = True
            save_settings(self.settings)
            return True
        return False

    def _dt_make_namespace(self) -> dict[str, Any]:
        api = QuillScriptAPI(self)
        return {
            "q": api,
            "commands": api.commands,
            "a11y": api.a11y,
        }

    def _dt_snapshot_vars(self) -> dict[str, Any]:
        """Fresh snapshot variables refreshed on each execution."""
        from quill.core.scripting import DocumentSnapshot

        name = self.console_get_document_name()
        stats = self.console_document_stats()
        snap = DocumentSnapshot(
            name=name or "",
            path="",
            modified=False,
            line_count=stats.get("lines", 0),
            char_count=stats.get("chars", 0),
        )
        return {
            "doc": snap,
        }

    def _dt_start_ts_worker(self) -> None:
        ts = self._dt_ts_console()
        try:
            ts.start()
            self._wx.CallAfter(
                self._dt_window().set_status,
                f"Ready - TypeScript | {self.console_get_document_name() or 'no document'}",
            )
            self._wx.CallAfter(self._announce, "Developer Console ready.")
        except TypeScriptConsoleError as exc:
            self._wx.CallAfter(
                self._dt_window().append_transcript,
                f"Error: Could not start TypeScript worker: {exc}\n",
            )
            self._wx.CallAfter(self._dt_window().set_status, "TypeScript worker unavailable")

    def _dt_restart_ts_worker(self) -> None:
        ts = self._dt_ts_console()
        self._wx.CallAfter(self._dt_window().set_status, "Restarting TypeScript worker...")
        try:
            ts.restart()
            self._wx.CallAfter(
                self._dt_window().set_status,
                f"Ready - TypeScript | {self.console_get_document_name() or 'no document'}",
            )
        except TypeScriptConsoleError as exc:
            self._wx.CallAfter(
                self._dt_window().append_transcript,
                f"Error: {exc}\n",
            )

    def _dt_bind_devtools_menu(self) -> None:
        wx = self._wx
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_python_console(),
            id=self._id_dev_console_python,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.open_typescript_console(),
            id=self._id_dev_console_ts,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.copy_diagnostic_summary(),
            id=self._id_dev_copy_diagnostic,
        )
        self.frame.Bind(
            wx.EVT_MENU,
            lambda _e: self.restart_typescript_worker(),
            id=self._id_dev_restart_ts_worker,
        )

    def _dt_marshal_to_ui(self, fn: Callable[[], Any]) -> Any:
        """Run *fn* on the UI thread and return its result; blocks the calling thread.

        Used by TypeScriptConsole to marshal invoke calls (host API calls) from
        the Node reader thread to the UI thread, satisfying the wx threading
        invariant that all widget access happens on the UI thread.
        """
        event = threading.Event()
        result_box: list[Any] = []
        error_box: list[BaseException] = []

        def wrapper() -> None:
            try:
                result_box.append(fn())
            except BaseException as exc:
                error_box.append(exc)
            finally:
                event.set()

        self._wx.CallAfter(wrapper)
        event.wait()
        if error_box:
            raise error_box[0]
        return result_box[0] if result_box else None

    def _dt_announce_output(self, output: str) -> None:
        """Announce stdout/stderr output from a console command.

        Short output (≤150 chars, ≤3 lines) is spoken verbatim so the user
        hears it without having to navigate the transcript.  Longer output
        gets a summary announcement — the full text is in the transcript.
        This matches the PRD §7.3 requirement: long output is summarized,
        not flood-spoken.
        """
        text = output.rstrip()
        if not text:
            return
        lines = text.splitlines()
        if len(lines) <= 3 and len(text) <= 150:
            self._announce(text)
        else:
            self._announce(
                f"{len(lines)} lines of output — review transcript with your screen reader."
            )

    def _mark_document_modified(self) -> None:
        """Signal that the active document has been changed from the console."""
        try:
            self._set_modified(True)
        except Exception:
            pass
