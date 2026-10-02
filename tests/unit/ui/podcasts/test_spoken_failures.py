"""Two failures that used to be silent are spoken (qc.md 6b items 4 and 20).

* Preview in Add Podcast set a status label when the feed could not be loaded.
  A status label is silent to a screen reader, so the button looked dead.
* The OPML import's feed check, when the check itself failed, reported "checked
  0 feeds, 0 unreachable" -- a success-shaped sentence for a check that never
  ran.

Both are driven with fakes: the task manager calls straight back, and the
dialog is a namespace holding the attributes the code touches.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


class _Label:
    def __init__(self) -> None:
        self.text = ""

    def SetLabel(self, text: str) -> None:  # noqa: N802 - wx API shape
        self.text = text


class _Button:
    def __init__(self) -> None:
        self.enabled = True

    def Enable(self, on: bool = True) -> None:  # noqa: N802
        self.enabled = bool(on)


def test_previews_failure_is_spoken_as_well_as_shown() -> None:
    from quill.ui.podcasts.preview_command import preview_search_result

    spoken: list[str] = []

    def submit(_name: str, _work: Any, *, on_success: Any, on_failure: Any) -> None:
        on_failure("podcast-preview", OSError("host unreachable"))

    dialog = SimpleNamespace(
        _status=_Label(),
        _preview_btn=_Button(),
        _announce=spoken.append,
        _task_manager=SimpleNamespace(submit=submit),
        _safe_mode=False,
    )
    result = SimpleNamespace(title="The Daily", feed_url="https://example.invalid/feed")
    preview_search_result(dialog, result, 0)
    assert dialog._preview_btn.enabled is True
    assert spoken == ["That podcast could not be loaded: host unreachable"]
    assert dialog._status.text == spoken[0]


def test_a_feed_check_that_could_not_run_says_so_not_checked_zero() -> None:
    from quill.ui.podcasts.opml_import_dialog import OpmlImportDialog

    spoken: list[str] = []
    finished: list[bool] = []
    host = SimpleNamespace(
        _results=["stale"],
        _running=True,
        _cancel_check_btn=_Button(),
        _status=_Label(),
        _announce=spoken.append,
        _finish=lambda: finished.append(True),
    )
    host._set_status = lambda text: OpmlImportDialog._set_status(host, text)
    OpmlImportDialog._on_validation_failed(host)
    assert host._results == []
    assert host._running is False
    assert host._cancel_check_btn.enabled is False
    assert len(spoken) == 1
    assert "could not run" in spoken[0]
    assert "Everything you imported is kept" in spoken[0]
    assert "0" not in spoken[0]  # never the success-shaped "checked 0 feeds"
    assert host._status.text == spoken[0]
    assert finished == [True]


def test_the_check_failure_route_is_the_one_wired_to_the_task() -> None:
    """A handler nothing calls fixes nothing: the task's on_failure must reach it."""
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[4] / "quill" / "ui" / "podcasts" / "opml_import_dialog.py"
    ).read_text(encoding="utf-8")
    assert "self._wx.CallAfter(self._on_validation_failed)" in source
    assert "on_failure=lambda _op, _error: self._wx.CallAfter(self._on_validated, [])" not in source
