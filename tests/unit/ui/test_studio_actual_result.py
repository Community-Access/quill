"""The actual result, said once (FUX-04), in QUILL Studio and QUILL Transcribe.

Every save and export here ends by naming the file *and its folder*, after the
write, and keeps the result in Activity with Open Folder so F9 and Shift+F9
reach it after the spoken sentence is gone. A long Audio Studio run ends with
what was made, where it is, the book's check said apart from the build, and --
when it was stopped -- what is kept, what is not, and how to make the rest.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import wx

from quill.core import activity
from quill.ui import activity_window
from quill.ui.audio_studio.run_result import (
    book_sentence,
    report_translated,
    run_sentence,
)


@pytest.fixture(autouse=True)
def _fresh_activity():
    activity.LOG.clear()
    yield
    activity.LOG.clear()


def _kept() -> activity.ActionResult:
    return activity.LOG.recent()[0]


def _opens_folder(result: activity.ActionResult) -> bool:
    return activity_window.can_run(result, activity.OPEN_FOLDER.id)


# -- the sentences of a run ------------------------------------------------------


def _run(**changes):
    values = dict(
        total=10,
        done=10,
        skipped=0,
        errors=0,
        cancelled=False,
        folder=Path("C:/Books/Reports"),
        resumes=False,
    )
    values.update(changes)
    return run_sentence(**values)


def test_a_finished_run_says_how_many_and_where():
    assert _run() == "Made audio for 10 documents in Reports."


def test_a_run_with_failures_says_how_many_failed_and_where_to_read_why():
    said = _run(done=8, skipped=1, errors=1)
    assert said == (
        "Made audio for 8 of 10 documents in Reports. 1 already had audio. "
        "1 failed; the run's log in Reports says why."
    )


def test_a_run_with_nothing_new_says_so_rather_than_done():
    assert _run(done=0, skipped=10) == (
        "Made no new audio: 10 documents in Reports already had it."
    )


def test_documents_that_already_had_audio_count_as_kept_after_a_stop():
    assert _run(done=2, skipped=1, cancelled=True, resumes=True).startswith(
        "Stopped after 3 of 10 documents. The audio for 3 documents is kept in Reports;"
    )


def test_a_stop_says_what_is_kept_what_is_not_and_how_to_make_the_rest():
    said = _run(done=3, cancelled=True)
    assert said == (
        "Stopped after 3 of 10 documents. The audio for 3 documents is kept in Reports; "
        "the other 7 have no audio yet. To make only the rest, run it again with "
        "If an audio file already exists set to Skip (resume)."
    )
    resumable = _run(done=3, cancelled=True, resumes=True, book=True)
    assert resumable.endswith(
        "the other 7 have no audio yet, and no audiobook was built. "
        "Run it again to make the rest; finished ones are skipped."
    )


def test_the_books_check_is_said_apart_from_the_build():
    folder = Path("C:/Books/Reports")
    assert book_sentence("audiobook Reports.m4b (verified 12 chapters)", folder) == (
        "Built the audiobook Reports.m4b in Reports. Its check found all 12 chapters."
    )
    assert book_sentence("audiobook Reports.m4b (expected 12 chapters, found 11)", folder) == (
        "Built the audiobook Reports.m4b in Reports. "
        "Its check found a problem: expected 12 chapters, found 11."
    )
    assert book_sentence("audiobook failed: disk full", folder) == (
        "The audiobook was not built: disk full."
    )
    assert book_sentence("audiobook cancelled at chapter review", folder).startswith(
        "No audiobook was built, because the chapter review was cancelled"
    )
    assert book_sentence("library: 3 audiobook(s) built", folder) == (
        "Built 3 audiobooks, one for each subfolder in Reports."
    )


def test_a_folder_of_audio_only_is_reported_by_its_book():
    said = _run(total=0, done=0, book=True, book_summary="audiobook Show.mp3 (verified 4 chapters)")
    assert said == "Built the audiobook Show.mp3 in Reports. Its check found all 4 chapters."


def test_translated_export_is_said_once_and_kept_with_open_folder(tmp_path):
    spoken = []
    document = tmp_path / "Reports" / "report.docx"
    document.parent.mkdir()
    report_translated(SimpleNamespace(_announce=spoken.append), document, 2, 9)
    assert spoken == ["Made translated audio of report.docx: 2 languages, 9 chapters, in Reports."]
    assert _kept().summary == spoken[0] and _opens_folder(_kept())


# -- saves that name the file and its folder, and stay reachable ---------------------


class _Picker:
    """A file dialog that answers OK with *path*, as a context manager too."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def __call__(self, *_args, **_kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def ShowModal(self):  # noqa: N802 - wx's name
        return wx.ID_OK

    def GetPath(self):  # noqa: N802 - wx's name
        return str(self._path)

    def Destroy(self):  # noqa: N802 - wx's name
        pass


def test_a_workbench_save_names_the_file_and_folder_after_the_write(tmp_path):
    from quill.ui.audio_studio.chapter_workbench import ChapterWorkbenchDialog

    spoken, wrote = [], []
    book = tmp_path / "Books" / "Long Walk.mp3"
    host = SimpleNamespace(
        _run_background=None,
        _announce=spoken.append,
        _sync_save_button=lambda: None,
    )
    host._say_saved = lambda said, where: ChapterWorkbenchDialog._say_saved(host, said, where)
    ChapterWorkbenchDialog._run_save(
        host, "Saving", lambda: wrote.append(1), "Saved Long Walk.mp3 in Books.", book
    )
    assert wrote == [1]
    assert spoken == ["Saved Long Walk.mp3 in Books."]
    assert _kept().object_name == "Long Walk.mp3" and _opens_folder(_kept())


def test_saving_tags_alone_names_the_file_and_folder(monkeypatch, tmp_path):
    from quill.core.speech import audio_tags
    from quill.ui.audio_studio import tag_editor

    target = tmp_path / "Music" / "Song.mp3"
    monkeypatch.setattr(audio_tags, "read_tags", lambda _p: audio_tags.AudioTags())
    monkeypatch.setattr(audio_tags, "write_tags", lambda _p, _t: None)
    monkeypatch.setattr(
        tag_editor,
        "TagEditorDialog",
        lambda *_a, **_k: SimpleNamespace(result=audio_tags.AudioTags, Destroy=lambda: None),
    )
    spoken = []
    frame = SimpleNamespace(
        frame=None, _announce=spoken.append, _show_modal_dialog=lambda *_a: wx.ID_OK
    )
    tag_editor.open_tags_in_editor(frame, target)
    assert spoken == ["Saved the tags of Song.mp3 in Music."]
    assert _opens_folder(_kept())


def test_saved_sections_name_the_file_and_folder(monkeypatch, tmp_path):
    from quill.ui.audio_studio import sections_dialog

    destination = tmp_path / "Clips" / "Talk sections.mp3"
    monkeypatch.setattr(sections_dialog, "save_sections", lambda *_a, **_k: destination)
    spoken = []
    dialog = object.__new__(sections_dialog.CopySectionsDialog)
    dialog._wx = SimpleNamespace(
        FileDialog=_Picker(destination), FD_OPEN=1, FD_SAVE=2, FD_OVERWRITE_PROMPT=4, ID_OK=wx.ID_OK
    )
    dialog._collection = SimpleNamespace(sections=[object(), object()])
    dialog._source = tmp_path / "Talk.mp3"
    dialog._dialog = None
    dialog._work_dir = tmp_path
    dialog._announce = spoken.append
    dialog.save(append=False)
    assert spoken[-1] == (
        "2 sections saved as Talk sections.mp3 in Clips. The original file is unchanged."
    )
    assert _opens_folder(_kept())


def test_a_diagnostics_bundle_names_the_file_and_folder_not_the_whole_path(monkeypatch, tmp_path):
    from quill.apps.studio import StudioAppFrame

    target = tmp_path / "Support" / "diag.zip"
    monkeypatch.setattr(wx, "FileDialog", _Picker(target))
    spoken = []
    host = SimpleNamespace(
        frame=None,
        _announce=spoken.append,
        _run_background_task=lambda _label, _work, done: done(None),
    )
    StudioAppFrame.save_diagnostics_bundle(host)
    assert spoken == ["Diagnostics bundle saved to diag.zip in Support."]
    assert _opens_folder(_kept())


def test_a_screenshot_report_is_said_as_the_file_and_folder(monkeypatch, tmp_path):
    from quill.ui import studio_capture_chat

    report = tmp_path / "Captures" / "shot.verification.json"
    monkeypatch.setattr(studio_capture_chat, "save_capture_report", lambda *_a, **_k: report)
    said = []
    host = SimpleNamespace(evidence=object(), observations="", _say=said.append)
    studio_capture_chat.ScreenshotChatDialog._save(host, False)
    assert said == ["Saved shot.verification.json in Captures."]


def test_transcribe_save_as_names_the_file_and_folder_and_keeps_it(monkeypatch, tmp_path):
    from quill.apps.transcribe_files import TranscribeFilesMixin

    target = tmp_path / "Notes" / "meeting.txt"
    target.parent.mkdir()
    monkeypatch.setattr(wx, "FileDialog", _Picker(target))
    spoken = []

    class Host(TranscribeFilesMixin):
        frame = None

        def _show_modal_dialog(self, _dialog, _label):
            return wx.ID_OK

        def _announce(self, text, force=False):
            spoken.append(text)

    Host()._save_transcript_as("Hello.")
    assert target.read_text(encoding="utf-8") == "Hello."
    assert spoken == ["Saved meeting.txt in Notes."]
    assert _kept().summary == "Saved meeting.txt in Notes." and _opens_folder(_kept())


def test_studio_help_offers_activity_and_repeat_last_result_on_their_keys(wx_session_app):
    from quill.apps.studio_results import append_result_items

    menu = wx.Menu()
    host = SimpleNamespace(
        _menu_label=lambda title, command: (
            f"{title}\t{ {'app.activity': 'Shift+F9'}.get(command, 'F9') }"
        ),
        open_activity=lambda: None,
        repeat_last_result=lambda: None,
    )
    pairs = append_result_items(host, menu)
    labels = [item.GetItemLabel() for item in menu.GetMenuItems()]
    assert labels == ["Activit&y...\tShift+F9", "Repeat Last Resul&t\tF9"]
    assert [handler for _id, handler in pairs] == [host.open_activity, host.repeat_last_result]
