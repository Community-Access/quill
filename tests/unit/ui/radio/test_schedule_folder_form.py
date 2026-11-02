"""The Schedule Recording form's folder field (quill-radio #21).

The builder keeps the folder and refuses one that cannot be written; the form
loads it for Edit, copies it on Duplicate, clears it on New, and speaks a
folder refusal (focus is on the Add button, so the status line alone would go
unread).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import quill.core.radio.schedule_folder as schedule_folder
from quill.core.radio.recording_schedule import RecordingScheduleEntry
from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.ui.radio.schedule_recording_dialog import (  # noqa: E402
    ScheduleRecordingDialog,
    build_schedule_entry,
)


@pytest.fixture(scope="module", autouse=True)
def _app():
    return shared_wx_app()


def _build(folder: str) -> tuple[RecordingScheduleEntry | None, str | None]:
    return build_schedule_entry(
        name="WXYZ",
        url="https://example.com/stream",
        recurrence_index=1,
        time_text="08:00",
        date_text="",
        weekday_index=0,
        timezone_name="",
        duration_minutes=60,
        folder=folder,
    )


def test_the_builder_keeps_the_folder(tmp_path: Path) -> None:
    entry, error = _build(f"  {tmp_path}  ")
    assert error is None and entry is not None
    assert entry.folder == str(tmp_path)


def test_the_builder_defaults_to_no_folder() -> None:
    entry, error = _build("")
    assert error is None and entry is not None and entry.folder == ""


def test_the_builder_refuses_a_folder_that_cannot_be_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _denied(*_args: object, **_kwargs: object) -> object:
        raise PermissionError("denied")

    monkeypatch.setattr(schedule_folder.tempfile, "TemporaryFile", _denied)
    entry, error = _build(str(tmp_path))
    assert entry is None
    assert error is not None and "cannot be written to" in error


@pytest.fixture
def form(tmp_path: Path):
    said: list[str] = []
    entry = RecordingScheduleEntry(
        id="jazz",
        station_name="Jazz FM",
        stream_url="https://example.com/jazz",
        recurrence="daily",
        run_at="2026-01-01T20:00:00",
        folder=str(tmp_path / "Jazz"),
    )
    added: list[RecordingScheduleEntry] = []
    dialog = ScheduleRecordingDialog(
        None,
        entries=[entry],
        on_add=added.append,
        on_remove=lambda _id: True,
        on_update=lambda _entry: True,
        announce_cb=said.append,
    )
    dialog.said, dialog.added, dialog.entry = said, added, entry
    yield dialog
    dialog._win.Destroy()


def test_duplicate_copies_the_folder(form) -> None:
    form._list.SetSelection(0)
    form._on_duplicate_click(None)
    assert form._folder_ctrl.GetValue() == form.entry.folder
    form._on_add_click(None)
    assert [e.folder for e in form.added] == [form.entry.folder]
    assert form.added[0].id != form.entry.id


def test_edit_loads_the_folder_and_new_clears_it(form) -> None:
    form._list.SetSelection(0)
    form._on_edit_click(None)
    assert form._folder_ctrl.GetValue() == form.entry.folder
    form._reset_form()
    assert form._folder_ctrl.GetValue() == ""


def test_a_folder_refusal_is_spoken(form, tmp_path: Path) -> None:
    afile = tmp_path / "notes.txt"
    afile.write_text("x", encoding="utf-8")
    form._name_ctrl.SetValue("WXYZ")
    form._url_ctrl.SetValue("https://example.com/stream")
    form._recurrence_choice.SetSelection(1)
    form._folder_ctrl.SetValue(str(afile))
    form._on_add_click(None)
    assert form.added == []
    assert form.said and "is a file, not a folder" in form.said[-1]
    assert form._status.GetLabel() == form.said[-1]


def test_the_folder_field_and_browse_button_have_help() -> None:
    import inspect

    source = inspect.getsource(ScheduleRecordingDialog.__init__)
    assert 'label="Sa&ve in folder:"' in source
    assert "self._folder_ctrl.SetHelpText(" in source
    assert "self._browse_btn.SetHelpText(" in source
