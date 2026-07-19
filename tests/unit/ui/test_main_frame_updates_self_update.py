"""One-click apply seam for QUILL (UpdatesMixin._apply_update_and_restart).

Calls the shared quill.core.self_update engine with QUILL's own portable
detection, then closes the frame; a SelfUpdateError leaves QUILL open.
"""

from __future__ import annotations

from types import SimpleNamespace

import quill.core.self_update as self_update
import quill.core.updates as updates
from quill.ui.main_frame_updates import UpdatesMixin


def _frame():
    calls: list[str] = []
    frame = UpdatesMixin.__new__(UpdatesMixin)
    frame._announce = lambda m, **k: calls.append("announce")  # type: ignore[method-assign]
    frame.frame = SimpleNamespace(Close=lambda: calls.append("close"))
    frame._show_message_box = lambda *a, **k: calls.append("msgbox")  # type: ignore[method-assign]
    frame._wx = SimpleNamespace(ICON_ERROR=0, OK=0)
    return frame, calls


def test_quill_apply_now_portable_calls_begin_self_update_then_closes(monkeypatch, tmp_path):
    frame, calls = _frame()
    monkeypatch.setattr(updates, "running_portable", lambda: True)
    got: dict = {}
    monkeypatch.setattr(self_update, "begin_self_update", lambda **kw: got.update(kw))

    frame._apply_update_and_restart(SimpleNamespace(version="2.0.3"), tmp_path / "q.zip")

    assert got["portable"] is True
    assert got["download_path"] == tmp_path / "q.zip"
    assert "close" in calls


def test_quill_apply_now_failure_keeps_app_open(monkeypatch, tmp_path):
    frame, calls = _frame()
    monkeypatch.setattr(updates, "running_portable", lambda: False)

    def boom(**kw):
        raise self_update.SelfUpdateError("nope")

    monkeypatch.setattr(self_update, "begin_self_update", boom)

    frame._apply_update_and_restart(SimpleNamespace(version="2.0.3"), tmp_path / "Setup.exe")

    assert "close" not in calls
    assert "msgbox" in calls
