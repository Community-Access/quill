"""Opening a file that is not there says so; it does not crash (#1423).

Reported against a OneDrive path: QUILL showed a *crash report* for a file that
had simply been moved or deleted. The office/PDF/large-file reads already went
through ``_run_background_task``, whose worker catches and surfaces whatever the
read raises; the cheap synchronous read of a small `.txt`/`.md`/`.html` had no
such path, so ``FileNotFoundError`` reached the crash handler.

A crash report for a missing file teaches a user that the app is broken when the
truth is that their file is not where it was.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.io.open_read import DocumentUnavailableError, read_open_document
from quill.ui.open_guard import read_document_or_report


class _Host:
    def __init__(self) -> None:
        self.status: list[str] = []
        self.said: list[str] = []

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _announce(self, message: str) -> None:
        self.said.append(message)


def test_the_io_layer_refuses_a_missing_file_with_a_sentence(tmp_path: Path) -> None:
    with pytest.raises(DocumentUnavailableError) as caught:
        read_open_document(tmp_path / "gone.html", ".html")

    assert caught.value.code == "QUILL-IO-OPEN-UNAVAILABLE"
    assert "gone.html" in str(caught.value)
    assert "no longer there" in str(caught.value)


def test_a_folder_is_named_as_a_folder(tmp_path: Path) -> None:
    with pytest.raises(DocumentUnavailableError) as caught:
        read_open_document(tmp_path, ".html")

    assert "folder" in str(caught.value)


def test_a_missing_file_is_reported_not_raised(tmp_path: Path) -> None:
    host = _Host()
    finished: list[object] = []

    opened = read_document_or_report(host, tmp_path / "Bingo3.html", ".html", None, finished.append)

    assert opened is False
    assert finished == []
    assert host.status and "no longer there" in host.status[0]
    # Said out loud as well as shown: the status bar is not where a screen
    # reader user is looking when an open silently does nothing.
    assert host.said == host.status


def test_the_spoken_sentence_does_not_carry_the_error_code(tmp_path: Path) -> None:
    """The code belongs in the log and the crash bundle, not in speech."""
    host = _Host()

    read_document_or_report(host, tmp_path / "gone.txt", ".txt", None, lambda _r: None)

    assert "QUILL-IO-OPEN-UNAVAILABLE" not in host.said[0]


def test_a_file_that_is_there_still_opens(tmp_path: Path) -> None:
    path = tmp_path / "here.txt"
    path.write_text("hello\n", encoding="utf-8")
    host = _Host()
    finished: list[object] = []

    opened = read_document_or_report(host, path, ".txt", None, finished.append)

    assert opened is True
    assert len(finished) == 1
    assert host.status == [] and host.said == []


def test_recent_is_left_alone() -> None:
    """#14 owns that decision, and its rules are not visible from here.

    Only confirmed fixed drives are ever probed, so a detached USB or an offline
    share never loses its history, and the whole behaviour sits behind
    ``recent_files_auto_clear_missing``. A quiet prune here would overrule both.
    """
    import inspect

    from quill.ui import open_guard

    # The docstring explains the decision, so look for the *import* rather than
    # the name: what matters is that this module cannot touch Recent at all.
    source = inspect.getsource(open_guard)
    assert "from quill.core.recent" not in source
    assert "import recent" not in source
