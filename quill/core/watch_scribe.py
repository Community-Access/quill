"""Watch action: Convert with Scribe for Documents (PRD 8.1.6, WATCH-7).

Files that arrive in a watched folder go to Scribe for Documents, through the
**family queue**, strictly one after another -- the batch exception Pneuma
approved on 2026-11-21 covers a watch folder too (PRD 7.4). The action adds
one job, wakes the app's queue runner and waits on the watch worker's thread
until the job is done, failed, or waiting for the person. That wait is what
makes the folder strictly one at a time: the worker takes the next file only
after this one has finished.

* **Consent per profile** (``requires_consent``, as
  :class:`~quill.core.watch_transcribe.CloudTranscribeAction`): the registry
  refuses to run it until the profile's ``consent`` option is on. Nothing else
  is ever a standing consent (PRD 10.1.1).
* **The profile names the formats** (``formats``: Scribe's format ids) and may
  name its own ``settings``; without them each file uses the person's Scribe
  for Documents Options (local defaults) at the moment it is sent, so a
  change in Options is never stale here.
* **Only the 23 types Scribe takes** are sent, up to 500 MB
  (:mod:`quill.core.scribe.inputs`). Anything else is skipped, untouched.
* **What is said** is what every watch result says: the watch queue's own
  outcome. The Scribe controller stays silent for these jobs (``open_as ==
  "watch"``), so nothing is said twice. A sign-in problem is said once per
  profile, not once per file: a folder of forty files waiting for sign-in is
  one sentence (accessibility review, 2026-11-21).
* **Background jobs never open a dialog.** A file that needs its password
  waits in Conversions on This Computer, and the outcome says so.

wx-free; the app gives the action ``on_wake`` (start its runner) and
``signed_in`` once it has a Scribe controller.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .watch_actions import WatchActionOutcome, WatchItem, _BaseAction

#: The open_as marker of a watch job: the controller speaks nothing for it.
WATCH_OPEN_AS = "watch"
#: How long one file may take before the folder moves on (it carries on in
#: Conversions on This Computer either way).
_WAIT_LIMIT_S = 4 * 60 * 60.0
_POLL_S = 2.0


@dataclass(slots=True)
class ScribeConvertAction(_BaseAction):
    """Send each arriving document to Scribe for Documents."""

    action_id: str = "scribe_convert"
    label: str = "Convert with Scribe for Documents"
    description: str = (
        "Send each arriving document (PDF, pictures, Office, OpenDocument, text, EPUB or "
        "MOBI) to Scribe for Documents (Pneuma Solutions), one after another, and save what "
        "it makes in your Scribe download folder. Uses Scribe pages from your account."
    )
    requires_consent: bool = True
    app_name: str = "QUILL"
    #: Start (or wake) this app's Scribe queue runner. Called on the worker thread.
    on_wake: Callable[[], None] | None = None
    #: Whether the person is signed in to Scribe right now.
    signed_in: Callable[[], bool] | None = None
    queue_factory: Callable[[], Any] | None = None
    clock: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    wait_limit_s: float = _WAIT_LIMIT_S
    #: (profile, cause) already said once, so a full folder is one sentence.
    _said: set[tuple[str, str]] = field(default_factory=set)

    def _formats(self, options: Mapping[str, object]) -> list[str]:
        from quill.core.scribe.model import valid_formats

        return valid_formats(options.get("formats")) or ["docx"]

    def validate(self, options: Mapping[str, object]) -> list[str]:
        from quill.core.scribe import unavailable_reason
        from quill.core.scribe.model import valid_formats

        reason = unavailable_reason(self.app_name)
        if reason:
            return [reason]
        if "formats" in options and not valid_formats(options.get("formats")):
            return ["Choose at least one format for Scribe for Documents to make."]
        return []

    def preview(self, item: WatchItem, options: Mapping[str, object]) -> str:
        from quill.core.scribe.inputs import refusal
        from quill.core.scribe.model import formats_phrase

        code, sentence = refusal(item.source_path)
        if code:
            return f"Would skip: {sentence}"
        return (
            f"Send {item.source_path.name} to Scribe for Documents (Pneuma Solutions) for "
            f"{formats_phrase(self._formats(options))}, after any file before it has "
            "finished, and save the results in your Scribe download folder. It uses "
            "Scribe pages from your account, about one for each page."
        )

    def _once(self, item: WatchItem, cause: str, message: str) -> WatchActionOutcome:
        """Fail (and so be said) the first time per profile; skip quietly after."""
        marker = (item.profile_id, cause)
        if marker in self._said:
            return WatchActionOutcome.skipped(message)
        self._said.add(marker)
        return WatchActionOutcome.failed(message)

    def _queue(self) -> Any:
        if self.queue_factory is not None:
            return self.queue_factory()
        from quill.core.scribe.queue import FamilyQueue

        return FamilyQueue()

    def run(self, item: WatchItem, options: Mapping[str, object]) -> WatchActionOutcome:
        from quill.core.scribe import PRODUCT_NAME
        from quill.core.scribe import queue as q
        from quill.core.scribe.inputs import refusal

        path = item.source_path
        code, sentence = refusal(path)
        if code:  # not one of the 23 types, or over 500 MB: nothing is sent
            return WatchActionOutcome.skipped(sentence)
        signin_message = (
            f"Watch profile needs you to sign in to {PRODUCT_NAME} before it can send files. "
            "Choose Tools, Scribe for Documents, Sign In."
        )
        if self.signed_in is not None and not self.signed_in():
            return self._once(item, "signin", signin_message)
        self._said.discard((item.profile_id, "signin"))
        settings = options.get("settings")
        if not isinstance(settings, dict):
            from quill.core.scribe.options import load_options

            settings = dict(load_options().settings)
        queue = self._queue()
        earlier = _earlier_job(queue, path)
        if earlier is not None:
            # The watch queue retries a failed file; Scribe has it already, so a
            # retry reports that job rather than uploading (and paying) again.
            return self._wait(queue, earlier, item, signin_message)
        job = q.Job(
            app=self.app_name,
            file_name=path.name,
            source_path=str(path),
            size=path.stat().st_size if path.exists() else 0,
            title=path.stem,
            formats=self._formats(options),
            settings=settings,
            open_as=WATCH_OPEN_AS,
        )
        queue.add([job])
        if self.on_wake is not None:
            self.on_wake()
        return self._wait(queue, job, item, signin_message)

    def _wait(
        self, queue: Any, job: Any, item: WatchItem, signin_message: str
    ) -> WatchActionOutcome:
        from quill.core.scribe import PRODUCT_NAME
        from quill.core.scribe import queue as q
        from quill.core.scribe.sentences import friendly_folder

        name = job.display_name
        deadline = self.clock() + self.wait_limit_s
        while True:
            found = queue.get(job.id)
            if found is None:
                return WatchActionOutcome.skipped(
                    f"{name} was removed from Conversions on This Computer."
                )
            state = found.state
            if state == q.DONE:
                made = ", ".join(Path(p).name for p in found.outputs.values()) or name
                where = f" in {friendly_folder(found.folder)}" if found.folder else ""
                first = next(iter(found.outputs.values()), "")
                return WatchActionOutcome.done(
                    f"{PRODUCT_NAME} made {made}{where}",
                    result_path=Path(first) if first else None,
                )
            if state == q.NEEDS_PASSWORD:
                return WatchActionOutcome.failed(
                    f"{name} needs its password. Open the Conversions on This Computer "
                    "window to enter it."
                )
            if state == q.NEEDS_SIGNIN:
                return self._once(item, "signin", signin_message)
            if state in (q.FAILED, q.GONE):
                return WatchActionOutcome.failed(
                    f"{PRODUCT_NAME} could not convert {name}: {found.message}"
                )
            if state == q.STOPPED:
                return WatchActionOutcome.skipped(f"Stopped waiting for {name}.")
            if self.clock() >= deadline:
                return WatchActionOutcome.skipped(
                    f"{name} is still converting; it carries on in Conversions on This Computer."
                )
            self.sleep(_POLL_S)


def _earlier_job(queue: Any, path: Path) -> Any:
    """This file's watch job from the last day, unless the person stopped it."""
    from quill.core.scribe import queue as q

    try:
        jobs = queue.jobs()
    except (OSError, TimeoutError):
        return None
    cutoff = time.time() - 24 * 60 * 60
    for job in reversed(jobs):
        if (
            job.open_as == WATCH_OPEN_AS
            and job.source_path == str(path)
            and job.created >= cutoff
            and job.state != q.STOPPED
        ):
            return job
    return None


__all__ = ["WATCH_OPEN_AS", "ScribeConvertAction"]
