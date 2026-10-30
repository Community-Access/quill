"""Make a picture from a description, with the user's own AI provider (roadmap V1).

Two providers make pictures today and both are already QUILL providers, so the
key is the one the person stored in Set Up AI and nothing new is configured:

- **OpenAI** image models (``gpt-image-1`` by default), ``POST /v1/images/generations``.
- **Google Gemini** Imagen models (``imagen-4.0-generate-001`` by default),
  ``POST /v1beta/models/<model>:predict``.

One request makes one picture; it is never sent without the caller's explicit
approval (the Studio window asks every time, naming the provider, model and
endpoint), never in Safe Mode, and never on a schedule. The description of the
result comes from a *separate* look by the vision model, so a blind user is not
relying on the generator's own claims about what it drew.

Revisions ("make the background darker") are new pictures from the whole
conversation so far: the generation endpoints that accept an image to edit
differ by provider and plan, and a full description is the one thing every
provider takes.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from quill.core.error_codes import CodedError

ImageProvider = Literal["openai", "gemini"]

#: Plain-word sizes -> (OpenAI size, Gemini aspect ratio).
IMAGE_SIZES: dict[str, tuple[str, str, str]] = {
    "landscape": ("Wide, for a YouTube video (16 by 9)", "1536x1024", "16:9"),
    "square": ("Square, for a cover or social post", "1024x1024", "1:1"),
    "portrait": ("Tall, for Shorts or a phone (9 by 16)", "1024x1536", "9:16"),
}
DEFAULT_MODELS: dict[str, str] = {"openai": "gpt-image-1", "gemini": "imagen-4.0-generate-001"}
DEFAULT_HOSTS: dict[str, str] = {
    "openai": "https://api.openai.com",
    "gemini": "https://generativelanguage.googleapis.com",
}
_TIMEOUT_S = 180.0


class ImageGenerationError(CodedError):
    """A picture could not be made by the AI provider."""

    code = "QUILL-AI-IMAGE-FAILED"


@dataclass(frozen=True)
class ImageRequest:
    provider: ImageProvider
    api_key: str
    prompt: str
    size: str = "landscape"
    model: str = ""
    host: str = ""

    @property
    def effective_model(self) -> str:
        return self.model.strip() or DEFAULT_MODELS[self.provider]

    @property
    def effective_host(self) -> str:
        return (self.host.strip() or DEFAULT_HOSTS[self.provider]).rstrip("/")


def image_provider_for(provider: str) -> ImageProvider | None:
    """The image provider behind a QUILL AI provider name, or None if it has none."""
    name = provider.strip().lower()
    if name == "openai":
        return "openai"
    if name in ("gemini", "google", "google gemini"):
        return "gemini"
    return None


def conversation_prompt(turns: Sequence[str]) -> str:
    """The first description and every change asked for since, as one request."""
    cleaned = [turn.strip() for turn in turns if turn.strip()]
    if not cleaned:
        raise ImageGenerationError("Describe the picture you want first.")
    if len(cleaned) == 1:
        return cleaned[0]
    changes = "\n".join(f"- {turn}" for turn in cleaned[1:])
    return f"{cleaned[0]}\n\nWith these changes, all of them applied:\n{changes}"


def build_request(request: ImageRequest) -> tuple[str, dict[str, str], bytes]:
    """``(endpoint, headers, body)`` for one picture."""
    if not request.api_key:
        raise ImageGenerationError(
            "No key is stored for this provider. Use AI, Set Up AI to add one."
        )
    if not request.effective_host.startswith("https://"):
        raise ImageGenerationError("Pictures are only requested over a secure (https) connection.")
    _label, openai_size, aspect = IMAGE_SIZES.get(request.size, IMAGE_SIZES["landscape"])
    if request.provider == "openai":
        endpoint = f"{request.effective_host}/v1/images/generations"
        headers = {
            "Authorization": f"Bearer {request.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": request.effective_model,
            "prompt": request.prompt,
            "size": openai_size,
            "n": 1,
        }
    else:
        endpoint = f"{request.effective_host}/v1beta/models/{request.effective_model}:predict"
        headers = {"x-goog-api-key": request.api_key, "Content-Type": "application/json"}
        body = {
            "instances": [{"prompt": request.prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": aspect},
        }
    return endpoint, headers, json.dumps(body).encode("utf-8")


def parse_image(provider: ImageProvider, payload: Any) -> bytes:
    """The picture's bytes from a provider's JSON answer."""
    try:
        if provider == "openai":
            encoded = payload["data"][0]["b64_json"]
        else:
            encoded = payload["predictions"][0]["bytesBase64Encoded"]
        return base64.b64decode(encoded)
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise ImageGenerationError(
            "The provider answered, but without a picture. It may have refused the description."
        ) from error


def generate_image(request: ImageRequest, *, opener: Callable[..., Any] | None = None) -> bytes:
    """Ask the provider for one picture; its PNG (or JPEG) bytes."""
    from quill.core.assistant_ai import _context_for

    endpoint, headers, body = build_request(request)
    outgoing = Request(endpoint, data=body, headers=headers, method="POST")
    context = _context_for(endpoint)
    try:
        if opener is None:
            reply = urlopen(outgoing, timeout=_TIMEOUT_S, context=context)
        else:  # tests pass a stand-in; nothing leaves the machine
            reply = opener(outgoing, timeout=_TIMEOUT_S, context=context)
        with reply as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except HTTPError as error:
        detail = ""
        try:
            detail = json.loads(error.read().decode("utf-8", errors="replace"))["error"]["message"]
        except Exception:  # noqa: BLE001 - the status alone is still an answer
            pass
        raise ImageGenerationError(
            f"The provider refused the request ({error.code})" + (f": {detail}" if detail else ".")
        ) from error
    except (URLError, TimeoutError, OSError) as error:
        raise ImageGenerationError(f"The provider could not be reached: {error}") from error
    except json.JSONDecodeError as error:
        raise ImageGenerationError("The provider's answer could not be read.") from error
    return parse_image(request.provider, payload)
