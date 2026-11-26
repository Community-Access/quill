"""FUX-16: a failed background task in QUILL says what happened and offers what fits.

It used to be an OK-only box whose whole text was ``str(error)``. Now the
sentence is plain, the error is behind Copy Details, a reading task offers
Retry (it changes nothing, so trying again cannot do anything twice), an
open whose file has gone offers Choose Another File, and a task that writes
or sends is never offered Retry from here.
"""

from __future__ import annotations

import errno
from typing import Any

from quill.ui.main_frame_write_safety import WriteSafetyMixin


class _Host(WriteSafetyMixin):
    def __init__(self, choose: bool) -> None:
        self.choose = choose
        self.asked: list[tuple[str, str, dict[str, Any]]] = []
        self.opened = 0

    def _show_failure_box(self, message: str, caption: str, **kwargs: Any) -> bool:
        self.asked.append((message, caption, kwargs))
        return self.choose

    def open_file(self) -> None:
        self.opened += 1


def test_a_failed_open_offers_retry_and_keeps_the_error_for_details() -> None:
    host = _Host(choose=True)
    retried: list[int] = []
    error = PermissionError(errno.EACCES, "Permission denied", "C:/a.docx")
    host._report_background_failure("Opening a.docx", error, lambda: retried.append(1))
    message, caption, kwargs = host.asked[0]
    assert caption == "Opening a.docx"
    assert message.startswith("Opening a.docx did not finish.")
    assert "Nothing was opened." in message
    assert "Errno" not in message
    assert kwargs["error"] is error
    assert kwargs["next_label"] == "&Retry"
    assert retried == [1]


def test_an_open_whose_file_is_gone_offers_choose_another_file() -> None:
    host = _Host(choose=True)
    retried: list[int] = []
    error = FileNotFoundError(errno.ENOENT, "No such file")
    host._report_background_failure("Opening a.docx", error, lambda: retried.append(1))
    assert host.asked[0][2]["next_label"] == "Choose Another &File..."
    assert host.opened == 1
    assert retried == []


def test_a_task_that_changes_something_is_never_offered_retry() -> None:
    host = _Host(choose=True)
    retried: list[int] = []
    host._report_background_failure("Rebasing", OSError("conflict"), lambda: retried.append(1))
    assert host.asked[0][2]["next_label"] == ""
    assert retried == []


def test_close_does_nothing_else() -> None:
    host = _Host(choose=False)
    retried: list[int] = []
    host._report_background_failure("Loading branches", TimeoutError(), lambda: retried.append(1))
    assert host.asked[0][2]["next_label"] == "&Retry"
    assert "The connection failed or timed out." in host.asked[0][0]
    assert retried == []


def test_the_background_runner_hands_its_retry_to_the_report() -> None:
    import inspect

    from quill.ui.main_frame import MainFrame

    source = inspect.getsource(MainFrame._finish_background_task)
    assert "self._report_background_failure(label, error, retry)" in source
    assert "str(error), label" not in source  # the raw OK-only box is gone
    assert "retry=again" in inspect.getsource(MainFrame._run_background_task)
