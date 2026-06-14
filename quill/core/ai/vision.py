"""On-demand image description (vision) for the AI assistant (GATE-11 split).

This module holds the multimodal *describe an image* path that used to live in
``quill.core.assistant_ai``. It was extracted verbatim to keep ``assistant_ai``
under its GATE-11 module-size budget; the behavior is unchanged.

A user can point the assistant at an image and get a written description back in
the document. The request is a single multimodal chat turn: a short text
instruction plus the image bytes, base64-encoded inline. Each provider spells
the image part differently, so :func:`build_image_description_body` is a pure,
per-provider body builder (tested without a network) and :func:`describe_image`
reads the file, encodes it, and reuses the shared chat POST + retry path that
still lives in :mod:`quill.core.assistant_ai`.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from quill.core.assistant_ai import (
    _DEFAULT_MAX_TOKENS,
    _RETRY_BACKOFF_SECONDS,
    _RETRYABLE_CATEGORIES,
    AssistantConnectionSettings,
    _FetchError,
    _post_chat,
    _validate_endpoint_security,
    build_chat_headers,
    chat_endpoint,
    default_host_for_provider,
    default_model_for_provider,
)

#: The default instruction sent with an image when the caller doesn't supply one.
DEFAULT_IMAGE_DESCRIPTION_PROMPT = (
    "Describe this image in clear, plain language for a blind reader. "
    "Lead with the most important content. If the image contains text, "
    "transcribe it verbatim. Be concise but complete."
)


def _heic_to_jpeg_bytes(path: Path) -> bytes:
    """Convert a HEIC/HEIF file to JPEG bytes in memory (requires pillow-heif).

    Raises ``ImportError`` if pillow-heif is not installed, ``OSError`` if the
    file cannot be read, and ``Exception`` for any other conversion failure.
    """
    import io

    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()
    with Image.open(path) as img:
        rgb = img.convert("RGB")
        buf = io.BytesIO()
        rgb.save(buf, format="JPEG", quality=90)
        return buf.getvalue()


#: Image MIME types we are willing to send to a vision model.
_IMAGE_MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


def image_mime_for_path(path: Path) -> str:
    """Return the image MIME type for ``path`` by extension (pure).

    Defaults to ``image/png`` for unknown suffixes, which the vision providers
    accept for raw bitmap data.
    """
    return _IMAGE_MIME_BY_SUFFIX.get(path.suffix.lower(), "image/png")


def build_image_description_body(
    provider: str,
    model: str,
    prompt: str,
    image_b64: str,
    mime_type: str,
    *,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
) -> dict[str, object]:
    """Return the multimodal chat request body for a vision request (pure).

    ``image_b64`` is the base64-encoded image payload (no ``data:`` prefix).
    Each provider carries the image differently: OpenAI-compatible APIs use an
    ``image_url`` content part with a data URI, Claude uses a base64 ``image``
    source block, Gemini uses ``inline_data``, and Ollama attaches an
    ``images`` array on the message.
    """
    normalized = provider.strip().lower()
    data_uri = f"data:{mime_type};base64,{image_b64}"
    if normalized == "claude":
        return {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": image_b64,
                            },
                        },
                    ],
                }
            ],
        }
    if normalized == "gemini":
        return {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": image_b64}},
                    ],
                }
            ]
        }
    if normalized == "ollama":
        # Ollama's /api/chat takes a parallel ``images`` array of base64 strings.
        return {
            "model": model,
            "messages": [{"role": "user", "content": prompt, "images": [image_b64]}],
            "stream": False,
        }
    content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": data_uri}},
    ]
    return {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": max_tokens,
    }


def describe_image(
    settings: AssistantConnectionSettings,
    api_key: str,
    image_path: Path,
    *,
    prompt: str = DEFAULT_IMAGE_DESCRIPTION_PROMPT,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    timeout_seconds: float = 90.0,
    max_attempts: int = 3,
) -> tuple[str | None, str | None]:
    """Ask the configured vision model to describe ``image_path``.

    Returns ``(text, error)``: on success ``text`` is the description and
    ``error`` is ``None``; on failure ``text`` is ``None`` and ``error`` is a
    cause-specific message from the shared taxonomy. The image is read from
    disk, base64-encoded, and sent as a single multimodal chat turn through the
    same secured POST + retry path used for text chat.
    """
    import base64

    provider = settings.provider.strip().lower()
    if provider == "off":
        return None, "The AI provider is set to Off."
    host = (settings.host or "").strip().rstrip("/") or default_host_for_provider(provider)
    policy_error = _validate_endpoint_security(provider, host)
    if policy_error:
        return None, policy_error
    model = (settings.model or "").strip() or default_model_for_provider(provider)
    if image_path.suffix.lower() in {".heic", ".heif"}:
        try:
            raw = _heic_to_jpeg_bytes(image_path)
        except ImportError:
            return None, (
                "HEIC images require the pillow-heif package. "
                "Install it with: pip install pillow-heif"
            )
        except OSError as exc:
            return None, f"Could not read the image: {exc.strerror or exc}"
        except Exception as exc:
            return None, f"Could not convert HEIC image: {exc}"
        mime_type = "image/jpeg"
    else:
        try:
            raw = image_path.read_bytes()
        except OSError as exc:
            return None, f"Could not read the image: {exc.strerror or exc}"
        mime_type = image_mime_for_path(image_path)
    if not raw:
        return None, "The image file is empty."
    image_b64 = base64.b64encode(raw).decode("ascii")
    endpoint = chat_endpoint(provider, host, model)
    headers = build_chat_headers(provider, host, api_key)
    body = json.dumps(
        build_image_description_body(
            provider, model, prompt, image_b64, mime_type, max_tokens=max_tokens
        )
    ).encode("utf-8")

    last_error: _FetchError | None = None
    attempts = max(1, max_attempts)
    for attempt in range(attempts):
        text, error = _post_chat(endpoint, headers, body, provider, timeout_seconds=timeout_seconds)
        if error is None:
            return text, None
        last_error = error
        if error.category not in _RETRYABLE_CATEGORIES:
            break
        if attempt + 1 < attempts:
            backoff = _RETRY_BACKOFF_SECONDS[min(attempt, len(_RETRY_BACKOFF_SECONDS) - 1)]
            time.sleep(backoff)

    if last_error is None:
        return None, "Could not reach AI endpoint."
    return None, last_error.message
