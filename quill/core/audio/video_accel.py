"""The graphics card's video encoder, when there is one that works.

H.264 and H.265 on the processor alone run at about real time on a typical
laptop -- H.265 slower -- so a film could take longer to convert than to
watch. Most Windows machines have a video encoder on the graphics chip (NVIDIA
NVENC, Intel Quick Sync, AMD AMF) that does the same job many times faster, and
the bundled FFmpeg can drive all three.

Which one works is a property of the machine, not the build, so it is found
out rather than assumed: each candidate encodes a fifth of a second of test
picture once per session, and the first that succeeds is used. A real encode
that still fails is retried on the processor (``convert_runner``) and the
card is not tried again this session. Nothing to configure: the result is the
same file, sooner.
"""

from __future__ import annotations

import os
import subprocess
import threading

from quill.core.audio.formats import VideoProfile, VideoQuality, video_quality_args

#: Software codec -> hardware encoders to try, best first.
_CANDIDATES: dict[str, tuple[str, ...]] = {
    "libx264": ("h264_nvenc", "h264_qsv", "h264_amf"),
    "libx265": ("hevc_nvenc", "hevc_qsv", "hevc_amf"),
}

#: Constant-quality numbers per rung, on each family's own scale. Chosen to land
#: near the software ladder's sizes (x264 18/23/28, x265 22/28/32).
_QUALITY: dict[str, dict[VideoQuality, int]] = {
    "libx264": {VideoQuality.HIGH: 20, VideoQuality.BALANCED: 25, VideoQuality.SMALL: 30},
    "libx265": {VideoQuality.HIGH: 23, VideoQuality.BALANCED: 28, VideoQuality.SMALL: 32},
}

_lock = threading.Lock()
_found: dict[tuple[str, str], str | None] = {}
_broken: set[str] = set()


def hardware_encoder(ffmpeg: str, codec: str) -> str | None:
    """The first graphics-card encoder standing in for *codec* that works here."""
    candidates = _CANDIDATES.get(codec)
    if not candidates or os.environ.get("QUILL_NO_HARDWARE_VIDEO"):
        return None
    key = (ffmpeg, codec)
    with _lock:
        if key not in _found:
            _found[key] = next((name for name in candidates if _works(ffmpeg, name)), None)
        found = _found[key]
    return None if found in _broken else found


def mark_broken(encoder: str) -> None:
    """A real encode failed on *encoder*; use the processor for the rest of the session."""
    with _lock:
        _broken.add(encoder)


def _works(ffmpeg: str, encoder: str) -> bool:
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=640x360:rate=30:duration=0.2",
        *_pixel_format(encoder),
        "-c:v",
        encoder,
        "-f",
        "null",
        "-",
    ]
    flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    try:
        done = subprocess.run(
            command,
            capture_output=True,
            timeout=20,
            check=False,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return done.returncode == 0


def _pixel_format(encoder: str) -> list[str]:
    # Quick Sync takes NV12, not the planar 4:2:0 the software encoders want.
    return ["-pix_fmt", "nv12"] if encoder.endswith("_qsv") else ["-pix_fmt", "yuv420p"]


def video_codec_args(video: VideoProfile, quality: VideoQuality, encoder: str) -> list[str]:
    """``-c:v`` and its rate control and profile switches, for *encoder* (pure).

    *encoder* is ``video.video_codec`` for the processor, or a hardware encoder
    from :func:`hardware_encoder`.
    """
    if encoder == video.video_codec:
        return ["-c:v", encoder, *video_quality_args(encoder, quality), *video.video_args]
    q = str(_QUALITY[video.video_codec][quality])
    if encoder.endswith("_nvenc"):
        rate = ["-rc", "vbr", "-cq", q, "-b:v", "0", "-preset", "p5"]
    elif encoder.endswith("_qsv"):
        rate = ["-global_quality", q, "-preset", "medium"]
    else:  # _amf: its fixed quantiser runs about four steps finer than the others'
        amf = str(int(q) + 4)  # scales, measured 2026-09-28 against x264/x265 file sizes
        rate = ["-rc", "cqp", "-qp_i", amf, "-qp_p", amf, "-qp_b", amf, "-quality", "balanced"]
    extra = list(video.video_args)
    if "-pix_fmt" in extra:
        at = extra.index("-pix_fmt")
        extra[at : at + 2] = _pixel_format(encoder)
    return ["-c:v", encoder, *rate, *extra]
