"""QUILL Audio Studio — the guided audio-production surface.

One studio, three journeys: narrate documents into chaptered speech audio or
an audiobook; combine a folder of recordings into one chaptered master; open
an existing book in the Chapter Workbench (player + chapter surgery + tags).
The first two journeys collect a
:class:`~quill.ui.audio_studio.request.BatchSpeechRequest` and the existing
``quill.ui.batch_speech_runner`` executes it — the Studio is the front door,
not a second pipeline.
"""

from __future__ import annotations

from quill.ui.audio_studio.request import BatchSpeechRequest

__all__ = ["BatchSpeechRequest", "show_audio_studio"]


def show_audio_studio(frame: object) -> BatchSpeechRequest | None:
    """Open the Audio Studio wizard for *frame* (a MainFrame); return the request.

    Wires the wizard to the frame's engine catalog, voice lists, voice preview,
    defaults (global settings overlaid by the folder's project profile), the
    screen-reader announcer, and ``_show_modal_dialog``. The edit journey opens
    the Chapter Workbench directly and returns ``None`` (there is no batch to
    run); cancel also returns ``None``. Imported lazily by the runner so a
    headless import stays wx-free.
    """
    import wx

    from quill.core.i18n import _
    from quill.ui import batch_speech_runner as runner
    from quill.ui.audio_studio.wizard import AudioStudioWizard

    def on_preview(engine: str, voice: str) -> None:
        if voice:
            frame._preview_voice(engine, voice)
        else:
            frame._set_status(str(_("Choose a voice to preview")))

    from quill.ui.audio_studio.wizard import RELOAD_WITH_JOB

    defaults = runner._defaults(frame)
    # Pre-select the journey the user used last so the second run lands
    # on the same first page (Skip to summary stays a 3-keystroke
    # promise). ``audio_studio_last_journey`` is a free-form string, so clamp
    # it to the JOURNEYS set; unknown values fall back to "documents".
    try:
        from quill.ui.audio_studio.request import JOURNEYS

        last_journey = str(getattr(frame.settings, "audio_studio_last_journey", "documents"))
        if last_journey not in JOURNEYS:
            last_journey = "documents"
    except Exception:  # noqa: BLE001 - settings import may be unavailable headless
        last_journey = "documents"
    while True:
        dlg = AudioStudioWizard(
            frame.frame,
            defaults=defaults,
            engine_options=runner._ENGINE_OPTIONS,
            engine_available=runner._engine_available(frame),
            voices_for=runner._voices_for,
            on_preview=on_preview,
            announce_cb=frame._announce,
            initial_journey=last_journey,
        )
        try:
            code = frame._show_modal_dialog(dlg, str(_("QUILL Audio Studio")))
            if code == RELOAD_WITH_JOB and dlg.loaded_job is not None:
                # A .quilljob was loaded: reopen with it as the defaults so
                # every page pre-fills and Skip to summary is three keystrokes.
                defaults = dlg.loaded_job
                continue
            edit_path = dlg.edit_path() if code == wx.ID_OK else None
            request = dlg.result() if code == wx.ID_OK else None
        finally:
            dlg.Destroy()
        break
    if edit_path is not None:
        from quill.ui.audio_studio.chapter_workbench import open_book_in_workbench

        open_book_in_workbench(frame, edit_path)
        return None
    return request
