"""Tests for the Audio Studio wizard's option collection and journey routing.

The wizard replaced the single-page Batch Export dialog; these tests carry
forward every collection behavior the old dialog's suite covered (extension
grouping, engine switching, round-robin rotation, translation targets, format
and mode mapping, book fields, the sounder and gap spinners) and add the
journey routing the wizard introduced. No real engine is exercised.
"""

from __future__ import annotations

from pathlib import Path

import pytest  # type: ignore[import-not-found]

wx = pytest.importorskip("wx")

from quill.ui.audio_studio.request import BatchSpeechRequest  # noqa: E402
from quill.ui.audio_studio.wizard import AudioStudioWizard  # noqa: E402


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
    dlg = AudioStudioWizard(
        frame,
        defaults=_defaults(tmp_path),
        engine_options=[
            ("Windows (SAPI 5)", "sapi5"),
            ("Kokoro (neural, offline)", "kokoro"),
        ],
        engine_available={"sapi5": True, "kokoro": True},
        voices_for=lambda e: _VOICES.get(e, []),
        on_preview=lambda engine, voice: None,
    )
    return frame, dlg


def test_collect_round_trips_defaults(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        req = dlg.build_request()
        assert req.engine == "kokoro"
        assert req.voice == "am_liam"
        assert req.output_format == "mp3"
        assert req.rate == 190
        assert abs(req.speed - 1.1) < 1e-6
        assert req.sentence_gap_ms == 250
        assert req.tail_padding_ms == 300
        assert req.sound_enabled is True
        assert req.sound_volume == 80
        # HTML default is checked and expands to both .html and .htm.
        assert ".html" in req.extensions and ".htm" in req.extensions
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_journey_documents_page_sequence(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        assert dlg.journey() == "documents"
        names = [p.GetName() for p in dlg._sequence()]
        assert names == [
            "audio_studio.start",
            "audio_studio.doc_source",
            "audio_studio.voices",
            "audio_studio.chapters",
            "audio_studio.output",
            "audio_studio.book",
            "audio_studio.summary",
        ]
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_journey_audio_request_shape(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg.start_page._journey.SetSelection(1)
        assert dlg.journey() == "audio"
        names = [p.GetName() for p in dlg._sequence()]
        assert names == [
            "audio_studio.start",
            "audio_studio.audio_source",
            "audio_studio.book",
            "audio_studio.summary",
        ]
        req = dlg.build_request()
        # A pure-audio run: nothing to synthesize, book always on, review forced.
        assert req.extensions == ()
        assert req.make_book is True
        assert req.book_review_chapters is True
        assert req.dry_run is False
        assert req.source_folder == tmp_path
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_switching_engine_reloads_voices(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        page = dlg.voices
        page.select_engine("sapi5")
        page.reload_voices()
        assert [vid for _lbl, vid in page._voice_pairs] == ["David", "Zira"]
        page.voice.SetSelection(1)
        assert page.current_voice_id() == "Zira"
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_chapter_mode_choice_maps(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        assert dlg.build_request().chapter_mode == "single"  # default
        dlg.chapters.mode.SetSelection(1)
        assert dlg.build_request().chapter_mode == "separate"
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_dry_run_and_diagnostics_collect(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        req = dlg.build_request()
        assert req.dry_run is False and req.save_spoken_text is False
        assert req.temp_folder == ""
        dlg.output.dry_run.SetValue(True)
        dlg.output.save_spoken.SetValue(True)
        dlg.output.temp_folder.SetValue(str(tmp_path / "scratch"))
        req = dlg.build_request()
        assert req.dry_run is True
        assert req.save_spoken_text is True
        assert req.temp_folder == str(tmp_path / "scratch")
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_combine_headings_and_normalize_collect(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        req = dlg.build_request()
        assert req.combine_headings is False and req.normalize_loudness is False
        dlg.chapters.combine.SetValue(True)
        dlg.output.normalize.SetValue(True)
        req = dlg.build_request()
        assert req.combine_headings is True and req.normalize_loudness is True
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_round_robin_add_reorder_remove_and_collect(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        page = dlg.voices
        page.rr_pick.SetSelection(0)  # Liam
        page.rr_add()
        page.rr_pick.SetSelection(1)  # Heart
        page.rr_add()
        assert dlg.build_request().round_robin_voices == ("am_liam", "af_heart")
        # Adding a duplicate is a no-op.
        page.rr_pick.SetSelection(0)
        page.rr_add()
        assert dlg.build_request().round_robin_voices == ("am_liam", "af_heart")
        # Move the second up.
        page.rr_list.SetSelection(1)
        page.rr_move(-1)
        assert dlg.build_request().round_robin_voices == ("af_heart", "am_liam")
        # Remove the first.
        page.rr_list.SetSelection(0)
        page.rr_remove()
        assert dlg.build_request().round_robin_voices == ("am_liam",)
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_switching_engine_clears_round_robin(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        page = dlg.voices
        page.rr_pick.SetSelection(0)
        page.rr_add()
        assert dlg.build_request().round_robin_voices  # non-empty
        page.engine.SetSelection(0)  # sapi5 is index 0 in engine_options
        page._on_engine_change()
        assert dlg.build_request().round_robin_voices == ()
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_translation_targets_add_remove_and_collect(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        page = dlg.voices
        names = [n for n, _c in page._tr_lang_pairs]
        page.tr_lang.SetSelection(names.index("Spanish"))
        page.reload_tr_voices()
        assert page._tr_voice_opts, "Spanish should have local eSpeak voices"
        page.tr_voice.SetSelection(0)
        page.tr_add()
        targets = dlg.build_request().translation_targets
        assert len(targets) == 1
        code, engine, _voice = targets[0]
        assert code == "es" and engine == "espeak"
        # Duplicate add is a no-op.
        page.tr_add()
        assert len(dlg.build_request().translation_targets) == 1
        # Remove it.
        page.tr_list.SetSelection(0)
        page.tr_remove()
        assert dlg.build_request().translation_targets == ()
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_translation_provider_collects(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        assert dlg.build_request().translation_provider == "ai_assistant"
        dlg.voices.tr_provider.SetSelection(1)
        assert dlg.build_request().translation_provider == "libretranslate"
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_format_choice_maps_each_option(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg.output.format.SetSelection(0)
        assert dlg.build_request().output_format == "mp3"
        dlg.output.format.SetSelection(1)
        assert dlg.build_request().output_format == "m4b"
        dlg.output.format.SetSelection(2)
        assert dlg.build_request().output_format == "wav"
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_existing_policy_maps_and_sets_skip(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg.output.on_existing.SetSelection(0)
        req = dlg.build_request()
        assert req.on_existing == "skip" and req.skip_existing is True
        dlg.output.on_existing.SetSelection(2)
        req = dlg.build_request()
        assert req.on_existing == "rename" and req.skip_existing is False
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_book_fields_collect_and_format_maps(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        # Off by default; the book fields are disabled until the toggle is set.
        # (IsThisEnabled reads the control's own flag; the page panel itself is
        # disabled while hidden, which would mask it from plain IsEnabled.)
        assert dlg.build_request().make_book is False
        assert dlg.book.title.IsThisEnabled() is False
        dlg.book.make_book.SetValue(True)
        dlg.book.sync_enabled()
        assert dlg.book.title.IsThisEnabled() is True
        dlg.book.title.SetValue("My Book")
        dlg.book.author.SetValue("Jane Doe")
        dlg.book.narrator.SetValue("Sam Reader")
        dlg.book.format.SetSelection(1)  # mp3
        req = dlg.build_request()
        assert req.make_book is True
        assert req.book_title == "My Book"
        assert req.book_author == "Jane Doe"
        assert req.book_narrator == "Sam Reader"
        assert req.book_format == "mp3"
        assert req.book_genre == "Audiobook"  # default carried through
        assert req.book_review_chapters is False  # off by default
        dlg.book.review.SetValue(True)
        assert dlg.build_request().book_review_chapters is True
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_doc_source_requires_folder_and_type(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        ok, _msg = dlg.doc_source.is_valid()
        assert ok
        dlg.doc_source.source.SetValue(str(tmp_path / "missing"))
        ok, msg = dlg.doc_source.is_valid()
        assert not ok and msg
        dlg.doc_source.source.SetValue(str(tmp_path))
        for cb, _ext in dlg.doc_source.ext_boxes:
            cb.SetValue(False)
        ok, msg = dlg.doc_source.is_valid()
        assert not ok and msg
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_speed_spinner_inner_edit_is_named(wx_app, tmp_path):
    # The SpinCtrlDouble's inner TextCtrl (what a screen reader focuses) must carry
    # the accessible name, not just the composite — regression for the unnamed speed.
    frame, dlg = _make(wx_app, tmp_path)
    try:
        inner = [c for c in dlg.voices.speed.GetChildren() if isinstance(c, wx.TextCtrl)]
        assert inner and inner[0].GetName() == "Kokoro speed"
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_summary_reflects_choices(wx_app, tmp_path):
    from quill.ui.audio_studio.pages_shared import summary_lines

    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg.chapters.sound.SetValue(True)
        req = dlg.build_request()
        text = "\n".join(summary_lines(req))
        assert str(tmp_path) in text
        assert "kokoro" in text
        assert "80" in text  # sounder volume carried into the summary
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_journey_edit_sequence_and_path(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg.start_page._journey.SetSelection(2)
        assert dlg.journey() == "edit"
        names = [p.GetName() for p in dlg._sequence()]
        assert names == ["audio_studio.start", "audio_studio.edit_source"]
        book = tmp_path / "book.mp3"
        book.write_bytes(b"stub")
        dlg.edit_source.file.SetValue(str(book))
        assert dlg.edit_path() == book
        ok, _msg = dlg.edit_source.is_valid()
        assert ok
        dlg.edit_source.file.SetValue(str(tmp_path / "missing.mp3"))
        ok, msg = dlg.edit_source.is_valid()
        assert not ok and msg
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_audition_and_credits_collect(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        req = dlg.build_request()
        assert req.audition is False and req.book_credits is False
        dlg.output.audition.SetValue(True)
        dlg.book.make_book.SetValue(True)
        dlg.book.sync_enabled()
        dlg.book.credits.SetValue(True)
        req = dlg.build_request()
        assert req.audition is True and req.book_credits is True
        # The combine-audio journey never speaks credits (no narration voice).
        dlg.start_page._journey.SetSelection(1)
        assert dlg.build_request().book_credits is False
    finally:
        dlg.Destroy()
        frame.Destroy()


def test_library_mode_collects_and_skips_review(wx_app, tmp_path):
    frame, dlg = _make(wx_app, tmp_path)
    try:
        dlg.start_page._journey.SetSelection(1)  # combine audio files
        req = dlg.build_request()
        assert req.library_mode is False and req.book_review_chapters is True
        dlg.audio_source.library.SetValue(True)
        req = dlg.build_request()
        assert req.library_mode is True
        assert req.book_review_chapters is False  # unattended library builds
    finally:
        dlg.Destroy()
        frame.Destroy()
