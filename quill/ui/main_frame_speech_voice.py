"""Offline voice interaction for MainFrame: dictation, voice commands,
conversation mode, and the "Hey QUILL" wake word (CQ-1 decomposition).

``VoiceInteractionMixin`` owns the push-to-talk and always-listening surfaces
split off from ``SpeechCommandsMixin``: offline dictation
(``dictate_offline_toggle`` and its record/insert helpers), offline voice
commands (#663, allowlist-dispatched via ``SAFE_TOOL_IDS``), conversation mode
(Hey QUILL Phase 2: VAD end-of-turn capture, spoken cues, Ask Quill routing),
and the wake-word listener (Phase 3). Extracted verbatim from
``main_frame_speech.py``; runs on ``MainFrame`` (``self``) and shares its
provider accessors and speech registry. Safety law unchanged: voice commands
are off by default, Safe-Mode gated, and only ever dispatch ids in
``SAFE_TOOL_IDS``.
"""

from __future__ import annotations


class VoiceInteractionMixin:
    # -- dictation (offline, push-to-talk) -------------------------------- #

    def dictate_offline_toggle(self) -> None:
        recorder = getattr(self, "_mic_recorder", None)
        if recorder is not None and recorder.is_recording:
            self._stop_and_insert_dictation(recorder)
        else:
            self._start_dictation()

    def _start_dictation(self) -> None:
        from quill.core.platform_nouns import primary_command_chord_label
        from quill.core.speech.capture import MicRecorder, capture_available

        wx = self._wx
        if not capture_available():
            self._show_message_box(
                "Offline dictation needs microphone-capture support (the optional "
                "'sounddevice' package). You can also use system dictation with "
                f"{primary_command_chord_label()}+V.",
                "Dictate (Offline)",
                wx.ICON_INFORMATION | wx.OK,
            )
            return
        provider = self._speech_provider()
        if self._installed_or_prompt(provider, "Dictate (Offline)") is None:
            return
        from quill.core.speech.service import load_input_device

        recorder = MicRecorder()
        try:
            recorder.start(load_input_device())
        except Exception as exc:  # noqa: BLE001 - surface a clean message
            self._set_status(f"Could not start dictation: {exc}")
            return
        self._mic_recorder = recorder
        self._play_speech_sound("transcription_started")
        self._set_status_quiet("Dictation listening")
        self._announce("Listening. Run Dictate (Offline) again to stop and insert.")

    def _stop_and_insert_dictation(self, recorder: object) -> None:
        self._mic_recorder = None
        self._play_speech_sound("transcription_stopped")
        try:
            wav_path = recorder.stop()  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Dictation failed: {exc}")
            return
        provider = self._speech_provider()
        installed = provider.list_installed_models()  # type: ignore[attr-defined]
        if not installed:
            self._set_status("No speech model installed.")
            return
        model_id = self._default_model_id(installed)

        from quill.core.speech.provider import TranscriptionRequest

        request = TranscriptionRequest(source_path=wav_path, model_id=model_id)

        def _work(progress):
            def _on_progress(fraction: float, message: str) -> None:
                progress(message, int(fraction * 100), 100)

            try:
                return provider.transcribe_file(request, _on_progress)  # type: ignore[attr-defined]
            finally:
                try:
                    wav_path.unlink(missing_ok=True)
                except OSError:
                    pass

        self._set_status_quiet("Transcribing dictation")
        self._announce("Transcribing dictation...")
        self._run_background_task("Transcribing dictation", _work, self._insert_dictation_result)

    def _insert_dictation_result(self, result: object) -> None:
        text = (getattr(result, "full_text", "") or "").strip()
        editor = getattr(self, "editor", None)
        if not text or editor is None:
            self._set_status_quiet("Dictation: no speech detected")
            self._announce("No speech detected.")
            return
        editor.WriteText(text + " ")
        self._play_speech_sound("transcription_word_inserted")
        words = len(text.split())
        self._set_status_quiet(f"Dictation inserted {words} words")
        self._announce(f"Inserted {words} words. Press Control+Z to undo.")

    @staticmethod
    def _play_speech_sound(event_id: str) -> None:
        """Play a dictation earcon (distinct from other sounds); never raises."""
        try:
            from quill.ui.sound_manager import post_sound

            post_sound(event_id)
        except Exception:  # noqa: BLE001 - a missing sound must not break dictation
            pass

    # -- offline voice commands (#663, push-to-talk) --------------------- #

    def voice_command_toggle(self) -> None:
        """Push-to-talk: speak one command and dispatch it (offline, allowlisted)."""
        from quill.core.speech.voice_commands import voice_commands_available

        if not voice_commands_available(
            self.settings, safe_mode_active=bool(getattr(self, "_safe_mode", False))
        ):
            self._announce(
                "Voice commands are off. Turn them on in Settings (they are disabled in Safe Mode)."
            )
            return
        recorder = getattr(self, "_voice_recorder", None)
        if recorder is not None and recorder.is_recording:
            self._stop_and_dispatch_voice_command(recorder)
            return
        # The "Voice conversation mode" setting promises that one Voice Command
        # becomes a hands-free conversation; honor it here instead of leaving
        # the setting with no effect (#793 review).
        if bool(getattr(self.settings, "voice_conversation_enabled", False)):
            self.voice_conversation_toggle()
            return
        self._start_voice_command()

    def _start_voice_command(self) -> None:
        from quill.core.speech.capture import MicRecorder, capture_available

        wx = self._wx
        if not capture_available():
            self._show_message_box(
                "Voice commands need microphone-capture support (the optional "
                "'sounddevice' package).",
                "Voice Commands",
                wx.ICON_INFORMATION | wx.OK,
            )
            return
        provider = self._voice_provider()
        if self._installed_or_prompt(provider, "Voice Commands") is None:
            return
        from quill.core.speech.service import load_input_device

        recorder = MicRecorder()
        try:
            recorder.start(load_input_device())
        except Exception as exc:  # noqa: BLE001 - surface a clean message
            self._set_status(f"Could not start voice commands: {exc}")
            return
        self._voice_recorder = recorder
        self._play_speech_sound("transcription_started")
        self._set_status_quiet("Listening for a command")
        self._announce("Listening for a command. Run the command again to stop and act.")

    def _stop_and_dispatch_voice_command(self, recorder: object) -> None:
        self._voice_recorder = None
        self._play_speech_sound("transcription_stopped")
        try:
            wav_path = recorder.stop()  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Voice command failed: {exc}")
            return
        provider = self._voice_provider()
        installed = provider.list_installed_models()  # type: ignore[attr-defined]
        if not installed:
            self._set_status("No speech model installed.")
            return
        model_id = self._default_model_id(installed)

        from quill.core.speech.provider import TranscriptionRequest

        request = TranscriptionRequest(source_path=wav_path, model_id=model_id)

        def _work(progress):
            def _on_progress(fraction: float, message: str) -> None:
                progress(message, int(fraction * 100), 100)

            try:
                return provider.transcribe_file(request, _on_progress)  # type: ignore[attr-defined]
            finally:
                try:
                    wav_path.unlink(missing_ok=True)
                except OSError:
                    pass

        self._set_status("Recognizing command")
        self._run_background_task("Recognizing command", _work, self._dispatch_voice_result)

    def _dispatch_voice_result(self, result: object) -> None:
        from quill.core.ai.agent import SAFE_TOOL_IDS
        from quill.core.speech.voice_commands import resolve_transcript

        transcript = (getattr(result, "full_text", "") or "").strip()
        outcome = resolve_transcript(transcript, self.commands)
        if outcome.kind == "run" and outcome.command_id in SAFE_TOOL_IDS:
            self._announce(outcome.message)
            try:
                self.commands.run(outcome.command_id)
            except KeyError:
                self._set_status("That command is not available right now.")
        else:
            # cancel / no_match / a command that fell outside the safe allowlist.
            self._set_status(outcome.message)

    # -- conversation mode (#663, Hey QUILL Phase 2) --------------------- #

    def voice_conversation_toggle(self) -> None:
        """Start or stop the hands-free conversation loop (Phase 2).

        Conversation mode wraps the same on-device capture/transcribe/dispatch
        as push-to-talk in the :class:`ConversationController` state machine:
        warm audio cues for every state, a brief cancel window before a command
        runs, and a follow-up window so commands chain without re-arming.
        """
        from quill.core.speech.conversation import Timing
        from quill.core.speech.voice_commands import voice_commands_available

        controller = getattr(self, "_conversation", None)
        if controller is not None and controller.state.value != "off":
            self._conv_run(controller.stop())
            return
        if not voice_commands_available(
            self.settings, safe_mode_active=bool(getattr(self, "_safe_mode", False))
        ):
            self._announce(
                "Voice commands are off. Turn them on in Settings (they are disabled in Safe Mode)."
            )
            return
        from quill.core.speech.capture import capture_available

        if not capture_available():
            self._announce(
                "Conversation mode needs microphone-capture support (the optional "
                "'sounddevice' package)."
            )
            return
        if self._installed_or_prompt(self._voice_provider(), "Conversation Mode") is None:
            return
        from quill.core.speech.conversation import ConversationController

        controller = ConversationController(
            timing=Timing.from_settings(self.settings),
            user_name=str(getattr(self.settings, "voice_conversation_user_name", "") or ""),
            varied_prompts=True,
        )
        self._conversation = controller
        self._conv_timers: dict[str, object] = {}
        self._conv_run(controller.start())

    def _voice_spoken_cues_active(self) -> bool:
        """SR-parity: speak prompts aloud only when the user turned cues on and
        no screen reader is running (so QUILL never talks over the reader)."""
        if not bool(getattr(self.settings, "voice_conversation_spoken_cues", False)):
            return False
        try:
            from quill.platform.windows.sr_detect import detect_screen_reader

            if detect_screen_reader().detected:
                return False
        except Exception:  # noqa: BLE001
            # On Windows a failed detection could mean a reader IS running, so
            # stay quiet rather than talk over it (#795 review). Off Windows
            # there is no detector at all; honor the user's explicit opt-in.
            import sys as _sys

            if _sys.platform == "win32":
                return False
        return True

    def _voice_speak_cue(self, text: str) -> None:
        """Speak a short cue aloud via the read-aloud voice (best-effort).

        Runs on the task pool so it never blocks the UI; barge-in discipline is
        handled by capture only starting after the effect list is executed."""
        if not text or not self._voice_spoken_cues_active():
            return
        try:
            import threading

            voice = self._build_voice_services()
            if voice is None or not voice.output_available():
                return

            def _work(_progress):
                voice.play(text, stop_event=threading.Event(), pause_event=threading.Event())
                return None

            self._run_background_task("Speaking prompt", _work, lambda _r: None)
        except Exception:  # noqa: BLE001 - a cue must never break the loop
            pass

    def _conv_run(self, effects: list) -> None:
        """Execute a list of conversation :class:`Effect` objects in order."""
        wx = self._wx
        for effect in effects:
            kind = effect.kind
            if kind == "sound":
                self._play_speech_sound(effect.value)
            elif kind == "announce":
                self._set_status_quiet(effect.value)
                self._announce(effect.value)
                self._voice_speak_cue(effect.value)
            elif kind == "start_capture":
                self._conv_start_capture()
            elif kind == "stop_capture":
                self._conv_stop_capture(discard=True)
            elif kind == "dispatch":
                self._conv_dispatch(effect.value)
            elif kind == "start_timer":
                self._conv_cancel_timer(effect.value)
                self._conv_timers[effect.value] = wx.CallLater(
                    max(1, effect.delay_ms), self._conv_on_timer, effect.value
                )
            elif kind == "cancel_timer":
                self._conv_cancel_timer(effect.value)

    def _conv_cancel_timer(self, channel: str) -> None:
        timer = getattr(self, "_conv_timers", {}).pop(channel, None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001 - already fired/stopped
                pass

    def _conv_on_timer(self, channel: str) -> None:
        self._conv_timers.pop(channel, None)
        controller = getattr(self, "_conversation", None)
        if controller is None:
            return
        from quill.core.speech.conversation import (
            TIMER_FOLLOWUP,
            TIMER_REVIEW,
            TIMER_THINKING,
        )

        if channel == TIMER_REVIEW:
            self._conv_run(controller.on_review_timer())
        elif channel == TIMER_THINKING:
            self._conv_run(controller.on_thinking_timer())
        elif channel == TIMER_FOLLOWUP:
            self._conv_run(controller.on_followup_timer())

    def _conv_start_capture(self) -> None:
        """Open the mic for one conversation turn, ending it when you stop
        speaking (voice-activity detection) with a hard cap as a backstop."""
        from quill.core.speech.capture import SAMPLE_RATE, MicRecorder
        from quill.core.speech.service import load_input_device
        from quill.core.speech.vad import SilenceDetector

        recorder = MicRecorder()
        try:
            recorder.start(load_input_device())
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Conversation mode could not open the microphone: {exc}")
            self._conv_run(self._conversation.stop())
            return
        self._conv_recorder = recorder
        silence_ms = int(getattr(self.settings, "voice_conversation_silence_ms", 2000))
        if silence_ms <= 0:
            # The setting documents 0 as "the engine default"; for this
            # timed-turn loop that is the standard 2 s pause window (#793).
            silence_ms = 2000
        # VAD endpointing works on the frame rate (samples/sec) = SAMPLE_RATE for
        # mono capture; the old `* CHANNELS` was a latent multi-channel bug.
        self._conv_vad = SilenceDetector(sample_rate=SAMPLE_RATE, silence_ms=silence_ms)
        self._conv_vad_seen = 0
        # Poll microphone energy; a turn ends when speech is followed by the
        # pause window. A hard cap stops a stuck-open mic even if VAD misses;
        # it must exceed the configured pause window (plus margin) or a long
        # window could never elapse before the cut-off (#795 review).
        self._conv_vad_timer = self._wx.CallLater(200, self._conv_poll_vad)
        cap_ms = max(15000, silence_ms + 5000)
        self._conv_capture_timer = self._wx.CallLater(cap_ms, self._conv_finish_capture)

    def _conv_poll_vad(self) -> None:
        recorder = getattr(self, "_conv_recorder", None)
        vad = getattr(self, "_conv_vad", None)
        if recorder is None or vad is None:
            return
        new, self._conv_vad_seen = recorder.frames_since(self._conv_vad_seen)
        if new and vad.feed(new):
            self._conv_finish_capture()
            return
        self._conv_vad_timer = self._wx.CallLater(200, self._conv_poll_vad)

    def _conv_stop_capture(self, *, discard: bool) -> object | None:
        for attr in ("_conv_capture_timer", "_conv_vad_timer"):
            timer = getattr(self, attr, None)
            if timer is not None:
                try:
                    timer.Stop()
                except Exception:  # noqa: BLE001
                    # A timer that is already dead (window destroyed mid-stop)
                    # is exactly what we want; cleanup must never raise.
                    pass
                setattr(self, attr, None)
        recorder = getattr(self, "_conv_recorder", None)
        self._conv_recorder = None
        if recorder is None:
            return None
        try:
            wav_path = recorder.stop()
        except Exception:  # noqa: BLE001
            return None
        if discard:
            try:
                wav_path.unlink(missing_ok=True)
            except OSError:
                pass
            return None
        return wav_path

    def _conv_finish_capture(self) -> None:
        """The turn window elapsed: transcribe and feed the controller."""
        self._conv_capture_timer = None
        wav_path = self._conv_stop_capture(discard=False)
        controller = getattr(self, "_conversation", None)
        if wav_path is None or controller is None:
            return
        provider = self._voice_provider()
        installed = provider.list_installed_models()  # type: ignore[attr-defined]
        if not installed:
            self._conv_run(controller.stop())
            return
        model_id = self._default_model_id(installed)
        from quill.core.speech.provider import TranscriptionRequest

        request = TranscriptionRequest(source_path=wav_path, model_id=model_id)

        def _work(progress):
            try:
                return provider.transcribe_file(  # type: ignore[attr-defined]
                    request, lambda f, m: progress(m, int(f * 100), 100)
                )
            finally:
                try:
                    wav_path.unlink(missing_ok=True)
                except OSError:
                    pass

        self._run_background_task("Recognizing command", _work, self._conv_on_transcript)

    def _conv_on_transcript(self, result: object) -> None:
        from quill.core.ai.agent import SAFE_TOOL_IDS
        from quill.core.speech.voice_commands import normalize, resolve_transcript

        controller = getattr(self, "_conversation", None)
        if controller is None:
            return
        transcript = (getattr(result, "full_text", "") or "").strip()
        outcome = resolve_transcript(transcript, self.commands)
        if outcome.kind == "cancel":
            # The docs promise a spoken "stop" turns conversation mode OFF;
            # the other cancel phrases only abort this turn and re-arm (#793).
            if normalize(transcript) == "stop":
                self._conv_run(controller.stop())
                return
            self._conv_run(controller.on_cancel())
        elif outcome.kind == "run" and outcome.command_id in SAFE_TOOL_IDS:
            self._conv_run(controller.on_transcript(outcome.command_id, outcome.message))
        elif self._voice_route_to_ask_quill(transcript):
            # A question, not a command: handed to Ask Quill. Turn conversation
            # mode off so the mic is free for the chat's own voice controls.
            self._conv_run(controller.stop())
        else:
            self._conv_run(controller.on_transcript(None, outcome.message))

    def _voice_route_to_ask_quill(self, transcript: str) -> bool:
        """Phase 4: if ``transcript`` sounds like a question, open Ask Quill with
        it pre-filled and return True. AI consent and sending stay with the
        user in the chat; voice never fires a request on its own."""
        from quill.core.speech.voice_routing import QUESTION, classify, question_text

        if classify(transcript) != QUESTION:
            return False
        # Pre-release ADP conversation routing wins when unlocked + opted in
        # (main_frame_adp.AdpMixin); voice capture/speech stay on-device.
        adp_router = getattr(self, "_adp_route_voice_question", None)
        if adp_router is not None and adp_router(transcript):
            return True
        opener = getattr(self, "open_ask_quill_conversation", None)
        if opener is None:
            return False
        self._announce("Opening Ask Quill with your question.")
        opener(initial_prompt=question_text(transcript))
        return True

    def _conv_dispatch(self, command_id: str) -> None:
        controller = getattr(self, "_conversation", None)
        try:
            self.commands.run(command_id)
        except KeyError:
            self._set_status("That command is not available right now.")
        if controller is not None:
            self._conv_run(controller.on_action_done())

    def speak_voice_status(self) -> None:
        """Say what voice is doing right now (ADP mic-live perceivability)."""
        parts: list[str] = []
        wake = getattr(self, "_wake", None)
        if wake is not None and wake.state != "off":
            parts.append(wake.status_text())
        conversation = getattr(self, "_conversation", None)
        if conversation is not None and conversation.state.value != "off":
            parts.append(conversation.status_text())
        recorder = getattr(self, "_voice_recorder", None)
        if recorder is not None and getattr(recorder, "is_recording", False):
            parts.append("Listening for a command")
        message = "; ".join(parts) if parts else "Voice is not listening right now."
        self._announce(message)
        self._set_status(message)

    # -- wake word "Hey QUILL" (#663, Hey QUILL Phase 3) ----------------- #

    def voice_wakeword_toggle(self) -> None:
        """Start or stop always-listening for the phrase "Hey QUILL".

        The microphone stays open in short windows; each is transcribed
        on-device and checked for the wake phrase. On a wake, an inline command
        ("Hey QUILL, save file") runs straight away, while a bare "Hey QUILL"
        opens one command turn. Off by default and always off in Safe Mode; the
        status stays visible and a periodic reminder keeps the live mic
        perceivable.
        """
        from quill.core.speech.voice_commands import voice_commands_available

        wake = getattr(self, "_wake", None)
        if wake is not None and wake.state != "off":
            self._wake_run(wake.stop())
            return
        if not voice_commands_available(
            self.settings, safe_mode_active=bool(getattr(self, "_safe_mode", False))
        ):
            self._announce(
                "Voice commands are off. Turn them on in Settings (they are disabled in Safe Mode)."
            )
            return
        from quill.core.speech.capture import capture_available

        if not capture_available():
            self._announce(
                "Listening for Hey QUILL needs microphone-capture support (the optional "
                "'sounddevice' package)."
            )
            return
        if self._installed_or_prompt(self._voice_provider(), "Hey QUILL") is None:
            return
        from quill.core.speech.wakeword import WakeController

        self._wake = WakeController()
        self._wake_run(self._wake.start())

    def _wake_run(self, effects: list) -> None:
        for effect in effects:
            kind = effect.kind
            if kind == "sound":
                self._play_speech_sound(effect.value)
            elif kind == "announce":
                self._set_status_quiet(effect.value)
                self._announce(effect.value)
            elif kind == "reminder":
                from quill.core.speech.conversation import CUE_IDLE

                self._play_speech_sound(CUE_IDLE)
                self._set_status_quiet('Still listening for "Hey QUILL"')
            elif kind == "listen_again":
                self._wake_capture_window()
            elif kind == "stop_listen":
                self._wake_stop_capture()
            elif kind == "arm":
                self._wake_capture_command()
            elif kind == "dispatch":
                self._wake_dispatch_inline(effect.value)

    def _wake_stop_capture(self) -> None:
        timer = getattr(self, "_wake_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001
                pass
            self._wake_timer = None
        recorder = getattr(self, "_wake_recorder", None)
        self._wake_recorder = None
        if recorder is not None:
            try:
                recorder.stop().unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass

    def _wake_capture_window(self, *, for_command: bool = False) -> None:
        """Record one short window, then transcribe and route it."""
        wake = getattr(self, "_wake", None)
        if wake is None or wake.state == "off":
            return
        from quill.core.speech.capture import MicRecorder
        from quill.core.speech.service import load_input_device

        recorder = MicRecorder()
        try:
            recorder.start(load_input_device())
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Hey QUILL listening stopped: {exc}")
            self._wake_run(wake.stop())
            return
        self._wake_recorder = recorder
        # A short window keeps latency low; command windows are a bit longer.
        window_ms = 4000 if for_command else 2500
        callback = self._wake_finish_command if for_command else self._wake_finish_window
        self._wake_timer = self._wx.CallLater(window_ms, callback)

    def _wake_capture_command(self) -> None:
        self._set_status_quiet("Listening for your command")
        self._wake_capture_window(for_command=True)

    def _wake_transcribe(self, on_text) -> None:
        """Stop the current window and transcribe it, calling on_text(str)."""
        timer = getattr(self, "_wake_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001
                pass
            self._wake_timer = None
        recorder = getattr(self, "_wake_recorder", None)
        self._wake_recorder = None
        if recorder is None:
            return
        try:
            wav_path = recorder.stop()
        except Exception:  # noqa: BLE001
            on_text("")
            return
        provider = self._voice_provider()
        installed = provider.list_installed_models()  # type: ignore[attr-defined]
        if not installed:
            # No model: nothing will consume the recording, so delete it now
            # instead of leaking a temp WAV per toggle (#794 review).
            try:
                wav_path.unlink(missing_ok=True)
            except OSError:
                pass
            self._wake_run(self._wake.stop())
            return
        model_id = self._default_model_id(installed)
        from quill.core.speech.provider import TranscriptionRequest

        request = TranscriptionRequest(source_path=wav_path, model_id=model_id)

        def _work(progress):
            try:
                result = provider.transcribe_file(  # type: ignore[attr-defined]
                    request, lambda f, m: progress(m, int(f * 100), 100)
                )
                return (getattr(result, "full_text", "") or "").strip()
            finally:
                try:
                    wav_path.unlink(missing_ok=True)
                except OSError:
                    pass

        self._run_background_task("Listening", _work, on_text)

    def _wake_finish_window(self) -> None:
        self._wake_transcribe(self._wake_on_window)

    def _wake_on_window(self, transcript: str) -> None:
        wake = getattr(self, "_wake", None)
        if wake is not None:
            self._wake_run(wake.on_window(transcript or ""))

    def _wake_finish_command(self) -> None:
        self._wake_transcribe(self._wake_on_command)

    def _wake_on_command(self, transcript: str) -> None:
        self._wake_dispatch_inline(transcript)

    def _wake_dispatch_inline(self, body: str) -> None:
        """Resolve a spoken command body against the safe allowlist, run it,
        then resume listening for the wake phrase."""
        from quill.core.ai.agent import SAFE_TOOL_IDS
        from quill.core.speech.conversation import CUE_ERROR, CUE_READY
        from quill.core.speech.voice_commands import normalize, resolve_transcript

        wake = getattr(self, "_wake", None)
        outcome = resolve_transcript(body, self.commands)
        if outcome.kind == "run" and outcome.command_id in SAFE_TOOL_IDS:
            self._announce(outcome.message)
            try:
                self.commands.run(outcome.command_id)
                self._play_speech_sound(CUE_READY)
            except KeyError:
                self._set_status("That command is not available right now.")
        elif outcome.kind == "cancel":
            # The docs promise "Hey QUILL, stop" turns always-listening OFF;
            # other cancel phrases just drop this utterance (#794 review).
            if normalize(body) == "stop" and wake is not None:
                self._wake_run(wake.stop())
                return
            self._set_status_quiet("Cancelled.")
        elif self._voice_route_to_ask_quill(body):
            # A question: handed to Ask Quill. Stop always-listening so the mic
            # is free for the chat, and do not resume automatically.
            if wake is not None:
                self._wake_run(wake.stop())
            return
        else:
            self._play_speech_sound(CUE_ERROR)
            self._set_status(outcome.message)
        if wake is not None and wake.state != "off":
            self._wake_run(wake.resume_listening())
