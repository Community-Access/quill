"""Tests for the queue-backed logging configuration (STAB-1) and the
runtime log relocation used by Quill Radio's log-folder preference (#5)."""

from __future__ import annotations

import logging
from pathlib import Path

from quill.stability.logging_config import configure_logging, relocate_log


def _drain_and_close(listener: logging.handlers.QueueListener) -> None:
    """Stop the listener and close its handlers so the file is released."""
    listener.stop()
    for handler in listener.handlers:
        handler.close()
    logging.getLogger().handlers.clear()


def test_configure_logging_writes_quill_log(tmp_path: Path) -> None:
    listener = configure_logging(tmp_path)
    try:
        logging.getLogger("quill.core.radio.test").warning("hello-configure")
        listener.stop()  # flush the queue to the file
        listener.start()
        assert (tmp_path / "quill.log").exists()
        assert "hello-configure" in (tmp_path / "quill.log").read_text(encoding="utf-8")
    finally:
        _drain_and_close(listener)


def test_relocate_log_moves_new_records_to_the_new_dir(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    listener = configure_logging(first)
    try:
        logging.getLogger("quill.core.radio.test").warning("in-first")
        relocate_log(listener, second)
        logging.getLogger("quill.core.radio.test").warning("in-second")
        listener.stop()
        listener.start()
        assert (second / "quill.log").exists()
        assert "in-second" in (second / "quill.log").read_text(encoding="utf-8")
    finally:
        _drain_and_close(listener)


def test_relocate_log_bad_path_keeps_current_handler(tmp_path: Path) -> None:
    listener = configure_logging(tmp_path)
    try:
        # A path whose parent is a file cannot be made a directory; relocation
        # must be a no-op that leaves logging working, not raise.
        blocker = tmp_path / "blocker"
        blocker.write_text("x", encoding="utf-8")
        relocate_log(listener, blocker / "sub")
        logging.getLogger("quill.core.radio.test").warning("still-logging")
        listener.stop()
        listener.start()
        assert "still-logging" in (tmp_path / "quill.log").read_text(encoding="utf-8")
    finally:
        _drain_and_close(listener)
