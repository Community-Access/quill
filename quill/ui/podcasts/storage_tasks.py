"""Responsive storage work, with UI authorization and truthful file outcomes."""

from __future__ import annotations

import logging
from collections.abc import Callable, Generator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.podcasts.storage_maintenance import (
    Deletion,
    DownloadTarget,
    EpisodeKey,
    Mode,
    StoragePlan,
    path_key,
    plan_storage,
)
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.podcasts.storage_delete import DeletionGate
from quill.ui.podcasts.storage_reconcile import (
    StorageOutcome,
    apply_deletions,
    apply_metadata,
    authorize_batch,
    drop_expired,
    permission_checks,
)
from quill.ui.podcasts.storage_report import UsageReport, usage_report
from quill.ui.podcasts.storage_snapshot import (
    CoherentSnapshot,
    StorageCapture,
    TurnJob,
    generation,
    owner_alive,
)
from quill.ui.surface_lifetime import surface_tasks
from quill.ui.undo_file_jobs import FileJobs

logger = logging.getLogger(__name__)


def _record_failure(data_dir: Path, count: int) -> None:
    if not count:
        return
    from quill.core import problem_log

    try:
        problem_log.record_problem(
            data_dir,
            problem_log.KIND_OTHER,
            "Podcast storage",
            f"{count} file(s) could not be inspected or removed. Download information was kept.",
        )
    except Exception:
        logger.exception("Could not record the podcast storage failure")


@dataclass(slots=True)
class Prepared:
    captured: StorageCapture
    value: StoragePlan | UsageReport
    data_dir: Path


StorageReader = Callable[[PodcastLibrary, frozenset[EpisodeKey], Path], StoragePlan | UsageReport]


class ReadJob:
    def __init__(
        self,
        jobs: StorageJobs,
        name: str,
        reader: StorageReader,
        completed: Callable[[Prepared], None],
        failed: Callable[[BaseException], None],
        *,
        include_inbox: bool = True,
    ) -> None:
        self.jobs = jobs
        self.name = name
        self.reader = reader
        self.completed = completed
        self.failed = failed
        self.include_inbox = include_inbox
        self.snapshot: CoherentSnapshot | None = None
        self.task: Any = None
        self.cancelled = False

    def start(self) -> None:
        if self.cancelled or not owner_alive(self.jobs.host):
            return
        self.snapshot = CoherentSnapshot(
            self.jobs.host,
            completed=self._captured,
            failed=self.failed,
            include_inbox=self.include_inbox,
        )
        self.snapshot.start()

    def cancel(self) -> None:
        self.cancelled = True
        if self.snapshot is not None:
            self.snapshot.cancel()
        operation = getattr(self.task, "operation_id", None)
        cancel = getattr(self.jobs.manager, "cancel", None)
        if operation is not None and callable(cancel):
            cancel(operation)

    def _captured(self, captured: StorageCapture) -> None:
        if self.cancelled or not owner_alive(self.jobs.host):
            return
        library = captured.library
        protected = frozenset(captured.protected)
        reader = self.reader
        existing = getattr(self.jobs.host, "_undo_file_jobs", None)
        known_dir = existing.data_dir if existing is not None else None

        def work(**kwargs: Any) -> tuple[StoragePlan | UsageReport, Path]:
            token = kwargs.get("cancellation_token")
            if token is not None:
                token.raise_if_cancelled()
            data_dir = known_dir if known_dir is not None else app_data_dir()
            value = reader(library, protected, data_dir)
            _record_failure(data_dir, value.unreadable)
            if token is not None:
                token.raise_if_cancelled()
            return value, data_dir

        def done(_operation: str, result: tuple[StoragePlan | UsageReport, Path]) -> None:
            if self.cancelled or not owner_alive(self.jobs.host):
                return
            if generation(self.jobs.host) != captured.revision:
                self.start()
                return
            value, data_dir = result
            self.completed(Prepared(captured, value, data_dir))

        def failed(_operation: str, error: BaseException) -> None:
            if not self.cancelled and owner_alive(self.jobs.host):
                self.failed(error)

        try:
            self.task = self.jobs.manager.submit(
                self.name, work, on_success=done, on_failure=failed, safe_to_cancel=True
            )
        except Exception as error:
            failed(self.name, error)


class StorageJobs:
    def __init__(self, host: Any) -> None:
        self.host = host
        self.raw_manager = getattr(host, "_task_manager", None)
        self.manager = surface_tasks(self.raw_manager, lambda: host.frame)
        self.active: StorageOperation | None = None
        self.pending: list[StorageOperation] = []

    def read(
        self,
        name: str,
        reader: StorageReader,
        completed: Callable[[Prepared], None],
        failed: Callable[[BaseException], None],
        *,
        include_inbox: bool = True,
    ) -> ReadJob:
        job = ReadJob(self, name, reader, completed, failed, include_inbox=include_inbox)
        if self.manager is None:
            failed(RuntimeError("Podcast storage needs a background task manager"))
        else:
            job.start()
        return job

    def usage(
        self, completed: Callable[[Prepared], None], failed: Callable[[BaseException], None]
    ) -> ReadJob:
        return self.read(
            "Reading podcast storage",
            usage_report,
            completed,
            failed,
            include_inbox=False,
        )

    def prepare_removal(
        self,
        show_id: str,
        completed: Callable[[Prepared], None],
        failed: Callable[[BaseException], None],
    ) -> ReadJob:
        return self.read(
            "Checking podcast downloads",
            lambda library, protected, _data_dir: plan_storage(
                library, mode="show", show_id=show_id, protected=protected
            ),
            completed,
            failed,
            include_inbox=False,
        )

    def run(
        self,
        mode: Mode,
        completed: Callable[[StorageOutcome], None],
        *,
        show_id: str = "",
        allowed: tuple[DownloadTarget, ...] | None = None,
    ) -> StorageOperation:
        if mode == "maintenance":
            for operation in ([self.active] if self.active is not None else []) + self.pending:
                if operation.mode == mode and not operation.cancelled:
                    operation.callbacks.append(completed)
                    return operation
        operation = StorageOperation(self, mode, completed, show_id=show_id, allowed=allowed)
        self.pending.append(operation)
        self._next()
        return operation

    def _next(self) -> None:
        if self.active is not None:
            return
        if not owner_alive(self.host):
            self.pending.clear()
            return
        if self.pending:
            self.active = self.pending.pop(0)
            self.host._podcast_maintenance_snapshot = self.active
            self.active.start()


class StorageOperation:
    def __init__(
        self,
        jobs: StorageJobs,
        mode: Mode,
        completed: Callable[[StorageOutcome], None],
        *,
        show_id: str,
        allowed: tuple[DownloadTarget, ...] | None,
    ) -> None:
        self.jobs = jobs
        self.host = jobs.host
        self.mode = mode
        self.show_id = show_id
        self.allowed = allowed
        self.callbacks = [completed]
        self.outcome = StorageOutcome()
        self.captured: StorageCapture | None = None
        self.plan: StoragePlan | None = None
        self.reader: ReadJob | None = None
        self.turn: TurnJob | None = None
        self.reconciliation: CoherentSnapshot | None = None
        self.permission: ReadJob | None = None
        self.permission_turn: TurnJob | None = None
        self.gate: DeletionGate | None = None
        self.files: FileJobs | None = None
        self.cursor = 0
        self.attempted: set[str] = set()
        self.successful: set[str] = set()
        self.saved_mutations = 0
        self.save_failed = False
        self.waiting = False
        self.reconciling = False
        self.cancelled = False
        self.finished = False
        self.replan = False

    def start(self) -> None:
        if self.cancelled or not owner_alive(self.host):
            self._finish()
            return
        self.replan = False
        mode, show_id, allowed = self.mode, self.show_id, self.allowed
        self.reader = self.jobs.read(
            "Planning podcast housekeeping",
            lambda library, protected, _data_dir: plan_storage(
                library,
                mode=mode,
                protected=protected,
                show_id=show_id,
                allowed=allowed,
            ),
            self._planned,
            self._failed,
            include_inbox=mode == "maintenance",
        )

    def cancel(self) -> None:
        self.cancelled = True
        if self.reader is not None:
            self.reader.cancel()
        if self.permission is not None:
            self.permission.cancel()
        if self.permission_turn is not None:
            self.permission_turn.cancel()
        if self.gate is not None:
            self.gate.cancel()
        if not self.waiting:
            if self.turn is not None:
                self.turn.cancel()
            self._finish()
        # A submitted file job still owns reconciliation. Cast waits for its
        # pending lease before transferring the final library to the saver.

    def _planned(self, prepared: Prepared) -> None:
        if not isinstance(prepared.value, StoragePlan):
            self._failed(TypeError("The storage plan had an invalid shape"))
            return
        self.captured = prepared.captured
        self.plan = prepared.value
        self.cursor = 0
        self.outcome.unreadable = max(self.outcome.unreadable, self.plan.unreadable)
        existing = getattr(self.host, "_undo_file_jobs", None)
        self.files = existing or FileJobs(self.jobs.raw_manager, self.host, prepared.data_dir)
        self._turn(
            self._metadata(),
            self._metadata_done,
        )

    def _metadata(self) -> Generator[None]:
        for path in self.plan.omitted:
            if path not in self.attempted:
                self.attempted.add(path)
                self.outcome.skipped += 1
            yield
        yield from apply_metadata(self.host, self.captured, self.plan, self.outcome, self._mutated)

    def _mutated(self) -> None:
        self.outcome.mutations += 1
        self.captured.revision = generation(self.host)

    def _save(self) -> None:
        if not self.save_failed and self.outcome.mutations > self.saved_mutations:
            try:
                self.host._save_podcast_library()
            except Exception:
                logger.exception("Could not save completed podcast storage changes")
                self.save_failed = True
                self.outcome.error = True
                if owner_alive(self.host):
                    self.host._announce(
                        "Podcast storage changed, but the library could not be saved. "
                        "Changes are still pending."
                    )
                return
            self.saved_mutations = self.outcome.mutations
            if self.captured is not None:
                self.captured.revision = generation(self.host)

    def _turn(
        self,
        chunks: Generator[None, None, Any],
        completed: Callable[[Any], None],
        *,
        essential: bool = False,
    ) -> None:
        self.turn = TurnJob(
            self.host._wx,
            chunks,
            completed=completed,
            failed=self._failed,
            alive=lambda: owner_alive(self.host, allow_closing=essential),
            valid=lambda: generation(self.host) == self.captured.revision,
            changed=self._recapture_results if essential else self._retry,
        )
        self.turn.start()

    def _retry(self) -> None:
        self._save()
        self.start()

    def _metadata_done(self, _result: Any) -> None:
        self._turn(
            drop_expired(
                self.host,
                self.captured,
                self.plan,
                self.successful,
                self.outcome,
                self._mutated,
            ),
            lambda _result: self._authorize(),
        )

    def _authorize(self) -> None:
        self._save()
        if self.cancelled or not owner_alive(self.host):
            self._finish()
            return
        self._turn(
            authorize_batch(
                self.host, self.captured, self.plan, self.cursor, self.attempted, self.outcome
            ),
            self._authorized,
        )

    def _authorized(self, result: tuple[tuple[DownloadTarget, ...], int]) -> None:
        targets, self.cursor = result
        if not targets:
            self._finish()
            return
        for target in targets:
            self.attempted.add(path_key(target.path))
        data_dir = self.files.data_dir
        gate = DeletionGate(self.host, targets, self._check_files)
        self.gate = gate

        def work() -> tuple[Deletion, ...]:
            results = gate.perform()
            _record_failure(data_dir, sum(result.status == "failed" for result in results))
            return results

        self.waiting = True
        self.files.pending += 1
        try:
            self.files.submit("Removing podcast downloads", work, self._deleted, self._file_failed)
        except Exception as error:
            self._release()
            self._failed(error)

    def _check_files(self, gate: DeletionGate) -> None:
        if self.cancelled or not owner_alive(self.host):
            gate.cancel()
            return
        mode, show_id, targets = self.mode, self.show_id, gate.targets

        def ready(prepared: Prepared) -> None:
            if self.cancelled or not owner_alive(self.host):
                gate.cancel()
                return
            captured, plan = prepared.captured, prepared.value
            if not isinstance(plan, StoragePlan):
                gate.fail(TypeError("The deletion permission had an invalid shape"))
                return
            self.replan |= captured.revision != self.captured.revision

            def authorized(result: tuple[tuple[DownloadTarget, ...], int]) -> None:
                gate.allow(
                    result[0], lambda: permission_checks(self.host, captured, plan, result[0])
                )

            self.permission_turn = TurnJob(
                self.host._wx,
                authorize_batch(self.host, captured, plan, 0, set(), StorageOutcome()),
                completed=authorized,
                failed=gate.fail,
                alive=lambda: owner_alive(self.host),
                valid=lambda: generation(self.host) == captured.revision,
                changed=lambda: self._check_files(gate),
            )
            self.permission_turn.start()

        if generation(self.host) == self.captured.revision:
            ready(
                Prepared(self.captured, replace(self.plan, downloads=targets), self.files.data_dir)
            )
            return
        self.permission = self.jobs.read(
            "Authorizing podcast file removal",
            lambda library, protected, _data_dir: plan_storage(
                library, mode=mode, protected=protected, show_id=show_id, allowed=targets
            ),
            ready,
            gate.fail,
            include_inbox=False,
        )

    def _deleted(self, results: tuple[Deletion, ...]) -> None:
        self.results = results
        if self.gate is not None and self.gate.error is not None:
            self.outcome.error = True
        for result in results:
            if result.status == "removed":
                self.outcome.removed += 1
                self.outcome.reclaimed += result.size
                self.outcome.swept += result.target.reason == "expired"
                self.successful.add(path_key(result.target.path))
            elif result.status == "missing":
                self.outcome.missing += 1
                self.successful.add(path_key(result.target.path))
            elif result.status == "failed":
                self.outcome.failed += 1
            else:
                self.outcome.skipped += 1
        self.reconciling = True
        self.replan |= generation(self.host) != self.captured.revision
        if self.replan:
            self._recapture_results()
        else:
            self._apply_results()

    def _recapture_results(self) -> None:
        self._save()
        self.replan = True
        self.reconciliation = CoherentSnapshot(
            self.host,
            completed=self._recaptured,
            failed=self._failed,
            allow_closing=True,
            include_inbox=False,
        )
        self.reconciliation.start()

    def _recaptured(self, captured: StorageCapture) -> None:
        self.captured = captured
        self._apply_results()

    def _apply_results(self) -> None:
        self._turn(
            apply_deletions(self.host, self.captured, self.results, self._mutated),
            lambda _result: self._turn(
                drop_expired(
                    self.host,
                    self.captured,
                    self.plan,
                    self.successful,
                    self.outcome,
                    self._mutated,
                ),
                self._results_done,
                essential=True,
            ),
            essential=True,
        )

    def _results_done(self, _result: Any) -> None:
        self._save()
        self.reconciling = False
        self._release()
        if self.cancelled or not owner_alive(self.host):
            self._finish()
        elif self.replan:
            self.start()
        else:
            self._authorize()

    def _release(self) -> None:
        if self.gate is not None:
            self.gate.cancel()
            self.gate = None
        if self.waiting:
            self.waiting = False
            self.files.pending -= 1

    def _file_failed(self) -> None:
        self._release()
        self.outcome.error = True
        self._finish()

    def _failed(self, error: BaseException) -> None:
        logger.error("Podcast storage work failed", exc_info=error)
        self.outcome.error = True
        self._release()
        self._finish()

    def _finish(self) -> None:
        if self.finished or self.waiting:
            return
        self.finished = True
        self._save()
        if getattr(self.host, "_podcast_maintenance_snapshot", None) is self:
            self.host._podcast_maintenance_snapshot = None
        self.jobs.active = None
        try:
            if not self.cancelled and owner_alive(self.host):
                for callback in self.callbacks:
                    try:
                        callback(self.outcome)
                    except Exception:
                        logger.exception("Could not deliver completed podcast storage results")
                        self.host._announce(
                            "Podcast storage finished, but a result could not be displayed."
                        )
        finally:
            self.jobs._next()


def for_host(host: Any) -> StorageJobs:
    jobs = getattr(host, "_podcast_storage_jobs", None)
    if jobs is None:
        jobs = StorageJobs(host)
        host._podcast_storage_jobs = jobs
    return jobs
