"""ElevenLabs premium cloud TTS — host-owned SDK gateway (roadmap §4.1).

This is the **only** module that imports the official ``elevenlabs`` SDK. Per the
decided "SDK inside one gateway" posture, everything else in QUILL talks to the
provider-neutral
:mod:`quill.core.ai.cloud_tts` seam, so ElevenLabs types never leak into the editor.

Two modes: **audio export** (:func:`export_audio` — a whole document to one MP3) and
**live Read Aloud** (:func:`synthesize_wav` — one sentence to WAV bytes the read-aloud
player streams sentence-by-sentence, with per-session consent gating owned by the UI).
Voice cloning / design (ElevenDesk's IVC) is intentionally out of scope.

The gateway: retrieves the key from the caller (QUILL's protected credential store,
never the environment), constructs and owns the SDK client, translates SDK errors
into QUILL's stable :class:`~quill.core.ai.tts.TTSError`, chunks long text on safe
boundaries, and is cancelable between chunks. ``elevenlabs`` ships as an optional
extra (``pip install quill[elevenlabs]``); when it is absent the provider is inert
and any use raises a clear "install the extra" message. wx-free, strict-typed.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from quill.core.ai.tts import TTSAuthError, TTSCancelledError, TTSError, chunk_text

# Default ElevenLabs model. ``eleven_multilingual_v2`` is the high-quality narration
# model; ``eleven_turbo_v2_5`` is the faster/cheaper option.
DEFAULT_MODEL = "eleven_multilingual_v2"
TURBO_MODEL = "eleven_turbo_v2_5"
MODELS: list[tuple[str, str]] = [
    (DEFAULT_MODEL, "Multilingual v2 (high quality)"),
    (TURBO_MODEL, "Turbo v2.5 (fast)"),
]

# A small fallback list of ElevenLabs premade voices so the picker is never empty
# before the user refreshes from their own account. (Account voices are fetched on
# demand via :func:`list_voices`.) These ids are ElevenLabs' stable premade voices.
VOICES: list[tuple[str, str]] = [
    ("21m00Tcm4TlvDq8ikWAM", "Rachel"),
    ("EXAVITQu4vr4xnSDxMaL", "Bella"),
    ("ErXwobaYiN019PkySvjV", "Antoni"),
    ("MF3mGyEYCl7XYWbV9V6O", "Elli"),
    ("TxGEqnHWrfWFTfGW9XjX", "Josh"),
    ("pNInz6obpgDQGcFmaJgB", "Adam"),
    ("yoZ06aMxZJJ28mfd3POQ", "Sam"),
]
DEFAULT_VOICE = VOICES[0][0]

# Standard, broadly-available MP3 output (no premium-tier requirement).
_OUTPUT_FORMAT = "mp3_44100_128"

# Live Read Aloud plays WAV through the OS (winsound) with no ffmpeg dependency, so
# there we request raw PCM and wrap it in a WAV container ourselves. 22.05 kHz mono
# 16-bit is a good speech quality/size balance and is a non-premium output format.
_PCM_SAMPLE_RATE = 22050
_PCM_OUTPUT_FORMAT = f"pcm_{_PCM_SAMPLE_RATE}"

# Conservative per-1,000-character price for the cost estimate. ElevenLabs bills by
# character and the rate is subscription-tier dependent, so this is intentionally a
# rough upper-ish guide shown with a "~" — never a quote.
PRICE_PER_1000_CHARS_USD = 0.30

_INSTALL_HINT = (
    "ElevenLabs support needs the optional SDK. Install it with: pip install quill[elevenlabs]"
)


def available() -> bool:
    """True when the optional ``elevenlabs`` SDK is importable."""
    try:
        import elevenlabs  # noqa: F401
    except Exception:  # noqa: BLE001 - any import failure means "not available"
        return False
    return True


def estimate_cost_usd(char_count: int) -> float:
    """Rough USD estimate to synthesize *char_count* characters (approximate)."""
    return (max(0, int(char_count)) / 1000.0) * PRICE_PER_1000_CHARS_USD


def _client(api_key: str) -> object:
    """Construct and return an owned ElevenLabs SDK client.

    The key is passed explicitly (never read from ``ELEVENLABS_API_KEY``); the SDK
    talks only to ``api.elevenlabs.io`` (no alternate ``base_url``). Raises
    :class:`TTSError` if the SDK is missing or the key is blank.
    """
    if not api_key.strip():
        raise TTSAuthError("ElevenLabs API key not configured.")
    try:
        from elevenlabs.client import ElevenLabs
    except Exception as exc:  # noqa: BLE001
        raise TTSError(_INSTALL_HINT) from exc
    try:
        return ElevenLabs(api_key=api_key)  # GATE-9: reviewed ElevenLabs SDK egress
    except (TypeError, ValueError) as exc:
        raise TTSError(f"Could not initialize ElevenLabs: {exc}") from exc


def _translate_error(exc: Exception) -> TTSError:
    """Map an SDK/transport error to a stable QUILL TTS error."""
    message = str(exc) or exc.__class__.__name__
    lowered = message.lower()
    if "401" in message or "unauthor" in lowered or "api key" in lowered:
        return TTSAuthError("ElevenLabs authentication failed. Check the API key.")
    if "quota" in lowered or "429" in message or "limit" in lowered:
        return TTSError(f"ElevenLabs quota or rate limit reached: {message}")
    return TTSError(f"ElevenLabs request failed: {message}")


def _join_chunks(response: object) -> bytes:
    """Join the SDK's audio response (bytes or an iterator of byte chunks)."""
    if isinstance(response, (bytes, bytearray)):
        return bytes(response)
    try:
        return b"".join(response)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        raise _translate_error(exc) from exc


def list_voices(api_key: str) -> list[tuple[str, str]]:
    """Fetch the account's voices as ``[(voice_id, name)]`` (read-only call)."""
    client = _client(api_key)
    try:
        response = client.voices.get_all()  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        raise _translate_error(exc) from exc
    collection = getattr(response, "voices", response) or []
    voices: list[tuple[str, str]] = []
    for voice in collection:
        vid = getattr(voice, "voice_id", "") or ""
        name = getattr(voice, "name", "") or vid
        if vid:
            voices.append((str(vid), str(name)))
    return voices or list(VOICES)


def _synthesize_chunk(client: object, text: str, *, voice: str, model: str) -> bytes:
    """One ElevenLabs ``text_to_speech.convert`` call → MP3 bytes (single attempt).

    Billable generation is **not** auto-retried: a blind re-POST after the service
    already accepted the request could double-charge the user.
    """
    try:
        response = client.text_to_speech.convert(  # type: ignore[attr-defined]
            voice_id=voice,
            text=text,
            model_id=model,
            output_format=_OUTPUT_FORMAT,
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate_error(exc) from exc
    return _join_chunks(response)


def synthesize_wav(
    text: str,
    api_key: str,
    *,
    voice: str = DEFAULT_VOICE,
    model: str = DEFAULT_MODEL,
) -> bytes:
    """Synthesize one sentence to WAV bytes for live Read Aloud (roadmap §4.2).

    Requests raw PCM (a non-premium output format, no ffmpeg needed) and wraps it in a
    WAV container with the standard library, so the read-aloud player can play it
    directly through winsound. **Single attempt** — billable generation is never
    blind-retried (a re-POST after the service accepted the request could double-charge
    the user). Raises :class:`~quill.core.ai.tts.TTSError` on failure.
    """
    client = _client(api_key)
    try:
        response = client.text_to_speech.convert(  # type: ignore[attr-defined]
            voice_id=voice,
            text=text,
            model_id=model,
            output_format=_PCM_OUTPUT_FORMAT,
        )
    except Exception as exc:  # noqa: BLE001
        raise _translate_error(exc) from exc
    return _pcm_to_wav(_join_chunks(response), sample_rate=_PCM_SAMPLE_RATE)


def _pcm_to_wav(pcm: bytes, *, sample_rate: int) -> bytes:
    """Wrap 16-bit mono PCM in a WAV container (standard library only, no ffmpeg)."""
    import io
    import wave

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # 16-bit samples
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)
    return buffer.getvalue()


def export_audio(
    text: str,
    output_path: str | Path,
    api_key: str,
    *,
    model: str = DEFAULT_MODEL,
    voice: str = DEFAULT_VOICE,
    speed: float = 1.0,  # accepted for seam parity; ElevenLabs paces via the voice
    cancel_event: threading.Event | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> Path:
    """Synthesize *text* to a single MP3 at *output_path* through ElevenLabs.

    Long text is split on safe sentence boundaries and the per-chunk MP3s are
    byte-concatenated (MP3 frames are self-delimiting). Checks *cancel_event*
    between chunks. Returns the written path; raises :class:`TTSError` on failure.
    """
    chunks = chunk_text(text)
    if not chunks:
        raise TTSError("No text to export.")
    client = _client(api_key)
    out = Path(output_path)
    out = out if out.suffix.lower() == ".mp3" else out.with_suffix(".mp3")
    out.parent.mkdir(parents=True, exist_ok=True)
    total = len(chunks)
    with out.open("wb") as handle:
        for index, chunk in enumerate(chunks):
            if cancel_event is not None and cancel_event.is_set():
                handle.close()
                out.unlink(missing_ok=True)
                raise TTSCancelledError("Export cancelled by user.")
            handle.write(_synthesize_chunk(client, chunk, voice=voice, model=model))
            if on_progress is not None:
                on_progress(index + 1, total)
    if not out.exists() or out.stat().st_size == 0:
        out.unlink(missing_ok=True)
        raise TTSError("ElevenLabs export produced an empty file.")
    return out
