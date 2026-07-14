"""Run a single document's translated speech export (roadmap §7).

Bound to Tools > Speech > Export to Translated Speech Audio. This is the
one-document counterpart to the folder-oriented batch translated export: it reuses
the same tested core (:func:`quill.ui.batch_speech_runner._export_translations`,
which drives ``document_speech`` with a per-language translator and the
voice-failure blacklist) against the active document's file, writing
``<doc> (<Language>).<ext>`` beside it.

Free functions, not a mixin, so the orchestration stays out of the budgeted
``main_frame`` modules (GATE-11). The handler takes the ``MainFrame`` as ``frame``
and uses its established helpers (``_show_modal_dialog``, ``_run_background_task``,
``_show_message_box``, ``_set_status``, ``settings``, ``frame``, ``_wx``).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from quill.ui.translated_speech_export_dialog import (
    TranslatedSpeechExportDialog,
    TranslatedSpeechRequest,
)


def _active_document(frame: Any) -> Any:
    """The active Document (or None) for the front tab."""
    return getattr(frame, "document", None)


_TITLE = "Export to Translated Speech Audio"


def _prompt_output_folder(frame: Any) -> Path | None:
    """Ask where the per-language audio for an unsaved document should be written."""
    wx = frame._wx
    with wx.DirDialog(
        frame.frame,
        "Choose a folder for the translated speech audio",
        style=wx.DD_DEFAULT_STYLE,
    ) as dlg:
        if frame._show_modal_dialog(dlg, _TITLE) != wx.ID_OK:
            return None
        return Path(dlg.GetPath())


def _write_temp_source(text: str) -> Path:
    """Write the current editor buffer to a temp .txt file used as the read source."""
    temp = Path(tempfile.mkdtemp(prefix="quill_tr_buf_")) / "Untitled.txt"
    temp.write_text(text, encoding="utf-8")
    return temp


def _route_to_audio_studio(frame: Any, source: Path) -> None:
    """Open the Audio Studio wizard with the saved document pre-filled.

    The wizard's source picker accepts a folder; for a single document we
    pre-fill the folder and remember the file via the audio-source MRU
    list. The user is then on the wizard's first page with a meaningful
    default and can Tab through the rest of the journey.
    """
    from quill.core.recent import add_recent_audiobook_file
    from quill.ui.batch_speech_runner import run_batch_export_to_speech

    # Add the on-disk document to the audiobooks MRU so the user can pick it
    # back up if they step back out of the wizard. The wizard itself will
    # appear with the folder choice page so they can confirm before any
    # synthesis kicks off.
    add_recent_audiobook_file(source)
    run_batch_export_to_speech(frame)


def run_translated_speech_export(frame: Any) -> None:
    """Entry point bound to the Export to Translated Speech Audio menu item."""
    wx = frame._wx
    doc = _active_document(frame)
    path = getattr(doc, "path", None) if doc is not None else None

    if path is not None:
        # Saved document: export reads the on-disk file. Offer to save unsaved
        # edits so they are spoken; outputs land beside the document.
        if getattr(doc, "modified", False):
            choice = frame._show_message_box(
                "The document has unsaved changes. Save before exporting so they are "
                "included in the translation?",
                _TITLE,
                wx.ICON_QUESTION | wx.YES_NO | wx.CANCEL,
            )
            if choice == wx.CANCEL:
                frame._set_status("Translated speech export cancelled")
                return
            if choice == wx.YES:
                frame.save_file()

        source = Path(path)
        dialog = TranslatedSpeechExportDialog(frame.frame, document_name=source.name)
        request = dialog.show(frame._show_modal_dialog)
        if dialog.open_studio_requested:
            _route_to_audio_studio(frame, source)
            return
        if request is None:
            frame._set_status("Translated speech export cancelled")
            return
        _run(
            frame,
            request,
            read_source=source,
            out_dir=source.parent,
            stem=source.stem,
            cleanup_source=False,
        )
        return

    # Unsaved document: export the current buffer without forcing a save to disk.
    editor = getattr(frame, "editor", None)
    text = editor.GetValue().strip() if editor is not None else ""
    if not text:
        frame._show_message_box(
            "There is nothing to export. Type or open a document first, then try "
            "Export to Translated Speech Audio again.",
            _TITLE,
            wx.ICON_INFORMATION | wx.OK,
        )
        return

    dialog = TranslatedSpeechExportDialog(frame.frame, document_name="Untitled")
    request = dialog.show(frame._show_modal_dialog)
    if dialog.open_studio_requested:
        # No on-disk source to hand the wizard; the user can pick the file
        # in the wizard's source picker. The button just opens the wizard.
        from quill.ui.batch_speech_runner import run_batch_export_to_speech

        run_batch_export_to_speech(frame)
        return
    if request is None:
        frame._set_status("Translated speech export cancelled")
        return

    out_dir = _prompt_output_folder(frame)
    if out_dir is None:
        frame._set_status("Translated speech export cancelled")
        return

    _run(
        frame,
        request,
        read_source=_write_temp_source(text),
        out_dir=out_dir,
        stem="Untitled",
        cleanup_source=True,
    )


def _run(
    frame: Any,
    request: TranslatedSpeechRequest,
    *,
    read_source: Path,
    out_dir: Path,
    stem: str,
    cleanup_source: bool,
) -> None:
    from quill.core.speech.chapter_assemble import ChapterAssembleOptions
    from quill.core.speech.voice_blacklist import load_blacklist, save_blacklist
    from quill.ui.batch_speech_runner import (
        _build_translator,
        _export_translations,
        confirm_cloud_cost,
    )

    s = frame.settings
    suffix = {"mp3": ".mp3", "m4b": ".m4b"}.get(request.output_format, ".wav")
    base_final = out_dir / f"{stem}{suffix}"
    # A req shim carrying just the fields _export_translations / _build_translator read.
    req = SimpleNamespace(
        translation_targets=request.targets,
        translation_provider=request.translation_provider,
        libretranslate_url=request.libretranslate_url,
        rate=int(s.read_aloud_rate),
        speed=float(s.read_aloud_kokoro_speed),
        combine_headings=False,
        source_folder=out_dir,
    )
    for_language = _build_translator(req)
    if for_language is None:
        frame._set_status("No translation targets selected")
        return

    # Cost surfacing (roadmap §7): the document character count is known exactly here,
    # so the combined translation + TTS estimate is precise. Confirm before metered work.
    try:
        from quill.core.speech.text_polish import extract_text

        char_count = len(extract_text(read_source))
    except Exception:  # noqa: BLE001 - estimate is best-effort
        char_count = 0
    if not confirm_cloud_cost(
        frame,
        translation_provider=request.translation_provider,
        targets=request.targets,
        char_count=char_count,
    ):
        frame._set_status("Translated speech export cancelled")
        return

    def opts(_sound_path: Path | None = None) -> ChapterAssembleOptions:
        return ChapterAssembleOptions(
            article_gap_ms=int(s.batch_speech_article_gap_ms),
            sound_enabled=False,
            output_format=request.output_format,
            speak_headings=True,
            sentence_gap_ms=int(s.batch_speech_sentence_gap_ms),
            tail_padding_ms=int(s.batch_speech_tail_padding_ms),
            max_chunk_chars=8000,
        )

    voice_blacklist = load_blacklist()

    def work(_progress: Any) -> object:
        import shutil

        work_dir = Path(tempfile.mkdtemp(prefix="quill_tr_single_"))
        try:
            chapters = _export_translations(
                frame,
                req,
                read_source,
                base_final,
                suffix,
                None,
                opts,
                for_language,
                voice_blacklist,
            )
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
            if cleanup_source:
                shutil.rmtree(read_source.parent, ignore_errors=True)
        save_blacklist(voice_blacklist)
        return chapters

    def on_success(result: object) -> None:
        count = int(result) if isinstance(result, int) else 0
        langs = len(request.targets)
        frame._set_status(
            f"Translated speech export complete: {langs} language(s), {count} chapter(s)"
        )

    frame._run_background_task(
        f"Translated speech export ({len(request.targets)} language(s))",
        work,
        on_success,
        notify_on_success=True,
        notify_on_error=True,
        notification_category="speech",
    )
