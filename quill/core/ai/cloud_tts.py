"""Provider-neutral cloud TTS: catalog, cost estimate, and synthesis dispatch.

The AI Voice feature can read aloud or export through OpenAI TTS
(:mod:`quill.core.ai.tts`) or Google Gemini TTS (:mod:`quill.core.ai.gemini_tts`).
This module is the thin selection layer the UI talks to: it lists the providers,
their models and voices, estimates the cost of a synthesis before it runs, and
dispatches read-aloud / export to the right backend. wx-free.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from quill.core.ai import elevenlabs_tts, gemini_tts
from quill.core.ai import tts as openai_tts

PROVIDERS: tuple[str, ...] = ("openai", "gemini", "elevenlabs")

_PROVIDER_LABELS = {"openai": "OpenAI", "gemini": "Google Gemini", "elevenlabs": "ElevenLabs"}

# Pricing for the live cost estimate. OpenAI bills per-character; Gemini bills by
# tokens, approximated from characters. Figures mirror the AI_TTS_Studio sample
# and are intentionally conservative -- the estimate is guidance, not a quote.
_OPENAI_PER_MILLION_CHARS = {"tts-1": 15.0, "tts-1-hd": 30.0}
_GEMINI_INPUT_PER_MILLION_TOKENS = {
    "gemini-2.5-flash-preview-tts": 0.50,
    "gemini-2.5-pro-preview-tts": 1.00,
}
_GEMINI_OUTPUT_PER_MILLION_TOKENS = {
    "gemini-2.5-flash-preview-tts": 10.0,
    "gemini-2.5-pro-preview-tts": 20.0,
}
# ~4 chars/token for input; audio output tokens estimated from speaking duration.
_CHARS_PER_TOKEN = 4.0
_AUDIO_TOKENS_PER_CHAR = 0.45


def provider_label(provider: str) -> str:
    return _PROVIDER_LABELS.get(provider.strip().lower(), provider)


def models_for(provider: str) -> list[str]:
    if provider == "openai":
        return [openai_tts.DEFAULT_MODEL, openai_tts.HD_MODEL]
    if provider == "gemini":
        return [gemini_tts.DEFAULT_MODEL, gemini_tts.PRO_MODEL]
    if provider == "elevenlabs":
        return [model_id for model_id, _label in elevenlabs_tts.MODELS]
    return []


def voices_for(provider: str) -> list[tuple[str, str]]:
    if provider == "openai":
        return list(openai_tts.VOICES)
    if provider == "gemini":
        return list(gemini_tts.VOICES)
    if provider == "elevenlabs":
        return list(elevenlabs_tts.VOICES)
    return []


def default_voice(provider: str) -> str:
    if provider == "openai":
        return openai_tts.DEFAULT_VOICE
    if provider == "gemini":
        return gemini_tts.DEFAULT_VOICE
    if provider == "elevenlabs":
        return elevenlabs_tts.DEFAULT_VOICE
    return ""


def default_model(provider: str) -> str:
    models = models_for(provider)
    return models[0] if models else ""


def estimate_cost_usd(provider: str, model: str, char_count: int) -> float | None:
    """Estimate the USD cost to synthesize *char_count* characters, or None.

    None means the provider/model has no known price (so the UI omits the line
    rather than implying free).
    """
    chars = max(0, int(char_count))
    if provider == "openai":
        rate = _OPENAI_PER_MILLION_CHARS.get(model)
        return None if rate is None else (chars / 1_000_000.0) * rate
    if provider == "gemini":
        in_rate = _GEMINI_INPUT_PER_MILLION_TOKENS.get(model)
        out_rate = _GEMINI_OUTPUT_PER_MILLION_TOKENS.get(model)
        if in_rate is None or out_rate is None:
            return None
        input_tokens = chars / _CHARS_PER_TOKEN
        output_tokens = chars * _AUDIO_TOKENS_PER_CHAR
        return (input_tokens / 1_000_000.0) * in_rate + (output_tokens / 1_000_000.0) * out_rate
    if provider == "elevenlabs":
        return elevenlabs_tts.estimate_cost_usd(chars)
    return None


def format_cost(cost: float | None) -> str:
    """Human label for a cost estimate (≈ to convey it is approximate)."""
    if cost is None:
        return "Estimated cost: unavailable"
    return f"Estimated cost: ~${cost:.4f}"


def speak_text(
    provider: str,
    text: str,
    api_key: str,
    *,
    model: str,
    voice: str,
    speed: float = 1.0,
    on_chunk_complete: Callable[[int, int], None] | None = None,
    stop_event: threading.Event | None = None,
) -> None:
    """Read *text* aloud through the selected provider (chunked, cancelable)."""
    if provider == "openai":
        openai_tts.speak_text(
            text,
            api_key,
            model=model,
            voice=voice,
            speed=speed,
            on_chunk_complete=on_chunk_complete,
            stop_event=stop_event,
        )
    elif provider == "gemini":
        gemini_tts.speak_text(
            text,
            api_key,
            model=model,
            voice=voice,
            on_chunk_complete=on_chunk_complete,
            stop_event=stop_event,
        )
    elif provider == "elevenlabs":
        # 1.0 scope is export only; live per-sentence Read Aloud via ElevenLabs
        # (streaming + continuous consent) is roadmap §4.2 (2.0).
        raise openai_tts.TTSError(
            "ElevenLabs is available for audio export. Live Read Aloud through "
            "ElevenLabs is planned for a future release — use Export Document as Audio."
        )
    else:
        raise openai_tts.TTSError(f"Unknown TTS provider: {provider}")


def export_audio(
    provider: str,
    text: str,
    output_path: str | Path,
    api_key: str,
    *,
    model: str,
    voice: str,
    speed: float = 1.0,
    cancel_event: threading.Event | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> Path:
    """Export *text* to an audio file, returning the written path.

    OpenAI and ElevenLabs export MP3; Gemini exports WAV (its native PCM output).
    The caller's chosen extension is honoured where the provider supports it.
    """
    out = Path(output_path)
    if provider == "elevenlabs":
        return elevenlabs_tts.export_audio(
            text,
            out,
            api_key,
            model=model,
            voice=voice,
            speed=speed,
            cancel_event=cancel_event,
            on_progress=on_progress,
        )
    if provider == "openai":
        openai_tts.export_to_mp3(
            text,
            out,
            api_key,
            model=model,
            voice=voice,
            speed=speed,
            cancel_event=cancel_event,
            on_progress=on_progress,
        )
        return out
    if provider == "gemini":
        wav_out = out if out.suffix.lower() == ".wav" else out.with_suffix(".wav")
        gemini_tts.export_to_wav(
            text,
            wav_out,
            api_key,
            model=model,
            voice=voice,
            cancel_event=cancel_event,
            on_progress=on_progress,
        )
        return wav_out
    raise openai_tts.TTSError(f"Unknown TTS provider: {provider}")
