"""The Speech Hub and the read-aloud voice downloads on QUILL's main window.

Moved whole out of ``MainFrame`` (todo D.4, 2026-10-17): opening the unified
Speech Hub (Speech and Dictation, each split Offline and Online), applying its
result, and the Piper voice and Kokoro model downloads it starts. The host
contract is unchanged: same ``self`` attributes, same command ids, keys,
dialogs and announcements.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from quill.core.read_aloud import default_piper_model_dir
from quill.core.settings import save_settings


class SpeechHubMixin:
    """The Speech Hub and its voice downloads; mixed into ``MainFrame``."""

    # ------------------------------------------------------------------
    # Voice preview and settings for the supported read-aloud engines
    # ------------------------------------------------------------------

    _PREVIEW_TEXT = (
        "QUILL is where your words come to life, turning quiet thoughts into "
        "finished pages with a little sprinkle of everyday magic."
    )

    def choose_read_aloud_configuration(self) -> None:
        """Open the unified Speech Hub on the Speech (Offline) tab."""
        from quill.ui.speech_hub_dialog import TAB_SPEECH_OFFLINE

        self.open_speech_hub(TAB_SPEECH_OFFLINE)

    def open_speech_hub(self, initial_tab: int = 0) -> None:  # noqa: PLR0912,PLR0915
        """Open the unified Speech Hub dialog: Speech and Dictation, each split
        into Offline/Online tabs (local engines vs. API-key cloud providers,
        #847)."""
        from quill.core.read_aloud import (
            discover_dectalk_executable,
            discover_espeak_executable,
            discover_piper_executable,
            kokoro_engine_ready,
            macos_say_available,
        )
        from quill.core.speech.engine_install import (
            is_faster_whisper_available,
            is_kokoro_onnx_available,
            kokoro_onnx_install_supported,
        )
        from quill.core.speech.ffmpeg import ffmpeg_available
        from quill.core.speech.providers.whispercpp import resolve_whisper_executable
        from quill.core.speech.service import (
            describe_models,
            detect_has_gpu,
            detect_total_ram_gb,
            dictation_providers,
            machine_summary,
        )
        from quill.ui.speech_hub_dialog import SpeechHubDialog

        wx = self._wx

        # --- Speech (Read Aloud) kwargs, split Offline/Online ---
        from quill.core.ai import elevenlabs_tts

        elevenlabs_ready = (
            bool(self._get_elevenlabs_api_key().strip()) and elevenlabs_tts.available()
        )
        offline_engine_options: list[tuple[str, str]] = [
            ("Windows (SAPI 5)", "sapi5"),
            ("DECtalk", "dectalk"),
            ("Piper (neural, offline)", "piper"),
            ("Kokoro (neural, offline)", "kokoro"),
            ("eSpeak-NG (many languages)", "espeak"),
        ]
        if macos_say_available():
            # macOS system voice via the say CLI — only offered on macOS (#21/#75).
            offline_engine_options.append(("macOS (system voice)", "macos"))
        online_engine_options: list[tuple[str, str]] = [
            ("ElevenLabs (premium cloud)", "elevenlabs"),
        ]
        offline_engine_available = {
            "sapi5": True,
            "dectalk": discover_dectalk_executable(self.settings.read_aloud_dectalk_executable)
            is not None,
            "piper": discover_piper_executable() is not None,
            "kokoro": kokoro_engine_ready(),
            "espeak": discover_espeak_executable(self.settings.read_aloud_espeak_executable)
            is not None,
            "macos": macos_say_available(),
        }
        online_engine_available = {"elevenlabs": elevenlabs_ready}
        configured_engine = self.settings.read_aloud_engine.strip().lower() or "sapi5"
        offline_current_engine = (
            configured_engine
            if configured_engine in {val for _, val in offline_engine_options}
            else "sapi5"
        )
        common_ra_kwargs: dict = {
            "piper_model_dir": default_piper_model_dir(),
            "settings": self.settings,
            "preview_fn": self._preview_voice,
            "preview_stop_fn": self._stop_active_voice_preview,
            "elevenlabs_api_key": self._get_elevenlabs_api_key() if elevenlabs_ready else "",
            "has_preview_sample": (
                lambda eng, vid: self._voice_preview_sample_path(eng, vid) is not None
            ),
        }
        read_aloud_offline_kwargs: dict = {
            "engine_options": offline_engine_options,
            "current_engine": offline_current_engine,
            "engine_available": offline_engine_available,
            **common_ra_kwargs,
        }
        read_aloud_online_kwargs: dict = {
            "engine_options": online_engine_options,
            "current_engine": "elevenlabs",
            "engine_available": online_engine_available,
            **common_ra_kwargs,
        }

        # --- Dictation kwargs, split Offline/Online ---
        registry = self._speech_registry()
        # Show every *registered* engine, not just the ones usable right now
        # (#514/#669 model-manager): an engine whose runtime isn't installed yet
        # — notably whisper.cpp when its binary is missing — must still appear in
        # the chooser, labelled "(not installed)", so the user can discover it and
        # reach its guided install path instead of having it silently disappear.
        # Chapter-only engines (Vosk) are never a dictation choice.
        all_providers = dictation_providers(registry.all())  # type: ignore[attr-defined]
        provider = self._configured_speech_provider(registry)  # saved engine, not avail-fallback
        total_ram = detect_total_ram_gb()
        has_gpu = detect_has_gpu()
        rows = describe_models(provider, total_ram, has_gpu)  # type: ignore[arg-type]
        common_dict_kwargs: dict = {
            "machine_summary": machine_summary(total_ram, has_gpu),
            "whispercpp_ok": resolve_whisper_executable() is not None,
            "ffmpeg_ok": ffmpeg_available(),
            "engine_ok": is_faster_whisper_available(),
            "kokoro_ok": is_kokoro_onnx_available(),
            "kokoro_can_install": kokoro_onnx_install_supported(),
            "all_providers": all_providers,
            "total_ram": total_ram,
            "has_gpu": has_gpu,
            "default_provider_id": str(getattr(self.settings, "speech_provider", "") or ""),
            "announce_cb": self._announce,
        }
        dictation_offline_kwargs: dict = {
            "provider": provider,
            "rows": rows,
            "engine_scope": "offline",
            **common_dict_kwargs,
        }
        known_offline_ids = {"whispercpp", "fasterwhisper"}
        cloud_providers = [
            p for p in all_providers if str(getattr(p, "id", "")) not in known_offline_ids
        ]
        dictation_online_kwargs: dict | None = None
        if cloud_providers:
            cloud_provider = (
                next((p for p in cloud_providers if getattr(p, "id", "") == provider.id), None)
                or cloud_providers[0]
            )
            dictation_online_kwargs = {
                "provider": cloud_provider,
                "rows": describe_models(cloud_provider, total_ram, has_gpu),  # type: ignore[arg-type]
                "engine_scope": "online",
                **common_dict_kwargs,
            }

        hub = SpeechHubDialog(
            self.frame,
            read_aloud_offline_kwargs=read_aloud_offline_kwargs,
            read_aloud_online_kwargs=read_aloud_online_kwargs,
            dictation_offline_kwargs=dictation_offline_kwargs,
            dictation_online_kwargs=dictation_online_kwargs,
            initial_tab=initial_tab,
        )
        ra_result, dict_result = hub.show(self._show_modal_dialog)

        # --- Handle Read Aloud result ---
        if ra_result is not None:
            # Downloads open a non-modal progress dialog. The hub modal is still
            # tearing down here, so creating it inline lets focus snap back to the
            # editor and the screen reader never announces the progress window
            # (the user is "thrown back to the document with no notification").
            # Deferring with CallAfter runs the download after the modal fully
            # closes, so the progress dialog presents and is announced.
            if ra_result.action == "download":
                if ra_result.engine == "piper":
                    wx.CallAfter(self._download_piper_voice, ra_result.voice_id)
                elif ra_result.engine == "kokoro":
                    wx.CallAfter(self._download_kokoro_models)
            elif ra_result.action == "download_engine":
                if ra_result.engine == "dectalk":
                    wx.CallAfter(self.download_dectalk_exe)
                elif ra_result.engine == "piper":
                    wx.CallAfter(self.download_piper_exe)
                elif ra_result.engine == "espeak":
                    wx.CallAfter(self.download_espeak_exe)
            else:  # 'select' or 'export'
                eng = ra_result.engine
                piper_dir = default_piper_model_dir()
                self.settings.read_aloud_engine = eng
                if ra_result.voice_id:
                    if eng == "dectalk":
                        self.settings.read_aloud_dectalk_voice = ra_result.voice_id
                    elif eng == "piper":
                        onnx_path = piper_dir / f"{ra_result.voice_id}.onnx"
                        if onnx_path.exists():
                            self.settings.read_aloud_piper_model = str(onnx_path)
                        else:
                            self._show_message_box(
                                f"'{ra_result.voice_id}' is not downloaded yet.\n"
                                "Use the Download Voice button to fetch it first.",
                                "Speech Settings",
                                wx.ICON_INFORMATION | wx.OK,
                            )
                            self.settings.read_aloud_engine = offline_current_engine
                            dict_result = None  # skip dictation processing
                    elif eng == "kokoro":
                        self.settings.read_aloud_kokoro_voice = ra_result.voice_id
                    elif eng == "espeak":
                        self.settings.read_aloud_espeak_voice = ra_result.voice_id
                    elif eng == "macos":
                        self.settings.read_aloud_macos_voice = ra_result.voice_id
                    elif eng == "elevenlabs":
                        self.settings.read_aloud_elevenlabs_voice = ra_result.voice_id
                    else:
                        self.settings.read_aloud_voice = ra_result.voice_id
                if eng == "sapi5":
                    self.settings.read_aloud_rate = ra_result.rate
                    self.settings.read_aloud_volume = ra_result.volume
                    self.settings.read_aloud_pitch = ra_result.pitch
                elif eng == "dectalk":
                    self.settings.read_aloud_dectalk_rate = ra_result.dectalk_rate
                elif eng == "espeak":
                    self.settings.read_aloud_espeak_rate = ra_result.espeak_rate
                elif eng == "macos":
                    self.settings.read_aloud_macos_rate = ra_result.macos_rate
                elif eng == "kokoro":
                    self.settings.read_aloud_kokoro_speed = ra_result.kokoro_speed
                save_settings(self.settings)
                engine_label = dict(offline_engine_options + online_engine_options).get(eng, eng)
                self._set_status(f"Read aloud configured: {engine_label}")
                if ra_result.action == "export":
                    self.generate_speech_audio()

        # --- Handle Dictation result ---
        if dict_result is not None:
            chosen_provider_id = dict_result.provider_id or ""
            if chosen_provider_id and chosen_provider_id != str(
                getattr(self.settings, "speech_provider", "") or ""
            ):
                chosen = registry.get(chosen_provider_id)  # type: ignore[attr-defined]
                if chosen is not None:
                    provider = chosen
                    self.settings.speech_provider = chosen_provider_id
                    try:
                        save_settings(self.settings)
                    except Exception:  # noqa: BLE001
                        pass
                    self._announce(
                        f"Speech engine set to {provider.display_name}."  # type: ignore[attr-defined]
                    )
            if dict_result.action == "download" and dict_result.model_row is not None:
                self._maybe_download_speech_model(provider, dict_result.model_row)
            elif dict_result.action == "remove" and dict_result.model_id:
                self._maybe_remove_speech_model(provider, dict_result.model_id)
            elif dict_result.action == "ffmpeg":
                self.download_ffmpeg()
            elif dict_result.action == "engine":
                self.download_faster_whisper()
            elif dict_result.action == "hf_token":
                self.set_huggingface_token()
            elif dict_result.action == "test":
                # Prove the selected engine (SAPI clip -> transcribe), speaking and
                # logging the result; the provider_id block above already made it
                # the default, so a successful Test doubles as "use this engine".
                test_id = dict_result.provider_id or getattr(provider, "id", "")
                self._test_optional_component(test_id)
            elif dict_result.action == "set_default" and dict_result.model_id:
                self.settings.speech_default_model_id = dict_result.model_id
                save_settings(self.settings)
                self._announce(f"{dict_result.model_id} set as the default speech model.")

    def _download_piper_voice(self, voice_id: str) -> None:
        """Download a Piper ONNX voice model in the background."""
        from quill.core.voice_catalog import piper_voice_download_urls
        from quill.ui.ai_transcribe_dialog import AIProgressDialog

        wx = self._wx
        piper_dir = default_piper_model_dir()
        urls = piper_voice_download_urls(voice_id)
        if urls is None:
            self._show_message_box(
                f"Cannot determine download URL for: {voice_id}",
                "Download Piper Voice",
                wx.ICON_WARNING | wx.OK,
            )
            return
        onnx_path = piper_dir / f"{voice_id}.onnx"
        json_path = piper_dir / f"{voice_id}.onnx.json"
        if onnx_path.exists() and json_path.exists():
            self._set_status(f"Piper voice '{voice_id}' is already downloaded.")
            self.choose_read_aloud_configuration()
            return
        # Offline Edition: a staged starter voice installs with no network at
        # all (same destination the download below would use).
        from quill.core.speech.piper_install import install_bundled_piper_voice

        if install_bundled_piper_voice(voice_id, dest_dir=piper_dir) is not None:
            self._set_status(f"Piper voice '{voice_id}' installed from the offline bundle.")
            self.choose_read_aloud_configuration()
            return
        piper_dir.mkdir(parents=True, exist_ok=True)

        cancel = threading.Event()
        progress = AIProgressDialog(
            self.frame,
            f"Downloading Piper voice: {voice_id}",
            "Preparing download...",
            on_cancel=cancel.set,
        )
        progress.show()
        self._announce(f"Downloading Piper voice {voice_id}.")

        def _run(_vid: str = voice_id) -> None:
            from quill.core.speech.piper_install import download_piper_voice

            try:
                # Mirror-first (assets-v1, SHA-verified), upstream files as fallback.
                download_piper_voice(
                    _vid,
                    piper_dir,
                    progress=lambda fr, msg: wx.CallAfter(
                        progress.set_progress, int(fr * 100), msg
                    ),
                    should_cancel=cancel.is_set,
                )
            except Exception as exc:  # noqa: BLE001
                wx.CallAfter(progress.close)
                if cancel.is_set():
                    wx.CallAfter(self._set_status, "Piper voice download cancelled.")
                else:
                    wx.CallAfter(self._set_status, f"Piper voice download failed: {exc}")
                return
            done_msg = (
                f"Piper voice '{_vid}' is ready. Click OK to open Manage Voices and select it."
            )
            wx.CallAfter(self._set_status, f"Piper voice '{_vid}' downloaded.")
            wx.CallAfter(self._announce, f"Piper voice {_vid} downloaded.")
            progress.switch_to_ok(done_msg, on_ok=self.choose_read_aloud_configuration)

        threading.Thread(  # GATE-40-OK: Piper voice download worker.
            target=_run, daemon=True
        ).start()

    def _download_kokoro_models(self, *, on_done: Callable[[bool], None] | None = None) -> None:
        """Fetch the Kokoro ONNX model + voices from QUILL's verified release asset,
        then ensure the kokoro-onnx package is installed (Kokoro unbundle, PRD 10.2.4).

        Kokoro is no longer bundled in fresh installers; this downloads it on demand
        into the user data dir, which the runtime prefers. The download is pinned +
        SHA-256-verified via quill.core.release_assets, runs on a worker thread behind
        a cancelable percentage, and is blocked in Safe Mode. Users upgrading from a
        release that bundled Kokoro keep their {app}/kokoro-models copy, so this only
        runs when Kokoro is actually missing.
        """
        from quill.core.read_aloud import (
            KOKORO_ONNX_MODEL_FILENAME,
            KOKORO_ONNX_VOICES_FILENAME,
            default_kokoro_model_dir,
            kokoro_onnx_ready,
        )
        from quill.ui.ai_transcribe_dialog import AIProgressDialog

        wx = self._wx
        dest_dir = default_kokoro_model_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        model_path = dest_dir / KOKORO_ONNX_MODEL_FILENAME
        voices_path = dest_dir / KOKORO_ONNX_VOICES_FILENAME

        # Smart re-download: if the voices are already present, don't silently
        # re-fetch ~120 MB -- offer to replace them. Declining keeps the existing
        # copy (and just finishes the package step if needed). Re-fetching only
        # happens when the user opts in. (#kokoro-replace)
        force = True
        if model_path.exists() and voices_path.exists():
            from quill.core.speech.engine_install import is_kokoro_onnx_available

            again = self._show_message_box(
                "The Kokoro voices are already downloaded. Download a fresh copy "
                "(replace what you have)?",
                "Download Kokoro",
                wx.ICON_QUESTION | wx.YES_NO,
            )
            if again != wx.YES:
                force = False  # keep the existing files
                if kokoro_onnx_ready() and is_kokoro_onnx_available():
                    # _set_status already speaks; a second _announce of the same
                    # text would double-speak it (#728).
                    self._set_status("Kokoro is already installed.")
                    return

        cancel = threading.Event()
        progress = AIProgressDialog(
            self.frame,
            "Downloading Kokoro Models",
            "Preparing download...",
            on_cancel=cancel.set,
        )
        progress.show()
        self._announce("Downloading Kokoro models.")

        def _run() -> None:
            try:
                from quill.core.release_assets import fetch_component
                from quill.core.speech.engine_install import (
                    install_kokoro_onnx,
                    is_kokoro_onnx_available,
                )

                if force or not (model_path.exists() and voices_path.exists()):
                    # Reserve 0-80% for the model + voices, 80-100% for the package.
                    def _model_progress(frac: float, msg: str) -> None:
                        wx.CallAfter(progress.set_progress, int(frac * 80), msg)

                    fetch_component(
                        "kokoro",
                        dest_dir,
                        progress=_model_progress,
                        should_cancel=cancel.is_set,
                        label="Downloading Kokoro voices...",
                    )
                if not is_kokoro_onnx_available():

                    def _pkg_progress(frac: float, msg: str) -> None:
                        wx.CallAfter(progress.set_progress, 80 + int(frac * 20), msg)

                    # GATE-40-OK: Kokoro engine install worker.
                    install_kokoro_onnx(progress=_pkg_progress)
            except Exception as exc:  # noqa: BLE001
                wx.CallAfter(progress.close)
                if cancel.is_set():
                    wx.CallAfter(self._set_status, "Kokoro download cancelled.")
                else:
                    wx.CallAfter(self._set_status, f"Kokoro download failed: {exc}")
                return
            if kokoro_onnx_ready():
                done_msg = "Kokoro is ready. Click OK to open Manage Voices and select a voice."
                wx.CallAfter(self._set_status, "Kokoro ready.")
                wx.CallAfter(self._announce, "Kokoro models downloaded.")
                progress.switch_to_ok(
                    done_msg,
                    on_ok=(lambda: on_done(True))
                    if on_done
                    else self.choose_read_aloud_configuration,
                )
            else:
                wx.CallAfter(progress.close)
                wx.CallAfter(
                    self._set_status, "Kokoro download failed; check your internet connection."
                )

        threading.Thread(  # GATE-40-OK: Kokoro model download worker.
            target=_run, daemon=True
        ).start()

    def choose_read_aloud_voice(self) -> None:
        self.choose_read_aloud_configuration()

    def choose_read_aloud_settings(self) -> None:
        self.choose_read_aloud_configuration()
