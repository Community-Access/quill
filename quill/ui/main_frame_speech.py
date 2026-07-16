"""Offline speech core for MainFrame: providers, transcription, captions (#617).

A mixin on :class:`~quill.ui.main_frame.MainFrame` providing the core **AI >
Speech** wiring: the offline provider/registry accessors, model prewarm,
transcription and caption generation, microphone selection, and the speech
command registration. It uses stock, fully-accessible wx dialogs and routes
work through ``_run_background_task`` so the UI never blocks. All speech logic
lives in ``quill.core.speech``; this is thin wiring.

The model/component *download* surface (``SpeechDownloadsMixin``,
``main_frame_speech_downloads.py``) and the offline *voice interaction* surface
-- dictation, voice commands, conversation mode, Hey QUILL wake word
(``VoiceInteractionMixin``, ``main_frame_speech_voice.py``) -- were split out of
this mixin (CQ-1); all three compose onto ``MainFrame`` together.
"""

from __future__ import annotations

from pathlib import Path

# Transcribe/Captions accept these; ffmpeg transcodes them to 16 kHz mono WAV.
_AV_EXTS = "*.wav;*.mp3;*.m4a;*.aac;*.flac;*.ogg;*.opus;*.wma;*.mp4;*.m4v;*.mov;*.mkv;*.webm;*.avi"
_AUDIO_VIDEO_WILDCARD = f"Audio/Video ({_AV_EXTS})|{_AV_EXTS}|All files (*.*)|*.*"


class SpeechCommandsMixin:
    """AI > Speech command handlers (offline model manager + transcription)."""

    # Relies on MainFrame helpers: _wx, frame, settings, _show_modal_dialog,
    # _show_message_box, _run_background_task, _create_document_tab, _announce,
    # _set_status.

    def _speech_registry(self) -> object:
        from quill.core.speech.service import default_registry

        configured = str(getattr(self.settings, "speech_whisper_path", "") or "") or None
        return default_registry(configured)

    def _speech_provider(self) -> object:
        from quill.core.speech.service import DEFAULT_PROVIDER_ID

        registry = self._speech_registry()
        chosen = str(getattr(self.settings, "speech_provider", "") or "")
        if chosen:
            provider = registry.get(chosen)  # type: ignore[attr-defined]
            try:
                if provider is not None and provider.is_available():
                    return provider
            except Exception:  # noqa: BLE001 - fall back to the bundled engine
                pass
        return registry.get(DEFAULT_PROVIDER_ID)  # type: ignore[attr-defined]

    def _configured_speech_provider(self, registry: object | None = None) -> object:
        """The dictation engine the user last chose, for UI initial selection.

        Unlike :meth:`_speech_provider`, this does NOT fall back to the bundled
        default when the saved engine isn't ready yet -- so Manage Speech Models
        opens on the engine you actually picked (showing its "needs a model"
        state) instead of silently snapping back to whisper.cpp. Real dictation
        still goes through :meth:`_speech_provider`, which keeps the availability
        fallback so speech always works.

        Pass ``registry`` to resolve from a registry the caller already built, so
        the returned provider is object-identical to that registry's ``all()``
        entries (the engine radio selects by identity).
        """
        from quill.core.speech.service import DEFAULT_PROVIDER_ID

        reg = registry if registry is not None else self._speech_registry()
        chosen = str(getattr(self.settings, "speech_provider", "") or "")
        if chosen:
            provider = reg.get(chosen)  # type: ignore[attr-defined]
            if provider is not None:
                return provider
        return reg.get(DEFAULT_PROVIDER_ID)  # type: ignore[attr-defined]

    def _voice_provider(self) -> object:
        """The speech engine that powers the voice-interaction features.

        Honors ``settings.voice_recognition_engine`` — whisper.cpp for accuracy,
        Vosk for fast, low-overhead streaming (ideal for the always-listening
        wake word) — and falls back to the main speech provider when the chosen
        engine is unavailable or has no installed model, so voice always works.
        """
        chosen = str(getattr(self.settings, "voice_recognition_engine", "") or "").strip()
        if chosen:
            registry = self._speech_registry()
            provider = registry.get(chosen)  # type: ignore[attr-defined]
            try:
                if (
                    provider is not None
                    and provider.is_available()
                    and provider.list_installed_models()
                ):
                    return provider
            except Exception:  # noqa: BLE001 - fall back to the main engine
                pass
        return self._speech_provider()

    def _dictation_provider(self) -> object:
        """Cached speech provider for dictation so a loaded model persists across
        sessions (and a startup prewarm stays warm). _speech_registry() builds a
        fresh provider each call, which would reload the model every dictation.
        Rebuilt when the chosen engine changes."""
        chosen = str(getattr(self.settings, "speech_provider", "") or "")
        cached = getattr(self, "_dictation_provider_cache", None)
        if cached is not None and getattr(self, "_dictation_provider_key", None) == chosen:
            provider = cached
        else:
            provider = self._speech_provider()
            self._dictation_provider_cache = provider
            self._dictation_provider_key = chosen
        # Track for the idle-unload / low-resource policy. note_loaded registers or
        # re-touches (so it re-tracks after an idle sweep). unload() frees the model;
        # the cached provider object persists and reloads on the next dictation.
        try:
            from quill.core import lifecycle_service

            lifecycle_service.note_loaded("speech:dictation", provider.unload)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - lifecycle tracking must never break dictation
            pass
        return provider

    def invalidate_dictation_provider(self) -> None:
        """Drop the cached dictation provider (after an engine/model change)."""
        self._dictation_provider_cache = None
        try:
            from quill.core import lifecycle_service

            lifecycle_service.note_unloaded("speech:dictation")
        except Exception:  # noqa: BLE001 - lifecycle untracking must never raise
            pass

    def prewarm_dictation_model(self) -> None:
        """Load the dictation model in the background so the first dictation is
        fast. Best-effort; never blocks the UI or raises. The cached provider
        (_dictation_provider) keeps the model loaded for later dictations."""
        import threading

        if not bool(getattr(self.settings, "warm_dictation_model", True)):
            return

        def _work() -> None:
            try:
                from quill.core.speech.capture import capture_available

                if not capture_available():
                    return
                provider = self._dictation_provider()
                installed = provider.list_installed_models()  # type: ignore[attr-defined]
                warm = getattr(provider, "warm", None)
                if installed and callable(warm):
                    from quill.core import lifecycle_service

                    # Low-resource mode may evict another engine before we warm this one.
                    lifecycle_service.reserve("speech:dictation")
                    warm(self._default_model_id(installed))
                    import logging

                    logging.getLogger(__name__).info("dictation: speech model prewarmed")
            except Exception:  # noqa: BLE001 - prewarm must never break startup
                pass

        threading.Thread(target=_work, daemon=True, name="quill-dictation-prewarm").start()

    def prewarm_kokoro_model(self) -> None:
        """Warm the Kokoro ONNX model in the background so the first preview or
        read-aloud is fast. Best-effort; gated by the warm_kokoro_model setting."""
        if not bool(getattr(self.settings, "warm_kokoro_model", True)):
            return
        import threading

        def _work() -> None:
            try:
                from quill.core.read_aloud import warm_kokoro_onnx

                if warm_kokoro_onnx():
                    import logging

                    logging.getLogger(__name__).info("read-aloud: kokoro model prewarmed")
            except Exception:  # noqa: BLE001 - prewarm must never break startup
                pass

        threading.Thread(target=_work, daemon=True, name="quill-kokoro-prewarm").start()

    # -- transcription ---------------------------------------------------- #

    _TRANSCRIPT_FORMATS = (
        ("Plain text", "text"),
        ("Markdown", "markdown"),
        ("HTML", "html"),
    )

    def _select_model_and_diarize(self, installed: list) -> tuple[str, bool]:
        """Prefer an installed speaker-detection model (enables diarization)."""
        from quill.core.speech.catalog import is_diarization_model

        for model in installed:
            if is_diarization_model(model.id):
                return model.id, True
        return self._default_model_id(installed), False

    def _choose_transcript_format(self, title: str) -> str | None:
        wx = self._wx
        labels = [label for label, _key in self._TRANSCRIPT_FORMATS]
        with wx.SingleChoiceDialog(self.frame, "Transcript format:", title, labels) as dialog:
            if self._show_modal_dialog(dialog, title) != wx.ID_OK:
                return None
            choice = dialog.GetSelection()
        if 0 <= choice < len(self._TRANSCRIPT_FORMATS):
            return self._TRANSCRIPT_FORMATS[choice][1]
        return "text"

    def transcribe_audio_offline(self) -> None:
        wx = self._wx
        provider = self._speech_provider()
        installed = self._installed_or_prompt(provider, "Transcribe Audio or Video")
        if installed is None:
            return
        model_id, diarize = self._select_model_and_diarize(installed)
        fmt = self._choose_transcript_format("Transcribe Audio or Video")
        if fmt is None:
            return

        with wx.FileDialog(
            self.frame,
            "Choose an audio or video file to transcribe",
            wildcard=_AUDIO_VIDEO_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Transcribe Audio or Video") != wx.ID_OK:
                return
            source = Path(dialog.GetPath())

        from quill.core.speech.provider import TranscriptionRequest

        request = TranscriptionRequest(
            source_path=source, model_id=model_id, output_timestamps=True, diarize=diarize
        )

        import threading

        from quill.core.speech.provider import SpeechError
        from quill.ui.ai_transcribe_dialog import AIProgressDialog

        cancel = threading.Event()
        progress = AIProgressDialog(
            self.frame,
            "Transcribing",
            f"Transcribing {source.name}...",
            on_cancel=cancel.set,
            # Quiet status mirroring so a minimized run does not announce every
            # percentage over and over; the start/finish are announced once.
            status_fn=self._set_status_quiet,
        )
        progress.show()
        self._announce(f"Transcribing {source.name}. This can take a while for long files.")

        def _on_progress(fraction: float, message: str) -> None:
            if cancel.is_set():
                raise SpeechError("Transcription cancelled.")
            percent = int(max(0.0, min(1.0, fraction)) * 100)
            progress.set_progress(percent, f"{message} {percent}%")

        def _run() -> None:
            try:
                result = provider.transcribe_file(request, _on_progress)  # type: ignore[attr-defined]
            except SpeechError as exc:
                wx.CallAfter(progress.close)
                msg = (
                    f"Transcription of {source.name} cancelled."
                    if cancel.is_set()
                    else f"Could not transcribe {source.name}: {exc}"
                )
                wx.CallAfter(self._set_status, msg)
                return
            except Exception as exc:  # noqa: BLE001 - surface a clean message
                wx.CallAfter(progress.close)
                wx.CallAfter(self._set_status, f"Could not transcribe {source.name}: {exc}")
                return
            # Done: close the progress dialog (which clears its status-bar line) and
            # open the transcript, which announces the word count once.
            wx.CallAfter(progress.close)
            wx.CallAfter(self._open_transcription_result, result, fmt)

        threading.Thread(  # GATE-40-OK: offline transcription worker.
            target=_run, daemon=True
        ).start()

    def _open_transcription_result(self, result: object, fmt: str = "text") -> None:
        from quill.core.document import Document
        from quill.core.speech import formatters

        if fmt == "markdown":
            text = formatters.to_markdown(result)  # type: ignore[arg-type]
        elif fmt == "html":
            text = formatters.to_html(result)  # type: ignore[arg-type]
        else:
            text = formatters.to_plain_text(result)  # type: ignore[arg-type]
        self._create_document_tab(Document(text=text), select=True)
        words = len((getattr(result, "full_text", "") or "").split())
        has_speakers = any(getattr(s, "speaker", "") for s in getattr(result, "segments", ()))
        extra = " with speaker labels" if has_speakers else ""
        self._announce(
            f"Transcription complete{extra}. {words} words. Review the draft transcript."
        )

    def _installed_or_prompt(self, provider: object, title: str) -> list | None:
        """Return installed models, or None after offering to open the manager."""
        wx = self._wx
        installed = provider.list_installed_models()  # type: ignore[attr-defined]
        if installed:
            return installed
        offer = self._show_message_box(
            "No offline speech model is installed yet. Open Manage Speech Models to download one?",
            title,
            wx.ICON_INFORMATION | wx.YES_NO,
        )
        if offer == wx.YES:
            self.open_speech_models()
        return None

    def _default_model_id(self, installed: list) -> str:
        """The model id to transcribe/dictate with: the user's explicit "Set as
        Default" choice when it is actually installed, else the catalog's
        recommended model, else whichever model is installed first."""
        from quill.core.speech.catalog import RECOMMENDED_MODEL_ID

        ids = [m.id for m in installed]
        preferred = str(getattr(self.settings, "speech_default_model_id", "") or "")
        if preferred and preferred in ids:
            return preferred
        return RECOMMENDED_MODEL_ID if RECOMMENDED_MODEL_ID in ids else ids[0]

    # -- captions --------------------------------------------------------- #

    def generate_captions_offline(self) -> None:
        wx = self._wx
        provider = self._speech_provider()
        installed = self._installed_or_prompt(provider, "Generate Captions")
        if installed is None:
            return
        model_id = self._default_model_id(installed)
        with wx.FileDialog(
            self.frame,
            "Choose an audio or video file to caption",
            wildcard=_AUDIO_VIDEO_WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Generate Captions") != wx.ID_OK:
                return
            source = Path(dialog.GetPath())

        from quill.core.speech.provider import TranscriptionRequest

        request = TranscriptionRequest(
            source_path=source, model_id=model_id, output_timestamps=True
        )

        def _work(progress):
            def _on_progress(fraction: float, message: str) -> None:
                progress(message, int(fraction * 100), 100)

            return provider.transcribe_file(request, _on_progress)  # type: ignore[attr-defined]

        self._run_background_task(
            f"Captioning {source.name}", _work, lambda result: self._save_captions(result, source)
        )

    def _save_captions(self, result: object, source: Path) -> None:
        from quill.core.speech import formatters

        wx = self._wx
        segments = getattr(result, "segments", ()) or ()
        if not segments:
            self._announce("No timed segments were produced, so captions cannot be made.")
            return
        formats = ["SubRip captions (.srt)", "WebVTT captions (.vtt)"]
        with wx.SingleChoiceDialog(
            self.frame, "Caption format:", "Generate Captions", formats
        ) as dialog:
            if self._show_modal_dialog(dialog, "Generate Captions") != wx.ID_OK:
                return
            choice = dialog.GetSelection()
        if choice == 0:
            text, ext = formatters.to_srt(segments), ".srt"
        else:
            text, ext = formatters.to_vtt(segments), ".vtt"
        with wx.FileDialog(
            self.frame,
            "Save captions",
            defaultFile=f"{source.stem}{ext}",
            wildcard="Caption files (*.srt;*.vtt)|*.srt;*.vtt|All files (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dialog:
            if self._show_modal_dialog(dialog, "Save captions") != wx.ID_OK:
                return
            target = Path(dialog.GetPath())
        target.write_text(text, encoding="utf-8", newline="\n")
        self._announce(f"Captions saved to {target.name}.")

    # -- microphone selection --------------------------------------------- #

    def choose_dictation_microphone(self) -> None:
        from quill.core.speech.capture import list_input_devices
        from quill.core.speech.service import load_input_device, save_input_device

        wx = self._wx
        devices = list_input_devices()
        if not devices:
            self._show_message_box(
                "No microphones were found, or microphone-capture support (the "
                "optional 'sounddevice' package) is not installed.",
                "Dictation Microphone",
                wx.ICON_INFORMATION | wx.OK,
            )
            return
        current = load_input_device()
        labels = ["System default microphone"] + [name for _index, name in devices]
        selected_row = 0
        for row, (index, _name) in enumerate(devices, start=1):
            if index == current:
                selected_row = row
        with wx.SingleChoiceDialog(
            self.frame,
            "Choose the microphone for offline dictation:",
            "Dictation Microphone",
            labels,
        ) as dialog:
            dialog.SetSelection(selected_row)
            if self._show_modal_dialog(dialog, "Dictation Microphone") != wx.ID_OK:
                return
            choice = dialog.GetSelection()
        if choice <= 0:
            save_input_device(-1)
            self._announce("Dictation microphone set to the system default.")
            return
        index, name = devices[choice - 1]
        save_input_device(index)
        self._announce(f"Dictation microphone set to {name}.")

    # -- command registration --------------------------------------------- #

    def _register_speech_commands(self) -> None:
        specs = [
            ("tools.speech_models", "Manage Speech Models", self.open_speech_models),
            (
                "tools.speech_transcribe",
                "Transcribe Audio or Video (Offline)",
                self.transcribe_audio_offline,
            ),
            (
                "tools.speech_captions",
                "Generate Captions (Offline)",
                self.generate_captions_offline,
            ),
            ("tools.speech_dictate", "Dictate (Offline)", self.dictate_offline_toggle),
            ("tools.speech_microphone", "Dictation Microphone", self.choose_dictation_microphone),
            ("tools.speech_ffmpeg", "Download FFmpeg", self.download_ffmpeg),
            ("tools.speech_hf_token", "Hugging Face Token", self.set_huggingface_token),
        ]
        for command_id, title, handler in specs:
            self.commands.try_register(
                command_id,
                title,
                handler,
                self._binding_for(command_id),
                feature_id="core.dictation",
            )
