"""Applying and remembering a window's geometry, against real wx frames.

The half of the feature that needs a display: whether ``apply_window_geometry``
actually maximizes a frame, and whether the remembered size is the one the user
chose rather than the screen.
"""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

from quill.core.window_geometry import (  # noqa: E402
    STORE_NAME,
    WindowGeometry,
    load_geometry,
    save_geometry,
)
from quill.ui.window_state import (  # noqa: E402
    apply_window_geometry,
    remember_window_geometry,
)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture()
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the geometry store at a temp directory, wherever it is imported."""
    import quill.ui.window_state as window_state

    monkeypatch.setattr(window_state, "_data_dir", lambda: tmp_path)
    return tmp_path


@pytest.fixture()
def frame(wx_app):
    made = wx.Frame(None, title="Geometry", size=(500, 400))
    yield made
    try:
        made.Destroy()
    except RuntimeError:
        pass  # a test that closed it for real; wx has already destroyed it
    wx_app.Yield()


# ---------------------------------------------------------------------------
# applying


def test_a_fresh_machine_opens_maximized(frame, data_dir: Path, wx_app) -> None:
    """The default, and the whole point of the change."""
    apply_window_geometry(frame, "radio", default_size=(500, 400))
    frame.Show()
    wx_app.Yield()
    assert frame.IsMaximized()


def test_a_remembered_un_maximized_window_comes_back_that_way(
    frame, data_dir: Path, wx_app
) -> None:
    save_geometry(data_dir, "radio", WindowGeometry(maximized=False, width=640, height=480))
    apply_window_geometry(frame, "radio", default_size=(500, 400))
    frame.Show()
    wx_app.Yield()
    assert not frame.IsMaximized()
    assert frame.GetSize().width == 640


def test_an_app_that_names_no_size_keeps_its_own(frame, data_dir: Path) -> None:
    """A user who has un-maximized but never resized gets the app's own number."""
    save_geometry(data_dir, "radio", WindowGeometry(maximized=False))
    apply_window_geometry(frame, "radio", default_size=(505, 405))
    assert frame.GetSize() == (505, 405)


def test_the_geometry_applied_is_returned(frame, data_dir: Path) -> None:
    applied = apply_window_geometry(frame, "radio", default_size=(500, 400))
    assert applied.maximized is True


def test_a_broken_store_leaves_the_frame_openable(frame, data_dir: Path) -> None:
    """A window that will not open is far worse than one at the wrong size."""
    (data_dir / STORE_NAME).write_text("{not json", encoding="utf-8")
    applied = apply_window_geometry(frame, "radio", default_size=(500, 400))
    assert applied.maximized is True
    assert frame.GetSize().width > 0


def test_two_apps_do_not_share_a_window_size(frame, data_dir: Path, wx_app) -> None:
    save_geometry(data_dir, "radio", WindowGeometry(maximized=False, width=640, height=480))
    apply_window_geometry(frame, "weather", default_size=(500, 400))
    frame.Show()
    wx_app.Yield()
    assert frame.IsMaximized(), "weather has no entry and must get the default"


# ---------------------------------------------------------------------------
# remembering


def test_an_un_maximized_size_is_what_gets_written(frame, data_dir: Path, wx_app) -> None:
    apply_window_geometry(frame, "radio", default_size=(500, 400))
    frame.Maximize(False)
    frame.SetSize((720, 560))
    frame.Show()
    wx_app.Yield()

    remember_window_geometry(frame, "radio")

    stored = load_geometry(data_dir, "radio")
    assert stored.maximized is False
    assert stored.width == 720


def test_maximizing_records_the_state_not_the_screen(frame, data_dir: Path, wx_app) -> None:
    """The detail that is easy to get wrong: a maximized GetSize is the screen.

    Recording that as the *restored* size means un-maximizing gives back a
    full-screen "restored" window, and the size the user actually chose is gone.
    """
    apply_window_geometry(frame, "radio", default_size=(500, 400))
    frame.Show()
    wx_app.Yield()
    frame.Maximize(False)
    frame.SetSize((640, 480))
    wx_app.Yield()
    frame.Maximize(True)
    wx_app.Yield()

    remember_window_geometry(frame, "radio")

    stored = load_geometry(data_dir, "radio")
    assert stored.maximized is True
    assert stored.width in (0, 640), stored
    assert stored.width < 2000, "the screen's width was recorded as the restored size"


def test_closing_the_frame_writes_the_store(frame, data_dir: Path, wx_app) -> None:
    """No app has to remember to save; the binding does it."""
    apply_window_geometry(frame, "radio", default_size=(500, 400))
    frame.Show()
    wx_app.Yield()
    frame.Maximize(False)
    frame.SetSize((680, 520))
    wx_app.Yield()

    frame.Close()
    wx_app.Yield()

    stored = load_geometry(data_dir, "radio")
    assert stored.maximized is False


def test_remembering_survives_a_read_only_profile(frame, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed write must not sit between the user and quitting."""
    import quill.ui.window_state as window_state

    def _refuse() -> Path:
        raise OSError("read-only profile")

    monkeypatch.setattr(window_state, "_data_dir", _refuse)
    remember_window_geometry(frame, "radio")  # must not raise
