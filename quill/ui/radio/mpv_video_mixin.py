"""The picture half of the mpv radio engine, as a mixin.

Extracted from ``mpv_radio_engine`` under GATE-11 (extract, never rebaseline),
and a mixin rather than a helper module because every method here is *engine
surface*: a caller holds an engine and asks it to show a picture, and pushing
that through a free function taking ``engine._mpv`` would mean reaching into a
private from outside.

The property this whole feature rests on: **mpv can be given a window to draw
into, and have it taken away again, while playing.** Showing and hiding the
picture therefore never restarts the stream and never costs the listener their
place -- which is what makes video safe to offer as a *view onto* playback
rather than a *mode of* it.

Every call is guarded and safe on a station that has no video at all, because
this engine plays far more radio than video. The mpv property names live in
:mod:`quill.ui.radio.video_output`, not here.
"""

from __future__ import annotations


class VideoOutputMixin:
    """Show a picture, load a caption track, snapshot a frame."""

    def attach_video(self, handle: int | None) -> bool:
        """Render into *handle*, or stop rendering when it is ``None``.

        Both directions work while playing, which is what makes showing and
        hiding the picture free: it never restarts the stream and never costs
        the listener their place.
        """
        from quill.ui.radio import video_output

        self._video_attached = handle is not None
        return video_output.attach(self._mpv, handle)

    def has_video_attached(self) -> bool:
        return bool(getattr(self, "_video_attached", False))

    def set_audio_file(self, url: str) -> bool:
        """Play *url* as the audio alongside the loaded video."""
        from quill.ui.radio import video_output

        return video_output.set_audio_file(self._mpv, url)

    def video_size(self) -> tuple[int, int] | None:
        """``(width, height)`` of the decoded picture, or ``None``."""
        from quill.ui.radio import video_output

        return video_output.video_size(self._mpv)

    def add_subtitles(self, url: str) -> bool:
        """Load an external caption file and select it."""
        from quill.ui.radio import video_output

        return video_output.add_subtitles(self._mpv, url)

    def set_subtitles_visible(self, visible: bool) -> bool:
        from quill.ui.radio import video_output

        return video_output.set_subtitles_visible(self._mpv, visible)

    def apply_caption_style(self, style: object) -> bool:
        from quill.ui.radio import video_output

        return video_output.apply_caption_style(self._mpv, style)

    def set_brightness(self, percent: int) -> bool:
        from quill.ui.radio import video_output

        return video_output.set_brightness(self._mpv, percent)

    def take_snapshot(self, path: str) -> bool:
        from quill.ui.radio import video_output

        return video_output.take_snapshot(self._mpv, path)
