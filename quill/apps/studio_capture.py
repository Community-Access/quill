"""Thin Studio adapter over shared target capture, OCR, vision and evidence."""

from __future__ import annotations

from pathlib import Path

import wx

from quill.apps.studio_capture_hotkeys import StudioCaptureHotkeysMixin
from quill.apps.studio_demo import StudioDemoMixin
from quill.core.paths import app_data_dir
from quill.core.studio_capture import save_capture_report
from quill.stability.task_manager import UiLifetimeToken


class StudioCaptureMixin(StudioDemoMixin, StudioCaptureHotkeysMixin):
    def _capture_command_specs(self):
        return (
            ("studio.capture", "&Capture screen...", self.capture_screen),
            ("studio.open_capture", "&Open saved screenshot...", self.open_capture_image),
            ("studio.inspect_capture", "Screenshot &Inspector...", self.inspect_last_capture),
            ("studio.cancel_capture", "Cancel &pending capture", self.cancel_screen_capture),
            ("studio.capture_active", "Screenshot &active window now", self.capture_active_window),
            ("studio.capture_desktop", "Screenshot full &desktop now", self.capture_full_desktop),
            (
                "studio.capture_selected",
                "&Repeat last selected target",
                self.capture_selected_target,
            ),
            ("studio.capture_hotkeys", "Capture global &hotkeys...", self.open_capture_hotkeys),
        )

    def _append_capture_menu(self, menu_bar):
        capture = wx.Menu()
        bindings = []
        for command_id, label, handler in self._capture_command_specs():
            item_id = wx.NewIdRef()
            capture.Append(item_id, self._menu_label(label, command_id))
            bindings.append((item_id, handler))
        bindings += self._append_demo_menu(capture)
        menu_bar.Append(capture, "&Capture")
        return bindings

    def _register_capture_commands(self):
        for command_id, label, handler in self._capture_command_specs():
            self.commands.register(
                command_id, label.replace("&", ""), handler, self._binding_for(command_id)
            )
        self._register_demo_commands()

    def _append_capture_tray(self, menu):
        self._append_demo_tray(menu)
        for command, label, action in (
            ("studio.capture", "Take a screenshot...", self.capture_screen),
            ("studio.inspect_capture", "Review screenshot...", self.inspect_last_capture),
            ("studio.cancel_capture", "Cancel pending screenshot", self.cancel_screen_capture),
        ):
            item_id = wx.NewIdRef()
            menu.Append(item_id, self._menu_label(label, command))
            menu.Bind(
                wx.EVT_MENU,
                lambda event, callback=action: (self._restore_from_tray(), callback()),
                id=item_id,
            )
            self._keep_menu_ids(item_id)

    def _ensure_capture_lifetime(self):
        if hasattr(self, "_capture_lifetime"):
            return
        self._capture_lifetime = UiLifetimeToken()

        def destroyed(event):
            if event.GetEventObject() is self.frame:
                self._capture_lifetime.invalidate()
                task = getattr(self, "_capture_task", None)
                if task is not None:
                    task.cancellation_token.cancel()
            event.Skip()

        self.frame.Bind(wx.EVT_WINDOW_DESTROY, destroyed)

    def capture_screen(self) -> None:
        if getattr(self, "_capture_pending", False):
            self._announce("A screen capture is pending. Cancel it or wait for completion.")
            return
        from quill.platform.windows.studio_capture import list_capture_targets
        from quill.ui.studio_capture_dialog import CaptureSetupDialog

        try:
            targets = list_capture_targets(include_all_windows=False)
        except Exception as error:
            self._show_message_box(str(error), "Capture screen", wx.OK | wx.ICON_ERROR)
            return
        dialog = CaptureSetupDialog(
            self.frame,
            str(app_data_dir() / "studio-captures"),
            targets,
            self._announce,
            choose_control=self._pick_capture_control,
        )
        try:
            while self._show_modal_dialog(dialog, "Capture screen") == wx.ID_OK:
                try:
                    target = dialog.selected_target()
                    delay = dialog.delay.GetValue()
                    mode, count, interval = dialog.capture_options()
                    countdown = dialog.extra_options.GetValue() and dialog.countdown.GetValue()
                    if mode.startswith("Scrolling") and (target.kind != "window" or count < 2):
                        raise ValueError(
                            "Scrolling needs a named window and at least 2 screenshots."
                        )
                    folder = Path(dialog.folder.GetValue().strip()).expanduser()
                    if not folder.is_absolute():
                        raise ValueError("Enter an absolute save folder.")
                    break
                except ValueError as error:
                    self._show_message_box(str(error), "Capture screen", wx.OK | wx.ICON_ERROR)
                    dialog.focus_invalid_input()
            else:
                return
        finally:
            dialog.Destroy()
        self._capture_recipe = (target, folder, delay, mode, count, interval, countdown)
        self._start_capture(*self._capture_recipe)

    def _pick_capture_control(self, source):
        from quill.ui.studio_capture_controls import ScreenshotControlDialog

        dialog = ScreenshotControlDialog(self, source)
        try:
            if self._show_modal_dialog(dialog, "Choose screenshot control") == wx.ID_OK:
                return dialog.selected_target()
            return None
        finally:
            dialog.stop()
            dialog.Destroy()

    def _start_capture(
        self, target, folder, delay, mode="One screenshot", count=1, interval=2, countdown=False
    ):
        if getattr(self, "_capture_pending", False):
            self._announce("A screen capture is already pending.")
            return
        self._ensure_capture_lifetime()
        self._capture_pending = True
        self._set_status(
            f"Capture in {delay} seconds: {target.label}. Cancel from the Capture menu."
        )

        def work(*, cancellation_token, progress_callback=lambda text: None, **_kwargs):
            from quill.platform.windows.studio_capture import capture_target

            if countdown:
                for seconds in range(delay, 0, -1):
                    cancellation_token.raise_if_cancelled()
                    progress_callback(f"Screenshot in {seconds} seconds.")
                    cancellation_token.event.wait(1)
            else:
                cancellation_token.event.wait(delay)
            cancellation_token.raise_if_cancelled()
            if mode.startswith("Scrolling"):
                from dataclasses import replace

                from quill.platform.windows.screenshot_scroll import capture_scrolling

                evidence, scrolling = capture_scrolling(folder, target, count, cancellation_token)
                evidence = replace(evidence, metadata={**evidence.metadata, "scrolling": scrolling})
            elif mode == "Several screenshots":
                from dataclasses import replace

                from quill.core.screenshot_sequences import capture_sequence

                captures = capture_sequence(
                    capture_target, target, folder, count, interval, cancellation_token
                )
                evidence = replace(
                    captures[-1],
                    metadata={
                        **captures[-1].metadata,
                        "sequence_paths": [item.path for item in captures],
                        "sequence_count": len(captures),
                    },
                )
            else:
                evidence = capture_target(folder, target)
            save_capture_report(evidence)
            return evidence

        def ready(_task_id, evidence):
            self._capture_pending = False
            self._last_capture = evidence
            self._set_status(
                "Screenshot saved; file decode verified. Open Screenshot Inspector to review."
            )
            # Do not steal focus from the application the user is capturing.
            scrolling = evidence.metadata.get("scrolling", {})
            if isinstance(scrolling, dict) and (
                scrolling.get("warning") or scrolling.get("restore_warning")
            ):
                self._announce(
                    "Scrolling capture needs review: "
                    + str(scrolling.get("warning", ""))
                    + " "
                    + str(scrolling.get("restore_warning", ""))
                )
            self._maybe_auto_inspect(evidence)

        def failed(_task_id, error):
            self._capture_pending = False
            self._set_status(f"Capture did not complete: {error}")

        self._capture_task = self._task_manager.submit(
            "Capture screen",
            work,
            on_success=ready,
            on_failure=failed,
            on_progress=lambda task, message: self._announce(str(message)),
            ui_lifetime=self._capture_lifetime,
        )

    def capture_active_window(self):
        try:
            import win32gui

            from quill.platform.windows.studio_capture import physical_pixels, window_target

            with physical_pixels():
                target = window_target(win32gui.GetForegroundWindow())
            self._start_capture(target, app_data_dir() / "studio-captures", 0)
        except Exception as error:
            self._set_status(f"Active-window screenshot failed: {error}")

    def capture_full_desktop(self):
        try:
            from quill.platform.windows.studio_capture import (
                desktop_target,
                display_targets,
                physical_pixels,
            )

            with physical_pixels():
                target = desktop_target(display_targets())
            self._start_capture(target, app_data_dir() / "studio-captures", 0)
        except Exception as error:
            self._set_status(f"Desktop screenshot failed: {error}")

    def capture_selected_target(self):
        recipe = getattr(self, "_capture_recipe", None)
        if recipe is None:
            self._announce("Choose a target in Capture screen before repeating a capture.")
            return
        self._start_capture(*recipe)

    def cancel_screen_capture(self) -> None:
        if getattr(self, "_capture_pending", False):
            self._capture_task.cancellation_token.cancel()
            self._announce(
                "Capture cancellation requested. A capture already in progress may finish."
            )
        else:
            self._announce("No screen capture is pending.")

    def inspect_last_capture(self) -> None:
        if getattr(self, "_inspection_pending", False):
            self._announce("Screenshot inspection is still running.")
            return
        evidence = getattr(self, "_last_capture", None)
        if evidence is None:
            self._announce("No screenshot captured this session. Choose Capture screen first.")
            return
        notes = getattr(self, "_capture_notes", {}).get(evidence.sha256, "")
        self._review_capture(evidence, notes)

    def _review_capture(self, evidence, observations="", question=""):
        from quill.ui.studio_capture_chat import show_capture_chat

        self._ensure_capture_lifetime()
        show_capture_chat(self, evidence, observations, question)

    def open_capture_image(self):
        from quill.core.storage import read_json
        from quill.core.studio_capture import verify_capture

        dialog = wx.FileDialog(
            self.frame,
            "Open saved screenshot",
            wildcard="PNG screenshots|*.png",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if self._show_modal_dialog(dialog, "Open saved screenshot") != wx.ID_OK:
                return
            path = Path(dialog.GetPath())
        finally:
            dialog.Destroy()
        try:
            evidence = verify_capture(path, "Imported PNG screenshot")
            if evidence.image_format != "PNG":
                raise ValueError("Choose a PNG screenshot.")
            saved = read_json(path.with_suffix(".verification.json"), {})
            notes = ""
            if isinstance(saved, dict) and isinstance(saved.get("evidence"), dict):
                if saved["evidence"].get("sha256") == evidence.sha256:
                    from dataclasses import replace

                    original = saved["evidence"]
                    evidence = replace(
                        evidence,
                        target=str(original.get("target", evidence.target)),
                        captured_at=str(original.get("captured_at", evidence.captured_at)),
                        metadata=original.get("metadata", {})
                        if isinstance(original.get("metadata"), dict)
                        else {},
                    )
                    notes = str(saved.get("observations_unverified", ""))
            self._last_capture = evidence
            self._remember_capture_notes(evidence, notes)
            self._review_capture(evidence, notes)
        except Exception as error:
            self._show_message_box(str(error), "Open saved screenshot", wx.OK | wx.ICON_ERROR)

    def _approve_capture_ai(self):
        from quill.core.ai.model_manager import load_ai_enabled
        from quill.core.assistant_ai import load_assistant_connection_settings
        from quill.core.studio_capture_ai import connection_identity

        if self._safe_mode or not load_ai_enabled():
            self._announce("AI is disabled. Capture and local verification remain available.")
            return None
        connection = load_assistant_connection_settings()
        if connection.provider.strip().lower() == "off":
            self._announce("No AI provider connected. Use AI > Set Up AI first.")
            return None
        identity = connection_identity(connection)
        result = self._show_message_box(
            f"Send this complete screenshot to {identity['provider']}?\n"
            f"Model: {identity['model']}\nEndpoint: {identity['host']}\n\n"
            "The image may contain private information. No automatic redaction has been applied.\n"
            "The image and your conversation are sent to the endpoint above. Service charges may "
            "apply; Studio cannot reliably estimate this request's price.\n"
            "AI observations are uncertain and do not verify privacy or correctness.",
            "Send screenshot to AI",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
        )
        return connection if result == wx.YES else None

    def _submit_capture_inspection(
        self,
        evidence,
        instructions,
        question,
        history,
        connection,
        on_success,
        on_failure,
        lifetime,
        automatic=False,
    ):
        from quill.core.studio_capture_ai import inspect_screenshot

        def work(*, cancellation_token, **_kwargs):
            if connection is not None and self._safe_mode:
                raise RuntimeError("AI is disabled in Safe Mode.")
            return inspect_screenshot(
                evidence,
                connection=connection,
                instructions=instructions,
                question=question,
                history=history,
                cancellation_token=cancellation_token,
                can_send=auto_permission if automatic else None,
            )

        def auto_permission():
            from quill.core.ai.model_manager import load_ai_enabled
            from quill.core.assistant_ai import load_assistant_connection_settings
            from quill.core.studio_capture_ai import (
                auto_ai_allowed,
                connection_identity,
                load_capture_ai_preferences,
            )

            actual = load_assistant_connection_settings()
            return connection_identity(actual) == connection_identity(
                connection
            ) and auto_ai_allowed(
                load_capture_ai_preferences(),
                actual,
                ai_enabled=load_ai_enabled(),
                safe_mode=self._safe_mode,
            )

        return self._task_manager.submit(
            "Inspect screenshot",
            work,
            on_success=on_success,
            on_failure=on_failure,
            ui_lifetime=lifetime,
        )

    def _remember_capture_notes(self, evidence, notes):
        if not hasattr(self, "_capture_notes"):
            self._capture_notes = {}
        self._capture_notes[evidence.sha256] = notes

    def _maybe_auto_inspect(self, evidence):
        from quill.core.ai.model_manager import load_ai_enabled
        from quill.core.assistant_ai import load_assistant_connection_settings
        from quill.core.settings import load_settings
        from quill.core.studio_capture_ai import (
            auto_ai_allowed,
            capture_prompt,
            load_capture_ai_preferences,
        )

        preferences = load_capture_ai_preferences()
        if preferences.get("auto_ai_enabled") is not True:
            return
        connection = load_assistant_connection_settings()
        if not auto_ai_allowed(
            preferences, connection, ai_enabled=load_ai_enabled(), safe_mode=self._safe_mode
        ):
            self._announce(
                "Automatic screenshot AI is paused. "
                "AI is disabled or the approved connection changed."
            )
            return
        instructions = capture_prompt(
            preferences.get("prompt_id", "screen-overview"), load_settings()
        )
        instructions = str(preferences.get("instructions") or instructions)

        def ready(_task, text):
            previous = getattr(self, "_capture_notes", {}).get(evidence.sha256, "")
            notes = previous + ("\n\n" if previous else "") + text
            self._remember_capture_notes(evidence, notes)
            view = getattr(self, "_capture_chat_views", {}).get(evidence.path)
            if view is not None and view.lifetime.is_alive:
                view.accept_external_observation(text)
                notes = view.observations
            try:
                save_capture_report(evidence, observations=notes)
            except Exception as error:
                self._announce(f"AI result retained, but the report could not be saved: {error}")
            self._set_status(
                "Automatic screenshot analysis ready. Open Screenshot Inspector to review."
            )

        def failed(_task, error):
            self._set_status(
                f"Automatic screenshot analysis failed; the image remains saved: {error}"
            )

        self._submit_capture_inspection(
            evidence,
            instructions,
            "Inspect this screenshot",
            "",
            connection,
            ready,
            failed,
            self._capture_lifetime,
            automatic=True,
        )
