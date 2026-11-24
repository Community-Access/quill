"""Converter's empty queue and Studio's empty library name their first task (FUX-09).

Both are built for real. With nothing queued, Converter opened on a silent,
empty list; with no book, Studio set focus on a static text that cannot take
it. Each now has a "Getting started" line naming the two commands that begin,
with their keys, that takes launch focus and goes when there is something.
"""

from __future__ import annotations

from pathlib import Path

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture
def converter(quill_data_dir: Path, wx_session_app, tmp_path: Path, monkeypatch):
    from quill.apps import converter as app
    from quill.core import converter_settings

    monkeypatch.setattr(
        converter_settings, "settings_path", lambda _d=None: tmp_path / "converter.json"
    )
    monkeypatch.setattr(app, "_find_ffmpeg", lambda: None)
    frame = app.QuillConverterFrame()
    try:
        yield frame
    finally:
        frame._ipc_timer.Stop()
        frame._remove_tray_icon()
        frame.frame.Destroy()


def test_an_empty_queue_has_a_line_naming_add_files_and_add_folder(converter) -> None:
    line = converter._first_task_line
    assert line.shown
    assert line.text == (
        "Nothing to convert yet. Add Files (Ctrl+O) chooses audio or video files, "
        "or Add Folder (Ctrl+Shift+O) brings a whole folder."
    )
    children = list(converter._list.GetParent().GetChildren())
    assert children.index(line.ctrl) < children.index(converter._list)  # first in Tab order


def test_launch_focus_is_the_line_then_the_queue_once_something_is_in_it(
    converter, tmp_path: Path, monkeypatch
) -> None:
    focused: list[str] = []
    monkeypatch.setattr(converter._first_task_line.ctrl, "SetFocus", lambda: focused.append("line"))
    monkeypatch.setattr(converter._list, "SetFocus", lambda: focused.append("queue"))
    converter._focus_initial_control()
    song = tmp_path / "song.wav"
    song.write_bytes(b"RIFF")
    converter.add_paths([song], announce=False)
    assert not converter._first_task_line.shown
    assert converter._list.GetCount() == 1
    converter._focus_initial_control()
    assert focused == ["line", "queue"]


@pytest.fixture
def studio(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch):
    from quill.apps.studio import StudioAppFrame
    from quill.core import recent
    from quill.ui.dialog_contract import set_transition_announcement_policy

    books: list[str] = []
    monkeypatch.setattr(recent, "recent_audiobook_files", lambda: list(books))
    frame = StudioAppFrame()
    frame.books = books
    try:
        yield frame
    finally:
        remove = getattr(frame, "_remove_tray_icon", None)
        if callable(remove):
            remove()
        set_transition_announcement_policy(None)
        frame.frame.Destroy()


def test_no_book_yet_names_narrate_and_build_and_takes_focus(studio, monkeypatch) -> None:
    line = studio._first_task_line
    assert line.text == (
        "No books yet. Narrate Documents (Ctrl+Shift+N) reads documents into a book, "
        "or Build From Recordings (Ctrl+Shift+B) makes one from your recordings."
    )
    focused: list[str] = []
    monkeypatch.setattr(line.ctrl, "SetFocus", lambda: focused.append("line"))
    studio._focus_initial_control()
    assert focused == ["line"]


def test_a_first_book_hides_the_line(studio, tmp_path: Path) -> None:
    book = tmp_path / "Garden.m4b"
    book.write_bytes(b"")
    studio.books.append(str(book))
    studio._refresh_statusbar()  # what the end of a run does
    assert not studio._first_task_line.shown


def test_narrating_a_first_book_hides_the_line_through_the_library_reload(studio) -> None:
    from quill.core.audio_studio import library as lib
    from quill.core.paths import app_data_dir

    state = lib.load_library(app_data_dir())
    state.books.append(lib.BookEntry(path="C:/Books/Garden.m4b", title="Garden"))
    lib.save_library(app_data_dir(), state)
    studio._reload_library_tree()  # what a finished narration calls
    assert not studio._first_task_line.shown


def test_when_the_line_goes_focus_goes_to_the_status_bar_not_a_bare_panel(
    studio, monkeypatch
) -> None:
    from quill.apps import studio_first_task

    went: list[str] = []
    monkeypatch.setattr(studio._status_bar, "is_shown", lambda: True)
    monkeypatch.setattr(studio._status_bar, "focus_bar", lambda **_k: went.append("bar"))
    studio_first_task._AfterTheLine(studio).SetFocus()
    assert went == ["bar"]


def test_escape_from_the_status_bar_comes_back_through_the_line(studio, monkeypatch) -> None:
    returned: list[object] = []
    monkeypatch.setattr(studio._status_bar, "is_shown", lambda: True)
    monkeypatch.setattr(studio._status_bar, "has_focus", lambda: False)
    monkeypatch.setattr(
        studio._status_bar, "focus_bar", lambda return_focus=None: returned.append(return_focus)
    )
    studio._focus_status_bar()
    assert returned == [None]  # so Escape reaches _focus_library, which prefers the line
