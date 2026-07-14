"""Optional Hugging Face authentication for speech-model downloads (#617).

A free Hugging Face access token is **not** required for QUILL's speech models
(they are public and MIT-licensed), but providing one raises Hugging Face's
anonymous download rate limits and would be required if QUILL ever offered a
gated model. The token is kept in the OS credential store — never in settings
JSON — and reused by both the whisper.cpp and Faster Whisper download paths.

wx-free; the credential store is the only platform dependency, mirroring how
``quill/core/ai/diarization.py`` already reads this same credential.
"""

from __future__ import annotations

# The credential name is shared with the diarization token so a user sets it once.
HF_TOKEN_CRED = "QUILL:huggingface:token"

# Where a user creates a free access token (a "Read" token is enough for downloads).
HF_TOKEN_URL = "https://huggingface.co/settings/tokens"

RATE_LIMIT_HELP = (
    "Hugging Face is rate-limiting downloads right now. Add a free Hugging Face "
    "access token (Tools > Speech > Whisperer > Hugging Face Token...) to raise the "
    "limit, or try again in a few minutes."
)


def load_hf_token() -> str:
    """Return the stored Hugging Face token, or "" if none/unavailable."""
    try:
        from quill.platform.windows.credential_store import load_secret

        return (load_secret(HF_TOKEN_CRED) or "").strip()
    except Exception:  # noqa: BLE001 - a missing/locked store must never block a download
        return ""


def save_hf_token(token: str) -> None:
    """Store (or, when ``token`` is blank, clear) the Hugging Face token."""
    from quill.platform.windows.credential_store import delete_secret, save_secret

    token = (token or "").strip()
    if token:
        save_secret(HF_TOKEN_CRED, token)
    else:
        delete_secret(HF_TOKEN_CRED)


def looks_rate_limited(error: object) -> bool:
    """Heuristically detect an HTTP 429 / rate-limit error from any download path."""
    text = str(error).lower()
    return "429" in text or "too many requests" in text or "rate limit" in text
