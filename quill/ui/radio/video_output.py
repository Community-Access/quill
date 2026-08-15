"""Attaching a picture to a stream that is already playing -- and detaching it.

The property that makes video safe to offer at all: **mpv can be given a window
to draw into, and have it taken away again, without restarting playback.**
Opening the Video Window therefore costs nothing and loses nothing; closing it
leaves the audio running mid-word. Video is a *view onto* playback, never a
*mode of* it, and this module is where that is true.

Everything here is a thin, guarded call onto the mpv client, kept out of
``mpv_radio_engine`` under GATE-11 and grouped because it is one concern: what
the player does with a picture, a second audio file, and a subtitle track.

Three rules:

* **Every call is safe when there is no picture.** The engine is used far more
  often for ordinary radio than for video, and none of this may raise on a
  station that has no video at all.
* **A detach is as important as an attach.** ``load`` resets the attachment for
  the same reason it resets boundedness: a video left attached must never leak
  into the next station.
* **mpv is spoken to in one place.** The property names live here and in
  :mod:`quill.core.radio.caption_style`, nowhere else.
"""

from __future__ import annotations

from typing import Any

#: mpv's property for the window handle to render into, and the one that turns
#: video decoding on or off. ``vid=no`` is what the engine starts with, and what
#: it returns to whenever the picture is hidden -- so an audio-only listener
#: never pays for a video decoder.
_WINDOW_ID = "wid"
_VIDEO_TRACK = "vid"


def attach(client: Any, handle: int | None) -> bool:
    """Render into the window *handle*, or stop rendering when it is ``None``.

    True when the call was accepted. Both directions work at runtime, which is
    the whole point: showing and hiding the picture never restarts the stream
    and never costs the listener their place.
    """
    if client is None:
        return False
    try:
        if handle is None:
            client.set_str(_VIDEO_TRACK, "no")
            client.set_str(_WINDOW_ID, "0")
            return True
        client.set_str(_WINDOW_ID, str(int(handle)))
        client.set_str(_VIDEO_TRACK, "auto")
        return True
    except Exception:  # noqa: BLE001 - a picture is never worth losing the audio
        return False


def set_audio_file(client: Any, url: str) -> bool:
    """Play *url* as the audio alongside the loaded video.

    YouTube serves adaptive video and audio separately, and this is how they are
    played together without downloading and merging the whole file first: mpv
    demuxes both and synchronises them itself. Passing "" clears it.
    """
    if client is None:
        return False
    try:
        client.set_str("audio-files", url or "")
        return True
    except Exception:  # noqa: BLE001
        return False


def video_size(client: Any) -> tuple[int, int] | None:
    """``(width, height)`` of the picture actually being decoded, or ``None``.

    From the player rather than from the format list, because the two can
    disagree -- and what the listener is told should be what is on screen.
    """
    if client is None:
        return None
    try:
        width = client.get_double("dwidth")
        height = client.get_double("dheight")
    except Exception:  # noqa: BLE001
        return None
    if not width or not height:
        return None
    return int(width), int(height)


def add_subtitles(client: Any, url: str) -> bool:
    """Load *url* as an external subtitle track and show it."""
    if client is None or not url:
        return False
    try:
        client.command("sub-add", url, "select")
        return True
    except Exception:  # noqa: BLE001
        return False


def set_subtitles_visible(client: Any, visible: bool) -> bool:
    """Show or hide the subtitles that are already loaded."""
    if client is None:
        return False
    try:
        client.set_str("sub-visibility", "yes" if visible else "no")
        return True
    except Exception:  # noqa: BLE001
        return False


def apply_caption_style(client: Any, style: Any) -> bool:
    """Apply a :class:`~quill.core.radio.caption_style.CaptionStyle`."""
    from quill.core.radio.caption_style import mpv_properties

    if client is None:
        return False
    try:
        for name, value in mpv_properties(style).items():
            client.set_str(name, value)
        return True
    except Exception:  # noqa: BLE001
        return False


def set_brightness(client: Any, percent: int) -> bool:
    """Dim or brighten the picture. 0 is mpv's normal; -100 is black.

    Here for light sensitivity and migraine triggers, which is a real
    requirement rather than a preference -- see the photosensitivity section of
    the video specification. Clamped, because a stored settings value is
    somebody else's input.
    """
    if client is None:
        return False
    try:
        client.set_str("brightness", str(max(-100, min(100, int(percent)))))
        return True
    except Exception:  # noqa: BLE001
        return False


def take_snapshot(client: Any, path: str) -> bool:
    """Write the current frame to *path* as a PNG.

    Deliberately "each-frame, no subtitles": somebody snapshotting a slide wants
    the slide, not the slide with a caption burned across it.
    """
    if client is None or not path:
        return False
    try:
        client.command("screenshot-to-file", path, "video")
        return True
    except Exception:  # noqa: BLE001
        return False
