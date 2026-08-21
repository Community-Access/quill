"""Podcast transcripts: fetch a feed-provided ``<podcast:transcript>`` link
and convert it to plain text, or transcribe a downloaded episode with
QUILL's own offline speech engines when the feed carries none.

Same fetch/parse split as ``core/podcasts/chapters.py``: one reviewed HTTPS
GET returning raw bytes, then pure parsing of already-fetched bytes. The
Podcasting 2.0 transcript tag (already extracted onto
``PodcastEpisode.transcript_url``/``transcript_type`` by feed_reader.py) can
point at one of a handful of format types; each gets converted to the same
plain-text shape the rest of QUILL already knows how to show/edit.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from quill import __version__
from quill.core.error_codes import CodedError
from quill.core.podcasts import feed_auth

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 15.0
_MAX_BYTES = 10_000_000

#: A WebVTT/SRT cue line: a sequence number, or a "00:00:01.000 --> 00:00:04.000"
#: timing line. Anything else is spoken text to keep.
_VTT_TIMING_RE = re.compile(r"^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}")
_SRT_INDEX_RE = re.compile(r"^\d+$")

#: The same cue-timing line, but capturing, for the timed-cue parser. Hours are
#: optional because plenty of real WebVTT writes ``00:04.000 --> 00:08.000``.
_CUE_TIMING_RE = re.compile(
    r"(?:(\d{1,3}):)?(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*(?:(\d{1,3}):)?(\d{2}):(\d{2})[.,](\d{3})"
)
#: WebVTT inline markup to drop from cue text: ``<v Speaker>``, ``<i>``, and the
#: per-word timestamps YouTube emits (``<00:00:01.240>``).
_VTT_TAG_RE = re.compile(r"<[^>]*>")


class TranscriptError(CodedError):
    """A transcript document could not be fetched or was unusable."""

    code = "QUILL-PODCASTS-TRANSCRIPT"


def refuse_in_safe_mode(safe_mode: bool) -> None:
    """Raise :class:`TranscriptError` when Safe Mode is active. Fetching an
    episode's transcript document is a network service."""
    if safe_mode:
        raise TranscriptError(
            "Podcast transcripts are disabled in Safe Mode. Restart QUILL normally to use them."
        )


def _fetch_transcript_bytes(url: str, *, auth_header: str = "") -> bytes:
    """One HTTPS GET returning raw transcript bytes -- the reviewed egress site."""
    if not url.startswith("https://"):
        raise TranscriptError("Only https:// transcript links can be fetched.")
    headers = {"User-Agent": _USER_AGENT}
    if auth_header:
        headers["Authorization"] = auth_header
    request = urllib.request.Request(url, headers=headers)
    context = ssl.create_default_context()
    try:
        with feed_auth.urlopen_auth_safe(
            request, timeout=_TIMEOUT_SECONDS, context=context
        ) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
            return payload
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise TranscriptError(f"Could not reach that transcript file: {error}") from error


@dataclass(frozen=True, slots=True)
class TranscriptCue:
    """One timed line of a transcript.

    The piece this module was missing. :func:`parse_transcript` deliberately
    throws timestamps away, which is right for "open this as a QUILL document"
    and wrong for anything that follows playback: a reader cannot move its caret
    with the audio, jump playback to a line, or say "found at 12 minutes 8
    seconds" without knowing when each line is spoken.

    Times are milliseconds, matching the rest of the player stack (``duration_ms``
    on a YouTube stream, mpv's position) so nothing has to convert at a boundary.
    """

    start_ms: int
    end_ms: int
    text: str
    speaker: str = ""

    @property
    def spoken_label(self) -> str:
        """The line as a listener hears it, speaker first when there is one."""
        return f"{self.speaker}: {self.text}" if self.speaker else self.text


def cues_to_text(cues: Sequence[TranscriptCue]) -> str:
    """Flatten *cues* to the same plain text :func:`parse_transcript` returns.

    So there is one parser rather than two that drift: the text form is defined
    as the cue form with the timings dropped, not as a separate code path.
    """
    return "\n".join(cue.spoken_label for cue in cues if cue.text.strip())


def _vtt_timestamp(ms: int) -> str:
    """``HH:MM:SS.mmm``, WebVTT's form."""
    ms = max(0, int(ms))
    hours, remainder = divmod(ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def cues_to_vtt(cues: Sequence[TranscriptCue]) -> str:
    """*cues* written back out as WebVTT (pure).

    So **Save Transcript As** can offer the timed forms rather than only flat
    text: a listener who wants to keep a transcript very often wants to keep it
    in a form another player can follow, and throwing the timings away on the
    way out would be the same mistake the reader was built to correct.

    Round-trips through :func:`parse_transcript_cues`, which is what its tests
    assert -- a writer that only *looks* right is worth nothing.
    """
    lines = ["WEBVTT", ""]
    for cue in cues:
        lines.append(f"{_vtt_timestamp(cue.start_ms)} --> {_vtt_timestamp(cue.end_ms)}")
        lines.append(cue.spoken_label)
        lines.append("")
    return "\n".join(lines)


def cues_to_srt(cues: Sequence[TranscriptCue]) -> str:
    """*cues* written back out as SubRip (pure).

    SubRip differs from WebVTT in three ways that matter and no more: a 1-based
    index line before each cue, a comma rather than a point before the
    milliseconds, and no header.
    """
    lines: list[str] = []
    for number, cue in enumerate(cues, start=1):
        start = _vtt_timestamp(cue.start_ms).replace(".", ",")
        end = _vtt_timestamp(cue.end_ms).replace(".", ",")
        lines.append(str(number))
        lines.append(f"{start} --> {end}")
        lines.append(cue.spoken_label)
        lines.append("")
    return "\n".join(lines)


def cue_at(cues: Sequence[TranscriptCue], position_ms: int) -> int:
    """Index of the cue being spoken at *position_ms* (pure), or ``-1``.

    Binary search, because Follow Playback calls this on every position update
    and a transcript can run to thousands of cues. Returns the last cue that has
    started, which is what a reader wants during the gap between two cues -- the
    caret should rest on the line just spoken, not jump back to nothing.
    """
    if not cues:
        return -1
    low, high, found = 0, len(cues) - 1, -1
    while low <= high:
        middle = (low + high) // 2
        if cues[middle].start_ms <= position_ms:
            found = middle
            low = middle + 1
        else:
            high = middle - 1
    return found


def _timestamp_ms(hours: str | None, minutes: str, seconds: str, fraction: str) -> int:
    """One ``HH:MM:SS.mmm`` timestamp in milliseconds. Hours are optional --
    plenty of real WebVTT writes ``00:04.000 --> 00:08.000``."""
    return ((int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds)) * 1000) + int(fraction)


def _parse_vtt_or_srt_cues(text: str) -> list[TranscriptCue]:
    """WebVTT and SRT into cues. One parser for both, as the text path already
    does: they differ only in the decimal separator and the cue-index line."""
    cues: list[TranscriptCue] = []
    pending: tuple[int, int] | None = None
    buffer: list[str] = []

    def flush() -> None:
        if pending is not None and buffer:
            body = " ".join(buffer).strip()
            if body:
                cues.append(TranscriptCue(pending[0], pending[1], body))

    for raw_line in text.splitlines():
        line = raw_line.strip()
        timing = _CUE_TIMING_RE.search(line)
        if timing:
            flush()
            buffer = []
            groups = timing.groups()
            pending = (_timestamp_ms(*groups[:4]), _timestamp_ms(*groups[4:]))
            continue
        if not line or line == "WEBVTT" or _SRT_INDEX_RE.match(line):
            continue
        if line.startswith(("NOTE ", "STYLE", "REGION")):
            continue  # WebVTT blocks that are not spoken content
        if pending is not None:
            # Strip WebVTT inline markup (<v Speaker>, <00:00:01.000>, <i>).
            buffer.append(_VTT_TAG_RE.sub("", line))
    flush()
    return cues


def _parse_json_cues(data: object) -> list[TranscriptCue]:
    """Podcasting 2.0 JSON (``segments[]``) and YouTube ``json3`` (``events[]``).

    Two shapes, one function, because both arrive here through the same
    ``application/json`` content type and telling them apart by their keys is
    cheaper and more honest than asking the caller to know which it fetched.
    """
    if not isinstance(data, dict):
        return []
    segments = data.get("segments")
    if isinstance(segments, list):
        cues: list[TranscriptCue] = []
        for entry in segments:
            if not isinstance(entry, dict):
                continue
            body = str(entry.get("body", "")).strip()
            if not body:
                continue
            start = _seconds_to_ms(entry.get("startTime"))
            end = _seconds_to_ms(entry.get("endTime"))
            cues.append(
                TranscriptCue(start, max(end, start), body, str(entry.get("speaker", "")).strip())
            )
        return cues
    events = data.get("events")
    if isinstance(events, list):
        cues = []
        for event in events:
            if not isinstance(event, dict):
                continue
            segs = event.get("segs")
            if not isinstance(segs, list):
                continue
            body = "".join(str(seg.get("utf8", "")) for seg in segs if isinstance(seg, dict))
            body = body.replace("\n", " ").strip()
            if not body:
                continue
            start = int(event.get("tStartMs") or 0)
            duration = int(event.get("dDurationMs") or 0)
            cues.append(TranscriptCue(start, start + duration, body))
        return cues
    return []


def _seconds_to_ms(value: object) -> int:
    try:
        return int(float(value) * 1000)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def parse_transcript_cues(raw_bytes: bytes, transcript_type: str) -> list[TranscriptCue]:
    """Parse already-fetched transcript bytes into **timed** cues.

    Sits beside :func:`parse_transcript` rather than replacing it -- callers that
    only want text keep working unchanged. Understands WebVTT, SRT, Podcasting
    2.0 JSON, and YouTube's ``json3`` caption format, which is the only new
    input: it arrives free with every YouTube resolve and was being discarded.

    An unrecognised or untimed document yields ``[]`` rather than raising, so a
    caller can fall back to :func:`parse_transcript` and still show *something*.
    Only genuinely invalid JSON raises, matching :func:`parse_transcript`.
    """
    text = raw_bytes.decode("utf-8", errors="replace")
    mime = transcript_type.strip().lower()
    if mime == "application/json" or (not mime and text.lstrip().startswith("{")):
        try:
            data = json.loads(text)
        except ValueError as error:
            raise TranscriptError(f"That transcript file was not valid JSON: {error}") from error
        return _parse_json_cues(data)
    return _parse_vtt_or_srt_cues(text)


def _parse_vtt_or_srt(text: str) -> str:
    """WebVTT and SRT share the same shape closely enough for one parser:
    drop the ``WEBVTT`` header, cue index numbers, and timing lines; keep
    everything else, collapsing consecutive blank lines."""
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line == "WEBVTT":
            continue
        if _VTT_TIMING_RE.match(line) or _SRT_INDEX_RE.match(line):
            continue
        lines.append(line)
    return "\n".join(lines)


def _parse_podcast_json_transcript(data: object) -> str:
    """Podcasting 2.0's JSON transcript shape: ``{"segments": [{"speaker":
    ..., "body": "..."}, ...]}``. Falls back to an empty string for anything
    unrecognized rather than raising -- a malformed transcript shouldn't
    block playback or the rest of the episode view."""
    if not isinstance(data, dict):
        return ""
    segments = data.get("segments")
    if not isinstance(segments, list):
        return ""
    lines: list[str] = []
    for entry in segments:
        if not isinstance(entry, dict):
            continue
        body = str(entry.get("body", "")).strip()
        if not body:
            continue
        speaker = str(entry.get("speaker", "")).strip()
        lines.append(f"{speaker}: {body}" if speaker else body)
    return "\n".join(lines)


def parse_transcript(raw_bytes: bytes, transcript_type: str) -> str:
    """Parse already-fetched transcript bytes into plain text, based on the
    feed-declared MIME type. Unrecognized types are decoded as best-effort
    plain text rather than rejected -- most real-world transcript files are
    readable as text regardless of the exact declared type."""
    text = raw_bytes.decode("utf-8", errors="replace")
    mime = transcript_type.strip().lower()
    if mime == "application/json":
        try:
            data = json.loads(text)
        except ValueError as error:
            raise TranscriptError(f"That transcript file was not valid JSON: {error}") from error
        return _parse_podcast_json_transcript(data)
    if mime in ("text/vtt", "application/srt", "text/srt", "application/x-subrip"):
        return _parse_vtt_or_srt(text)
    return text.strip()


def fetch_and_parse_transcript(
    url: str, transcript_type: str, *, safe_mode: bool = False, auth_header: str = ""
) -> str:
    """Fetch *url* and parse it in one step. Returns an empty string if *url*
    is blank (no feed-provided transcript for this episode)."""
    refuse_in_safe_mode(safe_mode)
    if not url:
        return ""
    raw_bytes = _fetch_transcript_bytes(url, auth_header=auth_header)
    return parse_transcript(raw_bytes, transcript_type)


# --------------------------------------------------------------------------- #
# Local transcript cache: once an episode's transcript has been fetched or
# transcribed, it is kept as a plain-text file so Search Everywhere can search
# transcripts without any network fetch, and reopening one is instant.
# --------------------------------------------------------------------------- #

_CACHE_DIRNAME = "podcast-transcripts"


def fetch_transcript_cues(
    url: str,
    transcript_type: str,
    *,
    safe_mode: bool = False,
    auth_header: str = "",
) -> list[TranscriptCue]:
    """Fetch *url* once and parse it into timed cues.

    The counterpart of :func:`fetch_and_parse_transcript` for anything that
    follows playback. One fetch, not two: a caller that needs both the cues and
    the flat text takes the cues and calls :func:`cues_to_text`, rather than
    downloading the same file twice for two shapes of the same content.
    """
    refuse_in_safe_mode(safe_mode)
    if not url:
        return []
    raw = _fetch_transcript_bytes(url, auth_header=auth_header)
    return parse_transcript_cues(raw, transcript_type)


def _cache_dir() -> Path:
    from quill.core.paths import app_data_dir

    return app_data_dir() / _CACHE_DIRNAME


def _safe_cache_name(show_id: str, episode_guid: str) -> str:
    import hashlib

    digest = hashlib.sha256(f"{show_id}\n{episode_guid}".encode()).hexdigest()[:32]
    return f"{digest}.txt"


def save_cached_transcript(show_id: str, episode_guid: str, text: str) -> None:
    """Persist a fetched/transcribed transcript for offline search. Best
    effort: a full disk or unwritable folder must never break the transcript
    flow that just succeeded."""
    if not text.strip():
        return
    try:
        from quill.core.storage import write_text_atomic

        directory = _cache_dir()
        directory.mkdir(parents=True, exist_ok=True)
        payload = f"{show_id}\n{episode_guid}\n{text}"
        write_text_atomic(directory / _safe_cache_name(show_id, episode_guid), payload)
    except OSError:
        return


def _timed_cache_name(show_id: str, episode_guid: str) -> str:
    return f"{_safe_cache_name(show_id, episode_guid)[:-4]}.vtt"


def save_cached_transcript_vtt(show_id: str, episode_guid: str, vtt: str) -> None:
    """Keep the **timed** form of a transcript beside the flat one.

    Two caches rather than one, because the two readers want opposite things
    and neither can use the other's file. Search wants a paragraph of words and
    would otherwise match a listener's query against a timestamp; chapters want
    to know when each line is spoken and cannot work at all without it. Writing
    only the flat form -- which is what happened until now -- meant the tier
    described as "segment a transcript already on this machine" could never
    find one, because every transcript on the machine had had its timings
    thrown away on the way in.

    Best effort, like its sibling: a transcript that cannot be cached is still
    a transcript that arrived.
    """
    if not vtt.strip():
        return
    try:
        from quill.core.storage import write_text_atomic

        directory = _cache_dir()
        directory.mkdir(parents=True, exist_ok=True)
        write_text_atomic(directory / _timed_cache_name(show_id, episode_guid), vtt)
    except OSError:
        return


def load_cached_transcript_vtt(show_id: str, episode_guid: str) -> str:
    """The cached WebVTT for an episode, or ""."""
    try:
        return (_cache_dir() / _timed_cache_name(show_id, episode_guid)).read_text(encoding="utf-8")
    except OSError:
        return ""


def load_cached_transcript(show_id: str, episode_guid: str) -> str:
    """The cached transcript text for an episode, or ""."""
    try:
        raw = (_cache_dir() / _safe_cache_name(show_id, episode_guid)).read_text(encoding="utf-8")
    except OSError:
        return ""
    parts = raw.split("\n", 2)
    return parts[2] if len(parts) == 3 else ""


def iter_cached_transcripts() -> list[tuple[str, str, str]]:
    """Every cached transcript as ``(show_id, episode_guid, text)`` tuples."""
    directory = _cache_dir()
    if not directory.is_dir():
        return []
    results: list[tuple[str, str, str]] = []
    for path in sorted(directory.glob("*.txt")):
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        parts = raw.split("\n", 2)
        if len(parts) == 3 and parts[0] and parts[1]:
            results.append((parts[0], parts[1], parts[2]))
    return results
