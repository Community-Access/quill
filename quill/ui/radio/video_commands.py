"""Show Video, Captions, Snapshot, Video Information -- and every refusal.

The commands behind the Video Window. Plain functions taking the app as ``host``,
the same shape as :mod:`quill.ui.radio.bounded_playback_ui`, which owns the rest
of the "this thing has a timeline" commands.

**Section 508's 503.4 is what shapes the menu**, and reading it as a design
instruction rather than a checkbox gets a better menu for free: if software plays
video with synchronised audio it must provide user controls for **captions** and
for **audio description**, at the same menu level as the controls for volume.
That is why Captions and Audio and Described Audio are Playback menu items beside
Volume, and not buried in Preferences or hidden on a toolbar.

The rules the refusals follow, which matter more than the happy path:

* **Nothing here is ever greyed out.** A live stream, an audio-only station, a
  video with no captions -- each says *why* rather than doing nothing, because a
  disabled item teaches nothing and an item that explains itself teaches the
  listener something true about what they are playing.
* **Hiding the picture is always one keystroke, from anywhere.** Somebody who
  needs the image gone -- light sensitivity, a migraine trigger, an unpleasant
  surprise -- must not have to find the right window first.
* **Video never starts on its own.** The default is audio-only and stays that
  way; the picture appears when it is asked for, which is also the honest answer
  to a photosensitivity requirement that cannot be met by inspecting a stream.
"""

from __future__ import annotations

from typing import Any

NO_VIDEO = "This station has no video."
NEEDS_MPV = "Video needs the mpv playback engine (the default -- see Preferences)."
HIDDEN = "Video hidden. Audio is still playing."


def _engine(host: Any) -> Any:
    """The mpv engine, or ``None`` when the classic backend is in use."""
    controller = getattr(host, "_radio_controller", None)
    if controller is None:
        return None
    engine = getattr(controller, "_engine", None)
    return engine if hasattr(engine, "attach_video") else None


def _stream(host: Any) -> Any:
    controller = getattr(host, "_radio_controller", None)
    return getattr(controller, "_youtube_stream", None) if controller is not None else None


def toggle_video(host: Any) -> None:
    """**Show Video** (Ctrl+Shift+V). Show the picture, or take it away."""
    window = getattr(host, "_video_window", None)
    if window is not None:
        hide_video(host)
        return

    engine = _engine(host)
    if engine is None:
        host._announce(NEEDS_MPV)
        return
    stream = _stream(host)
    video_url = str(getattr(stream, "video_url", "") or "") if stream is not None else ""
    if stream is None:
        host._announce(NO_VIDEO)
        return

    from quill.ui.radio.video_window import VideoWindow

    title = str(getattr(stream, "title", "") or "")
    window = VideoWindow(
        host.frame,
        title=title,
        announce=host._announce,
        on_closed=lambda: _window_closed(host),
    )
    host._video_window = window
    window.show()
    install_window_keys(host, window)

    handle = window.handle()
    if handle is None or not engine.attach_video(handle):
        host._announce("The picture could not be shown on this system. Audio is unaffected.")
        _forget_window(host)
        window.close()
        return
    if video_url:
        # YouTube serves picture and sound separately: the video is what mpv
        # loads and the audio rides alongside it, synchronised by mpv itself
        # rather than merged into a file first.
        engine.set_audio_file(str(getattr(stream, "stream_url", "") or ""))
    _apply_captions(host, engine, first_time=True)
    _apply_brightness(host, engine)
    size = engine.video_size() or (
        int(getattr(stream, "video_width", 0) or 0),
        int(getattr(stream, "video_height", 0) or 0),
    )
    window.set_status(_status_text(host, stream))
    if size and size[0] and size[1]:
        window.resize_to(*size)
        host._announce(f"Video shown, {size[0]} by {size[1]}.")
    else:
        host._announce("Video shown.")


def hide_video(host: Any) -> None:
    """Take the picture away. The audio does not pause, stutter or restart.

    The window is forgotten *before* it is closed, so the close event's own
    handler (:func:`_window_closed`) sees the cleanup already done and does not
    say "Video hidden" a second time.
    """
    window = getattr(host, "_video_window", None)
    engine = _engine(host)
    if engine is not None:
        engine.attach_video(None)
    _forget_window(host)
    if window is not None:
        window.close()
    host._announce(HIDDEN)


def _forget_window(host: Any) -> None:
    host._video_window = None


def _window_closed(host: Any) -> None:
    """The window went away by the listener's own hand -- Alt+F4, Escape, the X.

    This used to only forget the window, which left **mpv still drawing into a
    destroyed handle**: the engine was told to attach and never told to let go,
    so the next Show Video attached a second surface on top of a dead one. Every
    route out of the picture must detach, so the one route this module does not
    control detaches here.

    Returns immediately when :func:`hide_video` has already cleaned up, which is
    what stops the announcement being made twice for one gesture.
    """
    if getattr(host, "_video_window", None) is None:
        return
    engine = _engine(host)
    if engine is not None:
        engine.attach_video(None)
    _forget_window(host)
    host._announce(HIDDEN)


def close_for_stop(host: Any) -> None:
    """Close the window because playback stopped. Silent: the stop already spoke."""
    window = getattr(host, "_video_window", None)
    if window is None:
        return
    engine = _engine(host)
    if engine is not None:
        engine.attach_video(None)
    _forget_window(host)
    window.close()


#: The keys the Video Window carries itself. Every one of them is a menu item on
#: the app frame -- and a menu accelerator only fires for the frame that owns the
#: menu bar, so standing in the Video Window none of them existed. The reported
#: symptom was the one that matters most: "Ctrl+Shift+V shows the video window
#: but pressing the key does not close it" (2026-08-23). The window advertised a
#: transcript key in its own accessible description that could not be pressed
#: either.
#:
#: Ctrl+W and Ctrl+F4 ride along because this is a window and that is how the
#: rest of Quill Radio's windows close.
VIDEO_WINDOW_KEYS: tuple[tuple[str, str], ...] = (
    ("Ctrl+Shift+V", "hide"),
    ("Ctrl+W", "hide"),
    ("Ctrl+F4", "hide"),
    ("Ctrl+Shift+K", "captions"),
    ("Ctrl+Shift+Alt+T", "caption_settings"),
    ("Ctrl+Shift+I", "information"),
    ("Ctrl+Shift+Alt+H", "snapshot"),
    ("Ctrl+Shift+T", "transcript"),
)


def _window_verb(host: Any, verb: str) -> None:
    if verb == "hide":
        hide_video(host)
    elif verb == "captions":
        toggle_captions(host)
    elif verb == "caption_settings":
        caption_settings(host)
    elif verb == "information":
        video_information(host)
    elif verb == "snapshot":
        take_snapshot(host)
    elif verb == "transcript":
        from quill.ui.radio import transcript_command

        transcript_command.open_transcript(host)


def install_window_keys(host: Any, window: Any) -> int:
    """Give the Video Window its own keys, plus the whole transport. Count back.

    The transport rides along through the shared installer, so pausing, seeking
    and chapters work from the picture exactly as they do from every other
    window -- and :func:`quill.ui.radio.transport_keys.install` replaces the
    accelerator table rather than merging, which is why these entries are handed
    to it rather than set separately.
    """
    import wx

    from quill.ui.radio import transport_keys

    frame = getattr(window, "frame", None)
    if frame is None:
        return 0
    entries, refs = [], []
    for key, verb in VIDEO_WINDOW_KEYS:
        command_id = wx.NewIdRef()
        entry = wx.AcceleratorEntry(cmd=int(command_id))
        try:
            parsed = bool(entry.FromString("	" + key)) and bool(entry.GetKeyCode())
        except Exception:  # noqa: BLE001 - an unparsable key is a skipped key
            parsed = False
        if not parsed:
            continue
        entries.append(entry)
        refs.append(command_id)
        frame.Bind(wx.EVT_MENU, lambda _e, v=verb: _window_verb(host, v), id=int(command_id))
    # Pinned: wx frees an unreferenced NewIdRef, and a freed id is an
    # accelerator that fires nothing (the same hazard transport_keys names).
    frame._video_key_refs = refs
    transport_keys.install(frame, host, extra_entries=entries)
    return len(entries)


# -- captions -------------------------------------------------------------------


def toggle_captions(host: Any) -> None:
    """**Captions** (Ctrl+Shift+K). On, off, honest -- and *readable*.

    Captions used to mean one thing: mpv drawing text into the picture. That is
    pixels, so it was unreadable by a screen reader, unreachable by a braille
    display, and invisible to anyone listening without the Video Window open --
    which is most people here. Turning captions on and finding nothing to read
    is what was reported (2026-08-23).

    So this now opens the **Captions window** as well: the same caption track,
    as text you can arrow through, at the size Caption Settings already sets.
    The picture keeps its own captions when the picture is showing -- the two
    are the same track, and nobody has to choose.
    """
    if getattr(host, "_captions_window", None) is not None:
        _captions_off(host)
        return
    controller = getattr(host, "_radio_controller", None) or getattr(host, "_controller", None)
    url, automatic = controller.caption_track() if controller is not None else ("", False)
    if not url:
        host._announce("This video has no captions published.")
        return
    host._captions_on = True
    engine = _engine(host)
    if engine is not None:
        # The picture's own captions, when there is a picture. Not required:
        # the window below is the readable half and works on either engine.
        engine.add_subtitles(url)
        _apply_captions(host, engine, first_time=False)
    host._announce("Getting captions...")

    def _work(**_kwargs: Any) -> Any:
        from quill.core.podcasts import transcripts as transcripts_module

        return transcripts_module.fetch_transcript_cues(url, "application/json")

    def _ok(_op: str, result: object) -> None:
        cues = list(result) if isinstance(result, list) else []
        if not cues:
            host._announce(
                "Captions were published for this video but none could be read. "
                "The picture's own captions are still on if the video is showing."
            )
            return
        _open_captions_window(host, cues, automatic=automatic)

    def _failed(_op: str, error: BaseException) -> None:
        host._announce(f"The captions could not be fetched. {error}.")

    host._task_manager.submit("radio-captions", _work, on_success=_ok, on_failure=_failed)


def _open_captions_window(host: Any, cues: list, *, automatic: bool) -> None:
    """Show the fetched captions, following the player."""
    from quill.core.radio.caption_style import CaptionStyle
    from quill.ui.radio.captions_window import CaptionsWindow

    controller = getattr(host, "_radio_controller", None) or getattr(host, "_controller", None)
    if controller is None:
        return
    stream = _stream(host)
    style = getattr(host, "_caption_style", None) or CaptionStyle()
    window = CaptionsWindow(
        getattr(host, "frame", None),
        title=str(getattr(stream, "title", "") or ""),
        cues=cues,
        position_ms=controller.position_ms,
        size_percent=style.clamped().size_percent,
        is_automatic=automatic,
        announce=host._announce,
        on_closed=lambda: _captions_window_closed(host),
    )
    host._captions_window = window
    window.show()
    # Said once, plainly, and only after there is something to read.
    host._announce(
        "Captions on, in the Captions window. These are automatic captions, so expect mistakes."
        if automatic
        else "Captions on, in the Captions window."
    )


def _captions_off(host: Any) -> None:
    """Captions off: the window goes, and so does the picture's own overlay."""
    window = getattr(host, "_captions_window", None)
    host._captions_on = False
    host._captions_window = None
    engine = _engine(host)
    if engine is not None:
        engine.set_subtitles_visible(False)
    if window is not None:
        window.close()
    host._announce("Captions off.")


def _captions_window_closed(host: Any) -> None:
    """The listener closed the Captions window: that means captions off.

    A window somebody closed and a setting still switched on is the app
    disagreeing with itself -- and the next Ctrl+Shift+K would then read as
    doing nothing.
    """
    if getattr(host, "_captions_window", None) is None:
        return  # _captions_off already did this
    _captions_off(host)


def _apply_captions(host: Any, engine: Any, *, first_time: bool) -> None:
    """Push the stored caption style, and the on/off state, into the player."""
    from quill.core.radio.caption_style import CaptionStyle

    style = getattr(host, "_caption_style", None) or CaptionStyle()
    engine.apply_caption_style(style)
    on = bool(getattr(host, "_captions_on", False))
    engine.set_subtitles_visible(on)
    if on and first_time:
        controller = getattr(host, "_radio_controller", None)
        url, _automatic = controller.caption_track() if controller is not None else ("", False)
        if url:
            engine.add_subtitles(url)


def _apply_brightness(host: Any, engine: Any) -> None:
    engine.set_brightness(int(getattr(host, "_video_brightness", 0) or 0))


def dim_video(host: Any, percent: int) -> None:
    """Reduce the picture's brightness, for light sensitivity.

    A real requirement rather than a preference: flashing content cannot be
    detected before it plays, so the honest answer is control over the picture
    rather than a claim about it.
    """
    host._video_brightness = max(-100, min(0, int(percent)))
    engine = _engine(host)
    if engine is not None:
        engine.set_brightness(host._video_brightness)
    host._announce(
        "Picture at normal brightness."
        if host._video_brightness == 0
        else f"Picture dimmed by {abs(host._video_brightness)}%."
    )


# -- information and snapshots ---------------------------------------------------


def _status_text(host: Any, stream: Any) -> str:
    """The status line: what is playing, and where.

    Read on demand and never announced -- see the Video Window's docstring for
    why a position display must not be a live region.
    """
    from quill.ui.radio.bounded_playback_ui import spoken_duration

    controller = getattr(host, "_radio_controller", None)
    title = str(getattr(stream, "title", "") or "")
    parts = [title] if title else []
    if controller is not None and controller.is_seekable():
        parts.append(
            f"{spoken_duration(controller.position_ms())} of "
            f"{spoken_duration(controller.duration_ms())}"
        )
    track = controller.selected_audio_track() if controller is not None else None
    if track is not None:
        parts.append(f"Audio: {track.display_name}")
    return "\n".join(parts)


def video_information(host: Any) -> None:
    """**Video Information** (Ctrl+Shift+I). Resolution, rate, codec, and the
    two facts somebody is most likely listening for."""
    from quill.core.radio.audio_tracks import described_track
    from quill.core.radio.video_formats import VideoStream, describe_video

    controller = getattr(host, "_radio_controller", None)
    stream = _stream(host)
    if stream is None:
        host._announce(NO_VIDEO)
        return
    video = VideoStream(
        url=str(getattr(stream, "video_url", "") or ""),
        width=int(getattr(stream, "video_width", 0) or 0),
        height=int(getattr(stream, "video_height", 0) or 0),
        fps=float(getattr(stream, "video_fps", 0.0) or 0.0),
        codec=str(getattr(stream, "video_codec", "") or ""),
    )
    captions = bool(controller is not None and controller.caption_track()[0])
    described = (
        described_track(list(controller.audio_tracks())) is not None if controller else False
    )
    host._announce(describe_video(video, captions=captions, described_audio=described))


def take_snapshot(host: Any) -> None:
    """**Take a Snapshot**: the current frame as a PNG, named out loud.

    For a slide somebody wants to read with OCR, or send to a person who can
    describe it. Saved without the captions burned in, because a snapshot of a
    slide should be the slide.
    """
    engine = _engine(host)
    window = getattr(host, "_video_window", None)
    if engine is None or window is None:
        host._announce("There is no picture to snapshot. Show the video first.")
        return
    from quill.core.radio.recording import _default_dir  # the recordings folder

    stream = _stream(host)
    stamp = int(getattr(host, "_snapshot_counter", 0)) + 1
    host._snapshot_counter = stamp
    title = str(getattr(stream, "title", "") or "video").strip() or "video"
    safe = "".join(ch for ch in title if ch.isalnum() or ch in " -_")[:60].strip() or "video"
    target = _default_dir() / f"{safe} snapshot {stamp}.png"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        host._announce("The snapshot folder could not be created.")
        return
    if engine.take_snapshot(str(target)):
        host._announce(f"Snapshot saved as {target.name}.")
    else:
        host._announce("The snapshot could not be saved.")


def caption_settings(host: Any) -> None:
    """**Caption Settings...**: size, colour, background, opacity, position."""
    from quill.core.radio.caption_style import CaptionStyle
    from quill.ui.radio.caption_settings_dialog import CaptionSettingsDialog

    dialog = CaptionSettingsDialog(
        host.frame,
        style=getattr(host, "_caption_style", None) or CaptionStyle(),
        show_modal_dialog=getattr(host, "_show_modal_dialog", None),
        announce=host._announce,
    )
    chosen = dialog.show()
    if chosen is None:
        return
    host._caption_style = chosen
    engine = _engine(host)
    if engine is not None:
        engine.apply_caption_style(chosen)


def set_video_size(host: Any, percent: int) -> None:
    """**Video Size**: fit, 50%, 100%, 200%, or full screen.

    A keyboard command rather than a drag, because every capability in this
    feature has to be reachable without a pointer -- resize included.
    """
    window = getattr(host, "_video_window", None)
    if window is None:
        host._announce("There is no picture to resize. Show the video first.")
        return
    if percent <= 0:
        window.toggle_full_screen()
        return
    engine = _engine(host)
    size = engine.video_size() if engine is not None else None
    if not size:
        host._announce("The picture's size is not known yet.")
        return
    width = max(160, int(size[0] * percent / 100))
    height = max(90, int(size[1] * percent / 100))
    window.resize_to(width, height)
    host._announce(f"Video at {percent}%, {width} by {height}.")


def toggle_full_screen(host: Any) -> None:
    """**Full Screen** (F11). Says both ways out, on the way in."""
    window = getattr(host, "_video_window", None)
    if window is None:
        host._announce("There is no picture to show full screen. Show the video first.")
        return
    window.toggle_full_screen()
