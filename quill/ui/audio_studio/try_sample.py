"""Try a Sample on the Studio's summary page: hear the run before it starts (FUX-11).

A long narration is the moment this is for: an hour of synthesis before
finding the voice, the pace or the sounder was wrong. Try a Sample speaks the
opening words of the first document through exactly the pipeline the run uses
-- the same engine spec, assembly options, pronunciation dictionaries, voice
rotation and casting (:mod:`quill.ui.audio_studio.run_setup`) -- into a
temporary folder, plays it, and says what it measured: how long it took here,
and what the whole run should take, play for and weigh at that pace.

What it never does: write into the source or output folder, change a setting,
add to the voice blacklist, or stand in for the real run. The temporary folder
is removed when the wizard closes. A finished sample is kept only for the
settings it was made with; when any of them changes, its result says it is
out of date (:mod:`quill.core.rehearsal`). Pressing the button again replays a
current sample, makes a new one when the settings changed, and stops one that
is still being made.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import threading
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import wx

from quill.core.i18n import _
from quill.core.rehearsal import (
    SampleResult,
    estimate_sentence,
    fingerprint,
    limits_sentence,
    stale_sentence,
)
from quill.ui.audio_studio.request import BatchSpeechRequest
from quill.ui.audio_studio.run_setup import (
    chapter_options,
    effective_format,
    output_suffix,
    shaping_settings,
    synthesis_spec,
)
from quill.ui.dpi import dip_size
from quill.ui.spoken_name import set_spoken_name

_log = logging.getLogger(__name__)

#: How much of the first document a sample speaks: about thirty seconds at an
#: ordinary narration pace, enough to judge a voice, pace and sounder.
SAMPLE_WORDS = 80

#: The bit rate the audiobook assembler encodes at (``estimate_output``'s
#: default), used to estimate a book's size from the sample's length.
BOOK_KBPS = 96

#: The pause between "Sample ready." and the sample itself, so the sentence is
#: not spoken over the start of the sound.
PLAY_DELAY_MS = 1200

NO_SAMPLE_YET = (
    "No sample yet. Try a Sample speaks about the first 30 seconds of the first "
    "document with these settings, plays it, and estimates the whole run. "
    "Nothing is saved beside your documents."
)


class SampleStopped(Exception):  # noqa: N818 - a stop request, not an error
    """Raised inside the sample's progress callback when Stop was pressed."""


@dataclass(slots=True)
class SampleOutcome:
    """A finished sample: what to play and what it measured."""

    result: SampleResult
    play_path: Path
    summary: str  # what was made, in one sentence
    whole: str  # the whole run, as the estimate names it


def sample_fingerprint(host: Any, req: BatchSpeechRequest, first: Path | None) -> str:
    """The settings a sample proves, plus which document and how much of it."""
    from quill.ui import batch_speech_runner as runner

    dictionaries = runner._active_pronunciation_dictionaries(host, req.engine, req.source_folder)
    settings = shaping_settings(host, req, dictionaries)
    settings.update(
        first=str(first or ""),
        words=SAMPLE_WORDS,
        book=[req.make_book, req.book_format],
        heading_level=req.chapter_heading_level,
    )
    return fingerprint(settings)


def first_document(req: BatchSpeechRequest) -> tuple[list[Path], Path | None]:
    """The run's documents, found exactly as the run finds them, and the first."""
    from quill.core.speech.batch_export import discover_files

    files = discover_files(
        req.source_folder,
        list(req.extensions),
        req.recursive,
        include_glob=req.include_glob,
        exclude_glob=req.exclude_glob,
        max_file_bytes=req.max_file_bytes,
    )
    return files, (files[0] if files else None)


def _wav_seconds(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as wav:
            rate = wav.getframerate()
            return wav.getnframes() / rate if rate else None
    except (OSError, wave.Error, EOFError):
        return None


def _playable_wav(made: Path, folder: Path) -> Path:
    """*made* itself when it is WAV; otherwise a WAV decoded from it for playback."""
    if made.suffix.lower() == ".wav":
        return made
    from quill.core.audio.assemble import build_decode_to_wav_command
    from quill.core.speech.ffmpeg import find_ffmpeg
    from quill.stability.safe_subprocess import run_subprocess_safely

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        raise RuntimeError("FFmpeg is needed to play an MP3 or M4B sample.")
    out = folder / "sample-play.wav"
    done = run_subprocess_safely(
        build_decode_to_wav_command(ffmpeg, made, out), timeout_seconds=120.0
    )
    if getattr(done, "returncode", 1) != 0 or not out.is_file():
        raise RuntimeError("The sample was made but could not be decoded for playback.")
    return out


def make_sample(
    host: Any, req: BatchSpeechRequest, folder: Path, stop: threading.Event
) -> SampleOutcome:
    """Speak the first document's opening words with the run's own settings.

    Runs off the UI thread. Writes only inside *folder*. Raises
    :class:`SampleStopped` when *stop* is set between chunks, and
    ``RuntimeError`` (or the pipeline's own error) with a reason otherwise.
    """
    from quill.core.speech.batch_export import count_document_words
    from quill.core.speech.document_speech import synthesize_document_to_chaptered_file
    from quill.ui import batch_speech_runner as runner

    files, first = first_document(req)
    if first is None:
        raise RuntimeError("No matching documents were found in that folder.")
    print_fp = sample_fingerprint(host, req, first)
    word_counts = [count_document_words(path) for path in files]
    total_words = sum(word_counts)
    sample_words = min(SAMPLE_WORDS, word_counts[0])
    dictionaries = runner._active_pronunciation_dictionaries(host, req.engine, req.source_folder)
    sound = runner._resolve_chapter_sound_path(host, folder) if req.sound_enabled else None

    def check_stop(_done: int, _total: int) -> None:
        if stop.is_set():
            raise SampleStopped

    fmt = effective_format(req)
    started = time.monotonic()
    made = synthesize_document_to_chaptered_file(
        first,
        folder / f"sample{output_suffix(fmt)}",
        synthesis_spec(req),
        chapter_options(req, sound_path=sound),
        work_dir=folder / "work",
        pronunciation_dictionaries=dictionaries,
        combine_headings=req.combine_headings,
        voice_rotation=list(req.round_robin_voices),
        casting_rules=list(req.casting_rules),
        on_progress=check_stop,
        max_words=SAMPLE_WORDS,
    )
    elapsed = time.monotonic() - started
    if stop.is_set():
        raise SampleStopped
    deliverable = made.with_tones_path or made.output_path
    play = _playable_wav(deliverable, folder)
    seconds = _wav_seconds(play)
    if req.make_book:
        size = None if seconds is None else int(BOOK_KBPS * 1000 / 8 * seconds)
        kind = f"a {req.book_format.upper()} audiobook"
    else:
        size = deliverable.stat().st_size
        kind = f"{fmt.upper()} files"
    result = SampleResult(
        fingerprint=print_fp,
        covered=f"the first {sample_words} words of {first.name}",
        sample_units=float(sample_words),
        total_units=float(total_words),
        elapsed_seconds=elapsed,
        output_bytes=size,
        output_seconds=seconds,
    )
    count = len(files)
    what = "the one document" if count == 1 else f"all {count} documents"
    voice = req.voice or "the engine's default voice"
    summary = f"Sample of {first.name}, spoken by {req.engine} with {voice}, as {kind}."
    return SampleOutcome(result=result, play_path=play, summary=summary, whole=what)


def describe(outcome: SampleOutcome, req: BatchSpeechRequest) -> str:
    """The result field's text: what was made, the estimate and the limits."""
    lines = [
        outcome.summary,
        estimate_sentence(outcome.result, job=f"narrating {outcome.whole}"),
        limits_sentence(outcome.result.covered),
    ]
    if req.translation_targets:
        lines.append("Translated editions are not part of the sample.")
    if req.make_book:
        lines.append("The book's size assumes 96 kbps, the rate the book is built at.")
    return "\n".join(lines)


class SampleControls:
    """The summary page's Try a Sample button and its read-only result."""

    def __init__(self, page: wx.Window, sizer: wx.Sizer, host: Any) -> None:
        self._page = page
        self._host = host
        self.button = wx.Button(page, label=_("Try a Sam&ple"), name="audio_studio.try_sample")
        self.button.SetHelpText(
            "Speaks about the first 30 seconds of the first document with every "
            "setting above, plays it, and estimates how long the whole run takes "
            "and how large it will be. Nothing is saved beside your documents. "
            "Press again to stop a sample being made or playing, or to hear it again."
        )
        self.result = wx.TextCtrl(
            page,
            value=NO_SAMPLE_YET,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            name="audio_studio.sample_result",
        )
        self.result.SetMinSize(dip_size(self.result, -1, 110))
        set_spoken_name(self.result, _("Sample result"))
        self.result.SetHelpText(
            "What the last sample made, what it measured on this computer, what "
            "the whole run should take, and what a sample cannot prove. It says "
            "out of date when a setting changed after the sample was made."
        )
        sizer.Add(self.button, 0, wx.LEFT | wx.TOP, 12)
        sizer.Add(self.result, 0, wx.EXPAND | wx.ALL, 12)
        self.button.Bind(wx.EVT_BUTTON, lambda _e: self.press())
        page.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self._req: BatchSpeechRequest | None = None
        self._outcome: SampleOutcome | None = None
        self._stop: threading.Event | None = None
        self._folders: list[Path] = []
        self._text = NO_SAMPLE_YET
        self._playing = False
        self._generation = 0

    # -- state ---------------------------------------------------------------

    @property
    def running(self) -> bool:
        return self._stop is not None

    def show_for(self, req: BatchSpeechRequest) -> None:
        """The summary page is showing *req*: offer the button, and mark staleness."""
        self._req = req
        narrating = bool(req.extensions) and not req.dry_run
        self.button.Show(narrating)
        self.result.Show(narrating)
        if self._outcome is not None:
            current = self._is_current()
            self._set_text(self._text if current else f"{stale_sentence()}\n{self._text}")
        self._page.Layout()

    def _is_current(self) -> bool:
        if self._outcome is None or self._req is None:
            return False
        try:
            _files, first = first_document(self._req)
            return self._outcome.result.is_current(sample_fingerprint(self._host, self._req, first))
        except Exception:  # noqa: BLE001 - an unreadable folder is "not current"
            return False

    def _set_text(self, text: str) -> None:
        self.result.SetValue(text)

    def _say(self, text: str) -> None:
        announce = getattr(self._host, "_announce", None)
        if callable(announce):
            announce(text)

    # -- the button ----------------------------------------------------------

    def press(self) -> None:
        """Stop what is going on, replay a current sample, or make a new one."""
        if self.running:
            self.stop()
            return
        if self._playing:
            self._stop_playback()  # the sound stopping is the answer; nothing is said
            return
        if self._outcome is not None and self._is_current() and self._outcome.play_path.is_file():
            self._play(self._outcome.play_path)
            return
        self.start(changed=self._outcome is not None)

    def start(self, *, changed: bool = False) -> None:
        req = self._req
        if req is None:
            return
        from quill.ui import batch_speech_runner as runner

        if not runner._engine_available(self._host).get(req.engine, True):
            self._set_text(
                f"The {req.engine} voice engine is not fully installed yet, so no "
                "sample can be made. Download Optional Components installs it."
            )
            self._say(str(_("No sample: the voice engine is not installed.")))
            return
        parent = Path(req.temp_folder) if req.temp_folder.strip() else None
        folder = Path(tempfile.mkdtemp(prefix="quill-studio-sample-", dir=parent))
        self._folders.append(folder)
        stop = threading.Event()
        self._stop = stop
        self.button.SetLabel(str(_("Stop the Sam&ple")))
        self._set_text("Making a sample of the first document with these settings...")
        if changed:
            self._say(str(_("Settings changed; making a new sample. Press again to stop.")))
        else:
            self._say(str(_("Making a sample. Press again to stop.")))

        def work() -> None:
            try:
                outcome: SampleOutcome | None = make_sample(self._host, req, folder, stop)
                error: BaseException | None = None
            except BaseException as exc:  # noqa: BLE001 - delivered on the UI thread
                outcome, error = None, exc
            wx.CallAfter(self._finished, stop, req, outcome, error)

        threading.Thread(  # GATE-40-OK: one-shot sample; Stop sets its event and close orphans it
            target=work, daemon=True, name="studio-try-sample"
        ).start()

    def stop(self) -> None:
        """Stop the sample being made; nothing is kept."""
        if self._stop is not None:
            self._stop.set()
        self._stop = None
        self.button.SetLabel(str(_("Try a Sam&ple")))
        self._set_text("Sample stopped. Nothing was kept.")
        self._say(str(_("Sample stopped.")))

    def halt(self) -> None:
        """The page is being left: stop making and playing, silently."""
        if self._stop is not None:
            self._stop.set()
            self._stop = None
            self._set_text("Sample stopped when you left this page. Nothing was kept.")
        self._stop_playback()
        try:
            self.button.SetLabel(str(_("Try a Sam&ple")))
        except RuntimeError:
            pass  # the page is gone

    def _finished(
        self,
        stop: threading.Event,
        req: BatchSpeechRequest,
        outcome: SampleOutcome | None,
        error: BaseException | None,
    ) -> None:
        if stop is not self._stop or stop.is_set():
            return  # stopped, the page was left, or the window closed
        self._stop = None
        try:
            self.button.SetLabel(str(_("Try a Sam&ple")))
        except RuntimeError:
            return  # the page is gone
        if outcome is None:
            reason = str(error) if error is not None else "unknown"
            self._text = f"The sample could not be made: {reason}"
            self._set_text(self._text)
            self._say(str(_("The sample could not be made. The reason is in Sample result.")))
            return
        self._outcome = outcome
        self._text = describe(outcome, req)
        self._set_text(self._text)
        self._say(str(_("Sample ready.")))
        # Let the short sentence finish before the sample starts, so the two
        # are not heard on top of each other; the estimate stays in the field.
        self._play(outcome.play_path, delay_ms=PLAY_DELAY_MS)

    # -- playback ------------------------------------------------------------

    def _play(self, wav: Path, *, delay_ms: int = 0) -> None:
        self._generation += 1
        generation = self._generation
        self._playing = True
        self.button.SetLabel(str(_("Stop the Sam&ple")))
        if delay_ms > 0:
            wx.CallLater(delay_ms, self._start_sound, wav, generation)
        else:
            self._start_sound(wav, generation)

    def _start_sound(self, wav: Path, generation: int) -> None:
        if generation != self._generation or not self._playing:
            return  # stopped, or the page was left, during the pause
        try:
            import winsound

            winsound.PlaySound(str(wav), winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception as exc:  # noqa: BLE001 - no sound device, or not Windows
            _log.info("Could not play the Studio sample: %s", exc)
            self._playing = False
            self.button.SetLabel(str(_("Try a Sam&ple")))
            self._set_text(f"{self._text}\nThe sample could not be played here: {exc}")
            return
        seconds = _wav_seconds(wav) or 0.0
        wx.CallLater(int(seconds * 1000) + 300, self._sound_ended, generation)

    def _sound_ended(self, generation: int) -> None:
        if generation != self._generation or not self._playing:
            return
        self._playing = False
        try:
            self.button.SetLabel(str(_("Try a Sam&ple")))
        except RuntimeError:
            pass  # the page is gone

    def _stop_playback(self) -> None:
        self._generation += 1
        was_playing, self._playing = self._playing, False
        if was_playing:
            try:
                import winsound

                winsound.PlaySound(None, 0)
            except Exception:  # noqa: BLE001 - nothing playing, or not Windows
                pass
            try:
                self.button.SetLabel(str(_("Try a Sam&ple")))
            except RuntimeError:
                pass  # the page is gone

    # -- cleanup -------------------------------------------------------------

    def _on_destroy(self, evt: wx.WindowDestroyEvent) -> None:
        if evt.GetEventObject() is self._page:
            self.close()
        evt.Skip()

    def close(self) -> None:
        """Stop playback and any sample in progress, and remove the samples."""
        if self._stop is not None:
            self._stop.set()
            self._stop = None
        self._playing = True  # make sure the sound is purged
        self._stop_playback()
        for folder in self._folders:
            shutil.rmtree(folder, ignore_errors=True)
        self._folders.clear()
        self._outcome = None
