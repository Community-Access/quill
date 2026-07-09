"""Tests for :class:`quill.ui.mac_open_file_app.MacOpenFileApp`.

Without this ``wx.App`` subclass, QUILL launched via Finder's "Open With",
a Dock-icon drag, or `open -a Quill somefile.txt` from Terminal never sees
the requested file: those actions arrive as a macOS ``NSApplication``
"openFile" Apple Event, which wx only surfaces through the
``MacOpenFile``/``MacOpenFiles`` overrides exercised here.

``MacOpenFile``/``MacOpenFiles`` are Mac-only wx hooks, but the base
``wx.App`` implements them as harmless no-ops on every port, so these tests
run on any platform wx is installed on (including this Windows/msw dev
environment) -- only the *delivery* of the Apple Event itself is
Mac-specific and cannot be exercised without real macOS hardware.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import wx  # type: ignore[import-not-found]

pytest.importorskip("wx")

from quill.ui.mac_open_file_app import MacOpenFileApp  # noqa: E402


@pytest.fixture
def app():
    application = MacOpenFileApp(False)
    yield application
    application.Destroy()


class _FakeFrame:
    def __init__(self) -> None:
        self.shown = False
        self.raised = False
        self.attention_requested = False

    def Show(self, value: bool = True) -> None:  # noqa: N802 - wx API shape
        self.shown = value

    def Raise(self) -> None:  # noqa: N802 - wx API shape
        self.raised = True

    def RequestUserAttention(self) -> None:  # noqa: N802 - wx API shape
        self.attention_requested = True


class _FakeMainFrame:
    def __init__(self) -> None:
        self.frame = _FakeFrame()
        self.requests: list[object] = []

    def _handle_shell_request(self, candidate: object) -> None:
        self.requests.append(candidate)


@pytest.fixture
def sample_file():
    with tempfile.TemporaryDirectory(prefix="mac_open_file_") as tmp:
        path = Path(tmp) / "notes.txt"
        path.write_text("hello", encoding="utf-8")
        yield path


def test_mac_open_files_dispatches_immediately_when_frame_ready(app, sample_file) -> None:
    main_frame = _FakeMainFrame()
    app.main_frame = main_frame

    app.MacOpenFiles([str(sample_file)])

    assert len(main_frame.requests) == 1
    assert main_frame.requests[0].path == sample_file.resolve()
    assert main_frame.frame.shown is True
    assert main_frame.frame.raised is True
    assert main_frame.frame.attention_requested is True


def test_mac_open_file_singular_delegates_to_plural(app, sample_file) -> None:
    main_frame = _FakeMainFrame()
    app.main_frame = main_frame

    app.MacOpenFile(str(sample_file))

    assert len(main_frame.requests) == 1
    assert main_frame.requests[0].path == sample_file.resolve()


def test_mac_open_files_buffers_until_main_frame_assigned(app, sample_file) -> None:
    # Mirrors a cold launch: Finder's Apple Event can arrive before
    # run_app finishes constructing MainFrame.
    app.MacOpenFiles([str(sample_file)])
    main_frame = _FakeMainFrame()
    assert main_frame.requests == []  # nothing dispatched yet

    app.main_frame = main_frame
    app.flush_pending()

    assert len(main_frame.requests) == 1
    assert main_frame.requests[0].path == sample_file.resolve()


def test_flush_pending_is_a_noop_with_nothing_buffered(app) -> None:
    main_frame = _FakeMainFrame()
    app.main_frame = main_frame
    app.flush_pending()  # must not raise or touch the frame
    assert main_frame.requests == []
    assert main_frame.frame.shown is False


def test_nonexistent_path_is_not_dispatched(app, tmp_path) -> None:
    main_frame = _FakeMainFrame()
    app.main_frame = main_frame

    app.MacOpenFiles([str(tmp_path / "does-not-exist.txt")])

    assert main_frame.requests == []
    # No file was actually opened, so the window is not forced to the front.
    assert main_frame.frame.shown is False


def test_app_is_a_wx_app_subclass(app) -> None:
    assert isinstance(app, wx.App)
