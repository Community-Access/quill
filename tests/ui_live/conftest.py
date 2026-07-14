"""Live-UI test harness: boot the real MainFrame and exercise it in-process.

Unlike the source-contract UI tests (which never construct wx), these tests
build the actual `MainFrame` under a real `wx.App` so they catch the class of
bug that only appears at runtime — like a startup path touching `self.editor`
before it exists. They are **opt-in**: collected and run only when the
environment variable ``QUILL_RUN_LIVE_UI=1`` is set, so they never destabilize
the fast unit suite.

    QUILL_RUN_LIVE_UI=1 pytest tests/ui_live -q

The harness provides three things every live test relies on:

- a session ``wx.App``;
- a **modal auto-responder** — every blocking dialog (`ShowModal`, `MessageBox`)
  is patched to return a default immediately, so construction and command
  invocation can never hang waiting on a modal; and
- a ``build_frame`` factory that constructs ``MainFrame`` in an isolated data
  directory, installs a fault hook, and tears the frame down afterwards.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

_LIVE_ENV = "QUILL_RUN_LIVE_UI"

# Native/custom modal dialog classes whose ShowModal would otherwise block.
_MODAL_CLASSES = (
    "Dialog",
    "MessageDialog",
    "RichMessageDialog",
    "FileDialog",
    "DirDialog",
    "SingleChoiceDialog",
    "MultiChoiceDialog",
    "TextEntryDialog",
    "PasswordEntryDialog",
    "ColourDialog",
    "FontDialog",
    "PageSetupDialog",
    "PrintDialog",
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "live_ui: boots the real wx MainFrame; opt-in via QUILL_RUN_LIVE_UI=1"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get(_LIVE_ENV) == "1":
        return
    skip = pytest.mark.skip(reason=f"live UI test; set {_LIVE_ENV}=1 to run")
    for item in items:
        if "ui_live" in str(item.fspath):
            item.add_marker(skip)


@pytest.fixture(scope="session")
def wx_app():  # noqa: ANN201 - wx types are dynamic
    import wx

    from quill.stability.ui_responsiveness import mark_wx_main_thread

    app = wx.App(False)
    app.SetAppName("QUILL")
    mark_wx_main_thread()
    yield app
    # The process exits after the session; we deliberately do not destroy the
    # App (doing so mid-session can crash the interpreter on some platforms).


@pytest.fixture
def install_modal_responder(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201
    """Patch every blocking modal to return a default instead of waiting.

    Returns the wx id modals report; tests that need a different answer can
    re-patch a specific class.
    """
    import wx

    default_id = wx.ID_CANCEL
    for name in _MODAL_CLASSES:
        cls = getattr(wx, name, None)
        if cls is not None and hasattr(cls, "ShowModal"):
            monkeypatch.setattr(cls, "ShowModal", lambda _self: default_id, raising=False)
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: wx.OK, raising=False)
    return default_id


@pytest.fixture
def build_frame(
    wx_app, install_modal_responder, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[Callable[..., object]]:
    """Factory: build a real MainFrame in an isolated data dir, with teardown.

    Usage::

        frame = build_frame(safe_mode=True)

    ``settings`` (a dict) is written to the isolated profile before construction,
    so a test can exercise, for example, the first-run/wizard-pending path with
    ``{"setup_wizard_completed": False}``.
    """
    import wx

    # Isolate the profile so a live boot never touches the user's real data.
    data_dir = tmp_path / "profile"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("QUILL_DEV_BUILD", "1")
    monkeypatch.setenv("QUILL_DATA_DIR", str(data_dir))

    # Fail the test on any uncaught exception that reaches sys.excepthook
    # (wx otherwise swallows errors raised inside CallAfter / event handlers).
    captured: list[BaseException] = []
    original_hook = sys.excepthook

    def _hook(exc_type, exc, tb):  # noqa: ANN001
        captured.append(exc)
        original_hook(exc_type, exc, tb)

    monkeypatch.setattr(sys, "excepthook", _hook)

    built: list[object] = []

    def _build(*, safe_mode: bool = True, settings: dict | None = None) -> object:
        if settings is not None:
            # Persist via the real API so the path and versioned shape match
            # exactly what load_settings() reads (writes under QUILL_DATA_DIR).
            from quill.core.settings import Settings, save_settings

            profile = Settings()
            for key, value in settings.items():
                setattr(profile, key, value)
            save_settings(profile)
        from quill.ui.main_frame import MainFrame

        frame = MainFrame(safe_mode=safe_mode)
        built.append(frame)
        for _ in range(5):
            wx.SafeYield()
        return frame

    yield _build

    for frame in built:
        try:
            wx_frame = getattr(frame, "frame", None)
            if wx_frame is not None:
                wx_frame.Destroy()
            wx.SafeYield()
        except Exception:  # noqa: BLE001 - teardown must never mask a test result
            pass
    if captured:
        raise AssertionError(
            f"{len(captured)} uncaught exception(s) during the live session: "
            + "; ".join(repr(e) for e in captured)
        )
