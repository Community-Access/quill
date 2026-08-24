"""Quill Radio's Transcript command: read what a video says.

Every YouTube resolve has always answered with the video's caption track
alongside its audio address, and Quill Radio has always thrown that away. This
picks it up and opens the shared reader
(:mod:`quill.ui.transcript_reader`) -- the same window Quill Cast opens on a
podcast episode, deliberately, because two transcript readers would drift apart
the day after the second one was written.

Same shape as :mod:`quill.ui.radio.bounded_playback_ui`, which owns the rest of
the "this thing has a timeline" commands: plain functions taking the frame as
``host``.

The refusals matter as much as the feature, and each says why rather than doing
nothing:

* A **live** stream has no transcript to fetch and no timeline to follow.
* A video whose uploader published **no captions** is an ordinary thing, not a
  fault, and is reported as such.
* **Safe Mode** refuses out loud, because fetching a caption file is a network
  request.
* An **automatic** caption track is announced as automatic, in the reader's own
  heading. A machine transcript presented as a human one is a confident wrong
  answer.
"""

from __future__ import annotations

from typing import Any

#: yt-dlp hands back YouTube's `json3` caption format, which the shared cue
#: parser understands. Passed explicitly rather than sniffed, because the URL
#: carries its format in a query parameter that is easy to misread.
_CAPTION_TYPE = "application/json"


def open_transcript(host: Any) -> None:
    """Fetch the playing video's captions and open the reader."""
    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        return
    if getattr(host, "_safe_mode", False):
        host._announce("Transcripts are disabled in Safe Mode. Restart QUILL normally to use them.")
        return

    url, is_automatic = controller.caption_track()
    if not url:
        if not controller.is_seekable():
            host._announce("This is a live stream, so there is no transcript to read.")
        else:
            host._announce("This video has no captions published, so there is no transcript.")
        return

    task_manager = getattr(host, "_task_manager", None)
    if task_manager is None:
        host._announce("Transcripts are unavailable right now.")
        return

    host._announce("Fetching transcript...")

    def _work(**_kwargs: object) -> list:
        from quill.core.podcasts import transcripts as transcripts_module

        return transcripts_module.fetch_transcript_cues(url, _CAPTION_TYPE)

    def _ok(_op: str, cues: object) -> None:
        host._wx.CallAfter(_open_reader, host, controller, cues, is_automatic)

    def _failed(_op: str, error: object) -> None:
        host._wx.CallAfter(host._announce, f"The transcript could not be fetched. {error}")

    task_manager.submit("radio-transcript", _work, on_success=_ok, on_failure=_failed)


def _open_reader(host: Any, controller: Any, cues: object, is_automatic: bool) -> None:
    from quill.ui.transcript_reader import TranscriptReader

    rows = list(cues) if isinstance(cues, list) else []
    if not rows:
        host._announce("That transcript could not be read. It may be in a form Quill cannot parse.")
        return
    station = getattr(getattr(controller, "state", None), "station", None)
    title = getattr(station, "display_name", "") or "this video"
    # Follow and jump are offered only where there is a timeline to move along.
    seekable = bool(controller.is_seekable())
    reader = TranscriptReader(
        host.frame,
        title=title,
        cues=rows,
        position_ms=controller.position_ms if seekable else None,
        seek_to_ms=(lambda ms: bool(controller.seek_to(ms))) if seekable else None,
        announce=host._announce,
        show_modal_dialog=getattr(host, "_show_modal_dialog", None),
        on_send_to_quill=getattr(host, "_radio_send_text_to_quill", None),
        is_automatic=is_automatic,
        show_title=str(getattr(station, "source", "") or ""),
        source_url=str(getattr(station, "homepage", "") or ""),
        transcript_detail=str(
            getattr(getattr(host, "_radio_history", None), "transcript_detail", "") or ""
        ),
    )
    reader.show()


def open_audio_tracks(host: Any) -> None:
    """**Playback > Audio and Described Audio...**

    The feature this application exists for, given its own command rather than
    being buried: a video's *described* audio track narrates what is happening
    on screen, and almost no desktop player surfaces it in a form a blind
    listener can actually choose from.

    Opens even when there is no described track, because "this video has one
    audio track, English -- no described audio was published" is a true and
    useful answer, and a greyed-out menu item is not.
    """
    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        return
    tracks = controller.audio_tracks()
    if not tracks:
        if not controller.is_seekable():
            host._announce("This is a live stream, so it has no described audio track to choose.")
        else:
            from quill.core.radio.audio_tracks import summarise

            host._announce(summarise([]))
        return

    from quill.ui.radio.audio_track_dialog import AudioTrackDialog

    dialog = AudioTrackDialog(
        host.frame,
        tracks=tracks,
        current=controller.selected_audio_track(),
        show_modal_dialog=getattr(host, "_show_modal_dialog", None),
        announce=host._announce,
        play_track=controller.play_audio_track,
    )
    dialog.show()


def play_described_audio(host: Any) -> None:
    """Switch straight to the described track, or say why there is none.

    The one-keystroke form of the command above, for somebody who always wants
    description and should not have to walk a list to get it.
    """
    from quill.core.radio.audio_tracks import described_track, summarise

    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        return
    tracks = controller.audio_tracks()
    described = described_track(list(tracks))
    if described is None:
        host._announce(summarise(list(tracks)))
        return
    if controller.play_audio_track(described):
        host._announce("Playing the described audio track.")
    else:
        host._announce("The described audio track could not be played.")
