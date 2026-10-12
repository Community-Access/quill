"""Ordered, detached podcast bookkeeping that must never hold up a keypress."""

from __future__ import annotations

import logging
from collections.abc import Callable
from queue import SimpleQueue
from typing import Any

from quill.core.paths import app_data_dir
from quill.stability.task_manager import TaskManager

logger = logging.getLogger(__name__)


def submit(
    host: Any,
    step: str,
    work: Callable[[], Any],
    *,
    on_success: Callable[[Any], None] | None = None,
    failure_message: str = (
        "A listening record could not be saved. Recent Problems has the details."
    ),
) -> Any:
    pool = getattr(host, "_podcast_record_tasks", None)
    if pool is None:
        pool = TaskManager(max_workers=1)
        host._podcast_record_tasks = pool
        host._podcast_record_failures = SimpleQueue()
    failures = host._podcast_record_failures
    data_dir = app_data_dir()

    def write(**_kwargs: Any) -> Any:
        try:
            return work()
        except Exception as error:
            failures.put((step, type(error).__name__))
            from quill.core import problem_log

            try:
                problem_log.record_problem(
                    data_dir,
                    problem_log.KIND_OTHER,
                    "Podcast bookkeeping",
                    "A listening record or setting could not be saved. "
                    "Please check Recent Problems.",
                )
            except Exception:
                logger.exception("Could not record a podcast bookkeeping failure")
            raise

    def failed(_operation: str, _error: BaseException) -> None:
        if not getattr(host, "_cast_closing", False) and not getattr(host, "_cast_closed", False):
            host._announce(failure_message)

    def saved(_operation: str, result: Any) -> None:
        if (
            on_success is not None
            and not getattr(host, "_cast_closing", False)
            and not getattr(host, "_cast_closed", False)
        ):
            on_success(result)

    try:
        return pool.submit(
            f"podcast-{step}",
            write,
            on_success=saved,
            on_failure=failed,
            safe_to_cancel=False,
            ui_lifetime=getattr(host, "_cast_ui_lifetime", None),
        )
    except Exception as error:
        logger.exception("Could not submit podcast bookkeeping: %s", step)
        failures.put((step, type(error).__name__))
        failed(f"podcast-{step}", error)
        return None
