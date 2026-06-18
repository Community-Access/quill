"""OpenAI Text-to-Speech integration for QUILL.

Provides chunked synthesis, streaming playback, and background MP3 export.
All network calls use urllib (tracked by GATE-9 egress audit).
"""

from __future__ import annotations

import json
import re
import ssl
import threading
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

TTS_ENDPOINT = "https://api.openai.com/v1/audio/speech"
TTS_CHUNK_CHARS = 4000  # leave 96-char headroom under the 4096 limit

VOICES: list[tuple[str, str]] = [
    ("alloy", "Alloy (neutral)"),
    ("ash", "Ash (warm male)"),
    ("ballad", "Ballad (soft)"),
    ("coral", "Coral (warm female)"),
    ("echo", "Echo (male)"),
    ("fable", "Fable (storytelling)"),
    ("nova", "Nova (female, energetic)"),
    ("onyx", "Onyx (deep male)"),
    ("sage", "Sage (calm)"),
    ("shimmer", "Shimmer (bright female)"),
    ("verse", "Verse (dynamic)"),
]

VOICE_IDS: list[str] = [v for v, _ in VOICES]
DEFAULT_VOICE = "nova"
DEFAULT_MODEL = "tts-1"
HD_MODEL = "tts-1-hd"


class TTSError(Exception):
    pass


class TTSAuthError(TTSError):
    pass


class TTSQuotaError(TTSError):
    pass


class TTSCancelledError(TTSError):
    pass


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_PARAGRAPH_BOUNDARY = re.compile(r"\n\n+")


def chunk_text(text: str, max_chars: int = TTS_CHUNK_CHARS) -> list[str]:
    """Split *text* at sentence boundaries to stay under *max_chars* per chunk.

    Splitting strategy (highest to lowest priority):
    1. Paragraph break (blank line).
    2. Sentence boundary: ". ", "! ", "? ".
    3. Word boundary (last space before limit).
    4. Hard split at limit (last resort; rare for natural prose).

    Returns a list of non-empty strings.
    """
    if not text.strip():
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break
        # Try paragraph boundary first
        para_match = None
        for m in _PARAGRAPH_BOUNDARY.finditer(remaining, 0, max_chars):
            para_match = m
        if para_match:
            chunks.append(remaining[: para_match.start()].rstrip())
            remaining = remaining[para_match.end() :]
            continue
        # Try sentence boundary
        sent_match = None
        for m in _SENTENCE_BOUNDARY.finditer(remaining, 0, max_chars):
            sent_match = m
        if sent_match:
            chunks.append(remaining[: sent_match.start() + 1].rstrip())
            remaining = remaining[sent_match.end() :]
            continue
        # Fall back to last word boundary
        space_pos = remaining.rfind(" ", 0, max_chars)
        if space_pos > 0:
            chunks.append(remaining[:space_pos])
            remaining = remaining[space_pos + 1 :]
        else:
            # Hard split
            chunks.append(remaining[:max_chars])
            remaining = remaining[max_chars:]
    return [c for c in chunks if c.strip()]


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def _tls_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    return ctx


def request_speech(
    text: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    voice: str = DEFAULT_VOICE,
    speed: float = 1.0,
) -> bytes:
    """POST one chunk to the TTS endpoint. Returns raw MP3 bytes.

    Raises TTSAuthError on 401, TTSQuotaError on 429, TTSError on other failures.
    """
    payload = json.dumps({
        "model": model,
        "input": text,
        "voice": voice,
        "speed": round(float(speed), 2),
        "response_format": "mp3",
    }).encode()
    req = Request(
        TTS_ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, context=_tls_context(), timeout=60) as resp:
            return bytes(resp.read())
    except HTTPError as exc:
        if exc.code == 401:
            raise TTSAuthError("OpenAI TTS: authentication failed (401).") from exc
        if exc.code == 429:
            raise TTSQuotaError("OpenAI TTS: rate limited (429).") from exc
        body = ""
        try:
            body = exc.read().decode(errors="replace")
        except Exception:  # noqa: BLE001
            pass
        raise TTSError(f"OpenAI TTS HTTP {exc.code}: {body[:200]}") from exc


# ---------------------------------------------------------------------------
# High-level playback
# ---------------------------------------------------------------------------


def speak_text(
    text: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    voice: str = DEFAULT_VOICE,
    speed: float = 1.0,
    on_chunk_complete: Callable[[int, int], None] | None = None,
    stop_event: threading.Event | None = None,
) -> None:
    """Chunk *text*, fetch each chunk, play sequentially via sounddevice/soundfile.

    Checks *stop_event* between chunks. Calls *on_chunk_complete(done, total)*
    after each successful chunk.

    Falls back to writing chunks to a temp file and invoking winsound if
    sounddevice is not installed.
    """
    chunks = chunk_text(text)
    if not chunks:
        return
    total = len(chunks)
    for i, chunk in enumerate(chunks):
        if stop_event and stop_event.is_set():
            raise TTSCancelledError("Playback stopped by user.")
        mp3_bytes = request_speech(chunk, api_key, model=model, voice=voice, speed=speed)
        _play_mp3_bytes(mp3_bytes, stop_event=stop_event)
        if on_chunk_complete:
            on_chunk_complete(i + 1, total)


def _play_mp3_bytes(mp3_bytes: bytes, stop_event: threading.Event | None = None) -> None:
    """Play *mp3_bytes* through the system audio output."""
    import io
    import os
    import tempfile

    try:
        import sounddevice as sd  # type: ignore[import-not-found,import-untyped]
        import soundfile as sf  # type: ignore[import-not-found,import-untyped]

        buf = io.BytesIO(mp3_bytes)
        data, samplerate = sf.read(buf, dtype="float32")
        sd.play(data, samplerate)
        sd.wait()
        return
    except ImportError:
        pass

    # Fallback: temp file + winsound (Windows) or afplay (macOS)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(mp3_bytes)
        tmp_path = tmp.name
    try:
        import sys

        if sys.platform == "win32":
            try:
                # winsound can't play MP3 natively - try Windows Media Foundation via subprocess
                import subprocess

                subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        f"(New-Object Media.SoundPlayer '{tmp_path}').PlaySync()",
                    ],
                    check=False,
                    capture_output=True,
                    timeout=120,
                )
            except Exception:  # noqa: BLE001
                pass
        elif sys.platform == "darwin":
            import subprocess

            subprocess.run(["afplay", tmp_path], check=False, timeout=120)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Background MP3 export
# ---------------------------------------------------------------------------


def export_to_mp3(
    text: str,
    output_path: str | Path,
    api_key: str,
    model: str = HD_MODEL,
    voice: str = DEFAULT_VOICE,
    speed: float = 1.0,
    cancel_event: threading.Event | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> None:
    """Convert *text* to a single MP3 file at *output_path*.

    Chunks are byte-concatenated (valid: MP3 frames are self-delimiting).
    Checks *cancel_event* between chunks and raises TTSCancelledError if set.
    """
    chunks = chunk_text(text)
    if not chunks:
        raise TTSError("No text to export.")
    total = len(chunks)
    out = Path(output_path)
    with out.open("wb") as f:
        for i, chunk in enumerate(chunks):
            if cancel_event and cancel_event.is_set():
                f.close()
                try:
                    out.unlink()
                except OSError:
                    pass
                raise TTSCancelledError("Export cancelled by user.")
            mp3_bytes = request_speech(chunk, api_key, model=model, voice=voice, speed=speed)
            f.write(mp3_bytes)
            if on_progress:
                on_progress(i + 1, total)
    if not out.exists() or out.stat().st_size == 0:
        raise TTSError("Export produced an empty file.")
