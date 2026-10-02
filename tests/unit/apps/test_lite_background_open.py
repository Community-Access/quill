"""Large and networked files open off the UI thread (qc.md F-05).

``DocumentFrame.load`` read, decoded and safety-scanned on the UI thread, so a
large file, a slow network folder or a damaged RTF froze the window with
nothing said. Opening is now prepare (any thread, wx-free) then commit (UI
thread, only if still wanted). These cover:

* the prepare half on real files: plain decoding keeps encoding and line
  endings, rich text comes back sanitised, the size/network policy;
* the window half on a stand-in frame with the shipped mixin methods: busy is
  said once and the document is read-only while empty-and-loading; a result
  for an older generation, a closed window or a shutting-down app is dropped;
  failure offers Try Again, or closes the empty window;
* one run through the real ``TaskManager`` and a real wx event loop, which is
  the boundary the whole change exists for.
"""

from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.apps import lite_window_open as open_mod
from quill.apps.lite_window_open import DocumentBackgroundOpenMixin
from quill.core.lite import open_prepare

# -- prepare: the half that may run anywhere --------------------------------------- #


def test_plain_prepare_keeps_the_encoding_and_line_endings(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_bytes("caf\xe9\r\nsecond line\r\n".encode("cp1252"))
    prepared = open_prepare.prepare(path, open_prepare.PLAIN)
    assert prepared.mode == open_prepare.PLAIN
    assert "caf\xe9" in prepared.text
    assert prepared.encoding == "cp1252"
    assert prepared.newline == "\r\n"


def test_rich_prepare_returns_sanitised_rtf_and_what_it_removed(tmp_path: Path) -> None:
    path = tmp_path / "doc.rtf"
    path.write_text(
        r"{\rtf1\ansi Hello {\object\objemb {\*\objdata 0102}} world}", encoding="utf-8"
    )
    prepared = open_prepare.prepare(path, open_prepare.RICH)
    assert prepared.mode == open_prepare.RICH
    assert b"Hello" in prepared.rtf
    assert b"objdata" not in prepared.rtf
    assert prepared.blocked  # the embedded object was named


def test_an_unreadable_file_raises_oserror_for_the_caller_to_report(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        open_prepare.prepare(tmp_path / "missing.txt", open_prepare.PLAIN)


def test_the_policy_reads_large_and_networked_files_in_the_background(tmp_path: Path) -> None:
    small = tmp_path / "small.txt"
    small.write_text("short", encoding="utf-8")
    big = tmp_path / "big.txt"
    big.write_bytes(b"x" * open_prepare.BACKGROUND_THRESHOLD_BYTES)
    assert open_prepare.prepare_in_background(small) is False
    assert open_prepare.prepare_in_background(big) is True
    assert open_prepare.prepare_in_background(Path(r"\\server\share\notes.txt")) is True
    assert open_prepare.prepare_in_background(tmp_path / "missing.txt") is False


# -- the window half ----------------------------------------------------------------- #


class _Control:
    def __init__(self) -> None:
        self.editable = True
        self.focused = 0

    def SetEditable(self, on: bool) -> None:  # noqa: N802 - wx API shape
        self.editable = on

    def SetFocus(self) -> None:  # noqa: N802
        self.focused += 1


class _FakeTasks:
    def __init__(self) -> None:
        self.submitted: list[dict[str, Any]] = []

    def submit(self, name: str, func: Any, **kwargs: Any) -> None:
        self.submitted.append({"name": name, "func": func, **kwargs})


class _Frame(DocumentBackgroundOpenMixin):
    """A stand-in carrying exactly what the mixin touches."""

    def __init__(self, tasks: _FakeTasks) -> None:
        self.app = SimpleNamespace(
            shutting_down=False, task_manager=tasks, refresh_all_menus=lambda: None
        )
        self.control = _Control()
        self.number = 2
        self.path: Path | None = None
        self.modified = False
        self.titles: list[str] = []
        self.status: list[str] = []
        self.spoken: list[str] = []
        self.committed: list[tuple[Path, Any]] = []
        self.failures: list[str] = []
        self.closed = 0
        self.deleted = False

    # what the real frame provides
    def SetTitle(self, title: str) -> None:  # noqa: N802
        self.titles.append(title)

    def _set_status_message(self, message: str) -> None:
        self.status.append(message)

    def _announce(self, message: str) -> None:
        self.spoken.append(message)

    def _check_mode_available(self, mode: str) -> None:
        pass

    def _commit_load(self, path: Path, prepared: Any) -> bool:
        self.committed.append((path, prepared))
        self.path = path
        return True

    def _update_title(self) -> None:
        pass

    def _report_failure(self, caption: str, message: str) -> None:
        self.failures.append(message)

    def _cue(self, _event: str) -> None:
        pass

    def Close(self) -> None:  # noqa: N802
        self.closed += 1

    def IsBeingDeleted(self) -> bool:  # noqa: N802
        return self.deleted


@pytest.fixture
def frame() -> _Frame:
    return _Frame(_FakeTasks())


def test_starting_says_busy_once_and_locks_the_empty_document(frame: _Frame) -> None:
    frame.begin_background_load(Path("C:/big.txt"))
    assert frame.spoken == ["Opening big.txt"]
    assert frame.status == ["Opening big.txt"]
    assert frame.titles == ["2: Opening big.txt... - QUILL Lite"]
    assert frame.control.editable is False
    assert frame.opening_path == Path("C:/big.txt")
    submitted = frame.app.task_manager.submitted
    assert len(submitted) == 1 and submitted[0]["name"] == "lite-open"
    assert submitted[0]["ui_lifetime"].is_alive


def test_a_result_for_the_current_open_is_committed_and_focused(frame: _Frame) -> None:
    frame.begin_background_load(Path("C:/big.txt"))
    task = frame.app.task_manager.submitted[0]
    task["on_success"]("op", "prepared")
    assert frame.committed == [(Path("C:/big.txt"), "prepared")]
    assert frame.control.editable is True
    assert frame.control.focused == 1
    assert frame.opening_path is None
    assert frame.status[-1] == ""


def test_a_result_for_an_older_open_is_dropped(frame: _Frame) -> None:
    frame.begin_background_load(Path("C:/first.txt"))
    first = frame.app.task_manager.submitted[0]
    frame.begin_background_load(Path("C:/second.txt"))
    assert first["ui_lifetime"].is_alive is False  # the old token is invalidated
    first["on_success"]("op", "stale")
    assert frame.committed == []


def test_closing_the_window_is_cancel(frame: _Frame) -> None:
    frame.begin_background_load(Path("C:/big.txt"))
    task = frame.app.task_manager.submitted[0]
    frame.cancel_background_load()
    assert task["ui_lifetime"].is_alive is False
    task["on_success"]("op", "late")  # even delivered directly, it is dropped
    assert frame.committed == []
    assert frame.opening_path is None


def test_nothing_lands_in_a_window_being_destroyed_or_an_app_shutting_down(frame: _Frame) -> None:
    frame.begin_background_load(Path("C:/big.txt"))
    task = frame.app.task_manager.submitted[0]
    frame.deleted = True
    task["on_success"]("op", "late")
    frame.deleted = False
    frame.app.shutting_down = True
    task["on_success"]("op", "late")
    assert frame.committed == []


def test_failure_offers_try_again(frame: _Frame, monkeypatch: pytest.MonkeyPatch) -> None:
    import wx

    import quill.ui.dialog_contract as contract

    asked: list[str] = []
    monkeypatch.setattr(
        contract, "show_message_box", lambda message, *_a, **_k: asked.append(message) or wx.YES
    )
    frame.begin_background_load(Path("C:/big.txt"))
    frame.app.task_manager.submitted[0]["on_failure"]("op", OSError("device not ready"))
    assert "device not ready" in asked[0]
    assert "Try again?" in asked[0]
    assert len(frame.app.task_manager.submitted) == 2  # retried
    assert frame.control.editable is False  # locked again for the retry


def test_declining_closes_the_empty_window(frame: _Frame, monkeypatch: pytest.MonkeyPatch) -> None:
    import wx

    import quill.ui.dialog_contract as contract

    monkeypatch.setattr(contract, "show_message_box", lambda *_a, **_k: wx.NO)
    frame.begin_background_load(Path("C:/big.txt"))
    frame.app.task_manager.submitted[0]["on_failure"]("op", OSError("gone"))
    assert frame.closed == 1
    assert frame.control.editable is True


def test_declining_keeps_a_window_that_holds_something(
    frame: _Frame, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wx

    import quill.ui.dialog_contract as contract

    monkeypatch.setattr(contract, "show_message_box", lambda *_a, **_k: wx.NO)
    frame.modified = True
    frame.begin_background_load(Path("C:/big.txt"))
    frame.app.task_manager.submitted[0]["on_failure"]("op", OSError("gone"))
    assert frame.closed == 0


def test_the_app_creates_one_task_manager_on_first_use() -> None:
    app = SimpleNamespace()
    first = open_mod.app_task_manager(app)
    assert open_mod.app_task_manager(app) is first
    first.shutdown(wait=False, cancel_pending=True)


# -- the real boundary: a worker thread, then the wx event loop ------------------------ #


def test_a_real_background_open_reads_on_a_worker_and_commits_on_the_ui_thread(
    tmp_path: Path,
) -> None:
    wx = pytest.importorskip("wx")
    import threading

    from quill.stability.task_manager import TaskManager

    app = wx.App()
    path = tmp_path / "big.txt"
    path.write_text("hello from a large file\n", encoding="utf-8")
    tasks = TaskManager(max_workers=1)
    frame = _Frame(tasks)  # type: ignore[arg-type]
    commit_threads: list[str] = []
    original = frame._commit_load

    def recording_commit(p: Path, prepared: Any) -> bool:
        commit_threads.append(threading.current_thread().name)
        return original(p, prepared)

    frame._commit_load = recording_commit  # type: ignore[method-assign]
    try:
        frame.begin_background_load(path)
        deadline = time.monotonic() + 10
        while not frame.committed and time.monotonic() < deadline:
            app.Yield(True)
            time.sleep(0.01)
        assert frame.committed, "the prepared document never reached the window"
        committed_path, prepared = frame.committed[0]
        assert committed_path == path
        assert prepared.text.startswith("hello from a large file")
        assert commit_threads == [threading.main_thread().name]
    finally:
        tasks.shutdown(wait=True)
        app.Destroy()


# -- the app routes only large or networked files to the background -------------------- #


def _app_host(tmp_path: Path) -> Any:
    from quill.apps.lite import QuillLiteApp as LiteApp

    opened: list[Any] = []

    class _NewFrame:
        def begin_background_load(self, path: Path) -> None:
            opened.append(("background", path))

    host = SimpleNamespace(
        frames=[],
        new_window=lambda mode: _NewFrame(),
        _offer_to_create=lambda _p: True,
        _confirm_large_file=lambda _p: True,
        opened=opened,
    )
    host._frame_for = lambda path: LiteApp._frame_for(host, path)
    host.open_path = lambda path, reuse=None: LiteApp.open_path(host, path, reuse)
    return host


def test_a_large_file_opens_in_a_new_window_in_the_background(tmp_path: Path) -> None:
    big = tmp_path / "big.txt"
    big.write_bytes(b"x" * open_prepare.BACKGROUND_THRESHOLD_BYTES)
    host = _app_host(tmp_path)
    assert host.open_path(big) is True
    assert host.opened == [("background", big)]


def test_a_file_still_opening_is_not_opened_twice(tmp_path: Path) -> None:
    big = tmp_path / "big.txt"
    big.write_bytes(b"x")
    focused: list[Any] = []
    host = _app_host(tmp_path)
    loading = SimpleNamespace(path=None, opening_path=big)
    host.frames = [loading]
    host.focus_frame = focused.append
    assert host.open_path(big) is True
    assert focused == [loading]
    assert host.opened == []
