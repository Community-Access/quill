"""MainFrame._relaunch_quill must restart via ``-m quill``, not argv[0].

Uses the established ``MainFrame.__new__`` harness (no wx widget tree).
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

from quill.ui.main_frame import MainFrame


def test_relaunch_spawns_module_invocation(monkeypatch) -> None:
    frame = MainFrame.__new__(MainFrame)
    closed: list[str] = []
    frame.frame = SimpleNamespace(Close=lambda: closed.append("close"))
    commands: list[list[str]] = []
    monkeypatch.setattr("subprocess.Popen", lambda cmd, **kw: commands.append(cmd))
    monkeypatch.setattr(sys, "argv", ["S:/QUILL/quill/__main__.py", "--new-window"])
    monkeypatch.delattr(sys, "frozen", raising=False)

    frame._relaunch_quill()

    assert commands == [[sys.executable, "-m", "quill", "--new-window"]]
    assert closed == ["close"]


def test_relaunch_failure_reports_status_and_does_not_close(monkeypatch) -> None:
    frame = MainFrame.__new__(MainFrame)
    closed: list[str] = []
    statuses: list[str] = []
    frame.frame = SimpleNamespace(Close=lambda: closed.append("close"))
    frame._set_status = statuses.append  # type: ignore[method-assign]

    def _boom(cmd, **kw):
        raise OSError("nope")

    monkeypatch.setattr("subprocess.Popen", _boom)

    frame._relaunch_quill()

    assert closed == []
    assert statuses and "restart" in statuses[0].lower()
