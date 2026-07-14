"""Headless tests for translated_speech_runner (no wx app needed)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import quill.ui.batch_speech_runner as batch
import quill.ui.translated_speech_runner as tsr
from quill.ui.translated_speech_export_dialog import TranslatedSpeechRequest


def _frame(tmp_path: Path, modified: bool = False) -> SimpleNamespace:
    captured: dict = {}

    def _run_bg(label, work, on_success, **kw):
        captured["label"] = label
        result = work(lambda *a, **k: None)
        on_success(result)
        captured["result"] = result

    return SimpleNamespace(
        document=SimpleNamespace(path=tmp_path / "doc.md", modified=modified),
        settings=SimpleNamespace(
            read_aloud_rate=200,
            read_aloud_kokoro_speed=1.0,
            batch_speech_article_gap_ms=1200,
            batch_speech_sentence_gap_ms=0,
            batch_speech_tail_padding_ms=300,
            pronunciation_enabled=False,
            pronunciation_enabled_dictionary_ids=[],
        ),
        frame=object(),
        _wx=SimpleNamespace(ICON_INFORMATION=0, OK=0, ICON_QUESTION=0, YES_NO=0, CANCEL=2, YES=1),
        _show_message_box=lambda *a, **k: 0,
        _set_status=lambda _m: None,
        _run_background_task=_run_bg,
        _captured=captured,
    )


def test_unsaved_empty_buffer_warns(tmp_path: Path) -> None:
    # Unsaved document with an empty buffer: warn instead of exporting nothing.
    # (A non-empty unsaved buffer now exports without forcing a save.)
    frame = _frame(tmp_path)
    frame.document.path = None
    frame.editor = SimpleNamespace(GetValue=lambda: "   ")
    msgs: list[str] = []
    frame._show_message_box = lambda msg, *a, **k: msgs.append(msg) or 0
    tsr.run_translated_speech_export(frame)
    assert msgs and "nothing to export" in msgs[0].lower()


def test_run_invokes_export_translations(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "doc.md"
    src.write_text("# Hi\n\nbody\n", encoding="utf-8")
    frame = _frame(tmp_path)

    seen: dict = {}

    def _fake_export(frame_, req, source, base_final, suffix, sound, opts_fn, for_lang, bl):
        seen["targets"] = req.translation_targets
        seen["suffix"] = suffix
        seen["source"] = source
        return 3

    monkeypatch.setattr(batch, "_export_translations", _fake_export)
    monkeypatch.setattr(batch, "_build_translator", lambda req: lambda name: lambda t: t)
    monkeypatch.setattr(batch, "confirm_cloud_cost", lambda *a, **k: True)

    request = TranslatedSpeechRequest(targets=(("es", "espeak", "es"),), output_format="mp3")
    tsr._run(
        frame,
        request,
        read_source=src,
        out_dir=src.parent,
        stem=src.stem,
        cleanup_source=False,
    )
    assert seen["targets"] == (("es", "espeak", "es"),)
    assert seen["suffix"] == ".mp3" and seen["source"] == src
    assert frame._captured["result"] == 3
