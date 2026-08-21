"""Audio Health: ask whether this installation can play and record.

``media_preflight`` *tells* you, once, at launch, when something is missing.
This is the other direction: somebody whose station will not play, or who is
about to leave a two-hour scheduled recording running on a machine they are
walking away from, wants to ask. At launch nothing was wrong, so the notice --
correctly -- said nothing, and there was no way to put the question.

The report itself is pure (:mod:`quill.core.radio.audio_health`); this module
is only the half that knows where the live facts live and how to draw a list.
It gathers those facts with the *same* predicates the engine selection uses --
``media_preflight.current_health`` rather than a second, subtly different probe
-- for the reason that module's own docstring gives: a health report that asks a
different question from the code it describes eventually describes a machine
nobody has.

**Nothing here probes.** No test tone, no device opened, no file written. The
window can be opened during a recording without touching it, which is exactly
when somebody is most likely to want it.

House ListBox pattern, matching Station Catalog Status: one whole spoken
sentence per row, read-only rows, and a Close button bound through the dialog
contract.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from quill.core.radio.audio_health import (
    AudioHealthFacts,
    HealthRow,
    build_report,
    headline,
)
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

_log = logging.getLogger(__name__)

TITLE = "Audio Health"


def _folder_state(path: str) -> tuple[bool, bool]:
    """``(exists, writable)`` for the recordings folder, without writing to it.

    ``os.access`` rather than a probe file on purpose: creating and deleting a
    temp file in somebody's recordings folder to find out whether we could is
    the sort of "diagnostic" that shows up later as a mystery file, and it would
    be doing it while a recording may be writing into the same directory.

    An empty path means "the default folder", which the recorder creates on
    demand, so it is reported as fine rather than as missing -- warning about a
    folder that does not exist *yet* and never needed to would be a false alarm
    on a fresh install that has recorded nothing.
    """
    if not path:
        return True, True
    try:
        if not os.path.isdir(path):
            return False, False
        return True, os.access(path, os.W_OK)
    except OSError:
        # An unreachable network share raises rather than answering. That is a
        # real problem for a recording, so report it as one.
        return False, False


def _enhancement_summary(
    bass: float, mid: float, treble: float, compressor: bool, night: bool, channel: str
) -> str:
    """What the enhancements are set to, named rather than numbered.

    "Bass +4 dB" is a fact somebody can act on; "eq_bass_db=4.0" is a variable
    name read aloud. Parts are listed only when they are doing something, so a
    setup with one adjustment reads as one adjustment.
    """
    parts: list[str] = []
    for label, value in (("Bass", bass), ("Mid", mid), ("Treble", treble)):
        if value:
            parts.append(f"{label} {value:+.0f} dB")
    if compressor:
        parts.append("compressor on")
    if night:
        parts.append("night mode on")
    if channel and channel != "stereo":
        parts.append(f"channel mode {channel}")
    return ", ".join(parts)


def _has_own_enhancements(host: Any, station: Any) -> bool:
    """True when *station* carries its own remembered Sound Enhancements.

    Best-effort and quiet about it: the per-station store has moved once
    already, and a report that raised because it could not find it would fail
    the whole window over the least important row on it.
    """
    favorites = getattr(host, "_radio_favorites", None)
    if favorites is None or station is None:
        return False
    try:
        entry = favorites.find(station)
    except Exception:  # noqa: BLE001
        return False
    if entry is None:
        return False
    return any(
        getattr(entry, name, None) not in (None, "")
        for name in ("eq_bass_db", "eq_mid_db", "eq_treble_db", "compressor_enabled")
    )


def _gather(host: Any) -> AudioHealthFacts:
    """Read the live app into the report's input record.

    Every read is defensive. This window exists to be opened when something is
    already wrong, so a half-initialised host must produce a report with a gap
    in it rather than an exception instead of a report.
    """
    from quill.ui.radio import media_preflight

    health = media_preflight.current_health()

    controller = getattr(host, "_radio_controller", None)
    engine = getattr(controller, "_engine", None) if controller is not None else None
    active = ""
    if engine is not None:
        name = type(engine).__name__.lower()
        if "mpv" in name:
            active = "mpv"
        elif "spotify" in name:
            active = "spotify"
        else:
            active = "wx"

    history = getattr(host, "_radio_history", None)
    preference = str(getattr(history, "playback_engine", "auto") or "auto")
    device = str(getattr(history, "output_device", "") or "")

    device_available = True
    if device:
        try:
            from quill.ui.radio.mpv_radio_engine import list_audio_devices

            names = [str(name) for name, _description in list_audio_devices()]
            # Only contradict the setting when we got a real list back: an empty
            # answer means the question could not be asked, not that the device
            # is gone, and reporting "your headset is missing" on the strength of
            # a failed enumeration would be a confident wrong answer.
            if names:
                device_available = device in names
        except Exception:  # noqa: BLE001 - a probe must never be the failure
            _log.exception("output device enumeration failed; not contradicting the setting")

    settings = getattr(host, "_radio_recording_settings", None)
    folder = str(getattr(settings, "destination_root", "") or "")
    exists, writable = _folder_state(folder)
    recorder = getattr(host, "_radio_recorder", None)

    # Whether the audio is being changed at all, asked with the same predicate
    # the relay itself uses. Anything else would eventually disagree with what
    # the listener is hearing, which is the one thing this window must not do.
    summary = ""
    active_enhancements = False
    per_station = False
    if history is not None:
        try:
            from quill.core.audio_enhance import is_enhancement_active

            bass = float(getattr(history, "eq_bass_db", 0.0) or 0.0)
            mid = float(getattr(history, "eq_mid_db", 0.0) or 0.0)
            treble = float(getattr(history, "eq_treble_db", 0.0) or 0.0)
            compressor = bool(getattr(history, "compressor_enabled", False))
            night = bool(getattr(history, "night_mode_enabled", False))
            channel = str(getattr(history, "channel_mode", "stereo") or "stereo")
            active_enhancements = is_enhancement_active(
                bass,
                mid,
                treble,
                compressor_enabled=compressor,
                channel_mode=channel,
                night_mode_enabled=night,
            )
            summary = _enhancement_summary(bass, mid, treble, compressor, night, channel)
            # A station with its own remembered settings is the case people
            # forget they set, and then hear on one station and not another.
            station = getattr(getattr(host, "_radio_controller", None), "state", None)
            current = getattr(station, "station", None) if station is not None else None
            per_station = bool(current is not None and _has_own_enhancements(host, current))
        except Exception:  # noqa: BLE001
            _log.exception("sound-enhancement summary failed; reporting it as unknown")

    optilab = False
    try:
        from quill.core.optilab_adapter import available as optilab_available

        optilab = bool(optilab_available())
    except Exception:  # noqa: BLE001 - an absent adapter is the ordinary case
        optilab = False

    return AudioHealthFacts(
        active_engine=active,
        engine_preference=preference,
        ffmpeg_present=health.ffmpeg,
        mpv_present=health.mpv,
        output_device=device,
        output_device_available=device_available,
        enhancements_active=active_enhancements,
        enhancements_summary=summary,
        enhancements_per_station=per_station,
        optilab_available=optilab,
        recording_folder=folder,
        recording_folder_exists=exists,
        recording_folder_writable=writable,
        active_recordings=int(getattr(recorder, "active_count", 0) or 0),
    )


def _rows(host: Any) -> tuple[str, list[HealthRow]]:
    report = build_report(_gather(host))
    return headline(report), report


def show_audio_health(host: Any) -> None:
    """Open the Audio Health window. Modal, house pattern."""
    wx = host._wx

    line, report = _rows(host)
    dialog = wx.Dialog(host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetSize(wx.Size(700, 460))
    root = wx.BoxSizer(wx.VERTICAL)

    summary_label = wx.StaticText(dialog, label=line)
    root.Add(summary_label, 0, wx.ALL, 8)
    root.Add(
        wx.StaticText(dialog, label="&What the radio is using right now:"), 0, wx.LEFT | wx.RIGHT, 8
    )
    listbox = wx.ListBox(dialog, choices=[row.spoken() for row in report], style=wx.LB_SINGLE)
    listbox.SetName("Each part of the audio chain, and what it means when something is missing")
    root.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)

    row_sizer = wx.BoxSizer(wx.HORIZONTAL)
    refresh_btn = wx.Button(dialog, label="&Check Again")
    refresh_btn.SetName("Re-read every row, after plugging in a device or reinstalling a tool")
    ffmpeg_btn = wx.Button(dialog, label="&Get FFmpeg...")
    mpv_btn = wx.Button(dialog, label="Get &mpv...")
    mpv_btn.SetName("Download the mpv playback engine, which this installation is missing")
    close_btn = wx.Button(dialog, wx.ID_CLOSE, label="C&lose")
    for button in (refresh_btn, ffmpeg_btn, mpv_btn, close_btn):
        row_sizer.Add(button, 0, wx.RIGHT, 6)
    root.Add(row_sizer, 0, wx.ALL, 8)
    apply_modal_ids(dialog, affirmative_id=close_btn.GetId(), escape_id=close_btn.GetId())
    dialog.SetSizer(root)

    # Each Get button is offered only when it would do something. A button that
    # downloads what you already have teaches people to press buttons and see
    # what happens, which is the opposite of what this window is for.
    _MPV_ROW = "mpv playback engine"
    ffmpeg_btn.Enable(any(row.label == "FFmpeg" and row.severity != "ok" for row in report))
    mpv_btn.Enable(any(row.label == _MPV_ROW and row.severity != "ok" for row in report))

    def _refresh(_event: Any) -> None:
        new_line, new_report = _rows(host)
        listbox.Set([entry.spoken() for entry in new_report])
        summary_label.SetLabel(new_line)
        ffmpeg_btn.Enable(
            any(entry.label == "FFmpeg" and entry.severity != "ok" for entry in new_report)
        )
        mpv_btn.Enable(
            any(entry.label == _MPV_ROW and entry.severity != "ok" for entry in new_report)
        )
        if listbox.GetCount():
            listbox.SetSelection(0)
        # Speak the headline, because the visible change may be a row further
        # down the list than the cursor and a silent button is one that looks
        # broken.
        host._announce(new_line)

    def _get_ffmpeg(_event: Any) -> None:
        downloader = getattr(host, "download_ffmpeg_component", None)
        if downloader is None:
            host._announce("This build has no FFmpeg downloader.")
            return
        dialog.EndModal(wx.ID_CLOSE)
        downloader()

    def _get_mpv(_event: Any) -> None:
        downloader = getattr(host, "download_mpv_component", None)
        if downloader is None:
            host._announce("This build has no mpv downloader.")
            return
        dialog.EndModal(wx.ID_CLOSE)
        downloader()

    refresh_btn.Bind(wx.EVT_BUTTON, _refresh)
    ffmpeg_btn.Bind(wx.EVT_BUTTON, _get_ffmpeg)
    mpv_btn.Bind(wx.EVT_BUTTON, _get_mpv)
    close_btn.Bind(wx.EVT_BUTTON, lambda _e: dialog.EndModal(wx.ID_CLOSE))
    apply_listbox_activation(listbox, lambda _e: None)
    if listbox.GetCount():
        listbox.SetSelection(0)
    wx.CallAfter(listbox.SetFocus)
    try:
        host._show_modal_dialog(dialog, TITLE)
    finally:
        dialog.Destroy()
