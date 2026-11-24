"""Try the First Minute in Transcribe a Recording (FUX-11).

An hour-long recording transcribed with the wrong language or a model too
slow for this computer is an hour lost. **Try the First Minute** transcribes
the first minute of the first recording with exactly the job the queue would
run -- the same model, language, timestamps, spoken commands, translation,
filler removal and dashes (the host builds the ``FileJob``) -- and shows the
words with what it measured: how long the minute took here, and what the whole
recording, or every recording chosen, should take at that pace.

Nothing is written into a document or Notifications, and nothing is queued.
OpenAI's models are not offered, because every minute sent costs money. The
result is kept only for the choices it was made with; when the recording, the
model or an option changes, the window says it is out of date.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

import wx

from quill.core.rehearsal import (
    SampleResult,
    estimate_sentence,
    fingerprint,
    limits_sentence,
    stale_sentence,
)

_log = logging.getLogger(__name__)

#: How much of the recording a sample transcribes.
SAMPLE_SECONDS = 60.0

#: The words shown from a sample, at most; the rest is the job's to show.
_SHOWN_CHARS = 1500


def _job_print(job: Any) -> str:
    """Every choice that shapes the transcript, with the recording it was made on."""
    return fingerprint(asdict(job))


class FirstMinute:
    """The Try the First Minute button and what it found, for the dialog."""

    def __init__(
        self,
        dialog: Any,
        sizer: wx.Sizer,
        make_job: Callable[[Any, Path], tuple[Any, Callable[[str], str] | None]],
        announce: Callable[[str], None] | None = None,
    ) -> None:
        self._dialog = dialog
        self._make_job = make_job
        self._announce = announce
        self.button = wx.Button(dialog, label="Try the First M&inute")
        self.button.SetHelpText(
            "Transcribes only the first minute of the first recording, with the model, "
            "language and options chosen here, and shows the words and what the whole "
            "recording should take on this computer. Nothing is queued or saved. Press "
            "again to stop. With OpenAI's models it says why it does not run: they "
            "charge for every minute sent."
        )
        self.button.Bind(wx.EVT_BUTTON, lambda _e: self.press())
        sizer.Add(self.button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        dialog.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self._cancel: threading.Event | None = None
        self._result: SampleResult | None = None
        self._lines: list[str] = []

    # -- what the details box says --------------------------------------------

    @property
    def running(self) -> bool:
        return self._cancel is not None

    def lines(self) -> list[str]:
        """What the details box adds about the sample, current or out of date."""
        if self.running:
            return ["Transcribing the first minute with these choices..."]
        if self._result is None:
            return []
        job = self._current_job()
        if job is not None and self._result.is_current(_job_print(job)):
            return list(self._lines)
        return [stale_sentence(), *self._lines]

    def _current_job(self) -> Any | None:
        choice = self._dialog.current_choice()
        if choice is None or not choice.paths:
            return None
        return self._make_job(choice, choice.paths[0])[0]

    # -- the button -----------------------------------------------------------

    def press(self) -> None:
        if self.running:
            self.stop()
            return
        problem = self._dialog.sample_problem()
        if problem:
            self._say(problem)
            return
        choice = self._dialog.current_choice()
        job, rewrite = self._make_job(choice, choice.paths[0])
        total = self._dialog.total_seconds()
        count = len(choice.paths)
        cancel = threading.Event()
        self._cancel = cancel
        self.button.SetLabel("Stop the First M&inute")
        self._dialog.refresh_about()
        self._say("Transcribing the first minute. Press again to stop.")

        def work() -> None:
            from quill.core.windows_dictation.file_transcribe import (
                FileTranscriber,
                first_seconds,
            )

            try:
                clip = first_seconds(SAMPLE_SECONDS)
                transcriber = FileTranscriber(job, opener=clip, rewrite=rewrite)
                transcript: Any = transcriber.run(cancelled=cancel.is_set)
                error: BaseException | None = None
            except BaseException as exc:  # noqa: BLE001 - said on the UI thread
                transcript, error = None, exc
            wx.CallAfter(self._finished, cancel, job, total, count, transcript, error)

        threading.Thread(  # GATE-40-OK: one-shot sample; Stop sets its event, close orphans it
            target=work, daemon=True, name="transcribe-first-minute"
        ).start()

    def stop(self) -> None:
        if self._cancel is not None:
            self._cancel.set()
        self._cancel = None
        self.button.SetLabel("Try the First M&inute")
        self._dialog.refresh_about()
        self._say("Stopped. Nothing was kept.")

    def _finished(
        self,
        cancel: threading.Event,
        job: Any,
        total: float,
        count: int,
        transcript: Any,
        error: BaseException | None,
    ) -> None:
        if cancel is not self._cancel or cancel.is_set():
            return  # stopped, or the window closed
        self._cancel = None
        try:
            self.button.SetLabel("Try the First M&inute")
        except RuntimeError:
            return  # the window is gone
        if transcript is None:
            self._result = None
            self._lines = []
            self._dialog.refresh_about(
                extra=[f"The first minute could not be transcribed: {error}"]
            )
            self._say("The first minute could not be transcribed. The reason is in the details.")
            return
        name = job.path.name or str(job.path)
        heard = float(transcript.audio_seconds)
        self._result = SampleResult(
            fingerprint=_job_print(job),
            covered=f"the first {round(heard)} seconds of {name}",
            sample_units=heard,
            total_units=total,
            elapsed_seconds=float(transcript.elapsed_seconds),
        )
        whole = "this recording" if count == 1 else f"all {count} recordings"
        text = transcript.text(job.timestamps).strip() or "(no words were heard)"
        if len(text) > _SHOWN_CHARS:
            text = text[:_SHOWN_CHARS].rsplit(" ", 1)[0] + " ..."
        self._lines = [
            f"Sample: {transcript.words} words from the first minute of {name}.",
            estimate_sentence(self._result, job=f"transcribing {whole}"),
            "The first minute includes loading the model, so the rest is usually a little quicker.",
            limits_sentence(self._result.covered),
            "The words:",
            text,
        ]
        if transcript.notice:
            self._lines.insert(1, transcript.notice)
        self._dialog.refresh_about()
        self._say("First minute transcribed. The words and the estimate are in the details.")

    def _say(self, text: str) -> None:
        if self._announce is not None:
            self._announce(text)

    def _on_destroy(self, evt: wx.WindowDestroyEvent) -> None:
        if evt.GetEventObject() is self._dialog and self._cancel is not None:
            self._cancel.set()
            self._cancel = None
        evt.Skip()
