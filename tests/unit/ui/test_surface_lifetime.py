"""A window's background work cannot speak or touch it after it closes (qc.md F-02).

The shared guard (``UiLifetimeToken``, 84de01d) suppresses a task's delivery
once its token is invalidated; adoption was the missing half. Short-lived
surfaces now wrap the app's task manager in ``surface_tasks``, which ties every
task they start to their window's ``EVT_WINDOW_DESTROY``.

Three layers: the token follows a real wx window's destruction; a real
``TaskManager`` run through the wrapper delivers while the window lives and
drops the result after it is destroyed; and a gate that no short-lived surface
in ``quill/ui`` stores the raw task manager.
"""

from __future__ import annotations

import ast
import threading
import time
from pathlib import Path

import pytest

from quill.ui.surface_lifetime import SurfaceTasks, lifetime_for, surface_tasks

wx = pytest.importorskip("wx")

_ROOT = Path(__file__).resolve().parents[3]

#: Long-lived owners that hold the app's own task manager: their delivery is
#: suppressed by the manager's shutdown, which is the right lifetime for them.
_LONG_LIVED = {
    "quill/ui/app_shell.py",
    "quill/ui/main_frame.py",
    "quill/ui/radio/podcast_refresh.py",  # a monitor owned by the app, not a window
}


@pytest.fixture
def app():
    application = wx.App()
    yield application
    application.Destroy()


def _pump(application, until, seconds: float = 5.0) -> None:
    deadline = time.monotonic() + seconds
    while not until() and time.monotonic() < deadline:
        application.Yield(True)
        time.sleep(0.01)


def test_the_token_ends_with_its_window_and_not_with_a_child(app) -> None:
    """A panel surface (Radio's browse and Weather's centre are panels) is
    destroyed at once, so its token ends at once."""
    frame = wx.Frame(None)
    surface = wx.Panel(frame)
    token = lifetime_for(surface)
    assert lifetime_for(surface) is token  # one per window
    child = wx.Button(surface)
    child.Destroy()
    assert token.is_alive  # a child's destruction is not the window's
    surface.Destroy()
    assert not token.is_alive
    frame.Destroy()


def test_a_top_level_window_queued_for_deletion_already_counts_as_going(app) -> None:
    """Destroy() on a dialog or frame only queues it; the delivery guard reads
    that, so nothing lands in the gap before the destroy event."""
    from quill.ui.surface_lifetime import window_is_going

    frame = wx.Frame(None)
    assert window_is_going(frame) is False
    frame.Destroy()
    assert window_is_going(frame) is True


def test_none_stays_none_so_existing_checks_keep_their_meaning() -> None:
    assert surface_tasks(None, lambda: None) is None


def test_a_result_is_delivered_while_the_window_lives_and_dropped_after(app) -> None:
    from quill.stability.task_manager import TaskManager

    manager = TaskManager(max_workers=1)
    frame = wx.Frame(None)
    tasks = surface_tasks(manager, lambda: frame)
    delivered: list[str] = []
    try:
        tasks.submit("live", lambda **_k: "early", on_success=lambda _op, r: delivered.append(r))
        _pump(app, lambda: delivered == ["early"])
        assert delivered == ["early"]

        release = threading.Event()

        def slow(**_kwargs: object) -> str:
            release.wait(5)
            return "late"

        tasks.submit("slow", slow, on_success=lambda _op, r: delivered.append(r))
        frame.Destroy()  # queued for deletion: the callback guard already refuses
        release.set()
        time.sleep(0.2)
        _pump(app, lambda: False, seconds=0.5)
        assert delivered == ["early"]  # "late" was never delivered into the gone window
    finally:
        manager.shutdown(wait=True)


def test_an_explicit_lifetime_is_not_overridden() -> None:
    from quill.stability.task_manager import UiLifetimeToken

    seen: list[object] = []

    class _Manager:
        def submit(self, name, func, **kwargs):
            seen.append(kwargs.get("ui_lifetime"))

    mine = UiLifetimeToken()
    SurfaceTasks(_Manager(), lambda: object()).submit("x", lambda: None, ui_lifetime=mine)
    assert seen == [mine]


def test_everything_else_passes_through() -> None:
    class _Manager:
        def snapshot(self):
            return ["task"]

    assert SurfaceTasks(_Manager(), lambda: None).snapshot() == ["task"]


def test_no_short_lived_surface_keeps_the_raw_task_manager() -> None:
    """The gate: ``self._task_manager = task_manager`` in a window module is a
    window whose late results land in controls that are gone."""
    offenders: list[str] = []
    for path in sorted((_ROOT / "quill" / "ui").rglob("*.py")):
        rel = path.relative_to(_ROOT).as_posix()
        if rel in _LONG_LIVED or rel.startswith("quill/ui/main_frame"):
            continue
        source = path.read_text(encoding="utf-8")
        if "_task_manager" not in source:
            continue
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "_task_manager"
                and isinstance(node.value, ast.Name)
            ):
                offenders.append(f"{rel}:{node.lineno}")
    assert offenders == [], (
        "wrap it: surface_tasks(task_manager, lambda: <window>) -- " + ", ".join(offenders)
    )
