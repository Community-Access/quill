"""QUILL's document results: said once, with where, and kept in Activity (FUX-04)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from quill.core import activity
from quill.core.batch_convert import BatchEntry, BatchPlan, BatchReport
from quill.ui import activity_window
from quill.ui.main_frame_results import DocumentResultsMixin

_UI = Path(__file__).resolve().parents[3] / "quill" / "ui"


@dataclass
class _Doc:
    name: str
    path: Path | None
    modified: bool
    refuse: bool = False


@dataclass
class _Tab:
    document: _Doc


class _Host(DocumentResultsMixin):
    def __init__(self, docs: list[_Doc], active: int) -> None:
        self._document_tabs = [_Tab(doc) for doc in docs]  # type: ignore[assignment]
        self._active_tab_index = active
        self.document = docs[active]
        self.said: list[str] = []
        self.saved: list[str] = []

    def _select_tab(self, index: int) -> None:
        self._active_tab_index = index
        self.document = self._document_tabs[index].document

    def save_file(self) -> None:
        if not self.document.refuse:
            self.document.modified = False
            self.saved.append(self.document.name)

    def _announce(self, message: str, **_kwargs: object) -> None:
        self.said.append(message)


@pytest.fixture(autouse=True)
def _fresh_log() -> None:
    activity.LOG.clear()


def test_save_all_returns_to_your_document_and_names_what_it_saved(tmp_path: Path) -> None:
    docs = [
        _Doc("a.md", tmp_path / "a.md", True),
        _Doc("b.md", tmp_path / "b.md", False),
        _Doc("c.md", tmp_path / "c.md", True),
    ]
    host = _Host(docs, active=1)
    host.save_all_files()
    assert host._active_tab_index == 1
    assert host.said == ["Saved 2 documents: a.md and c.md."]


def test_save_all_with_nothing_changed_says_so() -> None:
    host = _Host([_Doc("a.md", Path("a.md"), False)], active=0)
    host.save_all_files()
    assert host.said == ["Nothing needed saving."]


def test_save_all_that_stops_says_what_is_left_unsaved(tmp_path: Path) -> None:
    docs = [
        _Doc("a.md", tmp_path / "a.md", True),
        _Doc("Untitled", None, True, refuse=True),
        _Doc("c.md", tmp_path / "c.md", True),
    ]
    host = _Host(docs, active=0)
    host.save_all_files()
    assert host.saved == ["a.md"]  # nothing after the stop is saved behind your back
    assert host.said == [
        f"Saved a.md in {tmp_path.name}. Stopped at Untitled, which is not saved. "
        "1 more is not saved."
    ]


def test_a_written_file_is_said_with_its_folder_and_kept_with_open_folder(tmp_path: Path) -> None:
    host = _Host([_Doc("a.md", None, False)], active=0)
    target = tmp_path / "report.docx"
    host._report_written("Export", "Exported", target)
    assert host.said == [f"Exported to report.docx in {tmp_path.name}."]
    kept = activity.LOG.latest_important()
    assert kept is not None and kept.has(activity.OPEN_FOLDER.id)
    assert activity_window.can_run(kept, activity.OPEN_FOLDER.id)


def test_a_finished_batch_is_said_once_and_its_file_list_kept(tmp_path: Path) -> None:
    plan = BatchPlan(tmp_path, False, "markdown", "docx", "subfolder", "never")
    out = tmp_path / "Output"
    report = BatchReport(
        plan=plan,
        total=2,
        converted=1,
        skipped=0,
        failed=1,
        entries=(
            BatchEntry(tmp_path / "a.md", out / "a.docx", True, 0, None, 0.1),
            BatchEntry(tmp_path / "b.md", None, False, 0, "pandoc exited 1", 0.1),
        ),
        duration_seconds=0.2,
    )
    host = _Host([_Doc("a.md", None, False)], active=0)
    host._report_batch_conversion(report)
    assert host.said == [
        f"Converted 1 of 2 files. It is in Output in {tmp_path.name}. 1 failed: b.md."
    ]
    kept = activity.LOG.latest_important()
    assert kept is not None and kept.outcome == activity.PARTIAL
    assert activity_window.can_run(kept, activity.OPEN_FOLDER.id)
    assert "b.md: pandoc exited 1" in kept.details


def test_batch_conversion_no_longer_opens_a_window_when_it_finishes() -> None:
    # The Application Status window opened over the document every time a
    # batch finished; a delayed result must not take focus (FUX-04).
    source = (_UI / "main_frame.py").read_text(encoding="utf-8")
    start = source.index("def run_batch_conversion_wizard(")
    body = source[start : source.index("\n    def ", start + 1)]
    assert "show_help_status_page" not in body
    assert "_report_batch_conversion(result)" in body


def test_exports_and_conversions_report_through_the_kept_result() -> None:
    main = (_UI / "main_frame.py").read_text(encoding="utf-8")
    assert '_report_written("Export", "Exported", target)' in main
    assert '"Exported the DAISY talking book", book_dir' in main
    convert = (_UI / "main_frame_convert_file.py").read_text(encoding="utf-8")
    assert '"Converted",\n            target,' in convert
