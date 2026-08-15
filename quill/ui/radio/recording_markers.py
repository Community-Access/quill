"""The breadcrumb a running recording leaves, so a crash can offer to resume it.

Extracted from ``main_frame_radio`` under GATE-11 (extract, never rebaseline).
Plain functions taking the frame as ``host``, the same shape as the other
``ui/radio`` helper modules, and touching no widget -- it is only here rather
than in core because the marker is written from the frame's view of the
recorder's live state.

The contract is small and worth stating: a marker is written when a recording
starts and cleared when it stops cleanly, so **only a crash or a kill leaves one
behind**. That is what makes the next launch's "resume this recording?" offer
trustworthy rather than a prompt that appears after every ordinary session.

Every failure here is swallowed on purpose. A marker that cannot be written
means no resume offer, which is a small loss; an exception on the path that
starts or finishes a recording is a much larger one.
"""

from __future__ import annotations

from typing import Any


def persist(host: Any, job_id: str = "") -> None:
    """Write one recording's marker from the recorder's live state.

    Keyed by ``job_id`` so several simultaneous recordings each persist their
    own marker instead of clobbering one another.
    """
    from datetime import timedelta

    from quill.core.paths import app_data_dir
    from quill.core.radio.recording_resume import ActiveRecordingMarker, save_marker

    rec = getattr(host, "_radio_recorder", None)
    if rec is None:
        return
    snap = rec.job(job_id) if job_id else None
    if snap is None:
        return
    started = snap.started_at
    minutes = snap.minutes
    if started is None or minutes <= 0:
        return
    marker = ActiveRecordingMarker(
        station_name=snap.station_name,
        stream_url=snap.stream_url,
        temp_path=str(snap.destination or ""),
        output_path=str(snap.final_destination or ""),
        started_at=started.isoformat(),
        scheduled_end=(started + timedelta(minutes=minutes)).isoformat(),
        duration_minutes=minutes,
        entry_id=snap.entry_id,
        job_id=snap.job_id,
    )
    try:
        save_marker(app_data_dir(), marker)
    except Exception:  # noqa: BLE001 - a marker we cannot persist just means no resume offer
        pass


def clear(host: Any, job_id: str | None = None) -> None:
    """Remove one recording's marker by job id, or every marker when *job_id*
    is ``None`` (the clean-stop and clean-close path)."""
    from quill.core.paths import app_data_dir
    from quill.core.radio.recording_resume import clear_all_markers, clear_marker

    del host  # signature parity with persist(); nothing on the frame is needed
    try:
        if job_id is None:
            clear_all_markers(app_data_dir())
        else:
            clear_marker(app_data_dir(), job_id)
    except Exception:  # noqa: BLE001 - best-effort
        pass
