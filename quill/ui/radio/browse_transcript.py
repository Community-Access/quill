"""Reading a transcript from a browse row, without playing it.

Split from ``browse_tree_menu`` under GATE-11 (extract, never rebaseline) when
the Podcast Index rows joined the subscribed ones -- and it reads better apart:
that module maps a row to the verbs it offers, and this is one verb's whole
story, from *where the transcript lives* to *what the exported file is called*.

Three shapes behind one menu item, and the third is the new one:

* A **subscribed episode** carries its feed-declared transcript address in its
  node id, so the fetch costs one request and no playback.
* A **YouTube row** costs the resolve playing it would have made, and its
  captions are the transcript. An automatic track is announced *as* automatic.
* A **Podcast Index episode** carries the index's own copy of the tag -- which
  means a transcript is readable for a show **nobody is subscribed to**. That
  is a source neither Earshot nor a feed-only reader has.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import row_actions


def view(dialog: Any, kind: str, args: list[str], station: Any) -> None:
    """View Transcript... on a row, without playing it (QA: the transcript and
    show-notes experience is a high-value target).

    Two shapes behind one menu item: a podcast episode's node id carries its
    feed-declared transcript address directly; a YouTube row costs one resolve
    (the same request playing it would make) to learn its caption track, and
    an automatic track is announced as automatic in the reader's heading.
    """
    if dialog._safe_mode:
        dialog._announce(
            "Transcripts are disabled in Safe Mode. Restart Quill Radio normally to read them."
        )
        return
    dialog._announce("Fetching transcript...")

    def _work(**_kwargs: Any) -> tuple[bool, list]:
        from quill.core.podcasts import transcripts as transcripts_module

        if kind in row_actions.TRANSCRIPT_IN_ID_KINDS:
            # A subscribed episode's id is (transcript, mime); a Podcast Index
            # episode's is (audio, transcript, mime) -- its first field is what
            # plays. Reading from the end keeps one branch for both.
            url = args[-2] if kind == "piepisode" and len(args) > 2 else (args[0] if args else "")
            mime = args[-1] if len(args) > 1 else ""
            return False, transcripts_module.fetch_transcript_cues(url, mime)
        from quill.core.radio.youtube import ensure_and_resolve

        stream = ensure_and_resolve(str(getattr(station, "stream_url", "")))
        if not stream.caption_url:
            return False, []
        cues = transcripts_module.fetch_transcript_cues(stream.caption_url, "application/json")
        return stream.caption_is_automatic, cues

    def _ok(_op: str, result: object) -> None:
        is_automatic, cues = result if isinstance(result, tuple) else (False, [])
        dialog._wx.CallAfter(_open_transcript_reader, dialog, station, cues, is_automatic)

    def _failed(_op: str, error: BaseException) -> None:
        dialog._wx.CallAfter(dialog._announce, f"The transcript could not be fetched. {error}")

    dialog._task_manager.submit(
        "radio-browse-transcript", _work, on_success=_ok, on_failure=_failed
    )


def _transcript_detail(host: Any) -> str:
    """How much scaffolding an exported transcript keeps, per this install.

    Read from the app's own history rather than passed down from the menu, so
    every route into the reader agrees; a window with no frame behind it gets
    the shipped default from ``normalize_detail``.
    """
    frame = getattr(host, "_download_host", None) or host
    return str(getattr(getattr(frame, "_radio_history", None), "transcript_detail", "") or "")


def _open_transcript_reader(dialog: Any, station: Any, cues: object, is_automatic: bool) -> None:
    from quill.ui.transcript_reader import TranscriptReader

    rows = list(cues) if isinstance(cues, list) else []
    if not rows:
        dialog._announce(
            "No transcript could be read for this one. The publisher may not have "
            "provided captions or a transcript file."
        )
        return
    title = str(getattr(station, "display_name", "") or "") or "this recording"
    # No position and no seek: nothing is playing, and jumping a live player
    # to a row of something it is not playing would be worse than not offering it.
    reader = TranscriptReader(
        dialog._win,
        title=title,
        cues=rows,
        position_ms=None,
        seek_to_ms=None,
        announce=dialog._announce,
        show_modal_dialog=getattr(dialog, "_show_modal_dialog", None),
        on_send_to_quill=None,
        is_automatic=is_automatic,
        show_title=str(getattr(station, "source", "") or ""),
        source_url=str(getattr(station, "homepage", "") or ""),
        transcript_detail=_transcript_detail(dialog),
    )
    reader.show()
