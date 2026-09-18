"""The frame half of F5: the real reader, a real second tab, a kept answer.

Three separate ways the old watcher path lost a document (bad.md F5, P0.7):

* it reloaded every suffix with ``path.read_text()``, so a ``.docx`` came back
  as its own bytes decoded into replacement characters and marked clean;
* "Open Disk Version in New Tab" called ``open_file`` on the path already open,
  and ``open_file`` answers an open path by *selecting that tab* -- so the
  button that promised a comparison selected the tab you were looking at and
  announced that it had opened it;
* and a person who does not want to be asked about a format had no way to say
  so, nor -- once the checkbox existed -- any way back from it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.document import Document
from quill.core.external_change import REMEMBER_KEEP, REMEMBER_RELOAD
from quill.core.settings import Settings
from quill.ui.main_frame import MainFrame


class _Host:
    """Only the surface the external-change helpers actually touch."""

    _remembered_external_change_answer = MainFrame._remembered_external_change_answer
    _remember_external_change_answer = MainFrame._remember_external_change_answer
    forget_external_change_answers = MainFrame.forget_external_change_answers
    _read_disk_version_text = MainFrame._read_disk_version_text
    _open_disk_version_in_new_tab = MainFrame._open_disk_version_in_new_tab

    def __init__(self, path: Path | None) -> None:
        self.settings = Settings()
        self.document = Document(text="mine", path=path)
        self.status: list[str] = []
        self.tabs: list[Document] = []

    def _set_status(self, message: str) -> None:
        self.status.append(message)

    def _create_document_tab(self, document: Document, select: bool = True) -> int:
        self.tabs.append(document)
        return len(self.tabs) - 1


@pytest.fixture(autouse=True)
def _no_settings_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """The helpers persist; this suite is about what they decide, not the disk."""
    import quill.core.settings as settings_module

    monkeypatch.setattr(settings_module, "save_settings", lambda _settings: None)


def test_ticking_the_box_records_the_answer_for_that_format(tmp_path: Path) -> None:
    host = _Host(tmp_path / "report.docx")
    host._remember_external_change_answer(REMEMBER_RELOAD)

    assert host.settings.external_change_always_reload == [".docx"]
    assert host._remembered_external_change_answer() == REMEMBER_RELOAD


def test_changing_your_mind_is_one_tick_not_a_contradiction(tmp_path: Path) -> None:
    host = _Host(tmp_path / "report.docx")
    host._remember_external_change_answer(REMEMBER_RELOAD)
    host._remember_external_change_answer(REMEMBER_KEEP)

    assert host.settings.external_change_always_reload == []
    assert host.settings.external_change_always_keep == [".docx"]
    assert host._remembered_external_change_answer() == REMEMBER_KEEP


def test_an_empty_answer_records_nothing(tmp_path: Path) -> None:
    host = _Host(tmp_path / "report.docx")
    host._remember_external_change_answer("")

    assert host.settings.external_change_always_reload == []
    assert host.settings.external_change_always_keep == []


def test_forgetting_says_how_many_it_forgot(tmp_path: Path) -> None:
    host = _Host(tmp_path / "report.docx")
    host.settings.external_change_always_reload = [".md"]
    host.settings.external_change_always_keep = [".docx", ".rtf"]

    host.forget_external_change_answers()

    assert host.settings.external_change_always_reload == []
    assert host.settings.external_change_always_keep == []
    assert "3 remembered file-format answers" in host.status[-1]


def test_forgetting_nothing_says_there_was_nothing(tmp_path: Path) -> None:
    host = _Host(tmp_path / "report.docx")
    host.forget_external_change_answers()
    assert host.status == ["No file formats are being answered for you."]


def test_a_text_file_reloads_through_the_reader(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("what is on disk now", encoding="utf-8")
    host = _Host(path)

    assert host._read_disk_version_text() == "what is on disk now"


def test_a_file_that_cannot_be_read_reports_instead_of_guessing(tmp_path: Path) -> None:
    host = _Host(tmp_path / "gone.docx")

    assert host._read_disk_version_text() is None
    assert host.status and "Could not reload" in host.status[0]


def test_the_disk_version_opens_as_a_second_read_only_tab(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("disk text", encoding="utf-8")
    host = _Host(path)

    host._open_disk_version_in_new_tab()

    assert len(host.tabs) == 1
    disk_tab = host.tabs[0]
    # A pathless document: two tabs on one path would leave the watcher, the
    # save path and the recent list arguing about which one is the file.
    assert disk_tab.path is None
    assert disk_tab.text == "disk text"
    assert disk_tab.name == "note.txt (on disk)"
    assert disk_tab.source_metadata["read_only_guard"] is True
    assert host.document.text == "mine"


def test_a_missing_file_opens_no_tab_at_all(tmp_path: Path) -> None:
    host = _Host(tmp_path / "gone.txt")
    host._open_disk_version_in_new_tab()

    assert host.tabs == []
    assert host.status == ["The file is no longer on disk."]


def test_a_document_with_no_path_is_never_answered_for(tmp_path: Path) -> None:
    host = _Host(None)
    assert host._remembered_external_change_answer() == ""
    assert host._read_disk_version_text() is None


def test_the_dialog_answer_maps_to_what_gets_stored() -> None:
    wx = pytest.importorskip("wx")
    assert wx is not None
    from quill.ui.external_change_dialog import KEEP, NEW_TAB, RELOAD, ExternalChangeAnswer

    assert ExternalChangeAnswer(RELOAD, True).remembered_value == REMEMBER_RELOAD
    assert ExternalChangeAnswer(KEEP, True).remembered_value == REMEMBER_KEEP
    assert ExternalChangeAnswer(RELOAD, False).remembered_value == ""
    # A one-off comparison is never a policy, however the box was left.
    assert ExternalChangeAnswer(NEW_TAB, True).remembered_value == ""
