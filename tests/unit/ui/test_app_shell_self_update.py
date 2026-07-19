"""One-click apply seam for the standalone apps (Radio + Cast) in AppShellFrame.

`_apply_update_and_restart` calls the shared `quill.core.self_update` engine and
closes the window on success; on a SelfUpdateError it announces and stays open.
"""

from __future__ import annotations

from types import SimpleNamespace

import quill.core.self_update as self_update
from quill.ui.app_shell import AppShellFrame


def _frame(*, portable: bool):
    calls: list[str] = []
    frame = AppShellFrame.__new__(AppShellFrame)
    frame._announce = lambda msg, **k: calls.append(f"announce:{msg}")  # type: ignore[method-assign]
    frame.frame = SimpleNamespace(Close=lambda: calls.append("close"))
    frame._running_portable_build = lambda: portable  # type: ignore[method-assign]
    frame._show_message_box = lambda *a, **k: calls.append("msgbox")  # type: ignore[method-assign]
    return frame, calls


def test_apply_now_portable_calls_begin_self_update_then_closes(monkeypatch, tmp_path):
    frame, calls = _frame(portable=True)
    got: dict = {}
    monkeypatch.setattr(self_update, "begin_self_update", lambda **kw: got.update(kw))
    target = tmp_path / "QuillRadio-Portable-2.0.3.zip"
    release = SimpleNamespace(version="2.0.3")

    frame._apply_update_and_restart(release, target)

    assert got["portable"] is True
    assert got["download_path"] == target
    assert "close" in calls


def test_apply_now_installed_passes_portable_false(monkeypatch, tmp_path):
    frame, calls = _frame(portable=False)
    got: dict = {}
    monkeypatch.setattr(self_update, "begin_self_update", lambda **kw: got.update(kw))

    frame._apply_update_and_restart(SimpleNamespace(version="2.0.3"), tmp_path / "Setup.exe")

    assert got["portable"] is False
    assert "close" in calls


def test_apply_now_failure_keeps_app_open(monkeypatch, tmp_path):
    frame, calls = _frame(portable=True)

    def boom(**kw):
        raise self_update.SelfUpdateError("nope")

    monkeypatch.setattr(self_update, "begin_self_update", boom)

    frame._apply_update_and_restart(SimpleNamespace(version="2.0.3"), tmp_path / "x.zip")

    assert "close" not in calls
    assert "msgbox" in calls
