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
from pathlib import Path

from quill import __version__
from quill.core.error_codes import CodedError

_USER_AGENT = f"QUILL/{__version__} (https://github.com/Community-Access/quill)"
_TIMEOUT_SECONDS = 15.0
_MAX_BYTES = 10_000_000

#: A WebVTT/SRT cue line: a sequence number, or a "00:00:01.000 --> 00:00:04.000"
#: timing line. Anything else is spoken text to keep.
_VTT_TIMING_RE = re.compile(r"^\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}")
_SRT_INDEX_RE = re.compile(r"^\d+$")


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


def _fetch_transcript_bytes(url: str) -> bytes:
    """One HTTPS GET returning raw transcript bytes -- the reviewed egress site."""
    if not url.startswith("https://"):
        raise TranscriptError("Only https:// transcript links can be fetched.")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS, context=context) as resp:
            payload: bytes = resp.read(_MAX_BYTES)
            return payload
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as error:
        raise TranscriptError(f"Could not reach that transcript file: {error}") from error


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


def fetch_and_parse_transcript(url: str, transcript_type: str, *, safe_mode: bool = False) -> str:
    """Fetch *url* and parse it in one step. Returns an empty string if *url*
    is blank (no feed-provided transcript for this episode)."""
    refuse_in_safe_mode(safe_mode)
    if not url:
        return ""
    raw_bytes = _fetch_transcript_bytes(url)
    return parse_transcript(raw_bytes, transcript_type)


# --------------------------------------------------------------------------- #
# Local transcript cache: once an episode's transcript has been fetched or
# transcribed, it is kept as a plain-text file so Search Everywhere can search
# transcripts without any network fetch, and reopening one is instant.
# --------------------------------------------------------------------------- #

_CACHE_DIRNAME = "podcast-transcripts"


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
