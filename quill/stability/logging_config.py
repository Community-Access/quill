"""Queue-backed logging configuration used during early startup.

Implements: ROADMAP STAB-1 (the rotating-file ``quill.log`` and the
queue listener that drains log records off the UI thread so a
flooded log channel never blocks the wx main thread). The handler
list installed here is what :mod:`quill.stability.crash_report` reads
when the user saves a diagnostic bundle.
"""

from __future__ import annotations

import logging
import logging.handlers
import queue
from pathlib import Path


def configure_logging(log_dir: Path) -> logging.handlers.QueueListener:
    log_dir.mkdir(parents=True, exist_ok=True)

    log_queue: queue.Queue[logging.LogRecord] = queue.Queue(maxsize=10_000)
    queue_handler = logging.handlers.QueueHandler(log_queue)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(queue_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "quill.log",
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s")
    )

    listener = logging.handlers.QueueListener(
        log_queue,
        file_handler,
        respect_handler_level=True,
    )
    listener.start()
    return listener


def relocate_log(listener: logging.handlers.QueueListener, log_dir: Path) -> None:
    """Move the active ``quill.log`` to *log_dir* at runtime (quill-radio #5).

    Swaps the listener's rotating-file handler for one writing into *log_dir*,
    so a user who changes the log-folder preference sees new records land there
    without a restart. The old handler is closed. A no-op (leaving the current
    handler in place) if the new directory can't be created, so a bad path
    never leaves logging broken.
    """
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        new_handler = logging.handlers.RotatingFileHandler(
            log_dir / "quill.log",
            maxBytes=5_000_000,
            backupCount=5,
            encoding="utf-8",
        )
    except OSError:
        logging.getLogger(__name__).warning(
            "Could not relocate the log to %s; keeping the current location.", log_dir
        )
        return
    new_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s")
    )
    old_handlers = list(listener.handlers)
    listener.stop()
    listener.handlers = (new_handler,)
    listener.start()
    for handler in old_handlers:
        try:
            handler.close()
        except OSError:
            pass
