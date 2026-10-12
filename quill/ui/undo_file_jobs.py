"""Background file holding, restore and disposal, with one truthful Undo outcome."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.undo_last import UndoableAction, discard_held, hold_files
from quill.core.undo_recovery import prepare_restore, restore_files

logger = logging.getLogger(__name__)
_jobs: FileJobs | None = None
_undo_run: ContextVar[UndoRun | None] = ContextVar("quill_undo_run", default=None)


@dataclass
class UndoRun:
    action: UndoableAction
    announce: Callable[[str], None]
    pending: int = 0
    failed: bool = False
    metadata_failed: bool = False
    running: bool = True

    def finish(self, *, failed: bool = False) -> None:
        self.failed |= failed
        self.pending -= 1
        if not self.pending and not self.running:
            self.say_done()

    def say_done(self) -> None:
        if self.metadata_failed:
            self.announce(f"Undo {self.action.verb} did not complete. Check Recent Problems.")
        elif self.failed:
            self.announce(
                f"Undid {self.action.verb}, but some files could not be restored. "
                "Available recovery copies were kept; Recent Problems has the details."
            )
        else:
            self.announce(self.action.done())


@dataclass
class HeldJob:
    held: dict[Path, Path]
    pending: bool = True
    restore_requested: bool = False
    dispose_requested: bool = False
    undo_run: UndoRun | None = None
    prepared: Callable[[], None] | None = None
    prepare_failed: Callable[[], None] | None = None
    missing: bool = False
    missing_paths: set[Path] = field(default_factory=set)
    references: list[tuple[Any, str]] = field(default_factory=list)
    metadata_failed: bool = False


class FileJobs:
    def __init__(self, manager: Any, owner: Any, data_dir: Path) -> None:
        from quill.stability.task_manager import TaskManager

        if type(manager) is TaskManager:
            manager = TaskManager(max_workers=1)
            owner._cast_undo_file_pool = manager
        self.manager = manager
        self.owner = owner
        self.data_dir = data_dir
        self.pending = 0
        self.held_jobs: dict[int, HeldJob] = {}
        owner._undo_file_jobs = self

    def submit(
        self,
        name: str,
        work: Callable[[], Any],
        completed: Callable[[Any], None] | None = None,
        failed: Callable[[], None] | None = None,
    ) -> None:
        self.pending += 1
        data_dir = self.data_dir

        def perform(**_kwargs: Any) -> Any:
            try:
                return work()
            except Exception:
                from quill.core import problem_log

                try:
                    problem_log.record_problem(
                        data_dir,
                        problem_log.KIND_OTHER,
                        name,
                        "The file operation could not finish. Files have been kept where possible.",
                    )
                except Exception:
                    logger.exception("Could not record the failed file operation")
                raise

        def success(_operation: str, result: Any) -> None:
            try:
                if completed is not None:
                    completed(result)
            finally:
                self.pending -= 1

        def failure(_operation: str, _error: BaseException) -> None:
            try:
                self.owner._announce(f"{name} could not finish. Recent Problems has the details.")
                if failed is not None:
                    failed()
            finally:
                self.pending -= 1

        try:
            self.manager.submit(
                name,
                perform,
                on_success=success,
                on_failure=failure,
                safe_to_cancel=False,
                ui_lifetime=getattr(self.owner, "_cast_ui_lifetime", None),
            )
        except Exception:
            self.pending -= 1
            raise

    def hold(
        self,
        paths: list[Path],
        directory: Path | None,
        *,
        held: dict[Path, Path] | None = None,
        references: list[tuple[Any, str]] | None = None,
    ) -> dict[Path, Path]:
        held = {} if held is None else held
        job = HeldJob(held, references=list(references or ()))
        self.held_jobs[id(held)] = job

        def work() -> tuple[dict[Path, Path], list[Path], list[Path]]:
            errors: list[Path] = []
            if directory is not None:
                result = hold_files(
                    paths, directory, on_error=lambda path, _error: errors.append(path)
                )
            else:
                result = {}
                for path in paths:
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        logger.exception("Could not remove a downloaded file")
                        errors.append(path)
            held_originals = set(result.values())
            missing = [
                path
                for path in paths
                if directory is not None and path not in held_originals and not path.exists()
            ]
            return result, errors, missing

        def done(result: tuple[dict[Path, Path], list[Path], list[Path]]) -> None:
            mapping, errors, missing = result
            held.update(mapping)
            job.pending = False
            job.missing = bool(missing)
            job.missing_paths = set(missing)
            self._repair_and_report(job, kept=set(errors), unavailable=set(missing))
            if errors:
                self.owner._announce(f"{len(errors)} file(s) could not be removed; they were kept.")
            if missing:
                self.owner._announce(
                    f"{len(missing)} file(s) were already unavailable. "
                    "Undo can restore only available files."
                )
            if errors or missing:
                from quill.core import problem_log

                try:
                    self.submit(
                        "Recording an Undo preparation problem",
                        lambda: problem_log.record_problem(
                            self.data_dir,
                            problem_log.KIND_OTHER,
                            "Preparing files for Undo",
                            f"{len(errors)} files could not be moved; "
                            f"{len(missing)} files were unavailable.",
                        ),
                    )
                except Exception:
                    logger.exception("Could not submit the Undo preparation diagnostic")
                    self.owner._announce("The Undo preparation problem could not be recorded.")
            if job.restore_requested:
                self.restore(held, run=job.undo_run)
            elif job.dispose_requested:
                self.discard(held)
            elif job.prepared is not None:
                ready = job.prepared
                retry = job.prepare_failed
                job.prepared = None
                job.prepare_failed = None
                try:
                    if not self.prepare(held, ready, failed=retry):
                        ready()
                except (OSError, RuntimeError, ValueError):
                    logger.exception("Could not continue the pending Undo")
                    if retry is not None:
                        retry()
                    else:
                        self.owner._announce("Could not prepare Undo. Check Recent Problems.")
                finally:
                    self.pending -= 1

        def failed() -> None:
            job.pending = False
            if job.undo_run is not None:
                job.undo_run.finish(failed=True)
            if job.prepared is not None:
                job.prepared = None
                retry = job.prepare_failed
                job.prepare_failed = None
                if retry is not None:
                    retry()
                self.pending -= 1

        self.submit("Preparing files for Undo", work, done, failed)
        return held

    def repair_metadata(
        self, job: HeldJob, *, kept: set[Path] | None = None, unavailable: set[Path]
    ) -> None:
        changed = False
        for episode, original in job.references:
            path = Path(original)
            if path in unavailable and episode.downloaded_path == original:
                episode.downloaded_path = ""
                changed = True
            elif kept is not None and path in kept and not episode.downloaded_path:
                episode.downloaded_path = original
                changed = True
        if changed:
            save = getattr(self.owner, "_save_podcast_library", None)
            if callable(save):
                save()

    def _repair_and_report(
        self, job: HeldJob, *, kept: set[Path] | None = None, unavailable: set[Path]
    ) -> bool:
        try:
            self.repair_metadata(job, kept=kept, unavailable=unavailable)
        except (OSError, RuntimeError, ValueError):
            job.metadata_failed = True
            logger.exception("Could not save repaired download metadata")
            self.owner._announce(
                "Could not save the updated download information. Changes remain pending."
            )
            return False
        return True

    def prepare(
        self,
        held: dict[Path, Path],
        ready: Callable[[], None],
        *,
        failed: Callable[[], None] | None = None,
    ) -> bool:
        job = self.held_jobs.get(id(held))
        if job is not None and job.pending:
            self.pending += 1
            job.prepared = ready
            job.prepare_failed = failed
            return True
        if not held:
            return False
        mapping = dict(held)
        self.submit(
            "Preparing Undo recovery",
            lambda: prepare_restore(mapping),
            lambda _result: ready(),
            failed,
        )
        return True

    def restore(self, held: dict[Path, Path], *, run: UndoRun | None = None) -> int:
        job = self.held_jobs.get(id(held))
        run = run or _undo_run.get()
        if run is not None and job is not None and job.missing:
            run.failed = True
        if run is not None and job is not None and job.metadata_failed:
            run.metadata_failed = True
        if job is not None and job.pending:
            job.restore_requested = True
            job.undo_run = run
            if run is not None:
                run.pending += 1
            return 0
        deferred = job is not None and job.restore_requested
        if run is not None and not deferred:
            run.pending += 1

        def done(result: tuple[int, int, set[Path]]) -> None:
            _restored, failures, unavailable = result
            self.held_jobs.pop(id(held), None)
            if job is not None:
                repaired = self._repair_and_report(job, unavailable=unavailable)
                if run is not None and not repaired:
                    run.metadata_failed = True
            if failures:
                from quill.core import problem_log

                try:
                    self.submit(
                        "Recording an Undo file problem",
                        lambda: problem_log.record_problem(
                            self.data_dir,
                            problem_log.KIND_OTHER,
                            "Undo",
                            "Some files could not be restored. "
                            "Their recovery copies have been kept.",
                        ),
                    )
                except Exception:
                    logger.exception("Could not submit the Undo restoration diagnostic")
                    self.owner._announce("The Undo restoration problem could not be recorded.")
            if run is not None:
                run.finish(failed=bool(failures))
            elif failures:
                self.owner._announce("Some files could not be restored; recovery copies were kept.")

        mapping = dict(held)
        requested = set(mapping.values()) | (job.missing_paths if job is not None else set())

        def unavailable_paths() -> set[Path]:
            missing: set[Path] = set()
            for path in requested:
                try:
                    path.stat()
                except (FileNotFoundError, NotADirectoryError):
                    missing.add(path)
            return missing

        def restore_work() -> tuple[int, int, set[Path]]:
            restored, failures = restore_files(mapping)
            unavailable = unavailable_paths()
            return restored, failures, unavailable

        def check_failed() -> None:
            self.held_jobs.pop(id(held), None)
            if run is not None:
                run.finish(failed=True)

        def restore_failed() -> None:
            try:
                self.submit(
                    "Checking files after failed Undo",
                    unavailable_paths,
                    lambda missing: done((0, max(1, len(mapping)), missing)),
                    check_failed,
                )
            except (OSError, RuntimeError, ValueError):
                logger.exception("Could not check files after the failed Undo")
                self.owner._announce(
                    "Could not verify restored downloads; their stored paths were left unchanged."
                )
                check_failed()

        self.submit(
            "Restoring files for Undo",
            restore_work,
            done,
            restore_failed,
        )
        return 0

    def discard(self, held: dict[Path, Path]) -> None:
        job = self.held_jobs.get(id(held))
        if job is not None and job.pending:
            job.dispose_requested = True
            return
        self.held_jobs.pop(id(held), None)
        mapping = dict(held)
        self.submit("Clearing old Undo files", lambda: discard_held(mapping))


def configure(manager: Any, owner: Any, data_dir: Path) -> None:
    global _jobs
    _jobs = (
        FileJobs(manager, owner, data_dir) if manager is not None and owner is not None else None
    )


def jobs() -> FileJobs | None:
    return _jobs


def deactivate(owner: Any) -> None:
    global _jobs
    if _jobs is not None and _jobs.owner is owner:
        _jobs = None


def pending_for(owner: Any) -> int:
    owned = getattr(owner, "_undo_file_jobs", None)
    return owned.pending if owned is not None else 0


def execute_undo(
    action: UndoableAction,
    announce: Callable[[str], None],
    *,
    retry: Callable[[], None] | None = None,
) -> None:
    started = False

    def ready() -> None:
        nonlocal started
        started = True
        _execute_ready(action, announce)

    def failed() -> None:
        if retry is not None:
            retry()
            announce(
                f"Could not prepare Undo {action.verb}. The action is still available to retry."
            )
        else:
            announce(f"Could not prepare Undo {action.verb}. Check Recent Problems.")

    try:
        deferred = action.prepare is not None and action.prepare(ready, failed)
    except Exception:
        logger.exception("Could not submit Undo preparation")
        failed()
        return
    if deferred:
        if not started:
            announce(f"Preparing Undo {action.verb} in the background.")
        return
    ready()


def _execute_ready(action: UndoableAction, announce: Callable[[str], None]) -> None:
    run = UndoRun(action, announce)
    token = _undo_run.set(run)
    try:
        action.undo()
    except Exception as error:
        run.failed = True
        run.metadata_failed = True
        logger.exception("Could not apply Undo metadata")
        announce(f"Could not undo {action.verb}: {error}.")
        owned = jobs()
        if owned is not None:
            from quill.core import problem_log

            try:
                owned.submit(
                    "Recording an Undo problem",
                    lambda: problem_log.record_problem(
                        owned.data_dir,
                        problem_log.KIND_OTHER,
                        "Undo",
                        f"Undo {action.verb} could not apply its saved changes.",
                    ),
                )
            except (OSError, RuntimeError, ValueError):
                logger.exception("Could not submit the Undo failure diagnostic")
                announce("The Undo problem could not be recorded.")
        return
    finally:
        _undo_run.reset(token)
        run.running = False
    if run.pending:
        announce(f"Restoring files for {action.verb} in the background.")
    else:
        run.say_done()
