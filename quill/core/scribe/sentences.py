"""Everything Scribe for Documents says, and when (PRD 7.4, 7.4a, 11).

The rules:

* Only the app holding the queue's runner lock speaks; the others show the
  same state silently (:class:`Speaker` is asked by that app only).
* Start, the result and errors are always spoken and always name Scribe for
  Documents (SCR-POL-1). Stage changes and the 25, 50 and 75 percent
  milestones of the *whole job* follow "Speak each stage": only while a QUILL
  app is in front (the default), always, or never. Intermediate stages may
  drop the "Scribe for Documents:" prefix.
* Each stage is said once; a percent between milestones is shown, never said.
* An error says the server's own sentence (Scribe writes it for people). The
  QUILL code is for Copy Details and is never spoken.
* Messages name the running app (QUILL, QUILL Lite), never a fixed "QUILL".

wx-free, no I/O.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.scribe import PRODUCT_NAME
from quill.core.scribe.model import format_label, formats_phrase, stage_words
from quill.core.scribe.queue import (
    DONE,
    DOWNLOADING,
    NEEDS_PASSWORD,
    NEEDS_SIGNIN,
    UPLOADING,
    Job,
)

MILESTONES = (25, 50, 75)


def friendly_folder(folder: str | Path) -> str:
    """``Documents\\Scribe for Documents\\Notes`` rather than the whole path."""
    text = str(folder)
    home = os.environ.get("USERPROFILE") or str(Path.home())
    if home and text.lower().startswith(home.lower().rstrip("\\/") + os.sep):
        return text[len(home.rstrip("\\/")) + 1 :]
    return text


def start_sentence(job: Job) -> str:
    if job.reuse:
        return f"{PRODUCT_NAME} is making {formats_phrase(job.formats)} from {job.display_name}."
    return f"{PRODUCT_NAME}: sending {job.display_name}, for {formats_phrase(job.formats)}."


def stage_sentence(job: Job, *, prefix: bool = False) -> str:
    """``"Notes.pdf, adding image descriptions."`` -- once per stage."""
    if job.state == UPLOADING:
        words = "uploading"
    elif job.state == DOWNLOADING:
        words = f"downloading {format_label(job.format)}"
    else:
        words = stage_words(job.stage) if job.stage else "converting"
        if job.format and len(job.formats) > 1 and job.stage in ("convert", "start"):
            words = f"{words} to {format_label(job.format)}"
    text = f"{job.display_name}, {words}."
    return f"{PRODUCT_NAME}: {text}" if prefix else text


def milestone_crossed(before: float, after: float) -> int | None:
    """The 25, 50 or 75 percent mark *after* passed and *before* had not."""
    crossed = [m for m in MILESTONES if before * 100 < m <= after * 100]
    return crossed[-1] if crossed else None


def percent_sentence(job: Job, percent: int) -> str:
    return f"{job.display_name}, {percent} percent."


def _join_names(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def result_sentence(
    job: Job, *, app_name: str, opened: str = "", offer: bool = False, note: str = ""
) -> str:
    """The one sentence a finished job gets (FUX-04).

    *opened* names what is now open ("Word is open in QUILL"); with nothing
    opened the sentence ends by saying where to open it from. *note* is what an
    app did to the result before it was said ("with 12 chapter markers"), so
    that step never needs a second message.
    """
    names = [Path(path).name for path in job.outputs.values()]
    folder = friendly_folder(job.folder) if job.folder else ""
    where = f" in {folder}" if folder else ""
    made = _join_names(names) if names else formats_phrase(job.formats)
    extra = f", {note}" if note else ""
    text = f"{PRODUCT_NAME} made {made}{extra}{where}."
    if opened:
        return f"{text} {opened}."
    if offer or names:
        return f"{text} Open it from Scribe Conversions."
    return text


def error_sentence(job: Job, message: str) -> str:
    return f"{PRODUCT_NAME} could not convert {job.display_name}: {message}"


def needs_you_sentence(job: Job, *, app_name: str) -> str:
    """Said once when a background job needs the person (7.4a)."""
    if job.state == NEEDS_PASSWORD:
        return f"{job.display_name} needs its password. Open Scribe Conversions to enter it."
    if job.state == NEEDS_SIGNIN:
        return (
            f"Your {PRODUCT_NAME} sign-in has ended. Conversions are paused until you "
            "sign in again."
        )
    return ""


def pages_sentence(message: str) -> str:
    """``needs_purchase``: the server's sentence, then where Buy Pages is."""
    return f"{message} Use Buy Pages in Scribe Conversions, then Retry."


def busy_sentence(app_name: str) -> str:
    """``rate_limited``, once per job (QUILL-SCRIBE-BUSY): the queue waits a minute."""
    return f"{PRODUCT_NAME} asked {app_name} to slow down; trying again in a minute."


def batch_sentence(jobs: list[Job]) -> str:
    """Said once when the last file of a batch finishes (7.4): what was made and
    what was not. Each file's own result or error was said as it happened."""
    made = [job.display_name for job in jobs if job.state == DONE]
    missed = [job.display_name for job in jobs if job.state != DONE]
    count = len(jobs)
    head = f"{PRODUCT_NAME} finished {count} file" + ("" if count == 1 else "s")
    if not missed:
        return f"{head}: all were made."
    if not made:
        return f"{head}: none were made. Scribe Conversions has the details."
    return (
        f"{head}. Made: {_join_names(made)}. Not made: {_join_names(missed)}; "
        "Scribe Conversions has the details."
    )


def offline_sentence(job: Job, *, app_name: str) -> str:
    if job.state == UPLOADING or not job.document_id:
        return f"Upload of {job.display_name} was interrupted; {app_name} will resume it."
    return f"Reconnecting to {PRODUCT_NAME}; your conversion is still running there."


def gone_sentence(job: Job) -> str:
    return f"{job.display_name} is no longer in your {PRODUCT_NAME} account."


def cancel_waiting_sentence(job: Job, *, app_name: str) -> str:
    return (
        f"{app_name} stopped waiting for {job.display_name}. Scribe will still finish it "
        "and may use pages; it stays in My Scribe Documents."
    )


def status_sentence(job: Job | None) -> str:
    """Scribe Status: the current job, once, without opening anything."""
    if job is None:
        return f"No {PRODUCT_NAME} conversions are running."
    parts = [stage_sentence(job).rstrip(".")]
    percent = int(round(job.progress * 100))
    if percent:
        parts.append(f"{percent} percent")
    if job.eta_seconds:
        minutes = max(1, round(job.eta_seconds / 60))
        parts.append(f"about {minutes} minute" + ("" if minutes == 1 else "s"))
    return ", ".join(parts) + "."


def closed_while_sentence(titles: list[str], *, app_name: str, folder: str) -> str:
    """Said once after startup: what finished while the app was closed."""
    count = len(titles)
    noun = "document" if count == 1 else "documents"
    return (
        f"{PRODUCT_NAME} finished {count} {noun} while {app_name} was closed: "
        f"{_join_names(titles)}, in {friendly_folder(folder)}."
    )


def sign_out_question(waiting: int, *, app_name: str = "QUILL") -> str:
    if waiting <= 0:
        return ""
    noun = "conversion is" if waiting == 1 else "conversions are"
    count = "One" if waiting == 1 else _number_word(waiting)
    return (
        f"{count} {noun} waiting. Signing out stops {app_name} waiting for them; they still "
        "finish in your Scribe account."
    )


def _number_word(count: int) -> str:
    words = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    return words[count] if 0 <= count < len(words) else str(count)


@dataclass(slots=True)
class Speaker:
    """Decides what the holding app says about one job, once each (7.4a)."""

    speak_stages: str = "front"
    _said_stage: dict[str, str] = field(default_factory=dict)
    _progress: dict[str, float] = field(default_factory=dict)
    _said_once: set[tuple[str, str]] = field(default_factory=set)

    def stages_allowed(self, app_in_front: bool) -> bool:
        if self.speak_stages == "never":
            return False
        if self.speak_stages == "always":
            return True
        return app_in_front

    def on_change(self, job: Job, *, app_in_front: bool) -> str:
        """The sentence for this change to *job*, or ``""`` to stay silent."""
        key = f"{job.state}:{job.format}:{job.stage}"
        said = ""
        if self._said_stage.get(job.id) != key:
            self._said_stage[job.id] = key
            if self.stages_allowed(app_in_front):
                said = stage_sentence(job)
        before = self._progress.get(job.id, 0.0)
        self._progress[job.id] = max(before, job.progress)
        crossed = milestone_crossed(before, job.progress)
        if not said and crossed and self.stages_allowed(app_in_front):
            said = percent_sentence(job, crossed)
        return said

    def once(self, job: Job, kind: str) -> bool:
        """True the first time *kind* happens for *job* (busy, offline...)."""
        marker = (job.id, kind)
        if marker in self._said_once:
            return False
        self._said_once.add(marker)
        return True

    def forget(self, job_id: str, kind: str) -> None:
        self._said_once.discard((job_id, kind))


__all__ = [
    "MILESTONES",
    "Speaker",
    "batch_sentence",
    "busy_sentence",
    "cancel_waiting_sentence",
    "closed_while_sentence",
    "error_sentence",
    "friendly_folder",
    "gone_sentence",
    "milestone_crossed",
    "needs_you_sentence",
    "offline_sentence",
    "pages_sentence",
    "percent_sentence",
    "result_sentence",
    "sign_out_question",
    "stage_sentence",
    "start_sentence",
    "status_sentence",
]
