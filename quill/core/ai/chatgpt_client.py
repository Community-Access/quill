"""Talking to OpenAI on a ChatGPT plan: the model list, and one answer at a time.

The plan-sharing preview speaks the **Responses API**, not Chat Completions,
and it insists on two things this module never lets a caller forget:
``store=false`` (nothing is kept on OpenAI's side) and ``stream=true`` (the
answer arrives as server-sent events). QUILL sends the whole conversation with
every request rather than a ``previous_response_id``, which is what makes
``store=false`` possible.

**Images are checked before they are sent.** :func:`image_part` opens the file
with Pillow and re-encodes JPEG, PNG and WebP, so a file with a misleading
extension, odd metadata or a colour mode the API rejects never produces a
data URL that fails on the far side with a sentence nobody can act on. A GIF
is validated and sent as it is, frames and all.

wx-free and strict-typed.
"""

from __future__ import annotations

import base64
import io
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.ai.chatgpt_account import API_BASE
from quill.core.ai.chatgpt_errors import (
    ChatGptError,
    ChatGptLimitError,
    ChatGptUnavailableError,
)
from quill.core.ai.chatgpt_http import Opener, StreamOpener, get_json, stream_sse

__all__ = [
    "IMAGE_SUFFIXES",
    "ChatGptAnswer",
    "ChatGptModel",
    "image_part",
    "list_models",
    "respond",
]

MODELS_URL = f"{API_BASE}/models"
RESPONSES_URL = f"{API_BASE}/responses"

#: What Ask About an Image offers in the file picker, and what :func:`image_part` accepts.
IMAGE_SUFFIXES: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".webp", ".gif")
_MIME_BY_FORMAT = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}
_MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
#: Past this the data URL alone is bigger than the API will take.
_MAX_IMAGE_BYTES = 20 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ChatGptModel:
    """One model the account can use, as OpenAI names it and as a person reads it."""

    slug: str
    label: str


@dataclass(slots=True)
class ChatGptAnswer:
    """What came back: the text, and the count OpenAI reported."""

    text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    #: Every event type seen, in order, for the event log and for tests.
    events: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #


def _model_rows(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """``(slug, label)`` rows from either shape OpenAI has answered with.

    The plan-sharing preview lists ``{"models": [{"slug", "display_name",
    "visibility"}]}``; the ordinary API lists ``{"data": [{"id"}]}``. Both are
    read, so a change on OpenAI's side costs a person nothing.
    """
    rows: list[tuple[str, str]] = []
    listed = payload.get("models")
    if isinstance(listed, list):
        for item in listed:
            if not isinstance(item, dict):
                continue
            if str(item.get("visibility", "list") or "list") != "list":
                continue
            slug = str(item.get("slug", "") or item.get("id", "") or "").strip()
            if slug:
                rows.append((slug, str(item.get("display_name", "") or slug)))
        return rows
    data = payload.get("data")
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                slug = str(item.get("id", "") or "").strip()
                if slug:
                    rows.append((slug, slug))
    return rows


def list_models(token: str, *, opener: Opener | None = None) -> list[ChatGptModel]:
    """Every model the account can use for text, best first. Raises on failure.

    Filtered and ordered by :mod:`quill.core.ai.own_key_models`, so a ChatGPT
    plan and an own key offer the same list in the same order for the same
    account, and neither offers a model that cannot answer a passage.
    """
    from quill.core.ai.own_key_models import ordered

    rows = _model_rows(get_json(MODELS_URL, token=token, opener=opener))
    labels = dict(rows)
    slugs = ordered(slug for slug, _ in rows)
    return [ChatGptModel(slug, labels.get(slug, slug)) for slug in slugs]


# --------------------------------------------------------------------------- #
# Images
# --------------------------------------------------------------------------- #


def image_part(path: Path) -> dict[str, Any]:
    """An ``input_image`` part for *path*, validated and normalised.

    Raises ``ValueError`` with a sentence for a person when the file is
    missing, empty, not an image, or not one of the formats the API takes.
    Pillow is used when it is installed (it ships with every QUILL app); without
    it the file's bytes go as they are, typed by extension.
    """
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"There is no file at {path}.")
    raw = path.read_bytes()
    if not raw:
        raise ValueError(f"{path.name} is empty.")
    if len(raw) > _MAX_IMAGE_BYTES:
        raise ValueError(f"{path.name} is larger than 20 MB, which is more than OpenAI accepts.")
    mime = ""
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:  # pragma: no cover - Pillow ships with every app
        Image = None  # type: ignore[assignment]
        UnidentifiedImageError = OSError  # type: ignore[assignment,misc]
    if Image is not None:
        try:
            with Image.open(io.BytesIO(raw)) as probe:
                fmt = (probe.format or "").upper()
                probe.verify()
        except (UnidentifiedImageError, OSError, ValueError) as error:
            raise ValueError(f"{path.name} is not an image QUILL can read.") from error
        mime = _MIME_BY_FORMAT.get(fmt, "")
        if not mime:
            raise ValueError(
                f"{path.name} is a {fmt or 'kind of'} image; use a JPEG, PNG, WebP or GIF."
            )
        if fmt != "GIF":
            raw = _normalised(raw, fmt, path.name)
    else:
        mime = _MIME_BY_SUFFIX.get(path.suffix.lower(), "")
        if not mime:
            raise ValueError(f"{path.name} is not a JPEG, PNG, WebP or GIF.")
    encoded = base64.b64encode(raw).decode("ascii")
    return {"type": "input_image", "image_url": f"data:{mime};base64,{encoded}", "detail": "auto"}


def _normalised(raw: bytes, fmt: str, name: str) -> bytes:
    from PIL import Image

    try:
        with Image.open(io.BytesIO(raw)) as opened:
            image: Any = opened
            out = io.BytesIO()
            if fmt == "JPEG":
                if image.mode not in ("RGB", "L"):
                    image = image.convert("RGB")
                image.save(out, format="JPEG", quality=95)
            elif fmt == "PNG":
                image.save(out, format="PNG")
            else:
                if image.mode not in ("RGB", "RGBA", "L"):
                    image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
                image.save(out, format="WEBP", quality=95)
            return out.getvalue()
    except (OSError, ValueError) as error:
        raise ValueError(f"{name} could not be prepared for sending.") from error


# --------------------------------------------------------------------------- #
# One answer
# --------------------------------------------------------------------------- #


def respond(
    token: str,
    *,
    model: str,
    items: Sequence[dict[str, Any]],
    instructions: str = "",
    tools: Sequence[dict[str, Any]] = (),
    on_delta: Callable[[str], None] | None = None,
    stop: Callable[[], bool] | None = None,
    opener: StreamOpener | None = None,
) -> ChatGptAnswer:
    """One Responses API request on the plan. Blocking; run it on a worker.

    *items* is the conversation as the API takes it (``role`` and ``content``
    parts); *instructions* is the system message. The text is accumulated and
    returned whole -- a screen reader has no use for a half-sentence -- while
    *on_delta* lets a window show that something is arriving. Raises the coded
    errors in :mod:`quill.core.ai.chatgpt_errors`.
    """
    if not model.strip():
        raise ChatGptError("No model is chosen. Pick one in Use My ChatGPT Subscription first.")
    body: dict[str, Any] = {
        "model": model.strip(),
        "input": list(items),
        "store": False,
        "stream": True,
    }
    if instructions.strip():
        body["instructions"] = instructions.strip()
    if tools:
        body["tools"] = list(tools)
    answer = ChatGptAnswer()
    parts: list[str] = []
    completed = False

    def on_event(kind: str, payload: dict[str, Any]) -> None:
        nonlocal completed
        answer.events.append(kind)
        if kind == "response.output_text.delta":
            delta = str(payload.get("delta", "") or "")
            parts.append(delta)
            if on_delta is not None and delta:
                on_delta(delta)
        elif kind == "response.completed":
            completed = True
            usage = (payload.get("response") or {}).get("usage") or {}
            answer.input_tokens = int(usage.get("input_tokens", 0) or 0)
            answer.output_tokens = int(usage.get("output_tokens", 0) or 0)
        elif kind in ("response.failed", "error"):
            raise _failure(payload)

    stream_sse(RESPONSES_URL, body, token=token, on_event=on_event, stop=stop, opener=opener)
    if not completed:
        raise ChatGptError("OpenAI's answer ended before it was complete. Nothing was kept.")
    answer.text = "".join(parts).strip()
    if not answer.text:
        raise ChatGptError("OpenAI sent back an empty answer.")
    return answer


def _failure(payload: dict[str, Any]) -> ChatGptError:
    error = (payload.get("response") or {}).get("error") or payload.get("error") or {}
    if not isinstance(error, dict):
        error = {"message": str(error)}
    code = str(error.get("code", "") or "response_failed")
    message = str(error.get("message", "") or "").strip()
    if code == "subscription_sharing_usage_limit_exceeded":
        return ChatGptLimitError(message or "Your ChatGPT plan's usage limit was reached.")
    if code == "subscription_sharing_usage_unavailable":
        return ChatGptUnavailableError(message or "ChatGPT plan usage is not available right now.")
    return ChatGptError(f"OpenAI did not answer ({code}). {message}".strip())
