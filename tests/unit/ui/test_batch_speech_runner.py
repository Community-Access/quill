"""Headless tests for batch_speech_runner helpers (no wx app needed)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from quill.ui.audio_studio.request import BatchSpeechRequest
from quill.ui.batch_speech_runner import (
    _book_output_path,
    _build_translator,
    _chaptered_output_path,
    _export_translations,
    _make_temp_root,
    _resolve_chapter_sound_path,
)


def _frame(sound_id: str, pack_path: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        settings=SimpleNamespace(batch_speech_chapter_sound_id=sound_id, sound_pack_path=pack_path)
    )


def _tr_frame(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        settings=SimpleNamespace(
            pronunciation_enabled=False, pronunciation_enabled_dictionary_ids=[]
        ),
        _wx=SimpleNamespace(CallAfter=lambda fn, *a: fn(*a)),
        _set_status=lambda _msg: None,
    )


def test_build_translator_none_without_targets(tmp_path: Path) -> None:
    req = SimpleNamespace(translation_targets=())
    assert _build_translator(req) is None


def test_book_output_path_named_from_folder(tmp_path: Path) -> None:
    folder = tmp_path / "MyBook"
    folder.mkdir()
    req = BatchSpeechRequest(
        source_folder=folder,
        recursive=False,
        extensions=(".md",),
        engine="sapi5",
        voice="",
        rate=200,
        speed=1.0,
        output_format="wav",
        sound_enabled=False,
        sound_volume=0,
        article_gap_ms=0,
        sentence_gap_ms=0,
        tail_padding_ms=0,
        speak_headings=True,
        skip_existing=False,
        make_book=True,
        book_format="m4b",
    )
    # No explicit save-as -> named from the folder, in the folder, with the format suffix.
    assert _book_output_path(req) == folder / "MyBook.m4b"
    # An explicit path is honored and forced to the book's suffix.
    req.book_output_path = str(tmp_path / "out.tmp")
    assert _book_output_path(req) == tmp_path / "out.m4b"


def test_make_temp_root_under_chosen_parent(tmp_path: Path) -> None:
    parent = tmp_path / "scratch"
    req = BatchSpeechRequest(
        source_folder=tmp_path,
        recursive=False,
        extensions=(".md",),
        engine="sapi5",
        voice="",
        rate=200,
        speed=1.0,
        output_format="wav",
        sound_enabled=False,
        sound_volume=0,
        article_gap_ms=0,
        sentence_gap_ms=0,
        tail_padding_ms=0,
        speak_headings=True,
        skip_existing=False,
        temp_folder=str(parent),
    )
    root = _make_temp_root(req)
    assert root.is_dir()
    assert root.parent == parent
    assert root.name.startswith("quill-batch-")


def test_export_translations_local_engine(tmp_path: Path, monkeypatch) -> None:
    import quill.core.speech.document_speech as ds

    seen: dict = {}

    class _Result:
        with_tones_path = None

        def __init__(self, out: Path) -> None:
            self.output_path = out
            self.chapters = [1, 2]

    def _fake_synth(src, out, spec, options, **kw):
        seen["engine"] = spec.engine
        seen["voice"] = spec.voice
        seen["translate"] = kw.get("translate")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"RIFF")
        return _Result(out)

    monkeypatch.setattr(ds, "synthesize_document_to_chaptered_file", _fake_synth)
    frame = _tr_frame(tmp_path)
    src = tmp_path / "doc.md"
    src.write_text("# Hi\n\nbody\n", encoding="utf-8")
    final = tmp_path / "doc.mp3"
    final.write_bytes(b"orig")
    req = SimpleNamespace(
        translation_targets=(("es", "espeak", "es"),),
        rate=200,
        speed=1.0,
        combine_headings=False,
        source_folder=tmp_path,
    )
    chapters = _export_translations(
        frame,
        req,
        src,
        final,
        ".mp3",
        None,
        lambda _sp=None: object(),
        for_language=lambda name: lambda t: f"ES[{t}]",
    )
    assert chapters == 2
    assert seen["engine"] == "espeak" and seen["voice"] == "es"
    assert seen["translate"]("x") == "ES[x]"  # the per-language translator was passed
    # Output named "<stem> (Spanish).mp3".
    assert (tmp_path / "doc (Spanish).mp3").is_file()


def test_export_translations_skips_cloud_engine_without_key(tmp_path: Path, monkeypatch) -> None:
    # A cloud target with no configured API key is skipped (no output), so a
    # missing key never aborts the rest of the batch.
    frame = _tr_frame(tmp_path)
    frame.settings.ai_tts_model = ""
    frame._get_openai_api_key = lambda: ""  # no key configured
    src = tmp_path / "doc.md"
    src.write_text("x", encoding="utf-8")
    req = SimpleNamespace(
        translation_targets=(("es", "openai", "nova"),),
        rate=200,
        speed=1.0,
        combine_headings=False,
        source_folder=tmp_path,
    )
    chapters = _export_translations(
        frame,
        req,
        src,
        tmp_path / "doc.mp3",
        ".mp3",
        None,
        lambda _sp=None: object(),
        for_language=lambda name: lambda t: t,
    )
    assert chapters == 0
    assert not (tmp_path / "doc (Spanish).mp3").exists()


def test_export_translations_cloud_engine_with_key(tmp_path: Path, monkeypatch) -> None:
    # A configured cloud key now ships a translated export: the spec carries the
    # provider key + model and the document is synthesized with the cloud voice.
    import quill.core.speech.document_speech as ds

    seen: dict = {}

    class _Result:
        with_tones_path = None

        def __init__(self, out: Path) -> None:
            self.output_path = out
            self.chapters = [1]

    def _fake_synth(src, out, spec, options, **kw):
        seen["engine"] = spec.engine
        seen["api_key"] = spec.api_key
        seen["model"] = spec.model
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"RIFF")
        return _Result(out)

    monkeypatch.setattr(ds, "synthesize_document_to_chaptered_file", _fake_synth)
    frame = _tr_frame(tmp_path)
    frame.settings.ai_tts_model = ""
    frame._get_openai_api_key = lambda: "sk-test"
    src = tmp_path / "doc.md"
    src.write_text("# Hi\n\nbody\n", encoding="utf-8")
    req = SimpleNamespace(
        translation_targets=(("es", "openai", "nova"),),
        rate=200,
        speed=1.0,
        combine_headings=False,
        source_folder=tmp_path,
    )
    chapters = _export_translations(
        frame,
        req,
        src,
        tmp_path / "doc.mp3",
        ".mp3",
        None,
        lambda _sp=None: object(),
        for_language=lambda name: lambda t: t,
    )
    assert chapters == 1
    assert seen["engine"] == "openai" and seen["api_key"] == "sk-test"
    assert seen["model"]  # defaulted from the provider
    assert (tmp_path / "doc (Spanish).mp3").is_file()


def test_confirm_cloud_cost_local_only_no_prompt(monkeypatch) -> None:
    # Local voices + a free/local translator -> nothing metered, so it proceeds
    # without ever prompting the user.
    from quill.ui import batch_speech_runner as bsr

    monkeypatch.setattr(bsr, "_ai_provider_metered", lambda: False)
    prompted: list[int] = []
    frame = SimpleNamespace(
        _wx=SimpleNamespace(ICON_QUESTION=0, YES_NO=0, YES=1),
        _show_message_box=lambda *a, **k: prompted.append(1) or 1,
    )
    ok = bsr.confirm_cloud_cost(
        frame,
        translation_provider="libretranslate",
        targets=(("es", "espeak", "es"),),
        char_count=10_000,
    )
    assert ok is True and not prompted  # never asked


def test_confirm_cloud_cost_cloud_prompts_and_respects_no(monkeypatch) -> None:
    from quill.ui import batch_speech_runner as bsr

    monkeypatch.setattr(bsr, "_ai_provider_metered", lambda: True)
    monkeypatch.setattr(bsr, "_cloud_credentials", lambda _f, _p: ("key", "tts-1"))
    shown: list[str] = []
    frame = SimpleNamespace(
        _wx=SimpleNamespace(ICON_QUESTION=0, YES_NO=0, YES=1),
        _show_message_box=lambda msg, *a, **k: shown.append(msg) or 0,  # user says No
    )
    ok = bsr.confirm_cloud_cost(
        frame,
        translation_provider="ai_assistant",
        targets=(("es", "openai", "nova"),),
        char_count=1_000_000,
    )
    assert ok is False  # declined
    assert shown and "Estimated cloud cost" in shown[0]


def test_resolve_chapter_sound_from_bundled_ink(tmp_path: Path) -> None:
    # An event id present in the bundled Ink pack resolves to a real WAV on disk.
    out = _resolve_chapter_sound_path(_frame("transcription_started"), tmp_path)
    assert out is not None
    assert out.exists() and out.suffix == ".wav"
    assert out.stat().st_size > 0


def test_resolve_chapter_sound_none_when_unset(tmp_path: Path) -> None:
    assert _resolve_chapter_sound_path(_frame(""), tmp_path) is None


def test_resolve_chapter_sound_none_for_unknown_id(tmp_path: Path) -> None:
    assert _resolve_chapter_sound_path(_frame("no_such_event_id"), tmp_path) is None


def _req(folder: Path, **overrides: object):
    from quill.ui.audio_studio.request import BatchSpeechRequest

    base = dict(
        source_folder=folder,
        recursive=False,
        extensions=(".md",),
        engine="sapi5",
        voice="",
        rate=200,
        speed=1.0,
        output_format="mp3",
        sound_enabled=False,
        sound_volume=100,
        article_gap_ms=1200,
        sentence_gap_ms=0,
        tail_padding_ms=300,
        speak_headings=True,
        skip_existing=False,
    )
    base.update(overrides)
    return BatchSpeechRequest(**base)  # type: ignore[arg-type]


def test_project_profile_save_then_apply_round_trips(tmp_path: Path) -> None:
    from quill.ui.batch_speech_runner import _apply_project_profile, _save_project_profile

    chosen = _req(
        tmp_path,
        engine="kokoro",
        voice="am_liam",
        rate=190,
        speed=1.1,
        output_format="m4b",
        sound_enabled=True,
        sound_volume=70,
        article_gap_ms=900,
        chapter_mode="separate",
        combine_headings=True,
        round_robin_voices=("am_liam", "af_heart"),
        translation_targets=(("es", "espeak", "es"), ("fr", "openai", "nova")),
        translation_provider="ai_assistant",
    )
    _save_project_profile(SimpleNamespace(), chosen)  # writes <tmp_path>/.quill/speech-project.json
    assert (tmp_path / ".quill" / "speech-project.json").is_file()

    # A frame whose active document lives in tmp_path pre-fills from that profile.
    frame = SimpleNamespace(_active_document_path=lambda: str(tmp_path / "doc.md"))
    applied = _apply_project_profile(frame, _req(tmp_path))  # global defaults overlaid
    assert applied.engine == "kokoro" and applied.voice == "am_liam"
    assert applied.output_format == "m4b" and applied.chapter_mode == "separate"
    assert applied.sound_enabled is True and applied.article_gap_ms == 900
    assert applied.combine_headings is True
    assert applied.round_robin_voices == ("am_liam", "af_heart")
    # Translated-export targets and backend are remembered per project.
    assert applied.translation_targets == (("es", "espeak", "es"), ("fr", "openai", "nova"))
    assert applied.translation_provider == "ai_assistant"


def test_apply_project_profile_no_profile_keeps_defaults(tmp_path: Path) -> None:
    from quill.ui.batch_speech_runner import _apply_project_profile

    frame = SimpleNamespace(_active_document_path=lambda: str(tmp_path / "doc.md"))
    defaults = _req(tmp_path, engine="sapi5", output_format="mp3")
    applied = _apply_project_profile(frame, defaults)
    assert applied.engine == "sapi5" and applied.output_format == "mp3"


class _FakeProgressDialog:
    """Stands in for AIProgressDialog: captures on_cancel so a test can invoke
    it, and records every message pushed to it (mirrors what the real dialog
    would show on screen)."""

    instances: list[_FakeProgressDialog] = []

    def __init__(self, parent, title, message, on_cancel=None, status_fn=None):
        self.on_cancel = on_cancel
        self.messages: list[str] = []
        _FakeProgressDialog.instances.append(self)

    def set_progress(self, percent, message=None):
        if message is not None:
            self.messages.append(message)

    def update_message(self, message):
        self.messages.append(message)

    def show(self):
        pass

    def close(self):
        pass


def _cancel_test_frame() -> SimpleNamespace:
    return SimpleNamespace(
        settings=SimpleNamespace(pronunciation_enabled=False),
        _wx=SimpleNamespace(CallAfter=lambda fn, *a: fn(*a)),
        _set_status=lambda _msg: None,
        _run_background_task=lambda label, work, on_success, **kw: on_success(
            work(lambda *a: None)
        ),
        frame=None,
    )


def test_cancel_finishes_the_current_file_then_stops_and_logs_it(
    tmp_path: Path, monkeypatch
) -> None:
    """Clicking Cancel (or Escape) must not corrupt the file in flight -- it
    finishes normally -- and the run must stop before the next file, with the
    stop recorded in the log (the batch-generation Cancel button fix)."""
    import quill.core.speech.chapter_assemble as chapter_assemble
    import quill.core.speech.document_speech as document_speech
    import quill.ui.ai_transcribe_dialog as ai_transcribe_dialog
    from quill.ui.batch_speech_runner import _run

    (tmp_path / "a.md").write_text("# A\n\nFirst document.\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("# B\n\nSecond document.\n", encoding="utf-8")

    _FakeProgressDialog.instances = []
    monkeypatch.setattr(ai_transcribe_dialog, "AIProgressDialog", _FakeProgressDialog)

    started: list[str] = []

    def _fake_synth(src, staged, spec, opts, *, on_progress=None, **kw):
        started.append(src.name)
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(b"fake-audio")
        if on_progress is not None:
            # Chunk-by-chunk progress, exactly like the real synthesizer reports it.
            on_progress(1, 2)
            on_progress(2, 2)
        # Simulate the user clicking Cancel (or pressing Escape) while this first
        # file is still "in flight" -- it must be allowed to finish normally, and
        # only the *next* file must be skipped.
        _FakeProgressDialog.instances[-1].on_cancel()
        return chapter_assemble.ChapterAssembleResult(
            output_path=staged, chapters=[], section_count=0
        )

    monkeypatch.setattr(document_speech, "synthesize_document_to_chaptered_file", _fake_synth)

    frame = _cancel_test_frame()
    req = _req(tmp_path, extensions=(".md",))
    _run(frame, req)

    # The first file completed (its output exists); the second was never started.
    assert started == ["a.md"]
    assert (tmp_path / "a.mp3").is_file()
    assert not (tmp_path / "b.mp3").is_file()

    log_files = list(tmp_path.glob("quill-batch-speech-*.log"))
    assert len(log_files) == 1
    log_text = log_files[0].read_text(encoding="utf-8")
    # Chunk-level progress reached the log file, not just the on-screen dialog.
    assert "chunk 1/2" in log_text
    assert "chunk 2/2" in log_text
    assert "Cancelled after 1/2 file(s)." in log_text


def test_no_cancel_button_when_generation_has_not_started(tmp_path: Path, monkeypatch) -> None:
    """Regression guard for the original bug: the progress dialog must always
    be given on_cancel now, so a Cancel button (and working Escape) exists."""
    import quill.core.speech.chapter_assemble as chapter_assemble
    import quill.core.speech.document_speech as document_speech
    import quill.ui.ai_transcribe_dialog as ai_transcribe_dialog
    from quill.ui.batch_speech_runner import _run

    (tmp_path / "a.md").write_text("# A\n\nOnly document.\n", encoding="utf-8")

    _FakeProgressDialog.instances = []
    monkeypatch.setattr(ai_transcribe_dialog, "AIProgressDialog", _FakeProgressDialog)

    def _fake_synth(src, staged, spec, opts, *, on_progress=None, **kw):
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(b"fake-audio")
        return chapter_assemble.ChapterAssembleResult(
            output_path=staged, chapters=[], section_count=0
        )

    monkeypatch.setattr(document_speech, "synthesize_document_to_chaptered_file", _fake_synth)

    frame = _cancel_test_frame()
    req = _req(tmp_path, extensions=(".md",))
    _run(frame, req)

    assert len(_FakeProgressDialog.instances) == 1
    assert _FakeProgressDialog.instances[0].on_cancel is not None


def test_chaptered_output_path_wav_goes_to_a_subfolder_mp3_stays_beside_source(
    tmp_path: Path,
) -> None:
    src = tmp_path / "chapter one" / "notes.md"

    mp3_path = _chaptered_output_path(src, ".mp3", book_mode=False)
    assert mp3_path == src.with_suffix(".mp3")  # unchanged: beside the source document

    wav_path = _chaptered_output_path(src, ".wav", book_mode=False)
    assert wav_path == src.parent / "Audio Output" / "notes.wav"
    assert wav_path.parent == src.parent / "Audio Output"  # local to this doc's own folder

    # Book-mode WAV chapters are intermediate inputs to audiobook assembly's flat
    # folder scan and must stay beside the source document, not redirected.
    book_wav_path = _chaptered_output_path(src, ".wav", book_mode=True)
    assert book_wav_path == src.with_suffix(".wav")


def test_chaptered_output_path_recursion_stays_local_to_each_document(tmp_path: Path) -> None:
    # Two documents in different subfolders of a recursive run each get their own
    # Audio Output subfolder, never a single shared top-level one.
    top_doc = tmp_path / "top.md"
    nested_doc = tmp_path / "sub" / "nested.md"

    top_wav = _chaptered_output_path(top_doc, ".wav", book_mode=False)
    nested_wav = _chaptered_output_path(nested_doc, ".wav", book_mode=False)

    assert top_wav == tmp_path / "Audio Output" / "top.wav"
    assert nested_wav == tmp_path / "sub" / "Audio Output" / "nested.wav"


def test_wav_output_actually_lands_in_audio_output_subfolder(tmp_path: Path, monkeypatch) -> None:
    """End-to-end: choosing WAV as the output format writes into <source>/Audio
    Output/, while the default MP3 format still writes beside the document."""
    import quill.core.speech.chapter_assemble as chapter_assemble
    import quill.core.speech.document_speech as document_speech
    import quill.ui.ai_transcribe_dialog as ai_transcribe_dialog
    from quill.ui.batch_speech_runner import _run

    (tmp_path / "a.md").write_text("# A\n\nDocument.\n", encoding="utf-8")

    _FakeProgressDialog.instances = []
    monkeypatch.setattr(ai_transcribe_dialog, "AIProgressDialog", _FakeProgressDialog)

    def _fake_synth(src, staged, spec, opts, *, on_progress=None, **kw):
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(b"fake-audio")
        return chapter_assemble.ChapterAssembleResult(
            output_path=staged, chapters=[], section_count=0
        )

    monkeypatch.setattr(document_speech, "synthesize_document_to_chaptered_file", _fake_synth)

    frame = _cancel_test_frame()
    req = _req(tmp_path, extensions=(".md",), output_format="wav")
    _run(frame, req)

    assert (tmp_path / "Audio Output" / "a.wav").is_file()
    assert not (tmp_path / "a.wav").exists()
