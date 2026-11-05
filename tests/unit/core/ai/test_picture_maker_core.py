"""The shared Picture Maker core (wordpress.md 6.9): provider, file, words."""

from __future__ import annotations

import io
import json
from datetime import datetime
from types import SimpleNamespace

from quill.core import assistant_ai
from quill.core.ai import image_generation as ig
from quill.core.ai import picture_maker as pm


def _png_bytes(size=(8, 4)) -> bytes:
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", size, (1, 2, 3)).save(out, format="JPEG")
    return out.getvalue()


def test_own_key_that_draws_comes_first(monkeypatch) -> None:
    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda p: f"key-{p}")
    connection = pm.picture_connection(own_key_provider="gemini")
    assert isinstance(connection, pm.PictureConnection)
    assert connection.provider_label == "Google Gemini"
    assert connection.api_key == "key-gemini"
    assert not connection.can_make_transparent
    assert "key-gemini" not in repr(connection)


def test_falls_back_to_the_set_up_provider(monkeypatch) -> None:
    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda p: f"key-{p}")
    monkeypatch.setattr(
        assistant_ai,
        "load_assistant_connection_settings",
        lambda: SimpleNamespace(provider="openai"),
    )
    connection = pm.picture_connection(own_key_provider="anthropic")
    assert isinstance(connection, pm.PictureConnection)
    assert connection.image_provider == "openai" and connection.can_make_transparent
    assert connection.model == "gpt-image-1" and connection.host == "api.openai.com"


def test_a_provider_that_cannot_draw_says_so(monkeypatch) -> None:
    monkeypatch.setattr(
        assistant_ai,
        "load_assistant_connection_settings",
        lambda: SimpleNamespace(provider="ollama"),
    )
    reason = pm.picture_connection()
    assert isinstance(reason, str) and "(ollama) does not make pictures" in reason


def test_no_key_says_so(monkeypatch) -> None:
    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda p: "")
    monkeypatch.setattr(
        assistant_ai,
        "load_assistant_connection_settings",
        lambda: SimpleNamespace(provider="openai"),
    )
    assert "No key is saved for openai" in str(pm.picture_connection())


def test_consent_names_provider_model_and_endpoint() -> None:
    message = pm.consent_message(pm.PictureConnection("OpenAI", "openai", "k"))
    assert "Send this description to OpenAI" in message
    assert "gpt-image-1" in message
    # The endpoint is named as a word of its own, not merely somewhere inside it.
    assert "api.openai.com" in {word.strip(".,;:()") for word in message.split()}
    assert "your chosen AI" in pm.consent_message(
        pm.PictureConnection("OpenAI", "openai", "k"), described_by="your chosen AI"
    )


def test_make_picture_saves_png_and_a_description_file(tmp_path) -> None:
    sent: list[ig.ImageRequest] = []

    def generate(request):
        sent.append(request)
        return _png_bytes()

    made = pm.make_picture(
        pm.PictureConnection("OpenAI", "openai", "k"),
        ["A radio mast", "make it darker"],
        "square",
        tmp_path / "pictures",
        background="transparent",
        describe=lambda path, prompt: ("A dark mast.", None),
        generate=generate,
        now=lambda: datetime(2026, 11, 4, 9, 30, 0),
    )
    assert made.path.name == "Picture - A radio mast - 2026-11-04 093000.png"
    assert made.path.read_bytes().startswith(b"\x89PNG")
    assert sent[0].background == "transparent" and sent[0].size == "square"
    assert "transparent background" in sent[0].prompt and "make it darker" in sent[0].prompt
    words = made.path.with_suffix(".description.txt").read_text(encoding="utf-8")
    assert "A dark mast." in words and made.description == "A dark mast."


def test_gemini_never_asks_for_transparent_and_solid_is_in_words(tmp_path) -> None:
    sent: list[ig.ImageRequest] = []
    pm.make_picture(
        pm.PictureConnection("Google Gemini", "gemini", "k"),
        ["A logo"],
        "square",
        tmp_path,
        background="transparent",
        generate=lambda r: sent.append(r) or _png_bytes(),
    )
    assert sent[0].background == ""
    pm.make_picture(
        pm.PictureConnection("Google Gemini", "gemini", "k"),
        ["A logo"],
        "square",
        tmp_path,
        background="solid",
        colour="navy",
        generate=lambda r: sent.append(r) or _png_bytes(),
    )
    assert "solid navy background" in sent[1].prompt


def test_a_failed_description_is_said_in_the_file(tmp_path) -> None:
    made = pm.make_picture(
        pm.PictureConnection("OpenAI", "openai", "k"),
        ["A mast"],
        "landscape",
        tmp_path,
        describe=lambda _p, _q: (None, "no vision model"),
        generate=lambda _r: _png_bytes(),
    )
    assert "could not be described: no vision model" in made.description


def test_openai_transparent_request_body() -> None:
    request = ig.ImageRequest("openai", "k", "A logo", size="square", background="transparent")
    _url, _headers, body = ig.build_request(request)
    data = json.loads(body)
    assert data["background"] == "transparent" and data["output_format"] == "png"
    plain = json.loads(ig.build_request(ig.ImageRequest("openai", "k", "A logo"))[2])
    assert "background" not in plain


def test_screenshot_requests_are_recognised() -> None:
    assert pm.asks_for_screenshot("A screenshot of the Save dialog")
    assert pm.asks_for_screenshot("the app's menu with File open")
    assert not pm.asks_for_screenshot("A radio mast at dawn")


def test_suggestion_prompt_and_parse() -> None:
    prompt = pm.suggestion_prompt("x" * (pm.SUGGEST_LIMIT + 50), palette=["Navy", "Cream"])
    assert "[The rest of the page was left out.]" in prompt and "Navy, Cream" in prompt
    found = pm.parse_suggestion(
        "**Description:** A mast at dawn\nShape: Portrait\nBackground: solid warm cream.\n"
        "Why: It matches the morning show."
    )
    assert found == pm.PictureSuggestion(
        "A mast at dawn", "portrait", "solid", "warm cream", "It matches the morning show."
    )
    assert pm.parse_suggestion("Description: A logo\nBackground: transparent").background == (
        "transparent"
    )
    assert pm.parse_suggestion("Description: A logo\nShape: odd").shape == "landscape"
    assert pm.parse_suggestion("No idea.") is None
