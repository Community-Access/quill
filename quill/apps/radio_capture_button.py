"""What the one capture button on the player is, and what it does.

Split out of ``quill/apps/radio.py`` under GATE-11 (extract, never rebaseline)
the day the button stopped meaning one thing. It used to be Record, always,
which meant that while a podcast episode played the player offered to *record*
a file -- an hour of ffmpeg transcoding in real time to obtain a worse copy of
something the publisher was already handing out (reported 2026-08-18: "when
playing a podcast the record button should not be available but perhaps change
it to a download button?").

The decision itself is wx-free and lives in
:func:`quill.core.radio.downloadable.capture_button`; this is the wiring that
reads the player's state, asks it, and applies the answer. Keeping the two
apart is what lets the four states -- Record, Stop Recording, Download, Remove
Download -- be tested without a window.

The button dispatches on that state rather than always toggling recording, so
it can never say Download and then start recording.
"""

from __future__ import annotations

from typing import Any

from quill.ui.dialog_contract import set_accessible_name


def download_group(app: Any) -> str:
    """The show a playing podcast episode belongs to, or "".

    The same folder name the browse tree files a single episode under, so
    an episode downloaded from the player and one downloaded from the tree
    land beside each other instead of in two different places.
    """
    station = app._radio_controller.state.station
    if station is None or not bool(getattr(station, "is_recording", False)):
        return ""
    feed = str(getattr(station, "homepage", "") or "")
    if not feed:
        return ""
    try:
        from quill.core.paths import app_data_dir
        from quill.core.radio.podcast_follow import show_facts_for_feed

        _unheard, _episodes, title = show_facts_for_feed(app_data_dir(), feed)
        return str(title or "")
    except Exception:  # noqa: BLE001 - a filing hint must never break the button
        return ""


def state_of(app: Any):
    """What the capture button should be right now (wx-free decision)."""
    from quill.core.paths import app_data_dir
    from quill.core.radio import downloadable, downloaded_media

    station = app._radio_controller.state.station
    recording = bool(getattr(app._radio_recorder, "is_recording", False))
    downloaded = False
    if station is not None and bool(getattr(station, "is_recording", False)):
        downloaded = downloaded_media.is_downloaded(
            app_data_dir(), station, group=download_group(app)
        )
    return downloadable.capture_button(station, recording_active=recording, downloaded=downloaded)


def act(app: Any) -> None:
    """Do whatever the capture button currently says it will do.

    Dispatched on the state rather than always toggling recording, so the
    button cannot say Download and then start an hour of ffmpeg.
    """
    from quill.core.paths import app_data_dir
    from quill.core.radio import downloadable, downloaded_media
    from quill.ui.radio import download_command

    state = state_of(app)
    station = app._radio_controller.state.station
    if state.action in (downloadable.CAPTURE_RECORD, downloadable.CAPTURE_STOP_RECORDING):
        app.radio_record_toggle()
        return
    if station is None:  # cannot happen from the button; cheap to be sure
        return
    group = download_group(app)
    if state.action == downloadable.CAPTURE_REMOVE_DOWNLOAD:
        app._announce(downloaded_media.remove_download(app_data_dir(), station, group=group))
    else:
        download_command.download_station(app, station, group=group)
    refresh(app)


def refresh(app: Any) -> None:
    """Keep the capture button honest about what it would capture.

    It is "Stop Recording" while a recording runs (#1152 feedback), and
    **Download** rather than Record while a podcast episode or other
    finished recording is playing: recording a file that is already a file
    means transcoding it in real time to get a worse copy of something the
    publisher is handing out (reported 2026-08-18). Once that file is on
    disk it becomes Remove Download, the same verb the row's context menu
    offers, so the two surfaces never disagree about what exists.
    """
    button = getattr(app, "_record_btn", None)
    if button is None:
        return
    state = state_of(app)
    if button.GetLabel() != state.label:
        button.SetLabel(state.label)
        set_accessible_name(button, state.name)
