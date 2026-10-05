"""Hearing a voice before choosing it: the sample, the generating cue, and
stopping or purging a preview.

Moved whole out of ``MainFrame`` under qc.md F-08 (2026-10-03); the host
contract is unchanged: these methods use the same ``self`` attributes they did.
"""

from __future__ import annotations

try:
    import winsound as _winsound  # type: ignore[import]
except ImportError:  # pragma: no cover - non-Windows fallback
    _winsound = None  # type: ignore[assignment]

import os
import sys
from collections.abc import Callable
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.read_aloud import (
    ReadAloudUnavailableError,
    discover_dectalk_executable,
    discover_espeak_executable,
    discover_piper_executable,
    resolve_piper_model_path,
    synthesize_to_file_with_dectalk,
    synthesize_with_espeak,
    synthesize_with_kokoro,
    synthesize_with_macos,
    synthesize_with_piper,
)
from quill.core.sound_events import SoundEvent
from quill.ui.sound_manager import post_sound


def _sapi5_voice_short_name(voice_id: str) -> str:
    """Normalize a SAPI5 registry voice ID to a lowercase short name.

    Windows SAPI 5 voices have IDs like:
      'HKEY_LOCAL_MACHINE\\...\\TTS_MS_EN-US_DAVID_11.0'
    This extracts 'david' so we can look up a bundled preview sample.
    """
    last = voice_id.replace("/", "\\").rsplit("\\", 1)[-1]
    skip = {"TTS", "MS"}
    for part in last.upper().split("_"):
        if not part or part in skip:
            continue
        if "-" in part:  # language codes: EN-US, EN-GB
            continue
        try:
            float(part)
            continue  # version numbers: 11.0
        except ValueError:
            pass
        if part.isalpha():
            return part.lower()
    return last.lower()


def _wav_duration_seconds(path: Path, *, fallback: float = 12.0) -> float:
    """Length of a PCM wav in seconds; a safe cap when it cannot be read so the
    preview wait loop never blocks the worker indefinitely."""
    try:
        import wave

        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
            if rate:
                return frames / float(rate)
    except Exception:  # noqa: BLE001 - an unreadable header degrades to the cap
        pass
    return fallback


def _await_playback(
    *,
    duration: float,
    still_current: Callable[[], bool],
    purge: Callable[[], None],
    sleep: Callable[[float], None],
    now: Callable[[], float],
    poll: float = 0.05,
) -> bool:
    """Wait out an asynchronously-playing preview clip, cutting it short the
    moment it is superseded.

    Returns True if playback was interrupted (Stop pressed / a newer preview
    started): ``purge`` is called to cut the audio. Returns False when the clip
    plays to its natural end. Pure (time and sleep are injected) so the
    interruption logic is unit-tested without winsound or real threads."""
    deadline = now() + duration
    while now() < deadline:
        if not still_current():
            purge()
            return True
        sleep(poll)
    return False


class VoicePreviewMixin:
    """Read-aloud voice previews; mixed into ``MainFrame``."""

    def _voice_preview_catalog_roots(self) -> list[Path]:
        roots: list[Path] = []
        app_root_raw = os.environ.get("QUILL_APP_ROOT", "").strip()
        if app_root_raw:
            app_root = Path(app_root_raw)
            roots.append(app_root / "quill" / "data" / "voice-previews")
            roots.append(app_root / "tools" / "speech" / "previews")
        roots.append(Path(__file__).resolve().parents[1] / "data" / "voice-previews")
        roots.append(app_data_dir() / "speech" / "previews")
        deduped: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            marker = str(root).lower()
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(root)
        return deduped

    def _voice_preview_sample_path(self, engine: str, voice_id: str) -> Path | None:
        safe_engine = (engine or "").strip().lower()
        safe_voice = (voice_id or "").strip()
        if not safe_engine or not safe_voice:
            return None
        if safe_engine == "sapi5":
            safe_voice = _sapi5_voice_short_name(safe_voice)
            if not safe_voice:
                return None
        for root in self._voice_preview_catalog_roots():
            provider_dir = root / safe_engine
            if not provider_dir.exists():
                continue
            for extension in (".wav", ".mp3"):
                candidate = provider_dir / f"{safe_voice}{extension}"
                if candidate.exists():
                    return candidate
        return None

    def _purge_preview_playback(self) -> None:
        """Best-effort: stop whatever voice-preview audio is currently sounding.

        Covers both playback backends `_play_preview_asset` uses. Never raises --
        called opportunistically whenever a new preview supersedes an old one.
        """
        if _winsound is not None:
            try:
                _winsound.PlaySound(None, _winsound.SND_PURGE)
            except Exception:  # noqa: BLE001
                pass
        try:
            import ctypes as _ct

            _ct.windll.winmm.mciSendStringW("stop quill_preview", None, 0, None)  # type: ignore[attr-defined]
            _ct.windll.winmm.mciSendStringW("close quill_preview", None, 0, None)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    def _stop_active_voice_preview(self) -> None:
        """Stop/supersede whatever voice preview is currently active.

        Bumps the generation counter first (so any in-flight callback from the
        old generation becomes a no-op the instant it checks), then best-effort
        stops the old preview's audio: SAPI5 goes through the ReadAloudController
        it already owns; every other engine plays through `_play_preview_asset`,
        stopped via `_purge_preview_playback`. Does NOT stop an old preview's
        synthesis if it is still computing (e.g. a Piper/Kokoro call in
        progress) -- that finishes in the background and its result is
        discarded when the stale generation check fails.
        """
        self._preview_generation = getattr(self, "_preview_generation", 0) + 1
        self._cancel_preview_cue_timer()
        try:
            self._read_aloud.stop()
        except Exception:  # noqa: BLE001
            pass
        self._purge_preview_playback()

    def _cancel_preview_cue_timer(self) -> None:
        """Stop and clear any pending "generating preview" cue timer.

        Called whenever a preview generation is superseded (Task 3) or
        whenever its synthesis completes on its own -- success or error --
        so a stray cue never fires after the preview it belonged to is
        already over (see ``_synth_done`` and ``_finish_background_task``).
        """
        timer = getattr(self, "_preview_cue_timer", None)
        if timer is not None:
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001
                pass
            self._preview_cue_timer = None

    def _fire_generating_cue(self, generation: int) -> None:
        """One-shot "still generating" cue -- fires only if *generation* is
        still current (the ~400ms delay elapsed before synthesis finished)."""
        if getattr(self, "_preview_generation", 0) != generation:
            return
        post_sound(SoundEvent.VOICE_PREVIEW_GENERATING)
        if getattr(self.settings, "voice_preview_announce_generating", True):
            self._announce("Generating preview, please wait.")

    def _play_preview_asset(
        self, sample_path: Path, still_current: Callable[[], bool] | None = None
    ) -> None:
        """Play a preview clip so Stop can cut it mid-phrase.

        Playback is asynchronous and this method returns only when the clip
        finishes or ``still_current`` reports the preview was superseded -- at
        which point it purges the audio. A blocking play (the old behavior)
        could not be interrupted: Stop's SND_PURGE only cancels async sounds,
        so speech ran to the end regardless of Stop."""
        import time as _time

        current = still_current if still_current is not None else (lambda: True)
        suffix = sample_path.suffix.lower()
        if suffix == ".wav" and _winsound is not None:
            _winsound.PlaySound(str(sample_path), _winsound.SND_FILENAME | _winsound.SND_ASYNC)
            _await_playback(
                duration=_wav_duration_seconds(sample_path),
                still_current=current,
                purge=self._purge_preview_playback,
                sleep=_time.sleep,
                now=_time.monotonic,
            )
            return
        # MP3 and other formats: use Windows MCI for in-process playback (async
        # + polling so a superseding Stop takes effect immediately, not after
        # the whole clip). This avoids opening an external media player.
        try:
            import ctypes as _ct

            _winmm = _ct.windll.winmm  # type: ignore[attr-defined]
            _alias = "quill_preview"
            _path = str(sample_path).replace('"', "")
            _winmm.mciSendStringW(f'open "{_path}" type mpegvideo alias {_alias}', None, 0, None)
            try:
                _winmm.mciSendStringW(f"play {_alias}", None, 0, None)
                buf = _ct.create_unicode_buffer(64)
                while True:
                    if not current():
                        break
                    _winmm.mciSendStringW(f"status {_alias} mode", buf, 64, None)
                    if buf.value != "playing":
                        break
                    _time.sleep(0.05)
            finally:
                _winmm.mciSendStringW(f"close {_alias}", None, 0, None)
            return
        except (AttributeError, OSError):
            pass
        if sys.platform == "darwin":
            import subprocess as _subprocess

            _subprocess.Popen(["afplay", str(sample_path)])  # noqa: S603,S607
            return
        import os as _os

        _os.startfile(str(sample_path))

    def _preview_voice(
        self,
        engine: str,
        voice_id: str,
        *,
        live: bool = False,
        text: str | None = None,
        on_state_change: Callable[[str], None] | None = None,
    ) -> None:
        """Preview *voice_id* through *engine* on a background thread.

        ``live`` True means the voice is downloaded and ready, so synthesize the
        preview phrase with the real model. ``live`` False (the voice is not yet
        downloaded) plays the bundled pre-recorded sample instead, so the user
        can still hear what the voice sounds like before downloading; if no
        sample ships for it, we say so rather than failing silently.

        Starting a preview always stops/supersedes whatever preview was
        previously active (see ``_stop_active_voice_preview``): its playback is
        cut short and its completion callback becomes a no-op, so two previews
        started in quick succession never overlap.
        """
        import tempfile as _tmpfile
        from pathlib import Path as _Path

        self._stop_active_voice_preview()
        my_generation = self._preview_generation

        def _still_current() -> bool:
            return getattr(self, "_preview_generation", 0) == my_generation

        def _report(state: str) -> None:
            if on_state_change is not None and _still_current():
                self._wx.CallAfter(on_state_change, state)

        sample = text or self._PREVIEW_TEXT
        s = self.settings

        # Not downloaded: play the bundled pre-recorded sample (same phrase the
        # live synthesis uses), or explain that none is available.
        if not live:
            preview_sample = self._voice_preview_sample_path(engine, voice_id)
            if preview_sample is None:
                self._set_status("Download this voice to hear a preview.")
                return

            def _play_sample(_progress: Callable[[str, int, int], None]) -> object:
                _report("playing")
                try:
                    self._play_preview_asset(preview_sample, _still_current)
                except Exception:
                    _report("idle")
                    raise
                return None

            def _sample_done(_r: object) -> None:
                if _still_current():
                    self._set_status("Preview finished")
                _report("idle")

            self._run_background_task(
                f"Previewing {engine} voice",
                _play_sample,
                _sample_done,
            )
            return

        # sapi5: delegate to ReadAloudController so SAPI5/COM runs on its own
        # dedicated thread, avoiding the "started a loop" error from ThreadPoolExecutor.
        if engine == "sapi5":
            try:
                _report("playing")
                self._read_aloud.start(
                    sample,
                    0,
                    voice_id,
                    engine_name="sapi5",
                    rate=s.read_aloud_rate,
                    volume=s.read_aloud_volume / 100.0,
                    pitch=s.read_aloud_pitch,
                    on_state_change=lambda state: (
                        (self._wx.CallAfter(self._set_status, "Preview finished"), _report("idle"))
                        if state in ("idle", "error") and _still_current()
                        else None
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                self._set_status(f"Preview failed: {exc}")
                _report("idle")
            return

        # ElevenLabs previews also cost quota, so gate them on the same per-session
        # consent and resolve the key on the UI thread before the worker runs.
        el_key = ""
        el_model = ""
        if engine == "elevenlabs":
            el_params = self._elevenlabs_read_aloud_params("elevenlabs")
            if el_params is None:
                return
            el_key, _el_voice, el_model = el_params

        def _work(_progress: Callable[[str, int, int], None]) -> object:
            with _tmpfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
                wav = _Path(fh.name)
            try:
                if engine == "dectalk":
                    exe = discover_dectalk_executable(s.read_aloud_dectalk_executable)
                    if exe is None:
                        raise ReadAloudUnavailableError("DECtalk executable not configured")
                    synthesize_to_file_with_dectalk(
                        sample,
                        wav,
                        executable_path=exe,
                        voice=voice_id,
                        rate=s.read_aloud_dectalk_rate,
                    )
                elif engine == "piper":
                    exe = discover_piper_executable(s.read_aloud_piper_executable)
                    if exe is None:
                        raise ReadAloudUnavailableError("Piper executable not configured")
                    synthesize_with_piper(
                        sample,
                        wav,
                        executable_path=exe,
                        model_path=resolve_piper_model_path(voice_id),
                    )
                elif engine == "kokoro":
                    synthesize_with_kokoro(
                        sample,
                        wav,
                        voice=voice_id,
                        speed=s.read_aloud_kokoro_speed,
                    )
                elif engine == "espeak":
                    exe = discover_espeak_executable(s.read_aloud_espeak_executable)
                    if exe is None:
                        raise ReadAloudUnavailableError("eSpeak-NG not found")
                    synthesize_with_espeak(
                        sample,
                        wav,
                        executable_path=exe,
                        voice=voice_id,
                        rate=s.read_aloud_espeak_rate,
                    )
                elif engine == "elevenlabs":
                    from quill.core.ai import elevenlabs_tts

                    wav.write_bytes(
                        elevenlabs_tts.synthesize_wav(
                            sample, el_key, voice=voice_id, model=el_model
                        )
                    )
                elif engine == "macos":
                    synthesize_with_macos(
                        sample,
                        wav,
                        voice=voice_id,
                        rate=s.read_aloud_macos_rate,
                    )
                else:
                    raise ReadAloudUnavailableError(f"Unknown engine: {engine}")
                _report("playing")
                self._play_preview_asset(wav, _still_current)
            except Exception:
                _report("idle")
                raise
            finally:
                try:
                    wav.unlink(missing_ok=True)
                except OSError:
                    pass
            return None

        def _synth_done(_r: object) -> None:
            # Synthesis reported success -- the pending cue is no longer
            # relevant regardless of whether this generation is still
            # current, so cancel it before anything else.
            self._cancel_preview_cue_timer()
            if _still_current():
                self._set_status("Preview finished")
            _report("idle")

        _report("generating")
        self._preview_cue_timer = self._wx.CallLater(400, self._fire_generating_cue, my_generation)
        self._run_background_task(
            f"Previewing {engine} voice",
            _work,
            _synth_done,
        )
