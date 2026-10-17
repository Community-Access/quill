"""Quill Converter's Auphonic lifecycle: create, upload, start, wait, download.

The acting half of Process with Auphonic (the plan is
:mod:`quill.core.publish.auphonic_plan`). One :class:`Runner` sends a batch:
separate productions strictly one after another, or one multitrack production
whose tracks are uploaded in queue order. Every phase can be stopped, and the
words for each outcome say what really happened -- in particular whether
Auphonic had already started a production, because a started production keeps
going (and keeps using credits) whatever QUILL does next, and must never be
sent twice by a blind retry.

Once Auphonic has accepted a production its minimal record is written to the
pending-work file *before* waiting begins, so closing the app, a lost
connection or Stop leaves something to resume; the record is removed only
when the result is saved, or when Auphonic reports that it failed.

Every network call is the shared client's (:mod:`quill.core.publish.auphonic`,
one reviewed egress site), passed in as *client* so tests use a fake. Runs on a
worker thread; reports through the callbacks it is given. wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.publish.auphonic import AuphonicCancelled, AuphonicError
from quill.core.publish.auphonic_history import record_outcome, record_sent
from quill.core.publish.auphonic_options import COVER_FIELD
from quill.core.publish.auphonic_plan import (
    MULTITRACK,
    SEPARATE,
    AuphonicChoices,
    PendingProduction,
    SourceDetails,
    add_pending,
    production_body,
    remove_pending,
    result_folder,
    track_ids,
    uploads_for,
)

SAVED = "saved"
FAILED = "failed"
STOPPED = "stopped"  # stopped before Auphonic started it: nothing processed
WAITING = "waiting"  # started at Auphonic, not fetched yet: resumable
NOT_SENT = "not sent"

_WAITING_DOOR = "Convert > Auphonic Work Waiting fetches it later"
#: Share of one item's progress each phase stands for.
_UPLOAD_SHARE, _PROCESS_SHARE = 0.4, 0.4


@dataclass(slots=True)
class Outcome:
    """What happened to one file (or one multitrack production)."""

    name: str
    state: str
    message: str
    files: list[Path] = field(default_factory=list)
    left_out: int = 0
    uuid: str = ""  # the Auphonic production, once there is one (Production History)


@dataclass(slots=True)
class RunResult:
    """Every outcome of one run, in order."""

    outcomes: list[Outcome] = field(default_factory=list)

    def count(self, state: str) -> int:
        return sum(1 for item in self.outcomes if item.state == state)

    @property
    def saved_files(self) -> int:
        return sum(len(item.files) for item in self.outcomes)

    def summary(self) -> str:
        """One spoken sentence (two at most) for the whole run."""
        if len(self.outcomes) == 1:
            return self.outcomes[0].message
        total = len(self.outcomes)
        parts = [f"{self.count(SAVED)} of {total} saved"]
        for state, words in (
            (FAILED, "failed"),
            (WAITING, "still at Auphonic"),
            (STOPPED, "stopped"),
            (NOT_SENT, "not sent"),
        ):
            if self.count(state):
                parts.append(f"{self.count(state)} {words}")
        return f"Auphonic: {', '.join(parts)}."

    def report_lines(self) -> list[str]:
        labels = {
            SAVED: "Saved",
            FAILED: "FAILED",
            STOPPED: "Stopped",
            WAITING: "Still at Auphonic",
            NOT_SENT: "Not sent",
        }
        lines: list[str] = []
        for item in self.outcomes:
            lines.append(f"{labels.get(item.state, item.state)}: {item.name}")
            lines.append(f"  {item.message}")
            lines += [f"  File: {path}" for path in item.files]
        return lines


def _default_client() -> ModuleType:
    from quill.core.publish import auphonic

    return auphonic


@dataclass(slots=True)
class Runner:
    """Sends a batch, or resumes pending work. See the module docstring."""

    token: str
    store: Path
    client: Any = None
    on_progress: Callable[[str, float], None] = lambda _text, _fraction: None
    on_outcome: Callable[[Outcome, int, int], None] | None = None
    is_cancelled: Callable[[], bool] = lambda: False
    sleep: Callable[[float], None] | None = None
    clock: Callable[[], float] | None = None
    poll_seconds: float = 10.0
    timeout_seconds: float = 4 * 3600.0
    #: Production History's file; every started production and its outcome
    #: is recorded there when it is given (post-MVP, auphonic_history).
    history: Path | None = None
    #: Where a person fetches a result later, said when one is left behind.
    waiting_door: str = _WAITING_DOOR
    _last: tuple[str, int] = ("", -1)

    def __post_init__(self) -> None:
        import time

        if self.client is None:
            self.client = _default_client()
        if self.sleep is None:
            self.sleep = time.sleep
        if self.clock is None:
            self.clock = time.monotonic

    # -- sending -------------------------------------------------------------------

    def send(
        self,
        choices: AuphonicChoices,
        eligible: list[Path],
        dest: Path,
        *,
        details: Callable[[Path], SourceDetails | None] = lambda _path: None,
    ) -> RunResult:
        """Send *eligible* as *choices* says; results go under *dest*."""
        result = RunResult()
        if choices.mode == MULTITRACK:
            title = choices.title.strip()
            ids = track_ids(eligible)
            outcome = self._submit(
                choices,
                name=title,
                title=title,
                body=production_body(choices, title=title, tracks=ids),
                uploads=uploads_for(choices, list(zip(ids, eligible, strict=True))),
                folder=result_folder(dest, title),
                place=(0, 1),
            )
            self._record(result, outcome, 0, 1)
            return result
        total = len(eligible)
        for index, path in enumerate(eligible):
            if self.is_cancelled():
                outcome = Outcome(
                    path.name, NOT_SENT, f"{path.name} was not sent: you stopped first."
                )
            else:
                found = details(path)
                title = (found.title if found is not None else "") or path.stem
                outcome = self._submit(
                    choices,
                    name=path.name,
                    title=title,
                    body=production_body(choices, title=title, details=found),
                    uploads=uploads_for(choices, [("input_file", path)]),
                    folder=result_folder(dest, path.stem),
                    place=(index, total),
                )
            self._record(result, outcome, index, total)
        return result

    def resume(self, records: list[PendingProduction]) -> RunResult:
        """Wait for and download each pending production, one at a time."""
        result = RunResult()
        for index, record in enumerate(records):
            if self.is_cancelled():
                outcome = Outcome(
                    record.title, WAITING, f"{record.title} was not checked: you stopped first."
                )
            else:
                outcome = self._finish(record, (index, len(records)))
            self._record(result, outcome, index, len(records))
        return result

    def _record(self, result: RunResult, outcome: Outcome, index: int, total: int) -> None:
        result.outcomes.append(outcome)
        if self.history is not None and outcome.uuid:
            try:
                record_outcome(
                    self.history, outcome.uuid, outcome.state, outcome.message, outcome.files
                )
            except OSError:
                pass  # the history line keeps its last state
        if self.on_outcome is not None:
            self.on_outcome(outcome, index, total)

    # -- one production ------------------------------------------------------------

    def _submit(
        self,
        choices: AuphonicChoices,
        *,
        name: str,
        title: str,
        body: dict[str, object],
        uploads: list[tuple[str, Path]],
        folder: Path,
        place: tuple[int, int],
    ) -> Outcome:
        unstarted = (
            "The production was never started, so it used no credits; your Auphonic "
            f"account may list it, unstarted, as {title}."
        )
        self._progress(f"Sending {name}{_of(place)} to Auphonic", place, 0.0)
        try:
            production = self.client.create_production(self.token, body)
        except AuphonicError as error:
            return Outcome(
                name, FAILED, f"Auphonic did not accept {name}: {said(error)} Nothing was uploaded."
            )
        for number, (field_name, path) in enumerate(uploads):

            def on_bytes(sent: int, size: int, _n: int = number, _p: Path = path) -> None:
                share = (_n + (sent / size if size else 0.0)) / len(uploads)
                pct = int(sent * 100 / size) if size else 0
                text = f"Uploading {_p.name}{_of(place)}: {pct} percent"
                self._progress(text, place, share * _UPLOAD_SHARE)

            try:
                self.client.upload_input(
                    self.token,
                    production,
                    path,
                    field_name=field_name,
                    on_bytes=on_bytes,
                    is_cancelled=self.is_cancelled,
                )
            except AuphonicCancelled:
                return Outcome(name, STOPPED, f"Stopped while uploading {path.name}. {unstarted}")
            except (AuphonicError, OSError) as error:
                return Outcome(
                    name, FAILED, f"Uploading {path.name} failed: {said(error)} {unstarted}"
                )
        if self.is_cancelled():
            return Outcome(name, STOPPED, f"Stopped before {name} started. {unstarted}")
        sounds = [path for field_name, path in uploads if field_name != COVER_FIELD]
        record = PendingProduction(
            uuid=production,
            mode=MULTITRACK if len(sounds) > 1 or choices.mode == MULTITRACK else SEPARATE,
            title=title,
            inputs=[path.name for path in sounds],
            preset_label=choices.preset_label or "your account's default preset",
            out_dir=str(folder),
        )
        try:
            self.client.start_created(self.token, production)
        except AuphonicError as error:
            self._history_sent(record)  # Refresh from Auphonic can settle what happened
            return Outcome(
                name,
                FAILED,
                f"Auphonic did not confirm that {name} started: {said(error)} It may have started "
                "anyway, so check your Auphonic account before sending it again.",
                uuid=production,
            )
        try:
            add_pending(self.store, record)
        except OSError:
            pass  # the run goes on; only a later Resume is lost
        self._history_sent(record)
        return self._finish(record, place, name=name)

    def _history_sent(self, record: PendingProduction) -> None:
        if self.history is not None:
            try:
                record_sent(self.history, record)
            except OSError:
                pass  # the run goes on; only the history line is lost

    def _finish(
        self, record: PendingProduction, place: tuple[int, int], *, name: str = ""
    ) -> Outcome:
        """Wait for a started production, then save its files; the outcome names it."""
        outcome = self._await(record, place, name=name)
        outcome.uuid = record.uuid
        return outcome

    def _await(
        self, record: PendingProduction, place: tuple[int, int], *, name: str = ""
    ) -> Outcome:
        """Wait for a started production, then save its sound files."""
        assert self.clock is not None and self.sleep is not None
        name = name or record.title
        deadline = self.clock() + self.timeout_seconds
        failures = 0
        while True:
            if self.is_cancelled():
                return Outcome(
                    name,
                    WAITING,
                    f"Stopped waiting for {name}. Auphonic keeps processing it in your "
                    f"account; {self.waiting_door}.",
                )
            try:
                status = self.client.production_status(self.token, record.uuid)
                failures = 0
            except AuphonicError as error:
                failures += 1
                if failures >= 3:
                    return Outcome(
                        name,
                        WAITING,
                        f"Lost touch with Auphonic while it processed {name}: {said(error)} It had "
                        f"already started and may still finish; {self.waiting_door}.",
                    )
                self._pause()
                continue
            if status.failed:
                self._forget(record)
                reason = status.status_string or "it reported an error"
                return Outcome(name, FAILED, f"Auphonic could not process {name}: {reason}.")
            if status.done:
                break
            state = status.status_string or "waiting its turn"
            self._progress(
                f"Auphonic is processing {name}{_of(place)}: {state}", place, _UPLOAD_SHARE
            )
            if self.clock() > deadline:
                hours = self.timeout_seconds / 3600
                return Outcome(
                    name,
                    WAITING,
                    f"Auphonic was still processing {name} after {hours:g} hours. "
                    f"{self.waiting_door}.",
                )
            self._pause()
        return self._download(record, status, place, name)

    def _download(
        self, record: PendingProduction, status: Any, place: tuple[int, int], name: str
    ) -> Outcome:
        kept, left_out = self.client.audio_results(status)
        left = _left_out(left_out)
        if not kept.output_files:
            self._forget(record)
            return Outcome(
                name, FAILED, f"Auphonic finished {name} but returned no sound file to save.{left}"
            )
        folder = Path(record.out_dir)
        base = _UPLOAD_SHARE + _PROCESS_SHARE

        def on_bytes(filename: str, got: int, size: int) -> None:
            pct = int(got * 100 / size) if size else 0
            share = base + (1 - base) * (got / size if size else 0.0)
            self._progress(f"Downloading {filename}{_of(place)}: {pct} percent", place, share)

        try:
            files = self.client.download_results(
                self.token, kept, folder, on_bytes=on_bytes, is_cancelled=self.is_cancelled
            )
        except AuphonicCancelled:
            return Outcome(
                name,
                WAITING,
                f"Stopped while downloading {name}; no partial file was kept. The result "
                f"stays in your Auphonic account; {self.waiting_door}.",
            )
        except (AuphonicError, OSError) as error:
            return Outcome(
                name,
                WAITING,
                f"Downloading {name} failed: {said(error)} The result stays in your Auphonic "
                f"account; {self.waiting_door}.",
            )
        self._forget(record)
        noun = "file" if len(files) == 1 else "files"
        return Outcome(
            name,
            SAVED,
            f"{name}: {len(files)} {noun} saved in {folder}.{left}",
            files=list(files),
            left_out=left_out,
        )

    # -- helpers ------------------------------------------------------------------------

    def _forget(self, record: PendingProduction) -> None:
        try:
            remove_pending(self.store, record.uuid)
        except OSError:
            pass

    def _pause(self) -> None:
        """Wait one polling interval, a second at a time, so Stop is prompt."""
        assert self.sleep is not None
        waited = 0.0
        while waited < self.poll_seconds and not self.is_cancelled():
            step = min(1.0, self.poll_seconds - waited)
            self.sleep(step)
            waited += step

    def _progress(self, text: str, place: tuple[int, int], within: float) -> None:
        index, total = place
        overall = (index + min(max(within, 0.0), 1.0)) / max(total, 1)
        key = (text, int(overall * 1000))
        if key == self._last:
            return  # a block-by-block upload would otherwise flood the UI thread
        self._last = key
        self.on_progress(text, overall)


def said(error: BaseException) -> str:
    """*error* as a plain sentence: no error code, always ending in a stop."""
    text = (Exception.__str__(error) if isinstance(error, CodedError) else str(error)).strip()
    text = text or type(error).__name__
    return text if text.endswith((".", "!", "?")) else text + "."


def _of(place: tuple[int, int]) -> str:
    index, total = place
    return f", {index + 1} of {total}" if total > 1 else ""


def _left_out(count: int) -> str:
    if not count:
        return ""
    if count == 1:
        return " 1 other file Auphonic made, such as a report or an image, was not downloaded."
    return f" {count} other files Auphonic made, such as reports or images, were not downloaded."
