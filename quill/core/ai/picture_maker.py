"""The Picture Maker, without a window: one implementation for every app (wordpress.md 6.9).

QUILL Studio had this inside its own mixin. It moved here so QUILL, QUILL Lite
(File > WordPress > Media and Files > Picture Maker) and Studio all make a
picture the same way: the same provider choice, the same approval sentence,
the same file names, the same description file beside each picture. The
window is :class:`quill.ui.studio_picture_maker.PictureMakerDialog`, also
shared; each app only says where requests are approved and run.

Nothing here sends anything by itself. :func:`make_picture` is called on a
worker after the person approved :func:`consent_message`, and it saves the
picture on this computer only -- it never uploads and never changes a page.
"""

from __future__ import annotations

import io
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from quill.core.ai.image_generation import (
    DEFAULT_HOSTS,
    DEFAULT_MODELS,
    ImageProvider,
    ImageRequest,
    conversation_prompt,
    generate_image,
    image_provider_for,
)

__all__ = [
    "BACKGROUNDS",
    "SCREENSHOT_NOTE",
    "MadePicture",
    "PictureConnection",
    "PictureSuggestion",
    "asks_for_screenshot",
    "background_sentence",
    "consent_message",
    "make_picture",
    "parse_suggestion",
    "picture_connection",
    "save_png",
    "suggestion_prompt",
]

#: Background choices, in the order a person meets them: (key, label).
BACKGROUNDS: tuple[tuple[str, str], ...] = (
    ("normal", "Normal"),
    ("solid", "Solid colour"),
    ("transparent", "Transparent"),
)

SCREENSHOT_NOTE = (
    "A made picture is an illustration, never a screenshot. If a reader needs to see real "
    "controls, a real screenshot is the right thing. Press Make the Picture again to go ahead "
    "anyway."
)

_SCREENSHOT_WORDS = re.compile(
    r"\b(screen ?shots?|screen captures?|dialog(?:ue)? box(?:es)?|dialogs?|toolbars?|"
    r"menu bar|user interface|settings (?:page|screen|window)|app(?:lication)?'?s? "
    r"(?:screen|window|menu))\b",
    re.IGNORECASE,
)

#: How much of the page goes into Suggest from Page Content.
SUGGEST_LIMIT = 12_000


@dataclass(frozen=True)
class PictureConnection:
    """Who makes the picture: the provider, its key, and its default model."""

    provider_label: str
    image_provider: ImageProvider
    api_key: str = field(repr=False)
    #: The assistant settings behind the key, for Studio's vision description.
    settings: Any = None

    @property
    def model(self) -> str:
        return DEFAULT_MODELS[self.image_provider]

    @property
    def host(self) -> str:
        return DEFAULT_HOSTS[self.image_provider].removeprefix("https://")

    @property
    def can_make_transparent(self) -> bool:
        """OpenAI image models can; Imagen cannot (wordpress.md 6.9)."""
        return self.image_provider == "openai"


@dataclass(frozen=True)
class MadePicture:
    path: Path
    prompt: str
    description: str = ""


@dataclass(frozen=True)
class PictureSuggestion:
    description: str
    shape: str = "landscape"
    background: str = "normal"
    colour: str = ""
    why: str = ""


def picture_connection(*, own_key_provider: str = "") -> PictureConnection | str:
    """The provider that will make the picture, or the sentence saying why none can.

    The own key chosen in Choose Your AI comes first when its company makes
    pictures and its key is saved; otherwise the assistant provider set up in
    QUILL (Studio's path since roadmap V1).
    """
    from quill.core import assistant_ai

    own = image_provider_for(own_key_provider) if own_key_provider else None
    if own is not None:
        key = _key_for(own_key_provider)
        if key:
            label = "OpenAI" if own == "openai" else "Google Gemini"
            return PictureConnection(label, own, key)
    settings = assistant_ai.load_assistant_connection_settings()
    provider = str(getattr(settings, "provider", "") or "").strip()
    image_provider = image_provider_for(provider)
    if image_provider is None:
        return (
            f"Your AI provider ({provider or 'none'}) does not make pictures. Choose OpenAI "
            "or Google Gemini in AI, Set Up AI, or use your own OpenAI or Gemini key in "
            "Choose Your AI."
        )
    key = _key_for(provider)
    if not key:
        return f"No key is saved for {provider}. Add one in Choose Your AI, then try again."
    label = "OpenAI" if image_provider == "openai" else "Google Gemini"
    return PictureConnection(label, image_provider, key, settings)


def _key_for(provider: str) -> str:
    from quill.core import assistant_ai

    try:
        return str(assistant_ai.load_provider_api_key(provider) or "")
    except Exception:  # noqa: BLE001 - an unreadable store is "no key"
        return ""


def consent_message(connection: PictureConnection, *, described_by: str = "") -> str:
    """What is said before anything is sent: the provider, model, endpoint and cost."""
    after = (
        f"The picture is then sent to {described_by} to be described for you."
        if described_by
        else "The picture is then sent to your AI vision model to be described for you."
    )
    return (
        f"Send this description to {connection.provider_label} to make a picture?\n"
        f"Model: {connection.model}\nEndpoint: {connection.host}\n\n"
        f"{after}\n"
        "Service charges may apply; QUILL cannot estimate this request's price."
    )


def asks_for_screenshot(words: str) -> bool:
    """Whether the description asks for an application's screen, menu or dialog."""
    return bool(_SCREENSHOT_WORDS.search(words or ""))


def background_sentence(background: str, colour: str = "") -> str:
    if background == "solid":
        return f"Use a plain, solid {colour.strip() or 'white'} background."
    if background == "transparent":
        return "Use a transparent background, with nothing behind the subject."
    return ""


def make_picture(
    connection: PictureConnection,
    turns: Sequence[str],
    size: str,
    folder: Path,
    *,
    background: str = "normal",
    colour: str = "",
    describe: Callable[[Path, str], tuple[str | None, str | None]] | None = None,
    generate: Callable[[ImageRequest], bytes] = generate_image,
    now: Callable[[], datetime] = datetime.now,
) -> MadePicture:
    """Make one picture and save it as PNG in *folder*; on a worker, after approval.

    *describe* (``(path, prompt) -> (text, error)``) is the separate look by a
    vision model; without one the caller describes it afterwards. Either way a
    ``.description.txt`` beside the picture keeps what was asked for.
    """
    from quill.core.demo_recording import unique_path

    prompt = conversation_prompt(turns)
    extra = background_sentence(background, colour)
    if extra:
        prompt = f"{prompt}\n\n{extra}"
    request = ImageRequest(
        connection.image_provider,
        connection.api_key,
        prompt,
        size=size,
        background="transparent"
        if background == "transparent" and connection.can_make_transparent
        else "",
    )
    data = generate(request)
    folder.mkdir(parents=True, exist_ok=True)
    words = re.sub(r"[^\w ]+", "", turns[0])[:40].strip() or "Picture"
    path = unique_path(folder / f"Picture - {words} - {now():%Y-%m-%d %H%M%S}.png")
    save_png(data, path)
    text = ""
    if describe is not None:
        description, error = describe(path, DESCRIBE_MADE_PICTURE)
        text = description or f"The picture was saved, but it could not be described: {error}"
    path.with_suffix(".description.txt").write_text(
        f"Asked for:\n{prompt}\n\nDescription:\n{text}\n", encoding="utf-8"
    )
    return MadePicture(path, prompt, text)


DESCRIBE_MADE_PICTURE = (
    "Describe this picture for a blind person who asked for it, so they can judge whether it "
    "matches what they wanted: subject, layout, colours, any text exactly as written, and "
    "anything odd or missing, such as distorted hands or faces or garbled lettering."
)


def save_png(data: bytes, path: Path) -> None:
    """Save the provider's image as PNG whatever format it arrived in."""
    from PIL import Image

    with Image.open(io.BytesIO(data)) as image:
        image.save(path, format="PNG")


# --------------------------------------------------------------------------- #
# Suggest from Page Content


def suggestion_prompt(page_text: str, *, palette: Sequence[str] = ()) -> str:
    """The instruction for Suggest from Page Content; *page_text* is the page or selection."""
    text = page_text.strip()
    if len(text) > SUGGEST_LIMIT:
        text = text[:SUGGEST_LIMIT] + "\n[The rest of the page was left out.]"
    colours = f" Prefer one of the site's colours: {', '.join(palette)}." if palette else ""
    return (
        "Propose one illustration for this web page. It must be an illustration, never a "
        "fake screenshot of an application. Answer in exactly four lines and nothing else:\n"
        "Description: what to draw: the subject, the style, the colours, the arrangement, and "
        "anything to avoid, in one or two sentences.\n"
        "Shape: landscape, square or portrait.\n"
        f"Background: normal, transparent, or solid followed by a colour name.{colours}\n"
        "Why: one sentence on why this picture suits the page.\n\n"
        f"The page:\n{text}"
    )


def parse_suggestion(answer: str) -> PictureSuggestion | None:
    """The four lines of :func:`suggestion_prompt`'s answer; None when there is no description."""
    fields: dict[str, str] = {}
    for line in (answer or "").splitlines():
        name, sep, value = line.partition(":")
        key = name.strip().strip("*-# ").lower()
        if sep and key in {"description", "shape", "background", "why"} and key not in fields:
            fields[key] = value.strip().strip("*").strip()
    description = fields.get("description", "")
    if not description:
        return None
    shape_word = fields.get("shape", "").lower()
    shape = next((s for s in ("landscape", "square", "portrait") if s in shape_word), "landscape")
    background_words = fields.get("background", "").lower()
    background, colour = "normal", ""
    if "transparent" in background_words:
        background = "transparent"
    elif "solid" in background_words:
        background = "solid"
        colour = background_words.split("solid", 1)[1].strip(" ,.:-") or "white"
    return PictureSuggestion(description, shape, background, colour, fields.get("why", ""))
