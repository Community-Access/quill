"""QUILL Lite: Search in Files and Replace Across Files, QUILL's window and keys.

QUILL Lite reserved Ctrl+Alt+Shift+F for Search in Files and never filled it
(QUILLVille, Chris Nova, October 2026). The window and the work are QUILL's
(ui/file_search_prompt, core/file_search); these hold QUILL Lite's half: what
it asks, where the report goes, and that nothing is written unless asked.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.apps import lite_file_search
from quill.apps.lite_file_search import DocumentFileSearchMixin
from quill.core.search import SearchOptions
from quill.ui.file_search_prompt import FileSearchRequest


class _Control:
    def __init__(self) -> None:
        self.value = ""

    def SetValue(self, text: str) -> None:
        self.value = text

    def SetInsertionPoint(self, _pos: int) -> None:
        pass


class _Window(DocumentFileSearchMixin):
    def __init__(self, folder: Path, request: FileSearchRequest | None) -> None:
        self.path = folder / "open.txt"
        self.said: list[str] = []
        self.opened: list[_Control] = []
        self.request = request

        def new_window(_mode: str) -> Any:
            control = _Control()
            self.opened.append(control)
            return SimpleNamespace(control=control)

        self.app = SimpleNamespace(
            new_window=new_window, settings=SimpleNamespace(default_mode="plain")
        )

    def _announce(self, text: str, **_kwargs: Any) -> None:
        self.said.append(text)

    def _file_search_request(self, *, replace: bool) -> Any:
        self.asked_replace = replace
        return self.request

    def _run_file_task(self, name: str, work: Any, done: Any) -> None:
        done(work())  # inline: the task manager is QUILL's, tested there


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    (tmp_path / "one.txt").write_text("a cat\nno\n", encoding="utf-8")
    (tmp_path / "two.txt").write_text("cat cat\n", encoding="utf-8")
    (tmp_path / "skip.md").write_text("cat\n", encoding="utf-8")
    return tmp_path


def _request(
    folder: Path, *, replacement: str | None = None, preview: bool = False
) -> FileSearchRequest:
    return FileSearchRequest(
        root=folder,
        pattern="*.txt",
        query="cat",
        replacement=replacement,
        options=SearchOptions(),
        output_mode="context",
        preview_before_replace=preview,
    )


def test_search_reports_in_a_new_window_and_says_the_counts(folder: Path) -> None:
    window = _Window(folder, _request(folder))
    window.cmd_search_in_files()
    assert window.asked_replace is False
    assert len(window.opened) == 1 and "two.txt" in window.opened[0].value
    assert "skip.md" not in window.opened[0].value  # the pattern is honoured
    assert window.said[-1] == "3 matches in 2 of 2 files."


def test_cancel_does_nothing(folder: Path) -> None:
    window = _Window(folder, None)
    window.cmd_search_in_files()
    window.cmd_replace_in_files()
    assert window.opened == [] and window.said == []


def test_replace_without_preview_writes_the_files(folder: Path) -> None:
    window = _Window(folder, _request(folder, replacement="dog"))
    window.cmd_replace_in_files()
    assert window.asked_replace is True
    assert (folder / "two.txt").read_text(encoding="utf-8") == "dog dog\n"
    assert (folder / "skip.md").read_text(encoding="utf-8") == "cat\n"


def test_the_preview_asks_and_no_writes_nothing(folder: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import wx

    from quill.ui import dialog_contract

    monkeypatch.setattr(dialog_contract, "show_message_box", lambda *a, **k: wx.NO)
    window = _Window(folder, _request(folder, replacement="dog", preview=True))
    window.cmd_replace_in_files()
    assert (folder / "two.txt").read_text(encoding="utf-8") == "cat cat\n"
    assert window.said[-1] == "Nothing was replaced."
    assert len(window.opened) == 1  # the preview itself


def test_the_preview_yes_writes(folder: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import wx

    from quill.ui import dialog_contract

    monkeypatch.setattr(dialog_contract, "show_message_box", lambda *a, **k: wx.YES)
    window = _Window(folder, _request(folder, replacement="dog", preview=True))
    window.cmd_replace_in_files()
    assert (folder / "one.txt").read_text(encoding="utf-8") == "a dog\nno\n"


def test_the_window_is_quills_own(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from quill.ui import file_search_prompt

    seen: dict[str, Any] = {}
    monkeypatch.setattr(file_search_prompt, "prompt_file_search", lambda **kw: seen.update(kw))

    class _Real(DocumentFileSearchMixin):
        path = tmp_path / "doc.txt"
        app = None

        def _announce(self, text: str, **_kwargs: Any) -> None:
            pass

    assert _Real()._file_search_request(replace=True) is None
    assert seen["replace"] is True and seen["default_root"] == tmp_path
    assert lite_file_search.__name__ == "quill.apps.lite_file_search"
