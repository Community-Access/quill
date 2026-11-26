"""At launch: a recording an unexpected close interrupted, offered back by name (R3, FUX-05).

Extracted from ``main_frame_radio`` under GATE-11. Plain functions taking the
frame as ``host``, the same shape as :mod:`quill.ui.radio.recording_markers`.

What each step promises:

* Files left in the temporary folder are moved home and **named**, not counted.
* A recording whose time has not run out is offered with what was recorded,
  where it is kept, and what Resume and Skip do. Nothing is deleted either way.
* A recording whose time ran out is no longer cleared silently: it is said once
  and kept in Activity, with the part that was recorded.
* A resume that cannot start says so by station, without exception text.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from quill.core.radio import resume_words as words
from quill.core.sound_events import SoundEvent

_log = logging.getLogger(__name__)


def _settings_paths(host: Any) -> tuple[str, str]:
    settings = getattr(host, "_radio_recording_settings", None)
    destination = str(getattr(settings, "destination_root", "") or "")
    if not destination:
        from quill.core.radio.recording import _default_dir

        destination = str(_default_dir())
    return destination, str(getattr(settings, "temp_dir", "") or "")


def _where(host: Any, path: Path | None) -> str:
    if path is None:
        return ""
    destination, temp = _settings_paths(host)
    return words.kept_where(path, destination, temp)


def _keep(sentence: str, station: str, path: Path | None) -> None:
    from quill.ui.outcome_report import keep_outcome

    try:
        keep_outcome("Record", sentence, object_name=station, path=path, partial=True)
    except Exception:  # noqa: BLE001 - keeping the note must never block launch
        _log.debug("could not keep the interrupted-recording note", exc_info=True)


def reconcile_and_offer(host: Any) -> None:
    """Move crash-orphaned temp files home, then offer each interrupted recording."""
    from quill.core.paths import app_data_dir
    from quill.core.radio.recording_resume import (
        load_markers,
        reconcile_temp_strays,
        remaining_minutes,
        within_resume_grace,
    )

    try:
        markers = load_markers(app_data_dir())
    except Exception:  # noqa: BLE001
        markers = []
    try:
        moved = reconcile_temp_strays(host._radio_recording_settings, markers=markers)
    except Exception:  # noqa: BLE001 - reconcile must never block launch
        moved = []
    loose = words.unclaimed(moved, markers)
    if loose:
        destination, _temp = _settings_paths(host)
        home = (
            "your recordings folder"
            if all(words.kept_where(p, destination) == "in your recordings folder" for p in loose)
            else "their recordings folders"
        )
        host._announce(words.moved_sentence(loose, home))

    resumable: list[tuple[Any, int, Path | None]] = []
    for marker in markers:
        if not getattr(marker, "stream_url", ""):
            continue
        part = words.partial_file(marker, moved)
        if not within_resume_grace(marker):
            # The show is over: say once what was cut short, keep it, clear it.
            sentence = words.cut_short_sentence(
                marker, seconds=words.recorded_seconds(marker, part), where=_where(host, part)
            )
            host._announce(sentence)
            _keep(sentence, marker.station_name, part)
            forget(host, marker)
            continue
        resumable.append((marker, remaining_minutes(marker), part))
    if not resumable:
        return
    choice = host._radio_history.recording_resume_choice
    if choice == "never":
        for marker, _left, _part in resumable:
            forget(host, marker)
        return
    if choice == "always":
        for marker, left, _part in resumable:
            start_resume(host, marker, left)
        return
    ask(host, resumable)


def ask(host: Any, resumable: list[tuple[Any, int, Path | None]]) -> None:
    """One dialog for one recording, a batched prompt for several."""
    from quill.ui.radio.resume_recording_dialog import (
        ResumeRecordingDialog,
        ResumeRecordingsBatchDialog,
    )

    if len(resumable) == 1:
        marker, left, part = resumable[0]
        message = words.offer_sentence(
            marker,
            left=left,
            seconds=words.recorded_seconds(marker, part),
            where=_where(host, part),
        )
        result = ResumeRecordingDialog(
            host.frame,
            station_name=marker.station_name or "the stream",
            remaining_minutes=left,
            scheduled_end=marker.scheduled_end,
            message=message,
            announce_cb=host._announce,
        ).show()
    else:
        lines = [
            words.batch_line(m, left=left, seconds=words.recorded_seconds(m, part))
            for m, left, part in resumable
        ]
        result = ResumeRecordingsBatchDialog(
            host.frame, lines=lines, announce_cb=host._announce
        ).show()
    if result is None:
        return  # dismissed: markers stay, offered again while inside the grace window
    action, remember = result
    if remember:
        host._radio_history.recording_resume_choice = "always" if action == "resume" else "never"
        host._save_radio_history()
    for marker, left, _part in resumable:
        if action == "resume":
            start_resume(host, marker, left)
        else:
            forget(host, marker)


def start_resume(host: Any, marker: Any, left: int) -> None:
    """Resume *marker*'s recording for the remaining minutes, as a separate file."""
    from quill.core.speech.ffmpeg import ffmpeg_available

    if not ffmpeg_available():
        host._announce("Cannot resume recording: FFmpeg is not installed.")
        forget(host, marker)
        return
    station_name = marker.station_name or "Recording"
    if not marker.stream_url:
        forget(host, marker)
        return
    # The old marker is superseded by the one the new job writes under its own
    # id; clear it first, by its own key, so the new one is never touched.
    forget(host, marker)
    try:
        host._radio_recorder.start(
            station_name=station_name,
            stream_url=marker.stream_url,
            settings=host._radio_recording_settings,
            duration_minutes=max(1, left),
            filter_graph=host._radio_recording_filter_graph(),
            exact_optilab=host._radio_recording_exact(),
            entry_id=marker.entry_id or "",
        )
    except Exception:  # noqa: BLE001 - a failed resume is announced, not fatal
        _log.warning("could not resume the recording of %s", station_name, exc_info=True)
        host._announce(words.resume_failed_sentence(marker))
        return
    host._announce(
        f"Resuming recording of {station_name} for {max(1, left)} minute(s).",
        sound=SoundEvent.RADIO_RECORDING_STARTED,
    )


def forget(host: Any, marker: Any) -> None:
    """Clear exactly *marker*: never every marker (a legacy one has no job id)."""
    from quill.ui.radio import recording_markers

    recording_markers.clear_marker_of(host, marker)
