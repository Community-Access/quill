"""Generate Captions (Offline): a file in, timed captions out, on this machine.

Extracted from ``apps/studio.py`` under GATE-11 (extract, never rebaseline). One
concern with two halves that only exist for each other: run the transcription,
then write what came back as ``.srt`` or ``.vtt``.

The property worth protecting is in the name. **Offline** is not a detail of the
implementation, it is the feature: an audio file somebody wants captioned is
frequently something they would not send to a company, and every engine this can
use runs on the listener's own machine. It is disabled in Safe Mode all the same,
because installing or loading a model is still work the listener did not ask for
in a recovery session.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_captions(host: Any) -> None:
    """Transcribe an audio/video file to timed captions on this machine, then
    save them as .srt or .vtt -- a faithful port of QUILL's Tools > Speech >
    Generate Captions (Offline). Disabled in Safe Mode."""
    wx = host._wx
    if bool(getattr(host, "_safe_mode", False)):
        host._announce("Generating captions is disabled in Safe Mode.")
        return
    provider = host._speech_provider()
    installed = host._installed_or_prompt(provider, "Generate Captions")
    if installed is None:
        return
    model_id = host._default_model_id(installed)
    with wx.FileDialog(
        host.frame,
        "Choose an audio or video file to caption",
        wildcard=_wildcard(),
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
    ) as dialog:
        if host._show_modal_dialog(dialog, "Generate Captions") != wx.ID_OK:
            return
        source = Path(dialog.GetPath())

    from quill.core.speech.provider import TranscriptionRequest

    request = TranscriptionRequest(source_path=source, model_id=model_id, output_timestamps=True)

    def _work(progress):
        def _on_progress(fraction: float, message: str) -> None:
            progress(message, int(fraction * 100), 100)

        return provider.transcribe_file(request, _on_progress)  # type: ignore[attr-defined]

    host._run_background_task(
        f"Captioning {source.name}", _work, lambda result: _save_captions(host, result, source)
    )


def _save_captions(host: Any, result: object, source: Path) -> None:
    from quill.core.speech import formatters

    wx = host._wx
    segments = getattr(result, "segments", ()) or ()
    if not segments:
        host._announce("No timed segments were produced, so captions cannot be made.")
        return
    formats = ["SubRip captions (.srt)", "WebVTT captions (.vtt)"]
    with wx.SingleChoiceDialog(
        host.frame, "Caption format:", "Generate Captions", formats
    ) as dialog:
        if host._show_modal_dialog(dialog, "Generate Captions") != wx.ID_OK:
            return
        choice = dialog.GetSelection()
    if choice == 0:
        text, ext = formatters.to_srt(segments), ".srt"
    else:
        text, ext = formatters.to_vtt(segments), ".vtt"
    with wx.FileDialog(
        host.frame,
        "Save captions",
        defaultFile=f"{source.stem}{ext}",
        wildcard="Caption files (*.srt;*.vtt)|*.srt;*.vtt|All files (*.*)|*.*",
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as dialog:
        if host._show_modal_dialog(dialog, "Save captions") != wx.ID_OK:
            return
        target = Path(dialog.GetPath())
    target.write_text(text, encoding="utf-8", newline="\n")
    host._announce(f"Captions saved to {target.name}.")


def _wildcard() -> str:
    """The file filter, read from Audio Studio rather than duplicated.

    One list of playable extensions, in the app that owns it: a second copy here
    would drift the first time a format was added, and the symptom would be a
    file the app can caption not appearing in its own picker.
    """
    from quill.apps.studio import _AUDIO_VIDEO_WILDCARD

    return _AUDIO_VIDEO_WILDCARD
