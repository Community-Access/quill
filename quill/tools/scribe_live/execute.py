"""Sending the plan to Scribe, through QUILL's own queue runner and client.

Each upload is a :class:`quill.core.scribe.queue.Job` run by
:class:`quill.core.scribe.runner.QueueService`, exactly as an app runs one:
the 23-type and 500 MB check before anything is sent, the full settings with
the upload, one conversion at a time in Scribe's order, the family's pace of
8 actions a minute, a minute's wait on ``rate_limited``, reconnecting without
uploading again, and the download with our names (F1, F6). The only
difference is the queue folder: a private one in the run folder, so the
run's jobs never appear in the person's Scribe Conversions window or library.
That is why the run refuses to start while a QUILL app is working through
the family queue: the two would not share Scribe's limit.

After the last upload: the account's pages and defaults are read again (the
run must never have changed the defaults), and every document this run
uploaded -- and only those -- is moved to the trash and deleted for good.

Network: every call goes through :class:`~quill.core.scribe.client.ScribeClient`
and the document channel (GATE-9). Tokens are never read here; the client's
token source is QUILL's stored sign-in. wx-free.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.scribe import queue as q
from quill.core.scribe.errors import ScribeError, ScribeGoneError
from quill.core.scribe.library import Library
from quill.core.scribe.model import format_label
from quill.tools.scribe_live import LiveRunError
from quill.tools.scribe_live.layout import place_outputs, save_record, staging_folder
from quill.tools.scribe_live.plan import Plan, Upload
from quill.tools.scribe_live.sources import CONVERTS, REFUSED_BY_SCRIBE, REFUSED_HERE

Say = Callable[[str], None]
_STILL_WORKING_S = 120.0
APP_NAME = "QUILL live regression run"


@dataclass(slots=True)
class Usage:
    """What the run actually used, as far as QUILL can tell."""

    uploads: int = 0
    formats_collected: int = 0
    failed: int = 0
    pages_before: int | None = None
    pages_after: int | None = None
    defaults_changed: list[str] = field(default_factory=list)
    deleted: int = 0
    not_deleted: list[str] = field(default_factory=list)

    @property
    def pages_used(self) -> int | None:
        if self.pages_before is None or self.pages_after is None:
            return None
        return self.pages_before - self.pages_after


def family_queue_busy() -> str:
    """A sentence when a QUILL app is working through the family queue now."""
    try:
        family = q.FamilyQueue()
        holder = family.holder()
        active = [job for job in family.jobs() if job.state in q.ACTIVE]
    except (OSError, TimeoutError):
        return ""
    if holder and active:
        return (
            f"{holder.get('app') or 'A QUILL app'} is converting {len(active)} document"
            f"{'' if len(active) == 1 else 's'} with Scribe right now. Let it finish, or close "
            "it, then run this again, so the two do not go over Scribe's limit together."
        )
    return ""


class Executor:
    """Runs a plan's uploads one after another and records what happened."""

    def __init__(
        self,
        run_dir: Path,
        record: dict[str, Any],
        *,
        client_factory: Callable[[], Any],
        channel_opener: Any = None,
        say: Say = print,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        queue_now: Callable[[], float] = time.time,
    ) -> None:
        from quill.core.scribe.runner import QueueService

        self.run_dir = run_dir
        self.record = record
        self.say = say
        self._clock = clock
        self._sleep = sleep
        self._client_factory = client_factory
        self.queue = q.FamilyQueue(run_dir / ".queue", now=queue_now)
        self.service = QueueService(
            APP_NAME,
            queue=self.queue,
            client_factory=client_factory,
            channel_opener=channel_opener,
            library=Library(run_dir / ".queue" / "library.json"),
            listener=self._on_event,
            sleep=sleep,
            clock=clock,
        )
        self.usage = Usage()
        self._uploads: dict[str, Upload] = {}
        self._entries: dict[str, dict[str, Any]] = {}
        self._numbers: dict[str, int] = {}
        self._total = 0
        self._last_line = clock()
        self._offline_said: set[str] = set()
        self.stopped = ""

    # --------------------------------------------------------------- before

    def preflight(self, plan: Plan) -> list[str]:
        """Read (never change) the account's pages, defaults and braille tables;
        drop BRF conversions whose table this Scribe does not offer. Returns
        what to say. These reads use no credit."""
        client = self._client_factory()
        notes: list[str] = []
        account = client.account()
        self.usage.pages_before = account.pages_remaining
        self.record["account"] = {"pages_before": account.pages_remaining}
        self.record["defaults_before"] = client.default_settings().to_dict()
        tables = {t.removesuffix(".ctb") for _name, t in client.braille_tables()}
        if tables:
            dropped = 0
            for upload in plan.uploads:
                table = str(upload.settings.get("braille_translation_table", ""))
                table = table.removesuffix(".ctb")
                if table and table not in tables and "brf" in upload.formats:
                    upload.conversions = [c for c in upload.conversions if c.format != "brf"]
                    dropped += 1
            if dropped:
                notes.append(
                    f"{dropped} braille conversion{'' if dropped == 1 else 's'} "
                    f"{'was' if dropped == 1 else 'were'} dropped because Scribe does not "
                    "offer their braille table."
                )
            plan.uploads = [u for u in plan.uploads if u.conversions]
        if account.pages_remaining is not None:
            notes.append(f"Scribe says the account has {account.pages_remaining:,} pages left.")
        return notes

    # ------------------------------------------------------------------ run

    def queue_plan(self, plan: Plan) -> None:
        """Add every upload to the run's private queue, in order."""
        entries = {e["name"]: e for e in self.record["uploads"]}
        jobs: list[q.Job] = []
        for upload in plan.uploads:
            source = upload.source
            job = q.Job(
                app=APP_NAME,
                file_name=source.file,
                source_path=str(source.path) if source.path else "",
                title=upload.name,
                formats=upload.formats,
                settings=dict(upload.settings),
                folder=str(staging_folder(self.run_dir, upload)),
            )
            jobs.append(job)
            entry = entries[upload.name]
            entry["job_id"] = job.id
            entry["conversions"] = [
                {"format": c.format, "label": c.label} for c in upload.conversions
            ]
        self.queue.add(jobs)
        for upload, job in zip(plan.uploads, jobs, strict=True):
            if upload.source.password:
                self.service.provide_password(job.id, upload.source.password)
        self.record["uploads"] = [entries[u.name] for u in plan.uploads]
        save_record(self.run_dir, self.record)

    def run(self, plan: Plan) -> Usage:
        """Run every queued job; place each one's files as soon as it ends."""
        self._uploads = {}
        for upload in plan.uploads:
            entry = next(e for e in self.record["uploads"] if e["name"] == upload.name)
            self._uploads[entry["job_id"]] = upload
            self._entries[entry["job_id"]] = entry
        self._total = len(plan.uploads)
        self._numbers = {job_id: n for n, job_id in enumerate(self._uploads, 1)}
        while not self.stopped:
            if self.service.tick():
                continue
            if self.queue.next_runnable() is None:
                break
            self._sleep(1.0)  # the runner lock was busy for a moment
        self.service.stop()
        for job in self.queue.jobs():
            self._finish(job)
        return self.usage

    def _finish(self, job: q.Job) -> None:
        entry = self._entries.get(job.id)
        upload = self._uploads.get(job.id)
        if entry is None or upload is None or entry.get("state") in ("done", "failed"):
            return
        if job.state not in q.FINISHED and job.state not in q.NEEDS_PERSON:
            entry["state"] = "not run"
            save_record(self.run_dir, self.record)
            return
        files = place_outputs(self.run_dir, upload, job.outputs)
        entry.update({
            "document_id": job.document_id,
            "state": "done" if job.state == q.DONE else "failed",
            "error_code": job.error_code,
            "message": job.message,
            "files": files,
            "outcome": _outcome(upload.source.expect, job),
        })
        if job.document_id:
            self.usage.uploads += 1
        self.usage.formats_collected += len(files)
        if entry["outcome"] != "as planned":
            self.usage.failed += 1
        save_record(self.run_dir, self.record)

    # ------------------------------------------------------------ listening

    def _on_event(self, kind: str, job: q.Job | None) -> None:
        if job is None or job.id not in self._uploads:
            return
        upload = self._uploads[job.id]
        number = self._numbers.get(job.id, 0)
        if kind == "started":
            self._line(
                f"Upload {number} of {self._total}: {upload.source.file}, {upload.spoken()}."
            )
        elif kind in ("done", "error"):
            self._finish(job)
            entry = self._entries[job.id]
            outcome = entry.get("outcome", "")
            saved = len(entry.get("files") or {})
            asked = len(upload.formats)
            of = f"{number} of {self._total}"
            if outcome == "as planned" and upload.source.expect == CONVERTS:
                self._line(f"Upload {of} finished: {saved} of {asked} files saved.")
            elif outcome == "as planned":
                self._line(f"Upload {of} was refused, as planned. {_sentence(job.message)}")
            else:
                self._line(
                    f"Upload {of} did not finish, and {saved} of {asked} files were saved. "
                    f"{_sentence(job.message)}"
                )
        elif kind == "needs_you":
            if job.state == q.NEEDS_SIGNIN:
                self.stopped = (
                    "Your Scribe sign-in ended during the run. Sign in again from QUILL, then "
                    f"continue with --resume {self.run_dir}."
                )
                self._line(self.stopped)
            else:
                self._line(f"Upload {number} is waiting for its password: {job.message}")
                self._finish(job)
        elif kind == "busy":
            self._line("Scribe asked to slow down, so the run waits a minute.")
        elif kind == "offline" and job.id not in self._offline_said:
            self._offline_said.add(job.id)
            self._line("The connection to Scribe dropped. The run keeps trying.")
        elif kind == "online":
            self._offline_said.discard(job.id)
            self._line("Connected to Scribe again.")
        elif kind == "changed" and self._clock() - self._last_line >= _STILL_WORKING_S:
            what = format_label(job.format) if job.format else "the upload"
            self._line(
                f"Still working on upload {number} of {self._total}: {what}. {job.state_words}."
            )

    def _line(self, text: str) -> None:
        self._last_line = self._clock()
        self.say(text)

    # ---------------------------------------------------------------- after

    def after(self) -> list[str]:
        """Pages and defaults read again; returns what to say."""
        client = self._client_factory()
        notes: list[str] = []
        try:
            account = client.account()
            self.usage.pages_after = account.pages_remaining
            self.record.setdefault("account", {})["pages_after"] = account.pages_remaining
            before = self.record.get("defaults_before") or {}
            now = client.default_settings().to_dict()
            self.record["defaults_after"] = now
            self.usage.defaults_changed = sorted(k for k in now if before.get(k) != now.get(k))
        except ScribeError as error:
            notes.append(f"The account could not be read after the run: {error.message}")
        if self.usage.defaults_changed:
            notes.append(
                "The account's own defaults changed during the run: "
                + ", ".join(self.usage.defaults_changed)
                + ". QUILL must never change them; this is a failure."
            )
        save_record(self.run_dir, self.record)
        return notes

    def clean_up(self) -> list[str]:
        """Trash and permanently delete every document this run uploaded."""
        return delete_uploaded(self.run_dir, self.record, self._client_factory, self.usage)


def delete_uploaded(
    run_dir: Path, record: dict[str, Any], client_factory: Callable[[], Any], usage: Usage
) -> list[str]:
    """Delete this run's documents (and only those) from the account."""
    client = client_factory()
    for entry in record.get("uploads", []):
        document_id = entry.get("document_id")
        if not document_id or entry.get("deleted"):
            continue
        try:
            try:
                client.trash(document_id)
            except ScribeGoneError:
                pass
            client.delete_forever(document_id)
            entry["deleted"] = True
            usage.deleted += 1
        except ScribeGoneError:
            entry["deleted"] = True
            usage.deleted += 1
        except ScribeError:
            usage.not_deleted.append(str(entry["name"]))
    save_record(run_dir, record)
    if usage.not_deleted:
        count = len(usage.not_deleted)
        noun = "test document" if count == 1 else "test documents"
        return [
            f"{count} {noun} could not be deleted from the account: "
            + ", ".join(usage.not_deleted)
            + f". Try again with --clean-up {run_dir}"
        ]
    return []


def _sentence(text: str) -> str:
    """*text* as one sentence ending in a full stop."""
    text = " ".join(str(text or "").split()).rstrip(".")
    return f"{text}." if text else ""


def _outcome(expect: str, job: q.Job) -> str:
    """Whether the job ended as the plan expected."""
    if expect == CONVERTS:
        return "as planned" if job.state == q.DONE else "failed"
    if expect == REFUSED_HERE:
        refused_here = job.state == q.FAILED and not job.document_id
        return "as planned" if refused_here else "not refused before upload"
    if expect == REFUSED_BY_SCRIBE:
        return "as planned" if job.state in (q.FAILED, q.GONE) else "Scribe did not refuse it"
    return "failed"


def require(condition: bool, sentence: str) -> None:
    if not condition:
        raise LiveRunError(sentence)


__all__ = ["APP_NAME", "Executor", "Usage", "delete_uploaded", "family_queue_busy", "require"]
