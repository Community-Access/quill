"""Picking a video stream, and why it is a *second* URL rather than a merged one.

The one non-obvious thing about playing YouTube video, and the reason this is its
own module: **YouTube serves adaptive video and audio as two separate streams.**
The usual answer is to have yt-dlp merge them with ffmpeg, which means
downloading the entire video before a frame plays. That is not streaming, and for
a live broadcast it is not possible at all.

The correct technique is to hand the player *both*: load the video URL as the
file and set mpv's ``audio-file`` property to the audio URL. mpv demuxes and
synchronises the two itself, live, with no merge step and no temporary file. It
is exactly what mpv's own ``ytdl_hook`` does internally, so it is well-trodden
rather than clever.

Live broadcasts are simpler and are deliberately left alone: a YouTube live
stream is a single HLS manifest carrying both, so the existing single-URL path
already works and this module answers "no separate video stream" for it.

Height is capped because this is a media player for listening, on machines that
are frequently modest, and 4K video decoded to be glanced at is a waste of a
processor that has a screen reader to keep responsive.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The tallest video stream worth choosing. Above this the decode cost rises
#: sharply for a picture nobody is studying frame by frame -- and on a machine
#: running a screen reader, spare processor is not a luxury.
MAX_HEIGHT = 1080


@dataclass(frozen=True, slots=True)
class VideoStream:
    """The video half of a resolved YouTube video.

    ``url`` empty means "there is no separate video stream to play", which is
    the honest answer both for an audio-only resolve and for a live HLS stream
    that already carries its own picture.
    """

    url: str = ""
    height: int = 0
    width: int = 0
    fps: float = 0.0
    codec: str = ""

    @property
    def available(self) -> bool:
        return bool(self.url)

    @property
    def spoken_size(self) -> str:
        """ "1280 by 720", the way the Show Video announcement says it."""
        if not self.width or not self.height:
            return ""
        return f"{self.width} by {self.height}"


def _as_float(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _as_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[call-overload,no-any-return]
    except (TypeError, ValueError):
        return 0


def pick_video_stream(info: dict[str, object], *, max_height: int = MAX_HEIGHT) -> VideoStream:
    """The best video-only stream in a yt-dlp info dict (pure).

    Video-*only* formats specifically: a combined format carries its own audio,
    and pairing one with a separate audio file would play the same programme
    twice. Where only combined formats exist, the caller's ordinary single-URL
    path is already correct, so this answers with nothing.

    Tallest first up to *max_height*, then by bitrate, then by frame rate --
    resolution being what a low-vision viewer actually notices, which is who
    this is for.
    """
    formats = info.get("formats")
    if not isinstance(formats, list):
        return VideoStream()
    candidates: list[dict[str, object]] = []
    for entry in formats:
        if not isinstance(entry, dict) or not isinstance(entry.get("url"), str):
            continue
        if entry.get("vcodec") in (None, "none"):
            continue
        if entry.get("acodec") not in (None, "none"):
            # A combined stream: the single-URL path handles it already, and
            # pairing it with an audio file would play the programme twice.
            continue
        if _as_int(entry.get("height")) > max_height:
            continue
        candidates.append(entry)
    if not candidates:
        return VideoStream()
    best = max(
        candidates,
        key=lambda item: (
            _as_int(item.get("height")),
            _as_float(item.get("tbr")) or _as_float(item.get("vbr")),
            _as_float(item.get("fps")),
        ),
    )
    return VideoStream(
        url=str(best.get("url") or ""),
        height=_as_int(best.get("height")),
        width=_as_int(best.get("width")),
        fps=_as_float(best.get("fps")),
        codec=str(best.get("vcodec") or ""),
    )


def describe_video(video: VideoStream, *, captions: bool, described_audio: bool) -> str:
    """What **Video Information** says, as sentences rather than a table.

    Every fact it states is one it actually has; nothing is inferred. The two
    accessibility facts come last because they are the ones somebody is most
    likely to be listening for, and last is what a screen reader leaves you on.
    """
    if not video.available:
        return "There is no video for this station."
    parts = [f"Picture {video.spoken_size}." if video.spoken_size else "Picture available."]
    if video.fps:
        parts.append(f"{round(video.fps)} frames a second.")
    if video.codec:
        parts.append(f"Encoded as {video.codec}.")
    parts.append("Captions are available." if captions else "No captions were published.")
    parts.append(
        "Described audio is available." if described_audio else "No described audio was published."
    )
    return " ".join(parts)
