"""Read Aloud, Read in Browser and Export to Speech Audio on QUILL's main window.

Moved whole out of ``MainFrame`` (todo D.4, 2026-10-17): starting, pausing and
stopping the live Read Aloud (with the per-session ElevenLabs consent), the
experimental read-in-browser page, synthesizing the document to an audio file,
and the controller's progress and state callbacks. The host contract is
unchanged: same ``self`` attributes, same command ids, keys and announcements.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from quill.core.browser_preview import (
    browser_choice_label_for_value,
    normalize_browser_choice,
    open_preview_url,
)
from quill.core.paths import app_data_dir
from quill.core.read_aloud import (
    ReadAloudUnavailableError,
    discover_dectalk_executable,
    discover_espeak_executable,
    discover_piper_executable,
    synthesize_to_file_with_dectalk,
    synthesize_to_file_with_sapi5,
    synthesize_with_espeak,
    synthesize_with_kokoro,
    synthesize_with_piper,
)
from quill.core.settings import save_settings


class ReadAloudMixin:
    """Live Read Aloud and speech-audio export; mixed into ``MainFrame``."""

    def _active_read_aloud_pronunciations(self, engine: str) -> list:
        """Active pronunciation dictionaries for live Read Aloud (same as batch)."""
        if not getattr(self.settings, "pronunciation_enabled", True):
            return []
        from quill.core.speech.pronunciation import active_dictionaries

        ids = list(getattr(self.settings, "pronunciation_enabled_dictionary_ids", []) or [])
        try:
            return active_dictionaries(
                engine, project_dir=None, enabled_ids=set(ids) if ids else None
            )
        except Exception:  # noqa: BLE001 - a broken store must not block read-aloud
            return []

    def _elevenlabs_read_aloud_params(self, engine: str) -> tuple[str, str, str] | None:
        """Resolve (api_key, voice, model) for an ElevenLabs Read Aloud, with consent.

        Returns ``("", "", "")`` when the engine is not ElevenLabs (a no-op passed to
        the controller). For ElevenLabs it obtains a **per-session** consent once — the
        voice sends each sentence to ElevenLabs over the internet and uses the user's
        paid quota — resolves the stored key, and returns the chosen voice/model.
        Returns ``None`` when there is no key or the user declines, so the caller aborts
        the read-aloud cleanly (nothing is sent without consent).
        """
        if engine != "elevenlabs":
            return ("", "", "")
        wx = self._wx
        api_key = self._get_elevenlabs_api_key()
        if not api_key.strip():
            self._show_message_box(
                "Connect ElevenLabs first (in AI setup) to use its Read Aloud voice.",
                "Read Aloud",
                wx.ICON_INFORMATION | wx.OK,
            )
            return None
        if not getattr(self, "_elevenlabs_read_aloud_consented", False):
            answer = self._show_message_box(
                "Reading aloud with the ElevenLabs voice sends each sentence to "
                "ElevenLabs over the internet and uses your ElevenLabs quota. Use it "
                "for this session?",
                "ElevenLabs Read Aloud",
                wx.ICON_QUESTION | wx.YES_NO,
            )
            if answer != wx.YES:
                return None
            self._elevenlabs_read_aloud_consented = True
        return (
            api_key,
            str(getattr(self.settings, "read_aloud_elevenlabs_voice", "") or ""),
            str(getattr(self.settings, "read_aloud_elevenlabs_model", "") or ""),
        )

    def toggle_read_aloud(self) -> None:
        wx = self._wx
        state = self._read_aloud.state
        if state == "playing":
            self._read_aloud.pause()
            self._set_status("Read aloud paused")
            return
        text = self.editor.GetValue()
        if state == "paused":
            start = self._read_aloud.cursor
            end = None
        else:
            start, end = self.editor.GetSelection()
            if start == end:
                start = self.editor.GetInsertionPoint()
                end = None
        try:
            read_aloud_engine = self.settings.read_aloud_engine.strip().lower() or "sapi5"
            el_params = self._elevenlabs_read_aloud_params(read_aloud_engine)
            if el_params is None:
                return  # ElevenLabs consent declined or no key
            el_key, el_voice, el_model = el_params
            self._read_aloud.start(
                text,
                start,
                self.settings.read_aloud_voice,
                engine_name=read_aloud_engine,
                rate=self.settings.read_aloud_rate,
                volume=self.settings.read_aloud_volume / 100.0,
                pitch=self.settings.read_aloud_pitch,
                dectalk_executable=self.settings.read_aloud_dectalk_executable,
                dectalk_voice=self.settings.read_aloud_dectalk_voice,
                dectalk_rate=self.settings.read_aloud_dectalk_rate,
                dectalk_dictionary=self.settings.read_aloud_dectalk_dictionary,
                elevenlabs_api_key=el_key,
                elevenlabs_voice=el_voice,
                elevenlabs_model=el_model,
                end=end,
                piper_model=self.settings.read_aloud_piper_model,
                kokoro_voice=self.settings.read_aloud_kokoro_voice,
                kokoro_speed=self.settings.read_aloud_kokoro_speed,
                espeak_executable=self.settings.read_aloud_espeak_executable,
                espeak_voice=self.settings.read_aloud_espeak_voice,
                espeak_rate=self.settings.read_aloud_espeak_rate,
                macos_voice=self.settings.read_aloud_macos_voice,
                macos_rate=self.settings.read_aloud_macos_rate,
                sentence_pause_ms=self.settings.read_aloud_sentence_pause_ms,
                punctuation_level=self.settings.announce_punctuation_level,
                pronunciation_dictionaries=self._active_read_aloud_pronunciations(
                    read_aloud_engine
                ),
                on_progress=lambda progress_start, progress_end: self._wx.CallAfter(
                    self._on_read_aloud_progress,
                    progress_start,
                    progress_end,
                ),
                on_state_change=lambda next_state: self._wx.CallAfter(
                    self._on_read_aloud_state_change,
                    next_state,
                ),
                on_error=lambda error: self._wx.CallAfter(self._on_read_aloud_error, error),
            )
        except ReadAloudUnavailableError as exc:
            self._show_message_box(
                str(exc),
                "Read Aloud",
                wx.ICON_INFORMATION | wx.OK,
            )
            return
        self._set_status("Read aloud started")

    def stop_read_aloud(self) -> None:
        self._read_aloud.stop()
        self._set_status("Read aloud stopped")

    # ------------------------------------------------------------------
    # Experimental: read the document aloud in the user's real browser, where
    # speechSynthesis exposes the full voice set (including Edge's Online
    # (Natural) voices) — unlike the embedded WebView2, which only sees local
    # SAPI voices. We write a self-contained accessible reader page (voice
    # picker + Play/Pause/Stop) and open it in the chosen browser. Opt-in under
    # Preferences > Experimental. See quill/core/browser_reader.py.
    # ------------------------------------------------------------------
    def _edge_read_aloud_enabled(self) -> bool:
        return bool(
            getattr(self.settings, "edge_read_aloud_enabled", False)
            and getattr(self.settings, "experimental_acknowledged", False)
        )

    def read_document_in_browser(self) -> None:
        wx = self._wx
        if not self._edge_read_aloud_enabled():
            self._show_message_box(
                "Turn on 'Read the document aloud in your browser' under "
                "Preferences > Experimental first (it takes effect right away).",
                "Read in Browser (Experimental)",
                wx.ICON_INFORMATION | wx.OK,
            )
            return
        text = self.editor.GetValue()
        if not text.strip():
            self._set_status("Nothing to read")
            return
        from quill.core.browser_reader import build_reader_html

        title = "Document"
        tabs = getattr(self, "_document_tabs", None)
        if tabs:
            tab_index = (
                self._active_tab_index if self._active_tab_index >= 0 else self._current_tab_index()
            )
            if 0 <= tab_index < len(tabs):
                title = tabs[tab_index].document.name or "Document"
        reader_lang = getattr(self, "_active_language", None) or "en"
        payload = build_reader_html(title, text, lang=reader_lang)
        reader_dir = app_data_dir() / "browser-reader"
        reader_dir.mkdir(parents=True, exist_ok=True)
        reader_path = reader_dir / "read-aloud.html"
        temp_path = reader_path.with_suffix(".tmp")
        temp_path.write_text(payload, encoding="utf-8")
        os.replace(temp_path, reader_path)
        browser_choice = normalize_browser_choice(self.settings.preview_browser)
        open_preview_url(reader_path.as_uri(), browser_choice)
        self._set_status(
            f"Opened read-aloud in {browser_choice_label_for_value(browser_choice)} — "
            "choose a voice and press Play"
        )

    def _cleanup_browser_reader_files(self) -> None:
        """Delete the browser read-aloud plaintext page(s) on exit (privacy)."""
        from quill.core.browser_reader import remove_reader_pages

        remove_reader_pages(app_data_dir() / "browser-reader")

    def generate_speech_audio(self) -> None:  # noqa: PLR0912,PLR0915
        wx = self._wx
        _TITLE = "Generate Speech Audio"
        editor = getattr(self, "editor", None)
        text = ""
        if editor is not None:
            text = editor.GetStringSelection().strip() or editor.GetValue().strip()
        if text:
            from quill.core.speech.text_polish import clean_markdown_text, polish_for_tts

            # Raw markdown syntax ('#', '**', '[label](url)') reaching a
            # synthesis engine directly -- Piper's espeak-ng phonemizer badly
            # mis-tokenizes it, sounding garbled or like the wrong language
            # (fix.md #4). Batch export and document-to-speech already clean
            # it; this shares the same sanitizer.
            text = polish_for_tts(clean_markdown_text(text))
        if not text:
            self._show_message_box(
                "There is nothing to export. Open or type a document first, then "
                "try Export to Speech Audio again.",
                _TITLE,
                wx.ICON_INFORMATION | wx.OK,
            )
            self._set_status("Nothing to synthesize")
            return

        # WAV is always available (the engines emit it directly). The compressed
        # listening formats (MP3, M4A/M4B, OGG, Opus, FLAC) need ffmpeg to encode
        # the synthesized WAV, so they only appear when ffmpeg is installed (#750).
        from quill.core.speech.ffmpeg import ffmpeg_available, resolve_export_format

        formats: list[tuple[str, str]] = [("wav", "Wave file")]
        if ffmpeg_available():
            formats += [
                ("mp3", "MP3 audio"),
                ("m4a", "M4A audio"),
                ("m4b", "M4B audiobook"),
                ("ogg", "OGG audio"),
                ("opus", "Opus audio"),
                ("flac", "FLAC audio"),
            ]
        wildcard = "|".join(f"{label} (*.{ext})|*.{ext}" for ext, label in formats)
        wildcard += "|All files (*.*)|*.*"

        with wx.FileDialog(
            self.frame,
            _TITLE,
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            if self._show_modal_dialog(dlg, _TITLE) != wx.ID_OK:
                self._set_status("Speech generation cancelled")
                return
            output_path = Path(dlg.GetPath())
            filter_index = dlg.GetFilterIndex()

        # Pick the target format: a recognized typed extension wins (so "song.mp3"
        # under "All files" still makes an MP3); otherwise the selected filter
        # decides and the extension is normalized to match (see resolve_export_format).
        target_fmt, _normalize_suffix = resolve_export_format(
            output_path.suffix, filter_index, [ext for ext, _ in formats]
        )
        if _normalize_suffix:
            output_path = output_path.with_suffix(f".{target_fmt}")

        engine = self.settings.read_aloud_engine.strip().lower() or "sapi5"
        s = self.settings

        # Kokoro-only: models on disk but the kokoro_onnx package missing (e.g.
        # upgraded from a build that bundled Kokoro). Set in the gate below and
        # honored on the export worker so the small package install happens off
        # the UI thread. (#kokoro-onnx)
        kokoro_install_pkg = False

        # Resolve / prompt for engine-specific paths before background work
        if engine == "piper":
            exe = discover_piper_executable()
            if exe is None:
                self._show_message_box(
                    "Piper executable was not found. "
                    "Re-run the Quill installer and select the Piper component.",
                    _TITLE,
                    wx.ICON_ERROR | wx.OK,
                )
                self._set_status("Speech generation cancelled")
                return
            model = Path(s.read_aloud_piper_model).expanduser()
            if not s.read_aloud_piper_model or not model.exists():
                with wx.FileDialog(
                    self.frame,
                    "Select Piper model (.onnx)",
                    wildcard="Piper model (*.onnx)|*.onnx|All files (*.*)|*.*",
                    style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
                ) as d:
                    if self._show_modal_dialog(d, _TITLE) != wx.ID_OK:
                        self._set_status("Speech generation cancelled")
                        return
                    model = Path(d.GetPath())
                s.read_aloud_piper_model = str(model)
            piper_exe_snap = exe
            piper_model_snap = model

        elif engine == "dectalk":
            exe = discover_dectalk_executable(s.read_aloud_dectalk_executable)
            if exe is None:
                self._show_message_box(
                    "DECtalk executable not found. Configure it in Read Aloud Settings.",
                    _TITLE,
                    wx.ICON_ERROR | wx.OK,
                )
                self._set_status("Speech generation cancelled")
                return
            dectalk_exe_snap = exe

        elif engine == "espeak":
            exe = discover_espeak_executable(s.read_aloud_espeak_executable)
            if exe is None:
                self._show_message_box(
                    "eSpeak-NG not found. Install it or configure the path in Read Aloud Settings.",
                    _TITLE,
                    wx.ICON_ERROR | wx.OK,
                )
                self._set_status("Speech generation cancelled")
                return
            espeak_exe_snap = exe

        elif engine == "kokoro":
            from quill.core.read_aloud import kokoro_engine_ready, kokoro_onnx_ready

            if not kokoro_engine_ready():
                if kokoro_onnx_ready():
                    # Model files are present but the kokoro_onnx package is not
                    # importable. The user already opted into Kokoro (downloaded
                    # the voices and selected the voice), so onboard the small
                    # (~20 MB) package on the export worker instead of dead-ending
                    # with a "go install it yourself" dialog. (#kokoro-onnx)
                    kokoro_install_pkg = True
                else:
                    self._show_message_box(
                        "Kokoro voices are not installed yet. Use Manage Voices to "
                        "download the Kokoro voices (~114 MB) before exporting.",
                        _TITLE,
                        wx.ICON_ERROR | wx.OK,
                    )
                    self._set_status("Speech generation cancelled")
                    return

        save_settings(s)
        task_label = f"Generating speech audio ({output_path.name}) via {engine}"

        # Capture settings snapshot for the background thread
        _engine = engine
        _voice = s.read_aloud_voice
        _rate = s.read_aloud_rate
        _vol = s.read_aloud_volume / 100.0
        _dectalk_voice = s.read_aloud_dectalk_voice
        _dectalk_rate = s.read_aloud_dectalk_rate
        _kokoro_voice = s.read_aloud_kokoro_voice
        _kokoro_speed = s.read_aloud_kokoro_speed
        _kokoro_install_pkg = kokoro_install_pkg
        _espeak_voice = s.read_aloud_espeak_voice
        _espeak_rate = s.read_aloud_espeak_rate
        _out = output_path
        _target_fmt = target_fmt

        def work(progress: Callable[[str, int, int], None]) -> object:
            import tempfile

            from quill.core.speech.ffmpeg import transcode_audio

            progress(f"Starting {_engine}", 0, 1)
            # The synthesis engines only emit WAV. For a compressed target, render
            # to a temporary WAV first, then encode it to the chosen format (#750).
            tmp_dir: str | None = None
            if _target_fmt == "wav":
                wav_target = _out
            else:
                tmp_dir = tempfile.mkdtemp(prefix="quill-speech-")
                wav_target = Path(tmp_dir) / f"{_out.stem}.wav"
            if _engine == "sapi5":
                synthesize_to_file_with_sapi5(
                    _out_text, wav_target, voice=_voice, rate=_rate, volume=_vol
                )
            elif _engine == "dectalk":
                synthesize_to_file_with_dectalk(
                    _out_text,
                    wav_target,
                    executable_path=dectalk_exe_snap,
                    voice=_dectalk_voice,
                    rate=_dectalk_rate,
                )
            elif _engine == "piper":
                synthesize_with_piper(
                    _out_text,
                    wav_target,
                    executable_path=piper_exe_snap,
                    model_path=piper_model_snap,
                )
            elif _engine == "kokoro":
                if _kokoro_install_pkg:
                    # GATE-40-OK: runs on the export worker (this callback is the
                    # background task body), so the ~20 MB pip install stays off
                    # the UI thread. A failure surfaces the real installer error
                    # via notify_on_error, not the masked fallback. (#kokoro-onnx)
                    from quill.core.speech.engine_install import install_kokoro_onnx

                    progress("Installing Kokoro component", 0, 1)
                    install_kokoro_onnx(
                        progress=lambda frac, msg: progress(msg, int(frac * 100), 100)
                    )
                synthesize_with_kokoro(
                    _out_text, wav_target, voice=_kokoro_voice, speed=_kokoro_speed
                )
            elif _engine == "espeak":
                synthesize_with_espeak(
                    _out_text,
                    wav_target,
                    executable_path=espeak_exe_snap,
                    voice=_espeak_voice,
                    rate=_espeak_rate,
                )
            if _target_fmt != "wav":
                progress(f"Encoding {_target_fmt.upper()}", 1, 1)
                try:
                    transcode_audio(wav_target, _out, _target_fmt)
                finally:
                    wav_target.unlink(missing_ok=True)
                    if tmp_dir:
                        try:
                            Path(tmp_dir).rmdir()
                        except OSError:
                            pass
            progress("Finalizing output", 1, 1)
            return str(_out)

        _out_text = text

        def on_success(result: object) -> None:
            self._set_status(f"Speech generation complete: {Path(str(result)).name}")

        self._run_background_task(
            task_label,
            work,
            on_success,
            notify_on_success=True,
            notify_on_error=True,
            notification_category="speech",
        )

    def _on_read_aloud_progress(self, start: int, end: int) -> None:
        # Following along selects each sentence as it is spoken. With a screen
        # reader running this makes it announce the selection over QUILL's voice,
        # so it is gated behind a setting screen-reader users can turn off.
        if self.settings.read_aloud_follow_cursor:
            self.editor.SetSelection(start, end)
            self.editor.SetFocus()
        self._set_status("Read aloud speaking")

    def _on_read_aloud_state_change(self, state: str) -> None:
        if state == "paused":
            self._set_status("Read aloud paused")
        elif state == "error":
            self._set_status("Read aloud failed")
        else:
            self._set_status("Read aloud finished")

    def _on_read_aloud_error(self, error: str) -> None:
        self._set_status(f"Read aloud error: {error}")
