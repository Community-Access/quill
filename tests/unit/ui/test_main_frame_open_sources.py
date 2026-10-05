"""QUILL's half of the 2026-10-04 PlanCake design note, on a light host.

The same five things QUILL Lite has (``tests/unit/apps/test_lite_open_sources.py``),
through the methods ``MainFrame`` binds: Open from Clipboard, Open from URL's
download handling and temp file, a drop, Reopen with Encoding, and the save
check that never overwrites a change made on disk since the tab last saw it.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import wx

from quill.core.document import Document
from quill.core.open_sources import FILES, NONE, NOTHING_TO_OPEN, URL, ClipboardOpen
from quill.ui.main_frame_open_sources import OpenSourcesMixin


class _Editor:
    def __init__(self, text: str = "") -> None:
        self.value = text
        self.caret = 0

    def GetInsertionPoint(self) -> int:  # noqa: N802 - wx API
        return self.caret

    def SetInsertionPoint(self, position: int) -> None:  # noqa: N802 - wx API
        self.caret = position

    def SetValue(self, text: str) -> None:  # noqa: N802 - wx API
        self.value = text


class _Host(OpenSourcesMixin):
    def __init__(self, document: Document) -> None:
        self._wx = wx
        self.frame = None
        self.document = document
        self.editor = _Editor(document.text)
        self.settings = SimpleNamespace()
        self._task_manager = None
        self._external_change_watcher = None
        self.tab = SimpleNamespace(document=document, disk_baseline=None, remote_temp_path="")
        self._document_tabs = [self.tab]
        self.announced: list[str] = []
        self.status: list[str] = []
        self.opened: list[Path] = []
        self.saved_as = 0
        self.discard_ok = True

    def _active_tab(self) -> Any:
        return self.tab

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def open_file(self, path: Path, **_kwargs: Any) -> None:
        self.opened.append(Path(path))

    def save_file_as(self) -> None:
        self.saved_as += 1

    def _confirm_discard_changes(self) -> bool:
        return self.discard_ok

    def _refresh_title(self) -> None:
        return None

    def _refresh_statusbar(self) -> None:
        return None


def test_open_from_clipboard_opens_each_file_and_says_how_many(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = (tmp_path / "a.md", tmp_path / "b.md")
    monkeypatch.setattr(
        "quill.ui.open_sources_ui.read_clipboard", lambda: ClipboardOpen(FILES, paths=paths)
    )
    host = _Host(Document())
    host.open_from_clipboard()
    assert host.opened == list(paths)
    assert host.announced == ["Opened 2 files from the clipboard."]


def test_a_link_on_the_clipboard_goes_through_open_from_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "quill.ui.open_sources_ui.read_clipboard",
        lambda: ClipboardOpen(URL, url="https://example.com/a.md"),
    )
    host = _Host(Document())
    links: list[str] = []
    monkeypatch.setattr(host, "_open_link", lambda url: links.append(url) or True)
    host.open_from_clipboard()
    assert links == ["https://example.com/a.md"]


def test_nothing_openable_is_said_plainly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("quill.ui.open_sources_ui.read_clipboard", lambda: ClipboardOpen(NONE))
    host = _Host(Document())
    host.open_from_clipboard()
    assert host.announced == [NOTHING_TO_OPEN]


def test_dropped_files_open_with_one_sentence(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text("x", encoding="utf-8")
    host = _Host(Document())
    host._open_dropped_files([str(note)])
    assert host.opened == [note]
    assert host.announced == ["Opened 1 dropped file."]


def test_closing_a_url_tab_removes_its_temp_file(tmp_path: Path) -> None:
    temp = tmp_path / "quill-url-x.md"
    temp.write_text("x", encoding="utf-8")
    host = _Host(Document())
    host.tab.remote_temp_path = str(temp)
    host._discard_remote_download(host.tab)
    assert not temp.exists()
    assert host.tab.remote_temp_path == ""


def test_an_unreadable_download_is_one_sentence_and_no_temp_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    temp = tmp_path / "quill-url-y.txt"
    temp.write_text("x", encoding="utf-8")

    def broken(*_args: Any, **_kwargs: Any) -> Any:
        raise ValueError("not a document")

    monkeypatch.setattr("quill.io.open_read.read_open_document", broken)
    host = _Host(Document())
    host._open_downloaded(SimpleNamespace(local_path=str(temp), filename="y.txt"))
    assert host.announced == ["y.txt downloaded, but QUILL could not read it as a document."]
    assert not temp.exists()


def test_reopen_with_encoding_reads_the_bytes_again(tmp_path: Path) -> None:
    target = tmp_path / "old.txt"
    target.write_bytes(bytes([0xC0, 0xE9, 0xF0]) + b"\r\n")
    host = _Host(Document(text="wrong", path=target, source_metadata={"source_kind": "text"}))
    assert host._can_reopen_with_encoding() is True
    host.reopen_with_encoding("cp1251")
    assert host.editor.value == "Айр\n"
    assert host.document.encoding == "cp1251"
    assert host.document.line_ending == "\r\n"
    assert host.document.modified is False
    assert host.announced[-1].startswith("Reopened as Windows-1251")
    assert host.tab.disk_baseline is not None


def test_reopen_that_does_not_fit_changes_nothing(tmp_path: Path) -> None:
    target = tmp_path / "old.txt"
    target.write_bytes(bytes([0x81, 0xFF]))
    host = _Host(Document(text="as it was", path=target))
    host.reopen_with_encoding("utf-8")
    assert host.editor.value == "as it was"
    assert host.announced[-1].startswith("This file is not valid UTF-8")


def _changed(host: _Host, target: Path) -> None:
    target.write_text("first", encoding="utf-8")
    host._remember_disk_baseline(host.tab)
    target.write_text("rewritten elsewhere", encoding="utf-8")


@pytest.mark.parametrize(
    ("answer", "allowed", "saved_as"),
    [("overwrite", True, 0), ("save_as", False, 1), ("cancel", False, 0)],
)
def test_save_asks_before_overwriting_an_unseen_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: str, allowed: bool, saved_as: int
) -> None:
    target = tmp_path / "plan.md"
    host = _Host(Document(text="mine", path=target))
    _changed(host, target)
    monkeypatch.setattr("quill.ui.save_conflict_dialog.ask_save_conflict", lambda *_a, **_k: answer)
    assert host._confirm_unseen_disk_change() is allowed
    assert host.saved_as == saved_as


def test_reload_answer_reopens_from_disk(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "plan.md"
    host = _Host(Document(text="mine", path=target, modified=True))
    _changed(host, target)
    monkeypatch.setattr(
        "quill.ui.save_conflict_dialog.ask_save_conflict", lambda *_a, **_k: "reload"
    )
    assert host._confirm_unseen_disk_change() is False
    assert host.opened == [target]


def test_an_unchanged_file_is_never_asked_about(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "plan.md"
    target.write_text("first", encoding="utf-8")
    host = _Host(Document(text="mine", path=target))
    host._remember_disk_baseline(host.tab)

    def never(*_a: Any, **_k: Any) -> str:
        raise AssertionError("asked about a file nobody changed")

    monkeypatch.setattr("quill.ui.save_conflict_dialog.ask_save_conflict", never)
    assert host._confirm_unseen_disk_change() is True


# -- the shared Open from URL flow ------------------------------------------- #


class _Tasks:
    def __init__(self) -> None:
        self.submitted: list[tuple[str, Any, dict[str, Any]]] = []

    def submit(self, name: str, func: Any, **kwargs: Any) -> None:
        self.submitted.append((name, func, kwargs))


def _flow(**kwargs: Any) -> tuple[Any, list[str], _Tasks]:
    from quill.ui.open_from_url import UrlOpenFlow

    said: list[str] = []
    tasks = _Tasks()
    flow = UrlOpenFlow(
        None,
        task_manager=tasks,
        announce=said.append,
        on_downloaded=lambda _download: None,
        **kwargs,
    )
    return flow, said, tasks


def test_the_flow_refuses_what_is_not_a_link() -> None:
    from quill.ui.open_from_url import NOT_A_LINK

    flow, said, tasks = _flow()
    assert flow.start("C:/not/a/link.md") is False
    assert said == [NOT_A_LINK]
    assert tasks.submitted == []


def test_the_flow_downloads_on_the_task_manager_asking_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flow, _said, tasks = _flow()
    assert flow.start("https://github.com/o/r/blob/main/p.md") is True
    name, work, kwargs = tasks.submitted[0]
    assert name == "open-from-url"
    assert "on_failure" in kwargs and "on_success" in kwargs
    seen: dict[str, Any] = {}

    def fake_download(url: str, **options: Any) -> str:
        seen["url"] = url
        seen.update(options)
        return "done"

    monkeypatch.setattr("quill.io.http_transport.download_url", fake_download)
    assert work(cancellation_token=None) == "done"
    assert seen["url"] == "https://raw.githubusercontent.com/o/r/main/p.md"
    assert callable(seen["confirm"]) and callable(seen["should_cancel"])
    assert callable(seen["progress"])


def test_no_to_the_question_cancels_and_says_so() -> None:
    flow, said, _tasks = _flow(ask_yes_no=lambda _q, _t: False)
    assert flow._confirm_on_ui("example.com", "p.md", 10) is False
    assert said == ["Download cancelled."]


def test_a_failed_download_is_one_plain_sentence() -> None:
    from quill.io.http_transport import DownloadCancelledError
    from quill.io.remote_transport import RemoteNotFoundError

    flow, said, _tasks = _flow()
    flow._host = "example.com"
    flow._failed(RemoteNotFoundError("HTTP 404: Not Found"))
    flow._failed(DownloadCancelledError("Download cancelled"))
    flow._failed(DownloadCancelledError("Download declined"))
    assert said == ["Nothing was found at that address on example.com.", "Download cancelled."]


def test_a_download_finishing_after_the_window_closed_touches_nothing() -> None:
    """The flow's task manager is tied to its window (surface lifetime gate)."""
    from quill.ui.open_from_url import UrlOpenFlow

    class _Closing:
        def IsBeingDeleted(self) -> bool:  # noqa: N802 - wx's spelling
            return True

    landed: list[Any] = []
    tasks = _Tasks()
    flow = UrlOpenFlow(
        _Closing(),
        task_manager=tasks,
        announce=landed.append,
        on_downloaded=landed.append,
    )
    assert flow.start("https://example.com/p.md") is True
    _name, _work, kwargs = tasks.submitted[0]
    kwargs["on_success"](None, object())
    kwargs["on_failure"](None, RuntimeError("late"))
    assert landed == []
