"""QUILL Lite's half of the 2026-10-04 PlanCake design note, behaviourally.

Open from URL, Open from Clipboard, a drop, Reopen with Encoding and the
save-time disk check, through the handlers the menu binds. The network, the
clipboard and the two questions are patched where the handlers import them;
everything else is the shipped code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.open_sources import FILES, NONE, NOTHING_TO_OPEN, URL, ClipboardOpen


class _FlowRecorder:
    """Stands in for the shared UrlOpenFlow; records what it was asked to open."""

    started: list[str] = []

    def __init__(self, parent: Any, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def start(self, address: str) -> bool:
        _FlowRecorder.started.append(address)
        return True


@pytest.fixture
def flow(monkeypatch: pytest.MonkeyPatch) -> type[_FlowRecorder]:
    _FlowRecorder.started = []
    monkeypatch.setattr("quill.ui.open_from_url.UrlOpenFlow", _FlowRecorder)
    return _FlowRecorder


def _clipboard(monkeypatch: pytest.MonkeyPatch, found: ClipboardOpen) -> None:
    monkeypatch.setattr("quill.ui.open_sources_ui.read_clipboard", lambda: found)


# -- Open from Clipboard ------------------------------------------------------ #


def test_open_from_clipboard_opens_every_copied_file_in_turn(
    lite_window: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first, second = tmp_path / "a.md", tmp_path / "b.txt"
    _clipboard(monkeypatch, ClipboardOpen(FILES, paths=(first, second)))
    win = lite_window("")
    win.cmd_open_from_clipboard()
    opened = [args[0] for args, _kwargs in win.app.opened]
    assert opened == [first, second]
    # Only the first may claim this blank window.
    assert win.app.opened[0][1]["reuse"] is win
    assert win.app.opened[1][1]["reuse"] is None
    assert win.announcements[-1] == "Opened 2 files from the clipboard."


def test_one_file_from_the_clipboard_says_nothing_extra(
    lite_window: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _clipboard(monkeypatch, ClipboardOpen(FILES, paths=(tmp_path / "a.md",)))
    win = lite_window("")
    win.cmd_open_from_clipboard()
    assert len(win.app.opened) == 1
    assert win.announcements == []


def test_a_link_on_the_clipboard_goes_through_open_from_url(
    lite_window: Any, monkeypatch: pytest.MonkeyPatch, flow: type[_FlowRecorder]
) -> None:
    _clipboard(monkeypatch, ClipboardOpen(URL, url="https://example.com/plan.md"))
    win = lite_window("")
    win.cmd_open_from_clipboard()
    assert flow.started == ["https://example.com/plan.md"]


def test_an_empty_clipboard_is_one_plain_sentence(
    lite_window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clipboard(monkeypatch, ClipboardOpen(NONE))
    win = lite_window("")
    win.cmd_open_from_clipboard()
    assert win.announcements == [NOTHING_TO_OPEN]
    assert win.app.opened == []


# -- Open from URL ------------------------------------------------------------ #


def test_open_from_url_starts_the_shared_flow_with_the_typed_address(
    lite_window: Any, monkeypatch: pytest.MonkeyPatch, flow: type[_FlowRecorder]
) -> None:
    monkeypatch.setattr(
        "quill.ui.open_from_url.ask_for_url", lambda _parent: "https://example.com/a.md"
    )
    win = lite_window("")
    win.cmd_open_from_url()
    assert flow.started == ["https://example.com/a.md"]


def test_open_from_url_cancelled_downloads_nothing(
    lite_window: Any, monkeypatch: pytest.MonkeyPatch, flow: type[_FlowRecorder]
) -> None:
    monkeypatch.setattr("quill.ui.open_from_url.ask_for_url", lambda _parent: None)
    win = lite_window("")
    win.cmd_open_from_url()
    assert flow.started == []


def test_a_finished_download_opens_untitled_and_its_temp_file_is_removed(
    lite_window: Any, tmp_path: Path
) -> None:
    temp = tmp_path / "quill-url-abc.md"
    temp.write_bytes(b"caf" + bytes([0xE9]) + b" plan\r\n")
    download = type("D", (), {"local_path": str(temp), "filename": "plan.md"})()
    win = lite_window("")
    win._open_downloaded(download)
    assert win.control.GetValue() == "café plan\n"
    assert win.encoding == "cp1252"
    assert win.path is None
    assert win.download_name == "plan.md"
    assert win.modified is True
    assert not temp.exists()


# -- dropped files ------------------------------------------------------------ #


def test_dropped_files_open_and_a_folder_is_counted_not_opened(
    lite_window: Any, tmp_path: Path
) -> None:
    note = tmp_path / "note.txt"
    note.write_text("x", encoding="utf-8")
    win = lite_window("")
    win._open_dropped_files([str(note), str(tmp_path)])
    assert [args[0] for args, _kwargs in win.app.opened] == [note]
    assert win.announcements[-1] == "Opened 1 dropped file. 1 could not be opened."


# -- Reopen with Encoding ----------------------------------------------------- #


def test_reopen_with_encoding_reads_the_same_bytes_as_the_chosen_code_page(
    lite_window: Any, tmp_path: Path
) -> None:
    target = tmp_path / "old.txt"
    target.write_bytes(bytes([0xC0, 0xE9, 0xF0]) + b"\r\n")
    win = lite_window("wrong")
    win.path = target
    win.reopen_with_encoding("cp1251")
    assert win.control.GetValue() == "Айр\n"
    assert (win.encoding, win.newline) == ("cp1251", "\r\n")
    assert win.modified is False
    assert win.announcements[-1].startswith("Reopened as Windows-1251")


def test_a_code_page_that_does_not_fit_changes_nothing(lite_window: Any, tmp_path: Path) -> None:
    target = tmp_path / "old.txt"
    target.write_bytes(bytes([0x81, 0xFF]))
    win = lite_window("as it was")
    win.path = target
    win.reopen_with_encoding("utf-8")
    assert win.control.GetValue() == "as it was"
    assert win.announcements[-1].startswith("This file is not valid UTF-8")


def test_the_file_format_window_offers_reopen_for_a_file_on_disk(
    lite_window: Any, lite_dialogs: Any, tmp_path: Path
) -> None:
    target = tmp_path / "f.txt"
    target.write_text("x", encoding="utf-8")
    win = lite_window("x")
    win.path = target
    win.cmd_file_format()
    assert lite_dialogs.kwargs_for("edit_file_format")["on_reopen"] == win.reopen_with_encoding


# -- never overwrite an unseen change ----------------------------------------- #


def _changed_on_disk(win: Any, tmp_path: Path) -> Path:
    target = tmp_path / "plan.md"
    target.write_text("first", encoding="utf-8")
    win.path = target
    win._remember_disk_baseline()
    target.write_text("an assistant rewrote this", encoding="utf-8")
    return target


@pytest.mark.parametrize("answer", ["cancel", "save_as"])
def test_save_stops_when_the_file_changed_on_disk(
    lite_window: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: str
) -> None:
    asked: list[str] = []

    def ask(_parent: Any, name: str, **_kwargs: Any) -> str:
        asked.append(name)
        return answer

    monkeypatch.setattr("quill.ui.save_conflict_dialog.ask_save_conflict", ask)
    win = lite_window("mine")
    target = _changed_on_disk(win, tmp_path)
    monkeypatch.setattr(type(win), "cmd_save_as", lambda self: False)
    assert win.save() is False
    assert asked == ["plan.md"]
    assert target.read_text(encoding="utf-8") == "an assistant rewrote this"


def test_overwrite_is_a_decision_and_then_saves(
    lite_window: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "quill.ui.save_conflict_dialog.ask_save_conflict", lambda *_a, **_k: "overwrite"
    )
    win = lite_window("mine")
    target = _changed_on_disk(win, tmp_path)
    assert win.save() is True
    assert target.read_bytes() == b"mine"


def test_an_unchanged_file_saves_without_a_question(
    lite_window: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def never(*_args: Any, **_kwargs: Any) -> str:
        raise AssertionError("asked about a file nobody changed")

    monkeypatch.setattr("quill.ui.save_conflict_dialog.ask_save_conflict", never)
    win = lite_window("mine")
    target = tmp_path / "plan.md"
    target.write_text("first", encoding="utf-8")
    win.path = target
    win._remember_disk_baseline()
    assert win.save() is True
    # Its own save is the new baseline: a second save asks nothing either.
    assert win.save() is True
