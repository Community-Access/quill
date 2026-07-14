"""Google Gemini 2.5 Text-to-Speech integration for QUILL.

Mirrors :mod:`quill.core.ai.tts` (OpenAI) so the AI Voice feature can use either
provider. Gemini's TTS models return raw 24 kHz, 16-bit, mono PCM (base64 in the
response), which this module wraps into WAV. Long text is split on sentence
boundaries by the shared :mod:`quill.core.ai.tts_chunk` splitter so no request
ends mid-sentence, and concatenated chunks get a small inter-chunk gap plus a
short trailing tail so sentence endings are never clipped.

All network calls use urllib (tracked by the GATE-9 egress audit) and run only on
an explicit user action with a configured key; blocked in Safe Mode by the UI.
"""

from __future__ import annotations

import base64
import io
import json
import ssl
import threading
import wave
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from quill.core.ai.tts import (
    TTSAuthError,
    TTSCancelledError,
    TTSError,
    TTSQuotaError,
)
from quill.core.ai.tts_chunk import chunk_text

_HOST = "https://generativelanguage.googleapis.com"
_ENDPOINT = _HOST + "/v1beta/models/{model}:generateContent"
# Gemini TTS accepts large inputs; keep chunks well under the request cap so a
# single round-trip stays responsive and ends on a sentence boundary.
TTS_CHUNK_CHARS = 3000
_SAMPLE_RATE = 24000  # Gemini TTS native output
_INTER_CHUNK_GAP_S = 0.18
_FINAL_TAIL_S = 0.35

DEFAULT_MODEL = "gemini-2.5-flash-preview-tts"
PRO_MODEL = "gemini-2.5-pro-preview-tts"
DEFAULT_VOICE = "Kore"

# The 30 prebuilt Gemini TTS voices.
VOICES: list[tuple[str, str]] = [
    ("Achernar", "Achernar"),
    ("Achird", "Achird"),
    ("Algenib", "Algenib"),
    ("Algieba", "Algieba"),
    ("Alnilam", "Alnilam"),
    ("Aoede", "Aoede"),
    ("Autonoe", "Autonoe"),
    ("Callirrhoe", "Callirrhoe"),
    ("Charon", "Charon"),
    ("Despina", "Despina"),
    ("Enceladus", "Enceladus"),
    ("Erinome", "Erinome"),
    ("Fenrir", "Fenrir"),
    ("Gacrux", "Gacrux"),
    ("Iapetus", "Iapetus"),
    ("Kore", "Kore"),
    ("Laomedeia", "Laomedeia"),
    ("Leda", "Leda"),
    ("Orus", "Orus"),
    ("Puck", "Puck"),
    ("Pulcherrima", "Pulcherrima"),
    ("Rasalgethi", "Rasalgethi"),
    ("Sadachbia", "Sadachbia"),
    ("Sadaltager", "Sadaltager"),
    ("Schedar", "Schedar"),
    ("Sulafat", "Sulafat"),
    ("Umbriel", "Umbriel"),
    ("Vindemiatrix", "Vindemiatrix"),
    ("Zephyr", "Zephyr"),
    ("Zubenelgenubi", "Zubenelgenubi"),
]
VOICE_IDS: list[str] = [v for v, _ in VOICES]


def _tls_context() -> ssl.SSLContext:
    return ssl.create_default_context()


def request_speech_pcm(text: str, api_key: str, model: str, voice: str) -> bytes:
    """POST one chunk to the Gemini TTS endpoint; return raw 16-bit PCM bytes.

    Raises :class:`TTSAuthError` on 401/403, :class:`TTSQuotaError` on 429, and
    :class:`TTSError` otherwise.
    """
    body = json.dumps({
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }).encode()
    req = Request(
        _ENDPOINT.format(model=model),
        data=body,
        headers={
            "x-goog-api-key": api_key,  # header, so the key never lands in a URL/log
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, context=_tls_context(), timeout=120) as resp:
            data = json.loads(resp.read().decode())
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise TTSAuthError("Gemini TTS: authentication failed.") from exc
        if exc.code == 429:
            raise TTSQuotaError("Gemini TTS: rate limited (429).") from exc
        detail = ""
        try:
            detail = exc.read().decode(errors="replace")
        except Exception:  # noqa: BLE001
            pass
        raise TTSError(f"Gemini TTS HTTP {exc.code}: {detail[:200]}") from exc
    try:
        b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    except (KeyError, IndexError, TypeError) as exc:
        raise TTSError("Gemini TTS returned no audio data.") from exc
    return base64.b64decode(b64)


def _silence_pcm(seconds: float) -> bytes:
    return b"\x00\x00" * int(_SAMPLE_RATE * max(0.0, seconds))


def _pcm_to_wav_bytes(pcm: bytes) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(_SAMPLE_RATE)
        handle.writeframes(pcm)
    return buffer.getvalue()


def synthesize_wav_bytes(
    text: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    voice: str = DEFAULT_VOICE,
    cancel_event: threading.Event | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> bytes:
    """Synthesize *text* to a single in-memory WAV (bytes).

    Chunks are joined with a short silence gap, and a trailing tail is appended so
    the final sentence ending is not clipped.
    """
    chunks = chunk_text(text, TTS_CHUNK_CHARS)
    if not chunks:
        raise TTSError("No text to synthesize.")
    total = len(chunks)
    parts: list[bytes] = []
    for index, chunk in enumerate(chunks):
        if cancel_event is not None and cancel_event.is_set():
            raise TTSCancelledError("Synthesis cancelled by user.")
        if index:
            parts.append(_silence_pcm(_INTER_CHUNK_GAP_S))
        parts.append(request_speech_pcm(chunk, api_key, model, voice))
        if on_progress is not None:
            on_progress(index + 1, total)
    parts.append(_silence_pcm(_FINAL_TAIL_S))
    return _pcm_to_wav_bytes(b"".join(parts))


def export_to_wav(
    text: str,
    output_path: str | Path,
    api_key: str,
    model: str = DEFAULT_MODEL,
    voice: str = DEFAULT_VOICE,
    cancel_event: threading.Event | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> None:
    """Synthesize *text* and write a WAV file at *output_path*."""
    wav = synthesize_wav_bytes(
        text, api_key, model=model, voice=voice, cancel_event=cancel_event, on_progress=on_progress
    )
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(wav)
    if not out.exists() or out.stat().st_size <= 44:
        raise TTSError("Export produced an empty file.")


def speak_text(
    text: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    voice: str = DEFAULT_VOICE,
    on_chunk_complete: Callable[[int, int], None] | None = None,
    stop_event: threading.Event | None = None,
) -> None:
    """Synthesize *text* and play it, checking *stop_event* between chunks."""
    chunks = chunk_text(text, TTS_CHUNK_CHARS)
    if not chunks:
        return
    total = len(chunks)
    for index, chunk in enumerate(chunks):
        if stop_event is not None and stop_event.is_set():
            raise TTSCancelledError("Playback stopped by user.")
        pcm = request_speech_pcm(chunk, api_key, model, voice)
        _play_wav_bytes(_pcm_to_wav_bytes(pcm), stop_event=stop_event)
        if on_chunk_complete is not None:
            on_chunk_complete(index + 1, total)


def _play_wav_bytes(wav_bytes: bytes, stop_event: threading.Event | None = None) -> None:
    """Play WAV *wav_bytes* through the system audio output (best effort)."""
    try:
        import sounddevice as sd  # type: ignore[import-not-found,import-untyped]
        import soundfile as sf  # type: ignore[import-not-found,import-untyped]

        data, samplerate = sf.read(io.BytesIO(wav_bytes), dtype="float32")
        sd.play(data, samplerate)
        sd.wait()
        return
    except ImportError:
        pass
    import os
    import sys
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name
    try:
        if sys.platform == "win32":
            import winsound

            winsound.PlaySound(tmp_path, winsound.SND_FILENAME)
        elif sys.platform == "darwin":
            import subprocess

            subprocess.run(["afplay", tmp_path], check=False, timeout=300)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
