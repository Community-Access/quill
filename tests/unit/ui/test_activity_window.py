"""The shared Activity window, and results that outlive their windows (qc.md F-10, F-02)."""

from __future__ import annotations

import threading
import time

import pytest

wx = pytest.importorskip("wx")

from quill.core import activity  # noqa: E402
from quill.ui import activity_window  # noqa: E402
from quill.ui.surface_lifetime import surface_tasks  # noqa: E402


@pytest.fixture(scope="module")
def app():
    application = wx.App()
    yield application
    application.Destroy()


@pytest.fixture(autouse=True)
def _fresh_log():
    activity.LOG.clear()
    yield
    activity.LOG.clear()


def _pump(app, until, seconds: float = 3.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and not until():
        app.Yield(True)
        time.sleep(0.01)


class _Host:
    def __init__(self, frame) -> None:
        self.frame = frame
        self.said: list[str] = []
        self.inspected: dict[str, object] = {}

    def _announce(self, message: str) -> None:
        self.said.append(message)

    def _show_modal_dialog(self, dialog, title) -> int:
        """Instead of showing: read the window, press Retry, read it again."""
        self.inspected["title"] = title
        children = {
            child.GetLabel(): child
            for child in dialog.GetChildren()
            if isinstance(child, wx.Button)
        }
        listbox = next(c for c in dialog.GetChildren() if isinstance(c, wx.ListBox))
        details = next(c for c in dialog.GetChildren() if isinstance(c, wx.TextCtrl))
        self.inspected["rows"] = [listbox.GetString(i) for i in range(listbox.GetCount())]
        self.inspected["details"] = details.GetValue()
        self.inspected["enabled"] = {
            label: button.IsEnabled() for label, button in children.items()
        }
        retry = children["&Retry"]
        retry.GetEventHandler().ProcessEvent(wx.CommandEvent(wx.wxEVT_BUTTON, retry.GetId()))
        self.inspected["selection_after"] = listbox.GetSelection()
        return wx.ID_CLOSE


def test_the_window_lists_results_and_enables_only_their_actions(app) -> None:
    frame = wx.Frame(None)
    try:
        host = _Host(frame)
        older = activity.ActionResult("refresh", "feeds", activity.COMPLETED, "Feeds checked.")
        activity.LOG.record(older)
        failed = activity.ActionResult(
            "save",
            "QUILL settings",
            activity.FAILED,
            "QUILL settings could not be saved.",
            "The disk is full.",
            (activity.RETRY, activity.OPEN_FOLDER),
        )
        activity_window.report_result(
            host,
            failed,
            {"retry": lambda: "Saved QUILL settings.", "open_folder": lambda: "Opened."},
        )
        assert host.said == ["QUILL settings could not be saved. The disk is full."]
        activity_window.show_activity(host)
        seen = host.inspected
        assert seen["title"] == "Activity"
        assert seen["rows"][0].startswith("Failed: QUILL settings could not be saved")
        assert "You can: Retry, Open Folder." in str(seen["details"])
        assert seen["enabled"]["&Retry"] and seen["enabled"]["Open &Folder"]
        assert not seen["enabled"]["&Undo"] and not seen["enabled"]["O&pen"]
        assert host.said[-1] == "Saved QUILL settings."
        assert seen["selection_after"] == 0  # focus stays on the same result
    finally:
        frame.Destroy()


def test_a_result_that_outlives_its_window_goes_to_activity(app) -> None:
    from quill.stability.task_manager import TaskManager

    manager = TaskManager(max_workers=1)
    frame = wx.Frame(None, title="Add Podcast")
    tasks = surface_tasks(manager, lambda: frame)
    delivered: list[str] = []
    try:
        release = threading.Event()

        def slow(**_kwargs: object) -> str:
            release.wait(5)
            return "late"

        tasks.submit("search", slow, on_success=lambda _op, r: delivered.append(r))
        frame.Destroy()
        release.set()
        _pump(app, lambda: bool(activity.LOG.recent()))
        assert delivered == []
        latest = activity.LOG.recent()[0]
        assert latest.summary == (
            "Add Podcast: its background work finished after the window closed."
        )
        assert latest.importance == activity.REVIEW  # reviewable, never spoken
    finally:
        manager.shutdown(wait=True)
