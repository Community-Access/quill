"""Everything the Podcast Manager does with a transcript.

Moved out of ``manager_phase4`` when **Read Transcript...** arrived: that module
was exactly at its GATE-11 ceiling, and the four transcript commands were already
a self-contained group with one shared fetch. Plain functions taking the manager
as ``host``, like the other extracted UI helpers.

The three commands, and why there are three rather than one:

* **Read Transcript...** opens the shared reader
  (:mod:`quill.ui.transcript_reader`) with **timed cues**, so it can follow the
  audio, take you to the moment a line was spoken, and say where a search hit
  falls. This is the one that was missing.
* **Open Transcript in Editor** hands the flat text to QUILL as a document. Kept
  exactly as it was -- it is a different thing to want, and the reader offers it
  as a button rather than replacing it.
* **Save Transcript As** writes it to a file. Also unchanged here; the reader has
  its own Save that keeps the timings.

One fetch path serves all three (:func:`fetch_then`), on the task manager and
never on the UI thread, with the feed's own authentication where the feed needs
it and a Safe Mode refusal. A fetched transcript is cached on the way past, so
Search Everywhere finds it later with no second request.
"""

from __future__ import annotations

from typing import Any


def read_transcript(host: Any, show: Any, episode: Any) -> None:
    """Open the episode's transcript in the shared reader.

    Cues rather than text, because the whole point of the reader is the timings.
    The player is handed over as two callables, so the reader never learns what a
    podcast controller is.
    """
    from quill.core.podcasts import feed_auth
    from quill.core.podcasts import transcripts as transcripts_module

    if not getattr(episode, "transcript_url", ""):
        # Said plainly rather than offered and then refused. Publishing a
        # transcript is optional, and an episode without one is ordinary.
        host._announce(
            f"{episode.title} has no published transcript. "
            "You can transcribe the downloaded audio in QUILL instead."
        )
        return
    if host._task_manager is None:
        host._announce("Transcript fetching is unavailable right now.")
        return

    host._announce("Fetching transcript...")
    auth_header = feed_auth.auth_header_for_url(show, episode.transcript_url)

    def _work(**_kwargs: object) -> list:
        cues = transcripts_module.fetch_transcript_cues(
            episode.transcript_url,
            episode.transcript_type,
            safe_mode=host._safe_mode,
            auth_header=auth_header,
        )
        if cues:
            # Cache the text form on the way past, so Search Everywhere finds
            # this episode later without a second request.
            transcripts_module.save_cached_transcript(
                show.id, episode.guid, transcripts_module.cues_to_text(cues)
            )
        return cues

    def _ok(_op: str, cues: object) -> None:
        host._wx.CallAfter(_open_reader, host, episode, cues)

    def _failed(_op: str, error: object) -> None:
        host._wx.CallAfter(host._announce, f"Transcript failed: {error}")

    host._task_manager.submit("podcast-transcript-cues", _work, on_success=_ok, on_failure=_failed)


def _open_reader(host: Any, episode: Any, cues: object) -> None:
    from quill.ui.transcript_reader import TranscriptReader

    rows = list(cues) if isinstance(cues, list) else []
    if not rows:
        host._announce(
            f"{episode.title}'s transcript could not be read. "
            "It may be in a form Quill does not understand yet."
        )
        return
    controller = getattr(host, "_controller", None)
    playing = _is_playing(controller, episode)
    reader = TranscriptReader(
        host.dialog,
        title=episode.title,
        cues=rows,
        # Following and jumping are offered only while *this* episode is the one
        # playing. Seeking a different episode to a line in this transcript would
        # be worse than not offering it.
        position_ms=controller.position_ms if (controller is not None and playing) else None,
        seek_to_ms=(lambda ms: bool(controller.seek_to(ms))) if playing else None,
        announce=host._announce,
        show_modal_dialog=getattr(host, "_show_modal_dialog", None),
        on_send_to_quill=getattr(host, "_on_send_show_notes", None),
    )
    reader.show()


def _is_playing(controller: Any, episode: Any) -> bool:
    """Whether *episode* is the one currently playing."""
    if controller is None:
        return False
    state = getattr(controller, "state", None)
    return bool(state is not None and getattr(state, "episode_guid", "") == episode.guid)


# -- the two commands that moved here unchanged ---------------------------------


def save_transcript(host: Any, show: Any, episode: Any) -> None:
    """Write the episode's transcript to a file the listener chooses."""
    wx = host._wx
    with wx.FileDialog(  # dialog_button_contract: exempt
        host.dialog,
        "Save Transcript As",
        defaultFile=f"{episode.title}.txt",
        wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*",
        style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
    ) as dialog:
        if dialog.ShowModal() != wx.ID_OK:
            return
        target = dialog.GetPath()
    fetch_then(host, show, episode, lambda text: _write(host, target, text))


def _write(host: Any, target: str, text: str) -> None:
    from pathlib import Path

    try:
        Path(target).write_text(text, encoding="utf-8", newline="\n")
    except OSError as error:
        host._announce(f"Could not save the transcript: {error}")
        return
    host._announce(f"Transcript saved to {Path(target).name}")


def open_in_editor(host: Any, show: Any, episode: Any) -> None:
    """Hand the transcript to QUILL as a document."""
    send = host._on_send_show_notes
    if send is None:
        host._announce("Opening in the editor is not available here.")
        return
    fetch_then(host, show, episode, send)


def fetch_then(host: Any, show: Any, episode: Any, consume: object) -> None:
    """Fetch the transcript as text, off the UI thread, then hand it to *consume*."""
    from quill.core.podcasts import feed_auth
    from quill.core.podcasts import transcripts as transcripts_module

    if host._task_manager is None:
        host._announce("Transcript fetching is unavailable right now.")
        return
    host._announce("Fetching transcript...")
    auth_header = feed_auth.auth_header_for_url(show, episode.transcript_url)

    def _do_fetch(**_kwargs: object) -> str:
        text = transcripts_module.fetch_and_parse_transcript(
            episode.transcript_url,
            episode.transcript_type,
            safe_mode=host._safe_mode,
            auth_header=auth_header,
        )
        if text:
            # Cache so Search Everywhere can search it with no re-fetch.
            transcripts_module.save_cached_transcript(show.id, episode.guid, text)
        return text

    def _on_success(_op: str, text: str) -> None:
        host._wx.CallAfter(consume, text)

    def _on_failure(_op: str, error: object) -> None:
        host._wx.CallAfter(host._announce, f"Transcript failed: {error}")

    host._task_manager.submit(
        "podcast-transcript", _do_fetch, on_success=_on_success, on_failure=_on_failure
    )
