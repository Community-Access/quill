"""BITS Whisperer speech-to-text management for MainFrame (CQ-1 decomposition).

``BwSpeechMixin`` owns dictation toggling and the BW (BITS Whisperer)
speech-to-text management surface: model status/recommendation, the
faster-whisper engine check, provider selection and status, the Provider
Center, readiness/diagnostics snapshots, the capability matrix page, model
downloads with the download queue manager, and the Model Manager dialog.
Extracted verbatim from ``main_frame.py``; runs on ``MainFrame`` (``self``).
Model downloads are user-initiated and covered by the network egress audit.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from quill.core.dictation import (
    DictationSettings,
    DictationUnavailableError,
)
from quill.core.settings import save_settings
from quill.ui.dialog_contract import (
    apply_modal_ids,
)


class BwSpeechMixin:
    def toggle_dictation(self) -> None:
        wx = self._wx
        state = self._dictation.state
        if state == "listening":
            self._dictation.stop()
            self._set_status("System dictation stopped")
            return

        self.editor.SetFocus()
        try:
            self._dictation.start(DictationSettings())
        except DictationUnavailableError:
            self._show_message_box(
                "System dictation is unavailable on this system.",
                "Dictation",
                wx.ICON_INFORMATION | wx.OK,
            )
            return
        self._set_status("System dictation started. Speak into the editor.")

    def show_bw_model_status(self) -> None:
        from quill.core.bw_speech import (
            downloaded_model_ids as bw_downloaded_model_ids,
        )
        from quill.core.bw_speech import (
            faster_whisper_status,
        )
        from quill.core.bw_speech import (
            list_models as bw_list_models,
        )
        from quill.core.bw_speech import (
            machine_guidance as bw_machine_guidance,
        )
        from quill.core.bw_speech import (
            recommended_model_id as bw_recommended_model_id,
        )

        models = bw_list_models()
        downloaded = bw_downloaded_model_ids()
        mode = str(getattr(self.settings, "bw_speech_selection_mode", "recommended"))
        current_model = str(getattr(self.settings, "bw_speech_model_id", "whisper-base"))
        recommended = bw_recommended_model_id()
        ok, engine_status = faster_whisper_status()
        status = [
            "BITS Whisperer Speech Model Status",
            "",
            bw_machine_guidance(),
            f"Selection mode: {mode}",
            f"Configured default: {current_model}",
            f"Recommended now: {recommended}",
            f"Installed models: {len(downloaded)} of {len(models)}",
            f"faster-whisper engine: {'Ready' if ok else 'Not installed'}",
            engine_status,
            "",
            "This is a phased rollout. Additional BITS Whisperer capabilities "
            "will arrive gradually.",
        ]
        self._show_message_box("\n".join(status), "BITS Whisperer Speech Models", self._wx.OK)
        self._set_status("BITS Whisperer speech model status shown")

    def apply_bw_recommended_model(self) -> None:
        from quill.core.bw_speech import recommended_model_id as bw_recommended_model_id

        model_id = bw_recommended_model_id()
        self.settings.bw_speech_selection_mode = "recommended"
        self.settings.bw_speech_model_id = model_id
        save_settings(self.settings)
        self._set_status(f"Recommended mode active. Selected speech model: {model_id}")

    def check_bw_faster_whisper_engine(self) -> None:
        from quill.core.bw_speech import faster_whisper_status

        ok, detail = faster_whisper_status()
        icon = self._wx.ICON_INFORMATION if ok else self._wx.ICON_WARNING
        self._show_message_box(detail, "faster-whisper Engine", self._wx.OK | icon)
        self._set_status("faster-whisper engine ready" if ok else "faster-whisper not installed")

    def _set_bw_download_status(
        self,
        model_id: str,
        *,
        model_name: str,
        status: str,
        progress: str,
        started_at: str | None = None,
        finished_at: str = "",
    ) -> None:
        existing = self._bw_download_status.get(model_id, {})
        self._bw_download_status[model_id] = {
            "model": model_name,
            "status": status,
            "progress": progress,
            "started_at": started_at
            or str(existing.get("started_at", datetime.now(UTC).isoformat())),
            "finished_at": finished_at,
        }
        self._maybe_refresh_live_status_tabs()

    def _bw_include_cloud_providers(self) -> bool:
        return bool(getattr(self.settings, "bw_show_cloud_providers", True))

    def _bw_local_first_mode(self) -> bool:
        return str(getattr(self.settings, "bw_provider_mode", "local_first")) == "local_first"

    def _bw_safe_mode_locked(self) -> bool:
        return bool(getattr(self.settings, "bw_safe_mode_lock", False))

    def _append_bw_safe_mode_badge(self, menu: object) -> None:
        if not self._bw_safe_mode_locked():
            return
        badge_item = menu.Append(self._wx.ID_ANY, "Safe Mode Lock: Enabled")
        badge_item.Enable(False)

    def apply_bw_recommended_provider(self) -> None:
        from quill.core.bw_providers import get_provider as bw_get_provider
        from quill.core.bw_providers import recommended_provider_id as bw_recommended_provider_id

        provider_id = bw_recommended_provider_id(local_first=self._bw_local_first_mode())
        self.settings.bw_provider_id = provider_id
        save_settings(self.settings)
        provider = bw_get_provider(provider_id, include_cloud=True)
        provider_name = provider.name if provider is not None else provider_id
        self._set_status(f"Recommended provider selected: {provider_name}")

    def select_bw_provider(self) -> None:
        from quill.core.bw_providers import list_providers as bw_list_providers

        providers = bw_list_providers(include_cloud=self._bw_include_cloud_providers())
        if not providers:
            self._set_status("No providers available for current provider visibility settings")
            return
        labels = [f"{provider.name} ({provider.provider_type})" for provider in providers]
        dialog = self._wx.SingleChoiceDialog(
            self.frame,
            "Select a provider to stage for upcoming BITS Whisperer phases.",
            "BITS Whisperer Provider Selection",
            labels,
        )
        apply_modal_ids(dialog, affirmative_id=self._wx.ID_OK, escape_id=self._wx.ID_CANCEL)
        try:
            if (
                self._show_modal_dialog(dialog, "BITS Whisperer Provider Selection")
                != self._wx.ID_OK
            ):
                return
            selection = dialog.GetSelection()
        finally:
            dialog.Destroy()

        if selection < 0 or selection >= len(providers):
            return
        selected = providers[selection]
        self.settings.bw_provider_id = selected.id
        save_settings(self.settings)
        self._set_status(f"Selected provider: {selected.name}")

    def show_bw_provider_status(self) -> None:
        from quill.core.bw_providers import get_provider as bw_get_provider
        from quill.core.bw_providers import provider_mode_guidance as bw_provider_mode_guidance
        from quill.core.bw_providers import provider_readiness as bw_provider_readiness
        from quill.core.bw_providers import recommended_provider_id as bw_recommended_provider_id

        provider_id = str(getattr(self.settings, "bw_provider_id", "local_whisper"))
        local_first = self._bw_local_first_mode()
        include_cloud = self._bw_include_cloud_providers()
        provider = bw_get_provider(provider_id, include_cloud=include_cloud)
        readiness = bw_provider_readiness(provider_id, local_first=local_first)
        recommended_id = bw_recommended_provider_id(local_first=local_first)
        recommended = bw_get_provider(recommended_id, include_cloud=True)
        mode_name = "Local-first" if local_first else "Cloud-first"
        lines = [
            "BITS Whisperer Provider Status",
            "",
            bw_provider_mode_guidance(local_first=local_first),
            f"Provider mode: {mode_name}",
            f"Cloud providers visible: {'Yes' if include_cloud else 'No'}",
            f"Configured provider: {provider.name if provider else provider_id}",
            f"Recommended provider: {recommended.name if recommended else recommended_id}",
            "",
            f"Readiness: {'Ready' if readiness.ready else 'Needs setup'}",
            readiness.summary,
            "",
            "Next steps:",
        ]
        lines.extend(f"- {step}" for step in readiness.next_steps)
        lines.append("")
        lines.append(
            "Providers are staged intentionally in this phase; "
            "runtime provider routing remains gated."
        )
        self._show_message_box("\n".join(lines), "BITS Whisperer Providers", self._wx.OK)
        self._set_status("BITS Whisperer provider status shown")

    def open_bw_provider_center(self) -> None:
        actions = [
            "Use recommended provider",
            "Select provider manually",
            "Show provider status",
            "Switch to local-first mode",
            "Switch to cloud-first mode",
            "Toggle cloud provider visibility",
        ]
        dialog = self._wx.SingleChoiceDialog(
            self.frame,
            "Choose a guided provider setup action.",
            "BITS Whisperer Provider Center",
            actions,
        )
        apply_modal_ids(dialog, affirmative_id=self._wx.ID_OK, escape_id=self._wx.ID_CANCEL)
        try:
            if self._show_modal_dialog(dialog, "BITS Whisperer Provider Center") != self._wx.ID_OK:
                return
            action = actions[dialog.GetSelection()]
        finally:
            dialog.Destroy()

        if action == "Use recommended provider":
            self.apply_bw_recommended_provider()
            return
        if action == "Select provider manually":
            self.select_bw_provider()
            return
        if action == "Show provider status":
            self.show_bw_provider_status()
            return
        if action == "Switch to local-first mode":
            self.settings.bw_provider_mode = "local_first"
            save_settings(self.settings)
            self._set_status("Provider mode set to local-first")
            return
        if action == "Switch to cloud-first mode":
            self.settings.bw_provider_mode = "cloud_first"
            save_settings(self.settings)
            self._set_status("Provider mode set to cloud-first")
            return
        if action == "Toggle cloud provider visibility":
            self.settings.bw_show_cloud_providers = not self._bw_include_cloud_providers()
            save_settings(self.settings)
            state_text = "enabled" if self.settings.bw_show_cloud_providers else "disabled"
            self._set_status(f"Cloud provider visibility {state_text}")
            return

    def _bw_readiness_snapshot(self) -> dict[str, object]:
        from quill.core.bw_providers import get_provider as bw_get_provider
        from quill.core.bw_providers import provider_readiness as bw_provider_readiness
        from quill.core.bw_providers import recommended_provider_id as bw_recommended_provider_id
        from quill.core.bw_speech import downloaded_model_ids as bw_downloaded_model_ids
        from quill.core.bw_speech import faster_whisper_status
        from quill.core.bw_speech import list_models as bw_list_models
        from quill.core.bw_speech import machine_guidance as bw_machine_guidance

        local_first = self._bw_local_first_mode()
        provider_id = str(getattr(self.settings, "bw_provider_id", "local_whisper"))
        provider = bw_get_provider(provider_id, include_cloud=True)
        readiness = bw_provider_readiness(provider_id, local_first=local_first)
        recommended_provider_id = bw_recommended_provider_id(local_first=local_first)
        recommended_provider = bw_get_provider(recommended_provider_id, include_cloud=True)
        downloaded_ids = bw_downloaded_model_ids()
        available_model_count = len(bw_list_models())
        engine_ok, engine_status = faster_whisper_status()
        return {
            "provider_mode": "local_first" if local_first else "cloud_first",
            "provider_id": provider_id,
            "provider_name": provider.name if provider is not None else provider_id,
            "recommended_provider_id": recommended_provider_id,
            "recommended_provider_name": (
                recommended_provider.name
                if recommended_provider is not None
                else recommended_provider_id
            ),
            "provider_ready": readiness.ready,
            "provider_summary": readiness.summary,
            "provider_next_steps": list(readiness.next_steps),
            "speech_model_mode": str(
                getattr(self.settings, "bw_speech_selection_mode", "recommended")
            ),
            "speech_model_id": str(getattr(self.settings, "bw_speech_model_id", "whisper-base")),
            "safe_mode_lock": self._bw_safe_mode_locked(),
            "downloaded_model_count": len(downloaded_ids),
            "available_model_count": available_model_count,
            "downloaded_model_ids": sorted(downloaded_ids),
            "engine_ready": engine_ok,
            "engine_status": engine_status,
            "machine_guidance": bw_machine_guidance(),
        }

    def _bw_diagnostics_snapshot(self) -> dict[str, object]:
        snapshot = self._bw_readiness_snapshot()
        snapshot["download_status"] = {
            model_id: {
                "model": str(entry.get("model", "")),
                "status": str(entry.get("status", "")),
                "progress": str(entry.get("progress", "")),
                "started_at": str(entry.get("started_at", "")),
                "finished_at": str(entry.get("finished_at", "")),
            }
            for model_id, entry in sorted(self._bw_download_status.items())
        }
        return snapshot

    def show_bw_readiness_check(self) -> None:
        snapshot = self._bw_readiness_snapshot()
        lines = [
            "BITS Whisperer Readiness Check",
            "",
            str(snapshot["machine_guidance"]),
            f"Provider mode: {snapshot['provider_mode']}",
            f"Configured provider: {snapshot['provider_name']}",
            f"Recommended provider: {snapshot['recommended_provider_name']}",
            f"Provider readiness: {'Ready' if snapshot['provider_ready'] else 'Needs setup'}",
            str(snapshot["provider_summary"]),
            f"Speech mode: {snapshot['speech_model_mode']}",
            f"Configured speech model: {snapshot['speech_model_id']}",
            f"Safe mode lock: {'Enabled' if snapshot['safe_mode_lock'] else 'Disabled'}",
            (
                "Downloaded whisper models: "
                f"{snapshot['downloaded_model_count']} of {snapshot['available_model_count']}"
            ),
            f"faster-whisper engine: {'Ready' if snapshot['engine_ready'] else 'Not installed'}",
            str(snapshot["engine_status"]),
            "",
            "Next steps:",
        ]
        lines.extend(f"- {step}" for step in snapshot["provider_next_steps"])
        self._show_message_box("\n".join(lines), "BITS Whisperer Readiness", self._wx.OK)
        self._set_status("BITS Whisperer readiness check complete")

    def show_bw_capability_matrix_page(self) -> None:
        from quill.ui.info_pages import show_bw_capability_matrix_native

        snapshot = self._bw_readiness_snapshot()
        rows = [
            (
                "Whisper model acquisition",
                "Phase 1",
                "Ready"
                if bool(snapshot["engine_ready"]) and int(snapshot["downloaded_model_count"]) > 0
                else "In setup",
                "Download and stage whisper models from the BITS Whisperer menu.",
            ),
            (
                "Provider onboarding",
                "Phase 1",
                "Ready" if bool(snapshot["provider_ready"]) else "In setup",
                "Use Provider Center and Readiness Check for safe staged onboarding.",
            ),
            (
                "Dynamic status monitoring",
                "Phase 1",
                "Ready",
                "Help Status Page refreshes live with accessibility-aware cadence controls.",
            ),
            (
                "Runtime provider routing",
                "Phase 2",
                "Gated",
                "Cloud and advanced routing behavior is delayed until validation is complete.",
            ),
        ]
        show_bw_capability_matrix_native(
            self.frame, self._wx, rows, snapshot, self._show_modal_dialog
        )
        self._set_status("Opened BITS Whisperer capability matrix")

    def _start_bw_model_download(self, spec: object) -> None:
        from quill.core.bw_speech import download_model as bw_download_model

        if self._bw_safe_mode_locked():
            self._show_message_box(
                "BITS Whisperer safe mode lock is enabled. Disable it in Preferences -> General "
                "to allow model downloads.",
                "BITS Whisperer Safe Mode",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            self._set_status("BITS Whisperer safe mode lock blocked model download")
            return
        model_id = str(getattr(spec, "id", ""))
        model_name = str(getattr(spec, "name", model_id))
        started_at = datetime.now(UTC).isoformat()
        self._set_bw_download_status(
            model_id,
            model_name=model_name,
            status="running",
            progress="Starting",
            started_at=started_at,
        )

        def work(progress: Callable[[str, int, int], None]) -> object:
            def _progress(done: int, total: int) -> None:
                total_display = total if total > 0 else 0
                self._wx.CallAfter(
                    self._set_bw_download_status,
                    model_id,
                    model_name=model_name,
                    status="running",
                    progress=f"{done}/{total_display}",
                    started_at=started_at,
                )
                progress("Downloading model", done, total)

            try:
                return bw_download_model(spec, progress=_progress)
            except Exception:
                self._wx.CallAfter(
                    self._set_bw_download_status,
                    model_id,
                    model_name=model_name,
                    status="failed",
                    progress="Failed",
                    started_at=started_at,
                    finished_at=datetime.now(UTC).isoformat(),
                )
                raise

        def on_success(_result: object) -> None:
            self._set_bw_download_status(
                model_id,
                model_name=model_name,
                status="completed",
                progress="Completed",
                started_at=started_at,
                finished_at=datetime.now(UTC).isoformat(),
            )
            self._set_status(f"Downloaded {model_name}. Check Help -> Status Page for details.")

        self._run_background_task(
            f"BITS Whisperer model download: {model_name}",
            work,
            on_success,
            notify_on_success=True,
            notify_on_error=True,
            notification_category="speech",
        )
        if bool(
            getattr(
                self.settings,
                "bw_auto_open_status_page_on_download_start",
                False,
            )
        ):
            self.show_help_status_page()
        self._set_status(f"Started background download for {model_name}")

    def manage_bw_download_queue(self) -> None:
        from quill.core.bw_speech import get_model as bw_get_model

        actions = [
            "Open live status page",
            "Retry failed download",
            "Clear completed and failed download history",
        ]
        dialog = self._wx.SingleChoiceDialog(
            self.frame,
            "Choose a download queue action.",
            "BITS Whisperer Download Queue",
            actions,
        )
        apply_modal_ids(dialog, affirmative_id=self._wx.ID_OK, escape_id=self._wx.ID_CANCEL)
        try:
            if self._show_modal_dialog(dialog, "BITS Whisperer Download Queue") != self._wx.ID_OK:
                return
            action = actions[dialog.GetSelection()]
        finally:
            dialog.Destroy()

        if action == "Open live status page":
            self.show_help_status_page()
            return

        if action == "Retry failed download":
            if self._bw_safe_mode_locked():
                self._show_message_box(
                    "BITS Whisperer safe mode lock is enabled. Disable it in Preferences -> "
                    "General to allow download retries.",
                    "BITS Whisperer Safe Mode",
                    self._wx.ICON_INFORMATION | self._wx.OK,
                )
                self._set_status("BITS Whisperer safe mode lock blocked download retry")
                return
            failed_ids = [
                model_id
                for model_id, entry in self._bw_download_status.items()
                if str(entry.get("status", "")).lower() == "failed"
            ]
            if not failed_ids:
                self._set_status("No failed BITS Whisperer downloads to retry")
                return
            failed_choices = [
                f"{model_id} ({self._bw_download_status[model_id].get('model', model_id)})"
                for model_id in failed_ids
            ]
            retry_dialog = self._wx.SingleChoiceDialog(
                self.frame,
                "Choose a failed model download to retry.",
                "Retry Download",
                failed_choices,
            )
            apply_modal_ids(
                retry_dialog,
                affirmative_id=self._wx.ID_OK,
                escape_id=self._wx.ID_CANCEL,
            )
            try:
                if self._show_modal_dialog(retry_dialog, "Retry Download") != self._wx.ID_OK:
                    return
                selection = retry_dialog.GetSelection()
            finally:
                retry_dialog.Destroy()
            if selection < 0 or selection >= len(failed_ids):
                return
            model_id = failed_ids[selection]
            spec = bw_get_model(model_id)
            if spec is None:
                self._set_status(f"Could not retry; model no longer available: {model_id}")
                return
            self._start_bw_model_download(spec)
            return

        if action == "Clear completed and failed download history":
            self._bw_download_status = {
                model_id: entry
                for model_id, entry in self._bw_download_status.items()
                if str(entry.get("status", "")).lower() == "running"
            }
            self._maybe_refresh_live_status_tabs()
            self._set_status("Cleared completed and failed BITS Whisperer download history")
            return

    def open_bw_model_manager(self) -> None:
        from quill.core.bw_speech import downloaded_model_ids as bw_downloaded_model_ids
        from quill.core.bw_speech import get_model as bw_get_model
        from quill.core.bw_speech import has_disk_capacity as bw_has_disk_capacity
        from quill.core.bw_speech import list_models as bw_list_models
        from quill.core.bw_speech import machine_guidance as bw_machine_guidance
        from quill.core.bw_speech import recommended_model_id as bw_recommended_model_id
        from quill.core.bw_speech import remove_model as bw_remove_model

        models = bw_list_models()
        downloaded = bw_downloaded_model_ids()
        recommended = bw_recommended_model_id()

        quick_actions = [
            "Use recommended model",
            "Choose model manually",
            "Show model status",
            "Check faster-whisper engine",
        ]
        quick_dialog = self._wx.SingleChoiceDialog(
            self.frame,
            (f"{bw_machine_guidance()}\n\nSelect a guided action for speech model setup."),
            "BITS Whisperer Speech Setup",
            quick_actions,
        )
        apply_modal_ids(
            quick_dialog,
            affirmative_id=self._wx.ID_OK,
            escape_id=self._wx.ID_CANCEL,
        )
        try:
            if (
                self._show_modal_dialog(quick_dialog, "BITS Whisperer Speech Setup")
                != self._wx.ID_OK
            ):
                return
            quick_action = quick_actions[quick_dialog.GetSelection()]
        finally:
            quick_dialog.Destroy()

        if quick_action == "Use recommended model":
            self.apply_bw_recommended_model()
            return
        if quick_action == "Show model status":
            self.show_bw_model_status()
            return
        if quick_action == "Check faster-whisper engine":
            self.check_bw_faster_whisper_engine()
            return

        choices: list[str] = []
        model_ids: list[str] = []
        for spec in models:
            markers: list[str] = []
            if spec.id in downloaded:
                markers.append("downloaded")
            if spec.id == recommended:
                markers.append("recommended")
            marker_text = f" [{' | '.join(markers)}]" if markers else ""
            choices.append(f"{spec.name} ({spec.family}){marker_text}")
            model_ids.append(spec.id)

        dialog = self._wx.SingleChoiceDialog(
            self.frame,
            "Choose a speech model to configure.",
            "BITS Whisperer Speech Models",
            choices,
        )
        apply_modal_ids(dialog, affirmative_id=self._wx.ID_OK, escape_id=self._wx.ID_CANCEL)
        try:
            if self._show_modal_dialog(dialog, "BITS Whisperer Speech Models") != self._wx.ID_OK:
                return
            selection = dialog.GetSelection()
        finally:
            dialog.Destroy()

        if selection < 0 or selection >= len(model_ids):
            return

        model_id = model_ids[selection]
        spec = bw_get_model(model_id)
        if spec is None:
            return

        actions = ["Set as default", "Show status"]
        is_present = spec.id in downloaded
        if is_present:
            actions.insert(1, "Remove downloaded model")
        else:
            actions.insert(1, "Download model")

        action_dialog = self._wx.SingleChoiceDialog(
            self.frame,
            (
                f"{spec.name}\n\n{spec.description}\n"
                f"Approx size: {spec.approx_size_gb:.2f} GB\n"
                f"Minimum RAM: {spec.min_ram_gb} GB"
            ),
            "BITS Whisperer Model Action",
            actions,
        )
        apply_modal_ids(
            action_dialog,
            affirmative_id=self._wx.ID_OK,
            escape_id=self._wx.ID_CANCEL,
        )
        try:
            if (
                self._show_modal_dialog(action_dialog, "BITS Whisperer Model Action")
                != self._wx.ID_OK
            ):
                return
            action = actions[action_dialog.GetSelection()]
        finally:
            action_dialog.Destroy()

        if action == "Set as default":
            self.settings.bw_speech_selection_mode = "manual"
            self.settings.bw_speech_model_id = spec.id
            save_settings(self.settings)
            self._set_status(f"Manual mode active. Default speech model set to {spec.name}")
            return

        if action == "Download model":
            if not bw_has_disk_capacity(spec):
                self._show_message_box(
                    "Not enough disk space for this model plus safety buffer.",
                    "BITS Whisperer Speech Models",
                    self._wx.ICON_WARNING | self._wx.OK,
                )
                self._set_status("Speech model download blocked by disk space check")
                return
            self._start_bw_model_download(spec)
            return

        if action == "Remove downloaded model":
            if bw_remove_model(spec):
                self._set_status(f"Removed downloaded model {spec.name}")
            else:
                self._set_status(f"Model was not downloaded: {spec.name}")
            return

        if action == "Show status":
            self.show_bw_model_status()

    def _on_dictation_state_change(self, state: str) -> None:
        if state == "listening":
            self._set_status("System dictation started. Speak into the editor.")
        else:
            self._set_status("System dictation stopped")

    def _on_dictation_error(self, error_msg: str) -> None:
        self._set_status("System dictation error")
