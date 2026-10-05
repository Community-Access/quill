"""A recording on disk as 16 kHz mono sound, a block at a time.

Transcribe a Recording hands the speech engines exactly what live dictation
hands them -- 16,000 samples a second, one channel, floating point -- so the
same engines, the same voice detection and the same tidying apply. This module
is the part live dictation never needed: reading a file.

**Three decoders, tried in order, and none of them new to the installers:**

1. **libsndfile** (``soundfile``, already in the shared runtime): WAV, FLAC,
   Ogg Vorbis, Opus and MP3.
2. **Windows Media Foundation** (:mod:`~quill.core.windows_dictation.media_foundation`),
   which every Windows has: MP3, M4A and AAC, MP4 sound, WMA, WAV and FLAC.
3. **ffmpeg**, only where the program has one (QUILL does; QUILL Lite does
   not), for anything the first two refused.

So every format the dialog offers is read in both editors without ffmpeg; the
third is a last resort for unusual files, never a requirement.

**Never the whole recording in memory.** An hour of stereo MP3 decoded at its
own rate is more than a gigabyte; at 16 kHz mono it is 230 MB, and even that is
more than a four-gigabyte computer should spend. So :meth:`AudioSource.blocks`
yields a second or so at a time, mixed to one channel and resampled as it
goes (:class:`Resampler`), and the caller lets each block go once the voice
detector has seen it.

wx-free; ``numpy`` and ``soundfile`` are imported lazily.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.error_codes import CodedError

__all__ = [
    "AUDIO_EXTENSIONS",
    "RATE",
    "AudioFileError",
    "AudioSource",
    "Resampler",
    "duration_of",
    "file_filter",
    "open_audio",
]

RATE = 16_000
#: What the file picker offers, and what the decoders above read.
AUDIO_EXTENSIONS: tuple[str, ...] = (
    ".mp3",
    ".m4a",
    ".aac",
    ".mp4",
    ".wav",
    ".ogg",
    ".oga",
    ".opus",
    ".flac",
    ".wma",
    ".aif",
    ".aiff",
)
#: Formats libsndfile reads well; everything else goes to Media Foundation first.
_SOUNDFILE_FIRST = frozenset({".wav", ".flac", ".ogg", ".oga", ".opus", ".aif", ".aiff", ".mp3"})
_BLOCK_SECONDS = 1.0


class AudioFileError(CodedError):
    """The recording could not be read. The message is a sentence a person can act on."""

    code = "QUILL-DICTATION-FILE-UNREADABLE"


def file_filter() -> str:
    """The wildcard for a wx file picker."""
    patterns = ";".join(f"*{extension}" for extension in AUDIO_EXTENSIONS)
    return f"Recordings ({patterns})|{patterns}|All files (*.*)|*.*"


class Resampler:
    """Any sample rate to 16 kHz, in pieces, without a click at the joins.

    Downsampling first passes the sound through a low-pass filter (a windowed
    sinc, 63 taps), so what is above the new rate's limit does not fold back as
    noise, then reads it at the new spacing by linear interpolation. Both keep
    their state between calls, so a recording fed a second at a time comes out
    exactly as it would have whole. 16 kHz in is passed straight through.
    """

    _TAPS = 63

    def __init__(self, rate_in: int, rate_out: int = RATE) -> None:
        import numpy as np

        if rate_in <= 0:
            raise AudioFileError("The recording says it has no sample rate.")
        self._in = int(rate_in)
        self._out = int(rate_out)
        self._filter: Any = None
        self._history: Any = None
        if self._in > self._out:
            cutoff = 0.45 * self._out / self._in  # a little under the new limit
            n = np.arange(self._TAPS) - (self._TAPS - 1) / 2
            taps = 2 * cutoff * np.sinc(2 * cutoff * n) * np.hamming(self._TAPS)
            self._filter = (taps / taps.sum()).astype(np.float32)
            self._history = np.zeros(self._TAPS - 1, dtype=np.float32)
        self._buffer = np.zeros(0, dtype=np.float32)
        self._base = 0  # absolute index of _buffer[0]
        self._produced = 0  # output samples made so far

    def process(self, samples: Any) -> Any:
        """The next piece of 16 kHz sound for the next piece of input."""
        import numpy as np

        data = np.asarray(samples, dtype=np.float32)
        if self._in == self._out:
            return data
        if self._filter is not None:
            joined = np.concatenate([self._history, data])
            self._history = joined[-(self._TAPS - 1) :]
            data = np.convolve(joined, self._filter, mode="valid").astype(np.float32)
        self._buffer = np.concatenate([self._buffer, data])
        last = self._base + self._buffer.size - 1  # interpolation needs i and i + 1
        step = self._in / self._out
        count = max(0, math.floor(last / step) - self._produced) if last > 0 else 0
        if count <= 0:
            return np.zeros(0, dtype=np.float32)
        positions = (np.arange(count) + self._produced) * step
        while positions.size and positions[-1] >= last:
            positions = positions[:-1]
        if not positions.size:
            return np.zeros(0, dtype=np.float32)
        index = np.floor(positions).astype(np.int64)
        fraction = (positions - index).astype(np.float32)
        local = index - self._base
        out = self._buffer[local] * (1 - fraction) + self._buffer[local + 1] * fraction
        self._produced += positions.size
        keep_from = int(math.floor(self._produced * step)) - self._base
        if keep_from > 0:
            self._buffer = self._buffer[keep_from:]
            self._base += keep_from
        return out.astype(np.float32)


def _mono(frames: Any) -> Any:
    import numpy as np

    data = np.asarray(frames, dtype=np.float32)
    if data.ndim == 2:
        data = data.mean(axis=1) if data.shape[1] > 1 else data[:, 0]
    return data


@dataclass(slots=True)
class AudioSource:
    """A recording ready to read: its length, and its sound a block at a time."""

    path: Path
    #: Seconds, or 0.0 when nothing could say (progress then counts minutes).
    duration: float
    #: What read it: ``soundfile``, ``media_foundation`` or ``ffmpeg``.
    decoder: str
    _blocks: Callable[[], Iterator[Any]]

    def blocks(self) -> Iterator[Any]:
        """16 kHz mono float32 blocks, about a second each."""
        return self._blocks()


def duration_of(path: Path) -> float:
    """The recording's length in seconds from its header, or 0.0. Cheap: no decoding."""
    try:
        import mutagen

        found = mutagen.File(str(path))
        length = float(getattr(getattr(found, "info", None), "length", 0.0) or 0.0)
        if length > 0:
            return length
    except Exception:  # noqa: BLE001 - mutagen is a convenience
        pass
    try:
        import soundfile  # type: ignore[import-untyped,unused-ignore]

        info = soundfile.info(str(path))
        return float(info.frames) / float(info.samplerate or 1)
    except Exception:  # noqa: BLE001 - unknown is an answer
        return 0.0


def _soundfile_source(path: Path) -> AudioSource:
    import soundfile  # type: ignore[import-untyped,unused-ignore]

    with soundfile.SoundFile(str(path)) as probe:  # raises when it cannot read the file
        rate = int(probe.samplerate)
        duration = float(probe.frames) / rate if probe.frames > 0 else 0.0

    def blocks() -> Iterator[Any]:
        resampler = Resampler(rate)
        with soundfile.SoundFile(str(path)) as audio:
            for frames in audio.blocks(
                blocksize=int(rate * _BLOCK_SECONDS), dtype="float32", always_2d=True
            ):
                out = resampler.process(_mono(frames))
                if out.size:
                    yield out

    return AudioSource(path, duration or duration_of(path), "soundfile", blocks)


def _media_foundation_source(path: Path) -> AudioSource:
    from quill.core.windows_dictation.media_foundation import MediaFoundationReader, available

    if not available():
        raise AudioFileError("Windows Media Foundation is not available here.")
    with MediaFoundationReader(str(path)) as probe:  # raises when Windows cannot read it
        duration = probe.duration

    def blocks() -> Iterator[Any]:
        with MediaFoundationReader(str(path)) as reader:
            resampler = Resampler(reader.rate)
            rate = reader.rate
            for frames in reader.blocks():
                if reader.rate != rate:  # the stream changed format part way
                    rate, resampler = reader.rate, Resampler(reader.rate)
                out = resampler.process(_mono(frames))
                if out.size:
                    yield out

    return AudioSource(path, duration or duration_of(path), "media_foundation", blocks)


def _ffmpeg_source(path: Path) -> AudioSource:
    from quill.core.speech.ffmpeg import find_ffmpeg

    if find_ffmpeg() is None:
        raise AudioFileError("ffmpeg is not part of this program.")

    def blocks() -> Iterator[Any]:
        import tempfile

        import soundfile  # type: ignore[import-untyped,unused-ignore]

        from quill.core.speech.ffmpeg import transcode_to_wav

        with tempfile.TemporaryDirectory(prefix="quill-transcribe-") as folder:
            wav = transcode_to_wav(path, out_dir=Path(folder), timeout_seconds=3600.0)
            with soundfile.SoundFile(str(wav)) as audio:
                for frames in audio.blocks(blocksize=RATE, dtype="float32", always_2d=True):
                    yield _mono(frames)

    return AudioSource(path, duration_of(path), "ffmpeg", blocks)


Opener = Callable[[Path], AudioSource]


def open_audio(path: Path, *, openers: tuple[Opener, ...] | None = None) -> AudioSource:
    """*path* ready to read, by the first decoder that can.

    Raises :class:`AudioFileError` with one sentence when the file is missing
    or nothing here reads it.
    """
    path = Path(path)
    if not path.is_file():
        raise AudioFileError(f"{path.name} was not found. It may have been moved or renamed.")
    if openers is None:
        ordered: list[Opener] = [_soundfile_source, _media_foundation_source]
        if path.suffix.lower() not in _SOUNDFILE_FIRST:
            ordered.reverse()
        openers = (*ordered, _ffmpeg_source)
    for opener in openers:
        try:
            return opener(path)
        except Exception:  # noqa: BLE001 - the next decoder may read it
            continue
    raise AudioFileError(
        f"{path.name} could not be read as a recording. MP3, M4A, AAC, WAV, Ogg, "
        "Opus, FLAC and WMA files can be transcribed; if this is one of those, it "
        "may be damaged or protected."
    )
