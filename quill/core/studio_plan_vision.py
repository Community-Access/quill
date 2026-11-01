"""Studio's picture questions on a ChatGPT plan: no key, and one click to set up.

The plan reads pictures, so Studio's screenshot inspector -- and Ask AI
questions about a video, which reduces the video to one labelled sheet of
frames -- can use it with no API key.

**Studio signs in on its own, as "QUILL Studio".** Like every family app
(:mod:`quill.core.ai.chatgpt_account` says why), it has its own client
registration, its own refresh token in the credential store, and its own row
in the person's ChatGPT settings. A sign-in QUILL or QUILL Lite made is never
used by Studio: plan usage stays with the app the person connected, and two
processes refreshing one rotating token is how OpenAI comes to see
``refresh_token_reused``. What a sibling's sign-in *does* buy is speed: the
browser is already signed in, so Studio's sign-in is one Allow
(:func:`siblings_signed_in`).

The plan's preview takes pictures in four formats up to 20 MB and nothing
else -- no video, no audio, no image generation -- so a picture that is too
big or in another format is converted here, before it is sent
(:func:`plan_ready_image`). Its refusals are said plainly and never retried
or routed elsewhere (:func:`plan_failure`): a used-up plan stops, and moving
to an API key is the person's choice, not a fallback.

wx-free and strict-typed.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.ai.chatgpt_account import USAGE_URL, ChatGptAccount
from quill.core.ai.chatgpt_errors import (
    ChatGptError,
    ChatGptLimitError,
    ChatGptSignedOutError,
    ChatGptUnavailableError,
    ChatGptUnsupportedError,
)

__all__ = [
    "PLAN_HOST",
    "PLAN_PROVIDER",
    "STUDIO_AGENT",
    "PlanConnection",
    "describe_on_plan",
    "find_plan",
    "plan_failure",
    "plan_identity",
    "plan_ready_image",
    "siblings_signed_in",
]

#: The provider name a plan connection carries, where an API connection carries "openai".
PLAN_PROVIDER = "chatgpt-plan"
PLAN_HOST = "api.openai.com"
#: The name OpenAI shows for Studio's sign-in.
STUDIO_AGENT = "QUILL Studio"

#: The plan's own ceiling on one picture, less a margin for re-encoding.
_PLAN_IMAGE_LIMIT = 19 * 1024 * 1024
_PLAN_FORMATS = {"PNG", "JPEG", "WEBP", "GIF"}
#: Past this the model scales the picture down itself, so nothing is lost.
_LONG_SIDE = 4096

_INSTRUCTIONS = (
    "You are helping a blind person in QUILL Studio understand a screenshot or a "
    "sheet of video frames. Answer in plain language suitable for a screen reader. "
    "Say what you can see, mark what you are unsure of, and never claim more than "
    "the picture shows."
)


@dataclass(frozen=True, slots=True)
class PlanConnection:
    """Studio's ChatGPT plan, shaped like a connection: provider, host, model."""

    account: ChatGptAccount

    @property
    def provider(self) -> str:
        return PLAN_PROVIDER

    @property
    def host(self) -> str:
        return PLAN_HOST

    @property
    def model(self) -> str:
        return self.account.model

    def label(self) -> str:
        """How the consent and choice dialogs name it."""
        return f"your ChatGPT plan ({self.account.state.account_label})"


def plan_identity(connection: PlanConnection) -> dict[str, str]:
    """What automatic analysis is approved for."""
    return {
        "provider": "ChatGPT plan",
        "host": PLAN_HOST,
        "model": connection.model or "the plan's first model",
    }


def find_plan(account: ChatGptAccount) -> PlanConnection | None:
    """Studio's plan, when Studio is signed in; else ``None``."""
    try:
        return PlanConnection(account) if account.signed_in else None
    except Exception:  # noqa: BLE001 - an unreadable store is "not signed in"
        return None


def siblings_signed_in(account: ChatGptAccount) -> list[str]:
    """The family apps already signed in here, which make Studio's sign-in one Allow."""
    try:
        return account.siblings_signed_in()
    except Exception:  # noqa: BLE001 - only a hint
        return []


def plan_ready_image(path: Path, folder: Path) -> Path:
    """*path* if the plan takes it as it is, else a converted copy in *folder*.

    Too big, too large in pixels, or not PNG, JPEG, WebP or GIF: the picture is
    scaled and saved as PNG, or as JPEG when even a scaled PNG is too big.
    Raises ``ValueError`` with a sentence when it is not a picture at all.
    """
    from PIL import Image, UnidentifiedImageError

    path = Path(path)
    size = path.stat().st_size
    try:
        with Image.open(path) as probe:
            fmt = (probe.format or "").upper()
            width, height = probe.size
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError(f"{path.name} is not a picture Studio can read.") from error
    if fmt in _PLAN_FORMATS and size <= _PLAN_IMAGE_LIMIT and max(width, height) <= _LONG_SIDE:
        return path
    with Image.open(path) as opened:
        image: Any = opened.convert("RGBA" if "A" in opened.getbands() else "RGB")
    scale = min(1.0, _LONG_SIDE / max(width, height))
    target = folder / f"{path.stem}-for-plan.png"
    while True:
        frame = image
        if scale < 1.0:
            frame = image.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))), Image.Resampling.LANCZOS
            )
        out = io.BytesIO()
        frame.save(out, format="PNG", optimize=True)
        if out.tell() > _PLAN_IMAGE_LIMIT:
            out = io.BytesIO()
            frame.convert("RGB").save(out, format="JPEG", quality=90)
            target = target.with_suffix(".jpg")
        if out.tell() <= _PLAN_IMAGE_LIMIT or scale < 0.05:
            break
        scale *= 0.7
    target.write_bytes(out.getvalue())
    return target


def _model_for(connection: PlanConnection) -> str:
    """The model to ask: the one chosen, else the plan's first, remembered."""
    if connection.model:
        return connection.model
    from quill.core.ai.chatgpt_client import list_models

    models = list_models(connection.account.access_token())
    if not models:
        raise ChatGptError("Your ChatGPT plan listed no models that can answer.")
    connection.account.set_model(models[0].slug)
    return models[0].slug


def describe_on_plan(
    connection: PlanConnection,
    picture: Path,
    prompt: str,
    *,
    stop: Any = None,
) -> str:
    """One picture question on the plan. Blocking; raises coded errors or ``ValueError``.

    One request, one picture: no ``temperature``, ``max_output_tokens`` or
    system item, which the plan's preview rejects, and no retry here.
    """
    from quill.core.ai.chatgpt_ai_help import respond_on_plan
    from quill.core.ai.chatgpt_client import image_part

    part = image_part(plan_ready_image(picture, Path(picture).parent))
    answer = respond_on_plan(
        connection.account,
        model=_model_for(connection),
        items=[{"role": "user", "content": [{"type": "input_text", "text": prompt}, part]}],
        instructions=_INSTRUCTIONS,
        stop=stop,
    )
    return answer.text


def plan_failure(error: ChatGptError) -> RuntimeError:
    """What to say when the plan did not answer, naming the next step.

    The result carries ``usage_url`` when the plan's usage is used up, so the
    window can offer to open ChatGPT's Usage settings.
    """
    usage_url = ""
    if isinstance(error, ChatGptLimitError):
        usage_url = USAGE_URL
        sentence = (
            "Your ChatGPT plan's usage limit has been reached, so nothing was sent. "
            "ChatGPT's Usage settings show your plan's usage. To use another AI you "
            "have set up, ask again and choose it."
        )
    elif isinstance(error, ChatGptUnavailableError):
        sentence = (
            "OpenAI could not check your ChatGPT plan's usage just now, so nothing was "
            "sent. Your sign-in is kept; try again in a little while."
        )
    elif isinstance(error, ChatGptUnsupportedError):
        sentence = (
            "Your ChatGPT plan does not take this kind of request from other apps, so "
            "nothing was sent and it was not retried. An AI provider with your own key "
            f"can answer it instead. OpenAI said: {error}"
        )
    elif isinstance(error, ChatGptSignedOutError):
        sentence = (
            "OpenAI no longer accepts Studio's ChatGPT sign-in. Choose Use My ChatGPT "
            "Subscription in the Capture menu to sign in again."
        )
    else:
        sentence = str(error) or "Your ChatGPT plan did not answer."
    failure = RuntimeError(sentence)
    failure.usage_url = usage_url  # type: ignore[attr-defined]
    return failure
