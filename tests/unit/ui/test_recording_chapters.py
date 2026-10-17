"""Automatic chapters for any local recording (item 42, 2026-10-16).

The policy (:mod:`quill.core.speech.chapter_proposals`), the Workbench flow
around the silence scan (keep or replace, stop, failure, guesses labelled),
and the three doors into it: QUILL's Tools > Speech row, Quill Studio's
Studio menu row, and ``open_book_in_workbench`` itself -- which Studio was
calling with two arguments it did not accept.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.speech.chapter_proposals import (
    has_authored_chapters,
    merge_proposals,
    retitle_as_proposed,
    scan_timeout_seconds,
)
from quill.core.speech.chapters import Chapter

wx = pytest.importorskip("wx")


def _chapters(*starts: int, total: int, prefix: str = "C") -> list[Chapter]:
    ends = [*starts[1:], total]
    return [
        Chapter(index=i, title=f"{prefix}{i + 1}", start_ms=s, end_ms=e)
        for i, (s, e) in enumerate(zip(starts, ends, strict=True))
    ]


# --------------------------------------------------------------------------- #
# Policy
# --------------------------------------------------------------------------- #


def test_one_whole_file_chapter_is_nobodys_work() -> None:
    assert not has_authored_chapters(_chapters(0, total=1000))
    assert has_authored_chapters(_chapters(0, 500, total=1000))


def test_merge_keeps_every_authored_chapter_and_adds_only_new_boundaries() -> None:
    mine = [
        Chapter(0, "Welcome", 0, 600_000),
        Chapter(1, "Questions", 600_000, 3_600_000),
    ]
    proposed = _chapters(0, 300_000, 605_000, 2_000_000, total=3_600_000, prefix="Chapter ")
    merged = merge_proposals(mine, proposed, 3_600_000)
    assert [(c.title, c.start_ms) for c in merged] == [
        ("Welcome", 0),
        ("Proposed chapter 1", 300_000),
        ("Questions", 600_000),  # 605 s is within ten seconds of it: the same place
        ("Proposed chapter 2", 2_000_000),
    ]
    assert [c.end_ms for c in merged] == [300_000, 600_000, 2_000_000, 3_600_000]
    assert [c.index for c in merged] == [0, 1, 2, 3]


def test_a_proposal_is_titled_as_one() -> None:
    proposed = retitle_as_proposed(_chapters(0, 10_000, total=20_000, prefix="Chapter "))
    assert [c.title for c in proposed] == ["Proposed chapter 1", "Proposed chapter 2"]


def test_a_long_recording_gets_time_to_be_scanned() -> None:
    assert scan_timeout_seconds(60_000) == 600.0
    assert scan_timeout_seconds(10 * 3600 * 1000) == 3600.0  # ten hours


def test_the_scan_uses_the_scaled_timeout(monkeypatch, tmp_path: Path) -> None:
    from quill.core.speech import ffmpeg, silence

    seen: dict[str, Any] = {}

    class _Done:
        stderr = "silence_start: 100\nsilence_end: 102\n"

    def fake_run(args, *, timeout_seconds):
        seen["timeout"] = timeout_seconds
        return _Done()

    monkeypatch.setattr(silence, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(ffmpeg, "probe_duration_ms", lambda _p: 8 * 3600 * 1000)
    monkeypatch.setattr("quill.stability.safe_subprocess.run_subprocess_safely", fake_run)
    chapters = silence.detect_silence_chapters(tmp_path / "lecture.mp3")
    assert seen["timeout"] == 2880.0
    assert [c.start_ms for c in chapters] == [0, 101_000]


# --------------------------------------------------------------------------- #
# The Workbench flow, on the real dialog
# --------------------------------------------------------------------------- #


@pytest.fixture
def workbench(tmp_path: Path, monkeypatch):
    from quill.core.speech.book_file import BookFile
    from quill.core.speech.ffmpeg import AudioMetadata
    from quill.ui.audio_studio import chapter_workbench_silence as cws
    from quill.ui.audio_studio.chapter_workbench import ChapterWorkbenchDialog

    class _Params:
        def __init__(self, _parent: Any) -> None: ...
        def __enter__(self) -> _Params:
            return self

        def __exit__(self, *_exc: object) -> bool:
            return False

        def ShowModal(self) -> int:  # noqa: N802
            return wx.ID_OK

        def values(self) -> tuple[float, float]:
            return (-30.0, 0.8)

    monkeypatch.setattr(cws, "SilenceParamsDialog", _Params)
    app = wx.App(False)
    frame = wx.Frame(None)
    made: list[Any] = []

    def make(chapters: list[Chapter], *, background: list | None = None) -> Any:
        path = tmp_path / "lecture.mp3"
        path.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 413)
        book = BookFile(path=path, tags=AudioMetadata(), chapters=chapters, total_ms=3_600_000)
        announced: list[str] = []
        runner = None
        if background is not None:

            def runner(label: str, work: Any, on_success: Any) -> None:
                background.append((work, on_success))

        dlg = ChapterWorkbenchDialog(frame, book, announce=announced.append, run_background=runner)
        dlg.announced = announced
        made.append(dlg)
        return dlg

    yield make
    for dlg in made:
        dlg.Destroy()
    frame.Destroy()
    del app


def _scan_answers(monkeypatch, chapters: list[Chapter] | Exception) -> None:
    def fake(*_a: object, **_k: object) -> list[Chapter]:
        if isinstance(chapters, Exception):
            raise chapters
        return chapters

    monkeypatch.setattr("quill.core.speech.silence.detect_silence_chapters", fake)


def test_an_ordinary_mp3_is_never_asked_and_gets_proposed_titles(workbench, monkeypatch) -> None:
    _scan_answers(monkeypatch, _chapters(0, 900_000, 1_800_000, total=3_600_000))
    dlg = workbench(_chapters(0, total=3_600_000))
    dlg._ask_keep_or_replace = lambda _n: pytest.fail("nothing of the user's to ask about")
    dlg._on_propose_from_silences()
    assert [c.title for c in dlg._book.chapters] == [
        "Proposed chapter 1",
        "Proposed chapter 2",
        "Proposed chapter 3",
    ]
    assert dlg._chapters_dirty


def test_authored_chapters_are_kept_by_default_answer(workbench, monkeypatch) -> None:
    _scan_answers(monkeypatch, _chapters(0, 900_000, total=3_600_000))
    dlg = workbench([Chapter(0, "Intro", 0, 60_000), Chapter(1, "Talk", 60_000, 3_600_000)])
    dlg._ask_keep_or_replace = lambda n: "keep" if n == 2 else None
    dlg._on_propose_from_silences()
    assert [c.title for c in dlg._book.chapters] == ["Intro", "Talk", "Proposed chapter 1"]
    assert "Kept your 2 chapters and added 1" in dlg.announced[-1]


def test_cancel_at_the_question_changes_nothing(workbench, monkeypatch) -> None:
    _scan_answers(monkeypatch, _chapters(0, 900_000, total=3_600_000))
    dlg = workbench([Chapter(0, "Intro", 0, 60_000), Chapter(1, "Talk", 60_000, 3_600_000)])
    dlg._ask_keep_or_replace = lambda _n: None
    dlg._on_propose_from_silences()
    assert [c.title for c in dlg._book.chapters] == ["Intro", "Talk"]
    assert not dlg._chapters_dirty


def test_pressing_again_stops_the_scan_and_its_answer_is_dropped(workbench, monkeypatch) -> None:
    from quill.ui.audio_studio.chapter_workbench_silence import PROPOSE_LABEL, STOP_LABEL

    _scan_answers(monkeypatch, _chapters(0, 900_000, total=3_600_000))
    pending: list[Any] = []
    dlg = workbench(_chapters(0, total=3_600_000), background=pending)
    dlg._on_propose_from_silences()
    assert dlg._propose_btn.GetLabel() == STOP_LABEL
    dlg._on_propose_from_silences()  # stop
    assert dlg._propose_btn.GetLabel() == PROPOSE_LABEL
    assert dlg.announced[-1] == "Chapter proposal stopped. The chapter list is unchanged."
    work, on_success = pending[0]
    on_success(work())  # ffmpeg finished after all; its answer is thrown away
    assert len(dlg._book.chapters) == 1 and not dlg._chapters_dirty


def test_a_failed_scan_is_shown_and_the_button_comes_back(workbench, monkeypatch) -> None:
    from quill.core.speech.ffmpeg import TranscodeError
    from quill.ui.audio_studio.chapter_workbench_silence import PROPOSE_LABEL

    _scan_answers(monkeypatch, TranscodeError("ffmpeg is not installed."))
    pending: list[Any] = []
    dlg = workbench(_chapters(0, total=3_600_000), background=pending)
    errors: list[str] = []
    dlg._error = errors.append
    dlg._on_propose_from_silences()
    work, on_success = pending[0]
    on_success(work())
    assert len(errors) == 1 and errors[0].endswith("ffmpeg is not installed.")
    assert dlg._propose_btn.GetLabel() == PROPOSE_LABEL


# --------------------------------------------------------------------------- #
# The doors
# --------------------------------------------------------------------------- #


def test_open_book_in_workbench_takes_studios_keys_and_can_start_proposing(
    monkeypatch, tmp_path: Path
) -> None:
    from quill.ui.audio_studio import chapter_workbench as cwb

    events: list[Any] = []

    class _Dialog:
        def __init__(self, _parent: Any, book: Any, **_kwargs: Any) -> None:
            events.append(("made", book))

        def _on_propose_from_silences(self) -> None:
            events.append("propose")

        def _cancel_silence_scan(self, *, spoken: bool) -> None:
            events.append(("cancel", spoken))

        def Destroy(self) -> None:  # noqa: N802
            events.append("destroyed")

    class _Frame:
        frame = None

        def _show_modal_dialog(self, _dlg: Any, title: str) -> int:
            events.append(("shown", title))
            return 0

    monkeypatch.setattr(cwb, "ChapterWorkbenchDialog", _Dialog)
    monkeypatch.setattr("quill.core.speech.book_file.read_book", lambda path: f"book:{path.name}")
    monkeypatch.setattr(cwb, "bind_host_shortcuts", lambda dlg, keys: events.append(sorted(keys)))
    monkeypatch.setattr(cwb.wx, "CallAfter", lambda fn: fn())
    cwb.open_book_in_workbench(
        _Frame(),
        tmp_path / "lecture.mp3",
        on_sleep_timer=lambda: None,
        on_play_queue=lambda: None,
        propose_silences=True,
    )
    assert events == [
        ("made", "book:lecture.mp3"),
        ["Ctrl+Shift+Q", "Ctrl+Shift+T"],
        "propose",
        ("shown", "Chapter Workbench"),
        ("cancel", False),
        "destroyed",
    ]


def test_host_shortcuts_become_an_accelerator_table() -> None:
    from quill.ui.audio_studio.chapter_workbench_silence import bind_host_shortcuts

    app = wx.App(False)
    dialog = wx.Dialog(None)
    try:
        calls: list[str] = []
        tables: list[Any] = []
        dialog.SetAcceleratorTable = tables.append  # type: ignore[method-assign]
        bind_host_shortcuts(dialog, {"Ctrl+Shift+T": lambda: calls.append("t"), "Ctrl+Q": None})
        assert len(tables) == 1 and tables[0].IsOk()
    finally:
        dialog.Destroy()
        del app


def test_quills_door_opens_the_workbench_proposing(monkeypatch, tmp_path: Path) -> None:
    from quill.ui.main_frame_recording_chapters import RecordingChaptersMixin

    picked = tmp_path / "meeting.mp3"
    opened: list[Any] = []
    monkeypatch.setattr(
        "quill.ui.audio_studio.chapter_workbench_silence.pick_recording", lambda _p: picked
    )
    monkeypatch.setattr(
        "quill.ui.audio_studio.chapter_workbench.open_book_in_workbench",
        lambda host, path, **kw: opened.append((path, kw)),
    )

    class _Quill(RecordingChaptersMixin):
        frame = None

    _Quill().find_chapters_in_recording()
    assert opened == [(picked, {"propose_silences": True})]
    monkeypatch.setattr(
        "quill.ui.audio_studio.chapter_workbench_silence.pick_recording", lambda _p: None
    )
    _Quill().find_chapters_in_recording()
    assert len(opened) == 1, "Cancel at the picker opens nothing"


def test_studios_door_opens_the_book_proposing(monkeypatch, tmp_path: Path) -> None:
    from quill.apps.studio import StudioAppFrame

    picked = tmp_path / "talk.m4a"
    monkeypatch.setattr(
        "quill.ui.audio_studio.chapter_workbench_silence.pick_recording",
        lambda _parent, _start: picked,
    )
    calls: list[Any] = []

    class _Studio:
        frame = None

        def _recent_books(self) -> list[Path]:
            return []

        def open_book(self, path: Path, *, propose_silences: bool = False) -> None:
            calls.append((path, propose_silences))

    StudioAppFrame.find_chapters_in_recording(_Studio())  # type: ignore[arg-type]
    assert calls == [(picked, True)]
