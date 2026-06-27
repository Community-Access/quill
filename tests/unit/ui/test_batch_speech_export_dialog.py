"""Tests for the Batch Speech Export dialog's option collection (no real engine).

Constructs the dialog under a module-scoped ``wx.App`` and exercises the pure
option-collection logic: extension grouping (HTML implies HTM), engine switching
reloading the voice list, format mapping, and that the gap/pause controls round
-trip into the returned :class:`BatchSpeechRequest`.
"""

from __future__ import annotations

from pathlib import Path

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui.batch_speech_export_dialog import (  # noqa: E402
    BatchSpeechExportDialog,
    BatchSpeechRequest,
)


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


_VOICES = {
    "kokoro": [("Liam", "am_liam"), ("Heart", "af_heart")],
    "sapi5": [("David", "David"), ("Zira", "Zira")],
}


def _defaults(tmp_path: Path) -> BatchSpeechRequest:
    return BatchSpeechRequest(
        source_folder=tmp_path,
        recursive=False,
        extensions=(".docx", ".html", ".htm"),
        engine="kokoro",
        voice="am_liam",
        rate=190,
        speed=1.1,
        output_format="mp3",
        sound_enabled=True,
        sound_volume=80,
        article_gap_ms=1200,
        sentence_gap_ms=250,
        tail_padding_ms=300,
        speak_headings=True,
        skip_existing=False,
    )


def _make(wx_app, tmp_path):
    frame = wx.Frame(None)
    dlg = BatchSpeechExportDialog(
        frame,
        engine_options=[("Windows (SAPI 5)", "sapi5"), ("Kokoro (neural, offline)", "kokoro")],
        engine_available={"sapi5": True, "kokoro": True},
        voices_for=lambda e: _VOICES.get(e, []),
        on_preview=lambda req: None,
        defaults=_defaults(tmp_path),
    )
    return frame, dlg


def test_collect_round_trips_defaults(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        req = dlg._collect(preview=False)
        assert req.engine == "kokoro"
        assert req.voice == "am_liam"
        assert req.output_format == "mp3"
        assert req.rate == 190
        assert abs(req.speed - 1.1) < 1e-6
        assert req.sentence_gap_ms == 250
        assert req.tail_padding_ms == 300
        assert req.sound_volume == 80
        # HTML default is checked and expands to both .html and .htm.
        assert ".html" in req.extensions and ".htm" in req.extensions
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_switching_engine_reloads_voices(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg._select_engine("sapi5")
        dlg._reload_voices()
        assert [vid for _lbl, vid in dlg._voice_pairs] == ["David", "Zira"]
        dlg._voice.SetSelection(1)
        assert dlg._current_voice_id() == "Zira"
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_chapter_mode_choice_maps(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        assert dlg._collect(preview=False).chapter_mode == "single"  # default
        dlg._mode.SetSelection(1)
        assert dlg._collect(preview=False).chapter_mode == "separate"
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_dry_run_checkbox_collects(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        assert dlg._collect(preview=False).dry_run is False
        dlg._dry_run.SetValue(True)
        assert dlg._collect(preview=False).dry_run is True
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_combine_headings_checkbox_collects(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        assert dlg._collect(preview=False).combine_headings is False
        dlg._combine.SetValue(True)
        assert dlg._collect(preview=False).combine_headings is True
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_round_robin_add_reorder_remove_and_collect(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        # Engine is kokoro -> voices am_liam, af_heart. Add both, in order.
        dlg._rr_pick.SetSelection(0)  # Liam
        dlg._on_rr_add()
        dlg._rr_pick.SetSelection(1)  # Heart
        dlg._on_rr_add()
        assert dlg._collect(preview=False).round_robin_voices == ("am_liam", "af_heart")
        # Adding a duplicate is a no-op.
        dlg._rr_pick.SetSelection(0)
        dlg._on_rr_add()
        assert dlg._collect(preview=False).round_robin_voices == ("am_liam", "af_heart")
        # Move the second up.
        dlg._rr_list.SetSelection(1)
        dlg._on_rr_move(-1)
        assert dlg._collect(preview=False).round_robin_voices == ("af_heart", "am_liam")
        # Remove the first.
        dlg._rr_list.SetSelection(0)
        dlg._on_rr_remove()
        assert dlg._collect(preview=False).round_robin_voices == ("am_liam",)
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_translation_targets_add_remove_and_collect(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        # Pick Spanish, choose its first (local eSpeak) voice, add it.
        names = [n for n, _c in dlg._tr_lang_pairs]
        dlg._tr_lang.SetSelection(names.index("Spanish"))
        dlg._reload_tr_voices()
        assert dlg._tr_voice_opts, "Spanish should have local eSpeak voices"
        dlg._tr_voice.SetSelection(0)
        dlg._on_tr_add()
        targets = dlg._collect(preview=False).translation_targets
        assert len(targets) == 1
        code, engine, _voice = targets[0]
        assert code == "es" and engine == "espeak"
        # Duplicate add is a no-op.
        dlg._on_tr_add()
        assert len(dlg._collect(preview=False).translation_targets) == 1
        # Remove it.
        dlg._tr_list.SetSelection(0)
        dlg._on_tr_remove()
        assert dlg._collect(preview=False).translation_targets == ()
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_normalize_loudness_checkbox_collects(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        assert dlg._collect(preview=False).normalize_loudness is False
        dlg._normalize.SetValue(True)
        assert dlg._collect(preview=False).normalize_loudness is True
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_translation_provider_collects(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        assert dlg._collect(preview=False).translation_provider == "ai_assistant"
        dlg._tr_provider.SetSelection(1)
        assert dlg._collect(preview=False).translation_provider == "libretranslate"
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_switching_engine_clears_round_robin(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg._rr_pick.SetSelection(0)
        dlg._on_rr_add()
        assert dlg._collect(preview=False).round_robin_voices  # non-empty
        # Switch engine kokoro -> sapi5: voices differ, rotation clears.
        dlg._engine.SetSelection(0)  # sapi5 is index 0 in engine_options
        dlg._on_engine_change()
        assert dlg._collect(preview=False).round_robin_voices == ()
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_format_choice_maps_each_option(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg._format.SetSelection(0)
        assert dlg._collect(preview=False).output_format == "mp3"
        dlg._format.SetSelection(1)
        assert dlg._collect(preview=False).output_format == "m4b"
        dlg._format.SetSelection(2)
        assert dlg._collect(preview=False).output_format == "wav"
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_temp_folder_and_save_spoken_collect(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        assert dlg._collect(preview=False).temp_folder == ""
        assert dlg._collect(preview=False).save_spoken_text is False
        dlg._temp_folder.SetValue(str(tmp_path / "scratch"))
        dlg._save_spoken.SetValue(True)
        req = dlg._collect(preview=False)
        assert req.temp_folder == str(tmp_path / "scratch")
        assert req.save_spoken_text is True
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_book_fields_collect_and_format_maps(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        # Off by default; the book fields are disabled until the toggle is set.
        assert dlg._collect(preview=False).make_book is False
        assert dlg._book_title.IsEnabled() is False
        dlg._make_book.SetValue(True)
        dlg._sync_book_enabled()
        assert dlg._book_title.IsEnabled() is True
        dlg._book_title.SetValue("My Book")
        dlg._book_author.SetValue("Jane Doe")
        dlg._book_narrator.SetValue("Sam Reader")
        dlg._book_format.SetSelection(1)  # mp3
        req = dlg._collect(preview=False)
        assert req.make_book is True
        assert req.book_title == "My Book"
        assert req.book_author == "Jane Doe"
        assert req.book_narrator == "Sam Reader"
        assert req.book_format == "mp3"
        assert req.book_genre == "Audiobook"  # default carried through
        assert req.book_review_chapters is False  # off by default
        dlg._book_review.SetValue(True)
        assert dlg._collect(preview=False).book_review_chapters is True
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()


def test_speed_spinner_inner_edit_is_named(wx_app, tmp_path):
    # The SpinCtrlDouble's inner TextCtrl (what a screen reader focuses) must carry
    # the accessible name, not just the composite — regression for the unnamed speed.
    frame, dlg = _make(wx_app, tmp_path)
    try:
        inner = [c for c in dlg._speed.GetChildren() if isinstance(c, wx.TextCtrl)]
        assert inner and inner[0].GetName() == "Kokoro speed"
    finally:
        dlg.dialog.Destroy()
        frame.Destroy()
