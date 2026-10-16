"""Keeping a station's pre-roll advert out of a recording (xradio2 section 6.1).

Many stations play something to *every new connection* before the broadcast:
a pre-roll advert, or a "you are listening to..." welcome. A recording opens
its own connection, so it can capture that instead of the programme the
listener is hearing -- and a recording that drops and reconnects opens
another, so a second one can land in the middle of the show. It reproduces
only on some stations and looks like the station's fault, which is why it
needs code rather than a report.

What this module does about it, in two halves:

* **No hidden reconnects.** ``recording_commands.build_record_command`` no
  longer asks ffmpeg to re-request a live stream inside one file
  (``-reconnect_streamed``), because each re-request is a new connection and
  can splice a fresh pre-roll into the file with nothing to mark where. A drop
  now ends the part, and the recorder's own reconnect starts the next one, so
  every connection begins at a known place: the start of a part.
  (:func:`input_dropped` is how the recorder tells that drop apart from a
  finished recording, since ffmpeg exits 0 when its input dies.)
* **Trim what every connection opens with** (the runner half lives in
  ``recording_preroll_guard``). Audio that opens two *separate*
  connections to the same station cannot be the live broadcast -- the
  broadcast moves on between them -- so it is the station's connection insert.
  At the start of a recording, ``OpeningGuard`` listens to a short
  *reference* connection opened some seconds later (decoded to a loudness
  outline in memory; nothing is saved), and when the recording ends it compares
  the opening of every part against the reference and against each other.
  Whatever they share from their first moment is cut from the front of each
  part, before the parts are joined.

The comparison is deliberately one-sided in its failures: when it is unsure,
it trims nothing. A station whose advert differs on every connection, or that
plays none, leaves the recording exactly as it was captured -- the guard can
only ever remove audio that it has heard open two different connections.

wx-free, strict-typed. The decode and trim runners are injectable, so the tests
use fakes and no network.
"""

from __future__ import annotations

import math
import re
import sys
from array import array
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "ALL_INSERT_MARGIN_SECONDS",
    "ANALYSE_SECONDS",
    "DECODE_SLACK_SECONDS",
    "HOP_SECONDS",
    "MAX_TRIM_SECONDS",
    "MIN_MATCH_SECONDS",
    "MIN_TRIMMED_BYTES",
    "REFERENCE_DELAY_SECONDS",
    "Opening",
    "build_opening_decode_command",
    "build_trim_command",
    "describe_trims",
    "envelope_from_pcm",
    "guard_applies",
    "input_dropped",
    "plan_trims",
    "shared_opening",
]

#: Seconds of each connection's opening that are compared. Pre-roll adverts run
#: 15 to 30 seconds, occasionally a minute; this covers that with room to see
#: the broadcast begin after it (the comparison needs to see where they part).
ANALYSE_SECONDS = 75

#: The most that is ever cut from the front of one part. Anything longer than
#: this that "matches" is not an advert, it is something the guard does not
#: understand, and it keeps its hands off.
MAX_TRIM_SECONDS = 70.0

#: How long after the recording's own connection the reference connection is
#: opened. Long enough that the two connections cannot be handed the same
#: stretch of *live* audio from the start: an Icecast server bursts its last few
#: seconds to every new listener, and an HLS playlist starts each one a few
#: segments back, so two connections opened together can genuinely begin with
#: the same broadcast audio. Twenty seconds apart they cannot.
REFERENCE_DELAY_SECONDS = 20.0

#: Decoded at 8 kHz mono: plenty to follow loudness, small enough to hold in
#: memory (75 s is 1.2 MB of PCM).
_SAMPLE_RATE = 8000
#: One loudness value per 50 ms.
_HOP_SAMPLES = 400
HOP_SECONDS = _HOP_SAMPLES / _SAMPLE_RATE
#: Two-second comparison windows, stepped a quarter of a second at a time.
_WINDOW = 40
_STEP = 5
#: Two decodes of the same audio can start a few frames apart (an encoder's
#: priming delay, a frame boundary); half a second either way is searched.
_MAX_LAG = 10
#: Shape agreement a window needs to count as the same audio.
_MIN_CORRELATION = 0.8
#: Level agreement, in dB, a window needs on top of its shape.
_MAX_LEVEL_GAP_DB = 10.0
#: A window whose loudness barely moves (a held tone, silence) has no shape to
#: correlate; it matches on level alone, within this many dB.
_FLAT_SPREAD_DB = 1.0
_FLAT_LEVEL_GAP_DB = 3.0
#: Two outlines that differ by more than this, twice running, have parted.
_PART_DB = 4.0
#: The shortest shared opening that is acted on. Below this, a chance
#: resemblance is a better explanation than an advert.
MIN_MATCH_SECONDS = 4.0
#: The shared stretch must be audible and must move: silence or a steady hum
#: would "match" between any two connections and prove nothing.
_QUIET_DB = -55.0
_MIN_RANGE_DB = 6.0
_FLOOR_DB = -90.0
#: A part left shorter than this after its trim was nothing *but* the insert.
ALL_INSERT_MARGIN_SECONDS = 1.0
#: A trimmed file smaller than this is a container header, not audio; the
#: original is kept.
MIN_TRIMMED_BYTES = 1024
#: Extra time the decoder is allowed beyond the audio it was asked for.
DECODE_SLACK_SECONDS = 45.0

#: ffmpeg's last words when its *input* died mid-stream. ffmpeg treats a read
#: error as the end of the input and exits 0, so without these the recorder
#: would file a dropped connection as a finished recording and never reconnect.
_INPUT_DROPPED_RE = re.compile(
    r"(?i)(error during demuxing|connection reset|connection aborted|"
    r"error number -1005[34]|end of file|i/o error|timed out|broken pipe|"
    r"failed to reconnect)"
)


def input_dropped(stderr_tail: Sequence[str]) -> bool:
    """Whether ffmpeg's last lines say the stream itself went away."""
    return any(_INPUT_DROPPED_RE.search(line) for line in stderr_tail)


def guard_applies(stream_url: str, capture_url: str) -> bool:
    """Whether a recording of this source gets a reference connection.

    Only a live http(s) stream has connections to compare. A YouTube broadcast
    (resolved to a media URL just before capture) and an HLS playlist are left
    alone: HLS hands every listener the same recent segments, so two openings
    can share genuine broadcast audio, which is exactly the false match the
    guard must never make.
    """
    from quill.core.radio.youtube import is_youtube_url

    url = capture_url.lower()
    if not url.startswith(("http://", "https://")):
        return False
    if is_youtube_url(stream_url) or ".m3u8" in url:
        return False
    return True


@dataclass(frozen=True, slots=True)
class Opening:
    """The loudness outline of one connection's first moments.

    ``complete`` is true when the source ran out before ``ANALYSE_SECONDS`` --
    the outline is then the whole of it, which is how a part that was nothing
    but the insert is recognised.
    """

    envelope: tuple[float, ...]
    complete: bool = False

    @property
    def seconds(self) -> float:
        return len(self.envelope) * HOP_SECONDS


def envelope_from_pcm(pcm: bytes) -> tuple[float, ...]:
    """Loudness in dB per 50 ms of signed 16-bit little-endian mono PCM (pure)."""
    samples = array("h")
    usable = len(pcm) - (len(pcm) % 2)
    samples.frombytes(pcm[:usable])
    if sys.byteorder != "little":
        samples.byteswap()
    out: list[float] = []
    for start in range(0, len(samples) - _HOP_SAMPLES + 1, _HOP_SAMPLES):
        chunk = samples[start : start + _HOP_SAMPLES]
        power = math.fsum(v * v for v in chunk) / (_HOP_SAMPLES * 32768.0 * 32768.0)
        out.append(max(_FLOOR_DB, 10.0 * math.log10(power)) if power > 0 else _FLOOR_DB)
    return tuple(out)


def _window_matches(a: Sequence[float], b: Sequence[float]) -> bool:
    n = len(a)
    mean_a = math.fsum(a) / n
    mean_b = math.fsum(b) / n
    spread_a = max(a) - min(a)
    spread_b = max(b) - min(b)
    if spread_a < _FLAT_SPREAD_DB and spread_b < _FLAT_SPREAD_DB:
        return abs(mean_a - mean_b) <= _FLAT_LEVEL_GAP_DB
    if abs(mean_a - mean_b) > _MAX_LEVEL_GAP_DB:
        return False
    return _correlation(a, b) >= _MIN_CORRELATION


def _correlation(a: Sequence[float], b: Sequence[float]) -> float:
    n = len(a)
    mean_a = math.fsum(a) / n
    mean_b = math.fsum(b) / n
    var_a = math.fsum((x - mean_a) ** 2 for x in a)
    var_b = math.fsum((y - mean_b) ** 2 for y in b)
    if var_a <= 1e-9 or var_b <= 1e-9:
        return 0.0
    cov = math.fsum((x - mean_a) * (y - mean_b) for x, y in zip(a, b, strict=True))
    return cov / math.sqrt(var_a * var_b)


def _best_lag(a: Sequence[float], b: Sequence[float]) -> int | None:
    """The offset (b index minus a index) at which the two openings line up."""
    best: tuple[float, int] | None = None
    for lag in range(-_MAX_LAG, _MAX_LAG + 1):
        start_a = max(0, -lag)
        if start_a + _WINDOW > len(a) or start_a + lag + _WINDOW > len(b):
            continue
        wa = a[start_a : start_a + _WINDOW]
        wb = b[start_a + lag : start_a + lag + _WINDOW]
        if not _window_matches(wa, wb):
            continue
        score = _correlation(wa, wb)
        if best is None or score > best[0]:
            best = (score, lag)
    return best[1] if best is not None else None


def _refine_end(ea: Sequence[float], eb: Sequence[float], lag: int, start: int, end: int) -> int:
    """Pull the end of a match back to where the two actually part.

    The last matching window can straddle the boundary by most of its length
    (a window that is mostly advert still correlates), which would cut up to two
    seconds of broadcast. Within that last window, the first point where the
    two outlines disagree by more than a few dB for two steps running is where
    the insert ended."""
    if end - start <= _WINDOW:
        return end
    diffs = [ea[i] - eb[i + lag] for i in range(start, end)]
    offset = sorted(diffs)[len(diffs) // 2]
    for i in range(max(start, end - _WINDOW), end - 1):
        if (
            abs(ea[i] - eb[i + lag] - offset) > _PART_DB
            and abs(ea[i + 1] - eb[i + 1 + lag] - offset) > _PART_DB
        ):
            return i
    return end


def shared_opening(a: Opening, b: Opening) -> tuple[float, float]:
    """How many seconds of audio *a* and *b* share from their first moment.

    Returns the length to cut from the front of each, ``(0.0, 0.0)`` when they
    do not share an opening worth acting on. Pure.
    """
    ea, eb = a.envelope, b.envelope
    lag = _best_lag(ea, eb)
    if lag is None:
        return (0.0, 0.0)
    start = max(0, -lag)
    end = start
    position = start
    while position + _WINDOW <= len(ea) and position + lag + _WINDOW <= len(eb):
        wa = ea[position : position + _WINDOW]
        wb = eb[position + lag : position + lag + _WINDOW]
        if not _window_matches(wa, wb):
            break
        end = position + _WINDOW
        position += _STEP
    end = _refine_end(ea, eb, lag, start, end)
    shared = ea[start:end]
    if (end - start) * HOP_SECONDS < MIN_MATCH_SECONDS:
        return (0.0, 0.0)
    audible = sum(1 for value in shared if value > _QUIET_DB)
    if audible < len(shared) / 2 or (max(shared) - min(shared)) < _MIN_RANGE_DB:
        return (0.0, 0.0)
    trim_a = end * HOP_SECONDS
    trim_b = (end + lag) * HOP_SECONDS
    if max(trim_a, trim_b) > MAX_TRIM_SECONDS:
        return (0.0, 0.0)
    return (trim_a, trim_b)


def plan_trims(reference: Opening | None, parts: Sequence[Opening | None]) -> list[float]:
    """Seconds to cut from the front of each part (pure).

    Every part is compared with the reference connection and with every other
    part; the longest opening it shares with any of them is its insert. A part
    with no outline (it could not be decoded) is never trimmed.
    """
    trims = [0.0] * len(parts)
    for index, part in enumerate(parts):
        if part is None:
            continue
        others: list[Opening] = [o for j, o in enumerate(parts) if j != index and o is not None]
        if reference is not None:
            others.append(reference)
        for other in others:
            mine, _theirs = shared_opening(part, other)
            trims[index] = max(trims[index], mine)
    return trims


def describe_trims(trims: Sequence[float], dropped: int) -> str:
    """One sentence for the listener about what was removed, or ``""``."""
    cut = [t for t in trims if t > 0]
    if not cut and not dropped:
        return ""
    seconds = round(max(cut)) if cut else 0
    if dropped and not cut:
        noun = "part" if dropped == 1 else "parts"
        return (
            f"Removed {dropped} recording {noun} that held only what the station "
            "plays to every new connection, usually an advert."
        )
    where = "the start of the recording" if len(cut) == 1 else f"the start of {len(cut)} parts"
    return (
        f"Removed about {seconds} seconds that the station plays to every new "
        f"connection, usually an advert, from {where}."
    )


def build_opening_decode_command(
    ffmpeg: str,
    source: str,
    *,
    seconds: int = ANALYSE_SECONDS,
    user_agent: str = "",
    rw_timeout_seconds: int = 30,
) -> list[str]:
    """ffmpeg argv that decodes the first *seconds* of *source* to raw PCM on
    stdout: 8 kHz mono signed 16-bit, which is all a loudness outline needs.
    For an http(s) source it identifies itself the way a recording does."""
    args = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin"]
    if source.lower().startswith(("http://", "https://")):
        if user_agent:
            args.extend(["-user_agent", user_agent])
        from quill.core.radio.stream_headers import referrer_for

        referrer = referrer_for(source)
        if referrer:
            args.extend(["-referer", referrer])
        if rw_timeout_seconds > 0:
            args.extend(["-rw_timeout", str(int(rw_timeout_seconds) * 1_000_000)])
    args.extend(["-i", source, "-t", str(max(1, seconds)), "-vn", "-ac", "1"])
    args.extend(["-ar", str(_SAMPLE_RATE), "-f", "s16le", "pipe:1"])
    return args


def build_trim_command(ffmpeg: str, source: Path, out_path: Path, seconds: float) -> list[str]:
    """ffmpeg argv that copies *source* without its first *seconds* (pure).

    A stream copy: no decode, no re-encode, so the trimmed file is the same
    audio, bit for bit, minus its opening."""
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-ss",
        f"{max(0.0, seconds):.2f}",
        "-i",
        str(source),
        "-map",
        "0:a",
        "-c",
        "copy",
        str(out_path),
    ]
