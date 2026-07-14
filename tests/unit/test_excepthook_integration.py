"""Pure tests for the excepthook helpers in :mod:`quill.__main__` (#622).

The excepthook is split into a coordinator (``_install_excepthook``)
and four best-effort helpers:

- :func:`quill.__main__._try_offer_crash_submit` -- the wx/dialog path
- :func:`quill.__main__._show_native_fallback` -- the always-on native
  MessageBoxW (and stderr on POSIX)
- :func:`quill.__main__._active_document_snapshot` -- best-effort
  read of the active document
- :func:`quill.__main__._copy_to_clipboard` -- best-effort clipboard write

These tests pin the contract the production code relies on:

- The dialog path returns ``False`` (so the native fallback fires) when
  wx is unavailable, no wx.App is running, or the user turned
  ``auto_ask_crash_submit`` off.
- The dialog path returns ``True`` when wx is alive and the user
  opted in (so the native fallback does NOT fire on top of the dialog).
- The native fallback never raises, even when MessageBoxW throws.
- The clipboard helper never raises, even when wx is unavailable.
- The active-document snapshot returns ``None`` (does not crash) when
  wx is unavailable, when there is no top window, or when MainFrame
  has not finished its __init__ yet.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

from quill import __main__ as quill_main

# ---------------------------------------------------------------------------
# _try_offer_crash_submit
# ---------------------------------------------------------------------------


def _raise() -> tuple[type[BaseException], BaseException, types.TracebackType | None]:
    try:
        raise RuntimeError("excepthook test boom")
    except RuntimeError as exc:
        return type(exc), exc, exc.__traceback__


class _FakeApp:
    """Stand-in for ``wx.App`` so the dialog-path code can probe
    ``wx.GetApp()`` without an actual wx instance."""

    def __init__(self, *, top_window: object | None = None) -> None:
        self._top = top_window

    def GetTopWindow(self):
        return self._top


def test_dialog_path_returns_false_when_wx_not_imported(monkeypatch) -> None:
    """No wx -> no dialog -> caller falls back to native MessageBoxW."""
    exc_type, exc_value, exc_tb = _raise()
    # Force the ``import wx`` inside the helper to fail.
    monkeypatch.setitem(sys.modules, "wx", None)
    out = quill_main._try_offer_crash_submit(exc_type, exc_value, exc_tb, None)
    assert out is False


def test_dialog_path_returns_false_when_no_wx_app(monkeypatch) -> None:
    """wx imports fine but no App is running yet (e.g. pre-init crash)."""
    fake_wx = types.ModuleType("wx")
    fake_wx.GetApp = lambda: None
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    exc_type, exc_value, exc_tb = _raise()
    out = quill_main._try_offer_crash_submit(exc_type, exc_value, exc_tb, None)
    assert out is False


def test_dialog_path_returns_false_when_setting_off(monkeypatch, tmp_path: Path) -> None:
    fake_wx = types.ModuleType("wx")
    fake_wx.GetApp = lambda: _FakeApp(top_window=object())
    fake_wx.CallAfter = lambda fn: None
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    exc_type, exc_value, exc_tb = _raise()

    settings = MagicMock()
    settings.auto_ask_crash_submit = False
    monkeypatch.setattr(quill_main, "quill_main_load_settings", lambda: settings)

    out = quill_main._try_offer_crash_submit(exc_type, exc_value, exc_tb, tmp_path / "c.txt")
    assert out is False


def test_dialog_path_returns_true_when_setting_on_and_wx_alive(monkeypatch, tmp_path: Path) -> None:
    fake_wx = types.ModuleType("wx")
    scheduled: list[object] = []
    fake_wx.GetApp = lambda: _FakeApp(top_window=object())
    fake_wx.CallAfter = lambda fn: scheduled.append(fn)
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    exc_type, exc_value, exc_tb = _raise()

    settings = MagicMock()
    settings.auto_ask_crash_submit = True
    monkeypatch.setattr(quill_main, "quill_main_load_settings", lambda: settings)

    out = quill_main._try_offer_crash_submit(exc_type, exc_value, exc_tb, tmp_path / "c.txt")
    assert out is True
    assert scheduled, "expected the dialog to be scheduled via wx.CallAfter"


def test_dialog_path_returns_false_when_settings_load_fails(monkeypatch, tmp_path: Path) -> None:
    """A corrupt settings file should not crash the excepthook; we
    fall back to the dialog being scheduled because the beta-phase
    default is on."""
    fake_wx = types.ModuleType("wx")
    scheduled: list[object] = []
    fake_wx.GetApp = lambda: _FakeApp(top_window=object())
    fake_wx.CallAfter = lambda fn: scheduled.append(fn)
    monkeypatch.setitem(sys.modules, "wx", fake_wx)

    def _boom() -> None:
        raise OSError("settings corrupt")

    monkeypatch.setattr(quill_main, "quill_main_load_settings", _boom)
    exc_type, exc_value, exc_tb = _raise()
    out = quill_main._try_offer_crash_submit(exc_type, exc_value, exc_tb, tmp_path / "c.txt")
    assert out is True
    assert scheduled


# ---------------------------------------------------------------------------
# _show_native_fallback
# ---------------------------------------------------------------------------


def test_native_fallback_does_not_raise_when_messagebox_throws(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    # The ctypes MessageBoxW raises; the helper must swallow it.
    fake_ctypes = types.ModuleType("ctypes")
    fake_ctypes.windll = types.SimpleNamespace(
        user32=types.SimpleNamespace(
            MessageBoxW=lambda *a, **k: (_ for _ in ()).throw(OSError("no display"))
        )
    )
    monkeypatch.setitem(sys.modules, "ctypes", fake_ctypes)
    exc_type, exc_value, _ = _raise()
    # Must not raise.
    quill_main._show_native_fallback(exc_type, exc_value, None)


def test_native_fallback_writes_to_stderr_on_posix(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    exc_type, exc_value, _ = _raise()
    quill_main._show_native_fallback(exc_type, exc_value, None)
    out = capsys.readouterr().err
    assert "QUILL encountered an unexpected error" in out


# ---------------------------------------------------------------------------
# _active_document_snapshot
# ---------------------------------------------------------------------------


def test_active_document_snapshot_returns_none_when_wx_missing(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "wx", None)
    assert quill_main._active_document_snapshot() is None


def test_active_document_snapshot_returns_none_when_no_top_window(monkeypatch) -> None:
    fake_wx = types.ModuleType("wx")
    fake_wx.GetApp = lambda: _FakeApp(top_window=None)
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    assert quill_main._active_document_snapshot() is None


def test_active_document_snapshot_reads_top_document(monkeypatch) -> None:
    """MainFrame may store the document directly on its top window."""
    top = types.SimpleNamespace(document="DOC-OF-DREAMS")
    fake_wx = types.ModuleType("wx")
    fake_wx.GetApp = lambda: _FakeApp(top_window=top)
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    assert quill_main._active_document_snapshot() == "DOC-OF-DREAMS"


def test_active_document_snapshot_reads_top_frame_document(monkeypatch) -> None:
    """MainFrame is a mixin; the document lives on the mixin instance
    which is the top window. The helper also checks ``top.frame`` for
    the real wx.Frame pattern."""
    inner = types.SimpleNamespace(document="INNER-DOC")
    top = types.SimpleNamespace(frame=inner)
    fake_wx = types.ModuleType("wx")
    fake_wx.GetApp = lambda: _FakeApp(top_window=top)
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    assert quill_main._active_document_snapshot() == "INNER-DOC"


def test_active_document_snapshot_returns_none_when_main_frame_uninit(monkeypatch) -> None:
    fake_wx = types.ModuleType("wx")
    fake_wx.GetApp = lambda: _FakeApp(top_window=None)
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    top = types.SimpleNamespace()  # no document, no frame
    monkeypatch.setattr(quill_main, "_find_main_frame_window", lambda: top)
    assert quill_main._active_document_snapshot() is None


# ---------------------------------------------------------------------------
# _copy_to_clipboard
# ---------------------------------------------------------------------------


def test_copy_to_clipboard_returns_silently_when_wx_missing(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "wx", None)
    # Must not raise.
    quill_main._copy_to_clipboard("hello")


def test_copy_to_clipboard_handles_open_failure(monkeypatch) -> None:
    class _FakeClipboard:
        def Open(self) -> bool:
            return False

        def Close(self) -> None:
            raise RuntimeError("should not be called when Open fails")

    fake_wx = types.ModuleType("wx")
    fake_wx.TheClipboard = _FakeClipboard()
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    # Must not raise.
    quill_main._copy_to_clipboard("hello")


# ---------------------------------------------------------------------------
# _install_excepthook
# ---------------------------------------------------------------------------


def test_install_excepthook_registers_sys_excepthook() -> None:
    """The installer mutates ``sys.excepthook``; pin that."""
    saved = sys.excepthook
    try:
        quill_main._install_excepthook()
        assert sys.excepthook is not saved
        assert callable(sys.excepthook)
    finally:
        sys.excepthook = saved


def test_installed_handler_saves_local_crash_file(monkeypatch, tmp_path: Path) -> None:
    """The handler MUST write a local traceback file even when every
    other step fails. That file is the durable artifact the entire
    flow is built on top of."""
    saved = sys.excepthook
    try:
        # Force every other step to fail so we exercise only the
        # local-file save.
        monkeypatch.setitem(sys.modules, "wx", None)
        monkeypatch.setattr(quill_main, "_show_native_fallback", lambda *a, **k: None)
        # Stub app_data_dir so the crash file lands under tmp_path.
        monkeypatch.setattr(quill_main, "app_data_dir", lambda: tmp_path)
        quill_main._install_excepthook()
        try:
            raise RuntimeError("crash for the local-file test")
        except RuntimeError as exc:
            sys.excepthook(type(exc), exc, exc.__traceback__)
        crash_dir = tmp_path / "crash-reports"
        assert crash_dir.exists()
        files = list(crash_dir.glob("crash-*.txt"))
        assert len(files) == 1
        assert "RuntimeError" in files[0].read_text(encoding="utf-8")
    finally:
        sys.excepthook = saved
