"""Tests for the Chapter Workbench dialog (split/retime/merge over a real plan).

Playback itself is not exercised (no media backend in CI); the playhead is
stubbed so the surgery operations can be driven exactly as the buttons do.
"""

from __future__ import annotations

from pathlib import Path

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.core.speech.book_file import BookFile  # noqa: E402
from quill.core.speech.chapters import Chapter  # noqa: E402
from quill.core.speech.ffmpeg import AudioMetadata  # noqa: E402
from quill.ui.audio_studio.chapter_workbench import ChapterWorkbenchDialog  # noqa: E402


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


def _book(tmp_path: Path) -> BookFile:
    path = tmp_path / "book.mp3"
    path.write_bytes(b"\xff\xfb\x90\x00" + b"\x00" * 413)
    return BookFile(
        path=path,
        tags=AudioMetadata(album="My Book", artist="Jane"),
        chapters=[
            Chapter(index=0, title="One", start_ms=0, end_ms=60_000),
            Chapter(index=1, title="Two", start_ms=60_000, end_ms=120_000),
        ],
        total_ms=120_000,
    )


def _make(wx_app, tmp_path, announces=None):
    frame = wx.Frame(None)
    dlg = ChapterWorkbenchDialog(
        frame,
        _book(tmp_path),
        announce=(announces.append if announces is not None else None),
    )
    return frame, dlg


def test_list_shows_times_and_titles(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        items = [dlg._chapter_list.GetString(i) for i in range(dlg._chapter_list.GetCount())]
        assert items[0] == "1. One — starts 0:00, runs 1:00"
        assert items[1] == "2. Two — starts 1:00, runs 1:00"
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_split_at_playhead(wx_app, tmp_path):
    announces: list[str] = []
    frame, dlg = _make(wx_app, tmp_path, announces)
    try:
        dlg.player.playhead_ms = lambda: 30_000  # stub the transport
        dlg._on_split()
        titles = [c.title for c in dlg._book.chapters]
        assert titles == ["One", "New chapter", "Two"]
        assert dlg._book.chapters[1].start_ms == 30_000
        assert any("Split at 0:30" in a for a in announces)
        assert dlg._dirty
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_retime_selected_chapter_to_playhead(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg._chapter_list.SetSelection(1)
        dlg.player.playhead_ms = lambda: 45_000
        dlg._on_retime()
        assert dlg._book.chapters[0].end_ms == 45_000
        assert dlg._book.chapters[1].start_ms == 45_000
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_bad_split_is_spoken_not_crash(wx_app, tmp_path, monkeypatch):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        errors: list[str] = []
        monkeypatch.setattr(dlg, "_error", errors.append)
        dlg.player.playhead_ms = lambda: 0  # not inside any chapter interior
        dlg._on_split()
        assert errors and len(dlg._book.chapters) == 2
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_merge_and_restore(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg._chapter_list.SetSelection(1)
        dlg._on_merge()
        assert [c.title for c in dlg._book.chapters] == ["One"]
        assert dlg._book.chapters[0].end_ms == 120_000
        dlg._on_restore()
        assert [c.title for c in dlg._book.chapters] == ["One", "Two"]
        assert not dlg._dirty
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_rename_updates_plan(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg._chapter_list.SetSelection(0)
        dlg._title_edit.SetValue("Prologue")
        dlg._on_rename()
        assert dlg._book.chapters[0].title == "Prologue"
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_m4b_disables_in_place_save(wx_app, tmp_path):
    frame = wx.Frame(None)
    book = _book(tmp_path)
    book.path = book.path.with_suffix(".m4b")
    book.path.write_bytes(b"stub")
    dlg = ChapterWorkbenchDialog(frame, book, announce=None)
    try:
        assert dlg._save_btn.IsThisEnabled() is False
    finally:
        dlg.Destroy()
        frame.Destroy()


# --- silence auto-chapter and ACX check ---------------------------------------


def test_propose_from_silences_replaces_chapters(wx_app, tmp_path, monkeypatch):
    """Patched detect_silence_chapters returns a 3-chapter proposal that lands in the list."""
    from quill.core.speech.chapters import Chapter as _Chapter
    from quill.ui.audio_studio import chapter_workbench as cwb

    proposed = [
        _Chapter(index=0, title="Chapter 1", start_ms=0, end_ms=20_000),
        _Chapter(index=1, title="Chapter 2", start_ms=20_000, end_ms=40_000),
        _Chapter(index=2, title="Chapter 3", start_ms=40_000, end_ms=60_000),
    ]
    captured: dict[str, object] = {}

    def fake_detect(path, **kwargs):
        captured["path"] = path
        captured["kwargs"] = kwargs
        return proposed

    # The dialog imports the symbol at call time from the source module, so
    # patch the symbol there, not on the dialog's own module. We also stub
    # the params modal so the test does not actually open a wx dialog.
    monkeypatch.setattr("quill.core.speech.silence.detect_silence_chapters", fake_detect)
    monkeypatch.setattr(cwb, "SilenceParamsDialog", _OKDialogWithDefaults)

    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg._on_propose_from_silences()
        assert captured["path"] == dlg._book.path
        assert captured["kwargs"]["noise_db"] == -30.0
        assert captured["kwargs"]["min_silence_s"] == 0.8
        assert [c.title for c in dlg._book.chapters] == ["Chapter 1", "Chapter 2", "Chapter 3"]
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_propose_from_silences_announces_count(wx_app, tmp_path, monkeypatch):
    """The spoken announcement includes the proposed chapter count."""
    from quill.core.speech.chapters import Chapter as _Chapter
    from quill.ui.audio_studio import chapter_workbench as cwb

    proposed = [
        _Chapter(index=0, title="Chapter 1", start_ms=0, end_ms=30_000),
        _Chapter(index=1, title="Chapter 2", start_ms=30_000, end_ms=60_000),
    ]
    monkeypatch.setattr(
        "quill.core.speech.silence.detect_silence_chapters",
        lambda *_a, **_k: proposed,
    )
    monkeypatch.setattr(cwb, "SilenceParamsDialog", _OKDialogWithDefaults)

    announces: list[str] = []
    frame, dlg = _make(wx_app, tmp_path, announces)
    try:
        dlg._on_propose_from_silences()
        assert any("2 chapters" in a for a in announces), f"got {announces!r}"
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_propose_from_silences_undo_with_restore(wx_app, tmp_path, monkeypatch):
    """After a proposal, Restore original returns the original chapter list."""
    from quill.core.speech.chapters import Chapter as _Chapter
    from quill.ui.audio_studio import chapter_workbench as cwb

    original_titles = ["One", "Two"]
    proposed = [
        _Chapter(index=0, title="A", start_ms=0, end_ms=20_000),
        _Chapter(index=1, title="B", start_ms=20_000, end_ms=40_000),
        _Chapter(index=2, title="C", start_ms=40_000, end_ms=60_000),
    ]
    monkeypatch.setattr(
        "quill.core.speech.silence.detect_silence_chapters",
        lambda *_a, **_k: proposed,
    )
    monkeypatch.setattr(cwb, "SilenceParamsDialog", _OKDialogWithDefaults)

    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg._on_propose_from_silences()
        assert [c.title for c in dlg._book.chapters] == ["A", "B", "C"]
        dlg._on_restore()
        assert [c.title for c in dlg._book.chapters] == original_titles
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_propose_no_silences_announces_and_does_not_change(wx_app, tmp_path, monkeypatch):
    """When ffmpeg finds no silences, the original list is kept and a message is announced."""
    from quill.ui.audio_studio import chapter_workbench as cwb

    original_titles = ["One", "Two"]
    monkeypatch.setattr(
        "quill.core.speech.silence.detect_silence_chapters",
        lambda *_a, **_k: [],
    )
    monkeypatch.setattr(cwb, "SilenceParamsDialog", _OKDialogWithDefaults)

    announces: list[str] = []
    frame, dlg = _make(wx_app, tmp_path, announces)
    try:
        dlg._on_propose_from_silences()
        assert [c.title for c in dlg._book.chapters] == original_titles
        assert any("no silences" in a.lower() for a in announces), f"got {announces!r}"
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_acx_check_passes_announces_and_shows_dialog(wx_app, tmp_path, monkeypatch):
    """A passing check announces 'passes' and the dialog carries the verdict."""
    from quill.core.speech.loudness import AcxCheck
    from quill.ui.audio_studio import chapter_workbench as cwb

    check = AcxCheck(
        integrated_lufs=-20.0,
        true_peak_db=-3.5,
        noise_floor_db=-65.0,
        loudness_ok=True,
        peak_ok=True,
        noise_ok=True,
    )
    monkeypatch.setattr("quill.core.speech.loudness.acx_check_file", lambda _path: check)
    captured: dict[str, object] = {}

    class _CaptureDialog:
        def __init__(self, parent, *, check):
            captured["check"] = check

        def ShowModal(self):
            return wx.ID_OK

    monkeypatch.setattr(cwb, "AcxResultDialog", _CaptureDialog)

    announces: list[str] = []
    frame, dlg = _make(wx_app, tmp_path, announces)
    try:
        dlg._on_check_acx()
        assert captured["check"] is check
        assert any("passes" in a for a in announces), f"got {announces!r}"
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_acx_check_failing_announces_fail(wx_app, tmp_path, monkeypatch):
    """A failing check announces 'fails' and the dialog gets the AcxCheck with recommendations."""
    from quill.core.speech.loudness import AcxCheck
    from quill.ui.audio_studio import chapter_workbench as cwb

    check = AcxCheck(
        integrated_lufs=-14.2,
        true_peak_db=-2.0,
        noise_floor_db=-55.0,
        loudness_ok=False,
        peak_ok=False,
        noise_ok=False,
    )
    monkeypatch.setattr("quill.core.speech.loudness.acx_check_file", lambda _path: check)
    captured: dict[str, object] = {}

    class _CaptureDialog:
        def __init__(self, parent, *, check):
            captured["check"] = check

        def ShowModal(self):
            return wx.ID_OK

    monkeypatch.setattr(cwb, "AcxResultDialog", _CaptureDialog)

    announces: list[str] = []
    frame, dlg = _make(wx_app, tmp_path, announces)
    try:
        dlg._on_check_acx()
        assert captured["check"] is check
        assert any("fails" in a for a in announces), f"got {announces!r}"
        # Recommendations are present and speakable.
        recs = check.recommendations()
        assert len(recs) == 3
        assert any("LUFS" in r for r in recs)
        assert any("True peak" in r for r in recs)
        assert any("Noise floor" in r for r in recs)
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_acx_check_none_shows_no_measurement_dialog(wx_app, tmp_path, monkeypatch):
    """When acx_check_file returns None (ffmpeg missing), the dialog still opens with no data."""
    from quill.ui.audio_studio import chapter_workbench as cwb

    monkeypatch.setattr("quill.core.speech.loudness.acx_check_file", lambda _path: None)
    captured: dict[str, object] = {}

    class _CaptureDialog:
        def __init__(self, parent, *, check):
            captured["check"] = check

        def ShowModal(self):
            return wx.ID_OK

    monkeypatch.setattr(cwb, "AcxResultDialog", _CaptureDialog)

    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg._on_check_acx()
        assert captured["check"] is None
    finally:
        dlg.Destroy()
        frame.Destroy()


class _OKDialogWithDefaults:
    """Stand-in for SilenceParamsDialog that returns the defaults without UI."""

    def __init__(self, _parent):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def ShowModal(self):
        return wx.ID_OK

    def values(self):
        return -30.0, 0.8
