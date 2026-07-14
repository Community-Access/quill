"""#25: Tools > Open Log Folder ("Reveal in Explorer") must not assume
Windows. _reveal_in_explorer used to shell out to ``explorer`` unconditionally,
which fails outright on macOS/Linux with "Explorer could not be found"."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.ui.main_frame import MainFrame


class _Frame:
    pass


def _build_frame(tmp_path: Path) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.frame = _Frame()
    frame._status: list[str] = []
    frame._set_status = lambda message: frame._status.append(message)
    return frame


def test_reveal_in_explorer_uses_explorer_on_windows(monkeypatch, tmp_path) -> None:
    import quill.ui.main_frame as main_frame_module

    frame = _build_frame(tmp_path)
    monkeypatch.setattr(main_frame_module.sys, "platform", "win32")
    calls: list[list[str]] = []
    import subprocess

    monkeypatch.setattr(subprocess, "Popen", lambda args, **kw: calls.append(args))

    frame._reveal_in_explorer(tmp_path)

    assert calls == [["explorer", str(tmp_path)]]
    assert "Explorer" in frame._status[-1]


def test_reveal_in_explorer_uses_open_on_macos(monkeypatch, tmp_path) -> None:
    import quill.ui.main_frame as main_frame_module

    frame = _build_frame(tmp_path)
    monkeypatch.setattr(main_frame_module.sys, "platform", "darwin")
    calls: list[list[str]] = []
    import subprocess

    monkeypatch.setattr(subprocess, "Popen", lambda args, **kw: calls.append(args))

    frame._reveal_in_explorer(tmp_path)

    assert calls == [["open", str(tmp_path)]]
    assert "Finder" in frame._status[-1]


def test_reveal_in_explorer_select_file_uses_open_dash_r_on_macos(monkeypatch, tmp_path) -> None:
    import quill.ui.main_frame as main_frame_module

    frame = _build_frame(tmp_path)
    target = tmp_path / "quill.log"
    target.write_text("hello", encoding="utf-8")
    monkeypatch.setattr(main_frame_module.sys, "platform", "darwin")
    calls: list[list[str]] = []
    import subprocess

    monkeypatch.setattr(subprocess, "Popen", lambda args, **kw: calls.append(args))

    frame._reveal_in_explorer(target)

    assert calls == [["open", "-R", str(target)]]


def test_reveal_in_explorer_uses_webbrowser_on_linux(monkeypatch, tmp_path) -> None:
    import quill.ui.main_frame as main_frame_module

    frame = _build_frame(tmp_path)
    monkeypatch.setattr(main_frame_module.sys, "platform", "linux")
    opened: list[str] = []
    monkeypatch.setattr(main_frame_module.webbrowser, "open", lambda uri: opened.append(uri))

    frame._reveal_in_explorer(tmp_path)

    assert opened == [tmp_path.as_uri()]


def test_reveal_in_explorer_reports_missing_path(tmp_path) -> None:
    frame = _build_frame(tmp_path)
    missing = tmp_path / "gone"

    frame._reveal_in_explorer(missing)

    assert "no longer exists" in frame._status[-1]


def test_open_containing_folder_uses_open_dash_r_on_macos(monkeypatch, tmp_path) -> None:
    import quill.ui.main_frame as main_frame_module

    frame = _build_frame(tmp_path)
    target = tmp_path / "notes.txt"
    target.write_text("hello", encoding="utf-8")
    frame.document = SimpleNamespace(path=target, name=target.name)
    monkeypatch.setattr(main_frame_module.sys, "platform", "darwin")
    calls: list[list[str]] = []
    import subprocess

    monkeypatch.setattr(subprocess, "Popen", lambda args, **kw: calls.append(args))

    frame.open_containing_folder()

    assert calls == [["open", str(target.parent)]]
    assert "Opened folder" in frame._status[-1]


def test_run_current_file_uses_open_on_macos(monkeypatch, tmp_path) -> None:
    import sys

    import quill.ui.main_frame_power_tools as power_tools_module

    frame = _build_frame(tmp_path)
    target = tmp_path / "script.py"
    target.write_text("print('hi')", encoding="utf-8")
    frame.document = SimpleNamespace(path=target, name=target.name, modified=False)
    frame.save_file = lambda: None
    frame._set_status = lambda message: frame._status.append(message)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(power_tools_module, "is_dangerous_executable", lambda _path: False)
    calls: list[list[str]] = []
    import subprocess

    monkeypatch.setattr(subprocess, "Popen", lambda args, **kw: calls.append(args))

    frame.run_current_file()

    assert calls == [["open", str(target)]]
    assert "Running script.py" in frame._status[-1]
