from __future__ import annotations

import sys
import unittest.mock
from pathlib import Path

import pytest

from quill.core.ai.vision import (
    DEFAULT_IMAGE_DESCRIPTION_PROMPT,
    _heic_to_jpeg_bytes,
    build_image_description_body,
    describe_image,
    image_mime_for_path,
)

_B64 = "aGVsbG8="  # "hello"


def test_image_mime_for_path_known_suffixes() -> None:
    assert image_mime_for_path(Path("x.png")) == "image/png"
    assert image_mime_for_path(Path("x.JPG")) == "image/jpeg"
    assert image_mime_for_path(Path("x.jpeg")) == "image/jpeg"
    assert image_mime_for_path(Path("x.gif")) == "image/gif"
    assert image_mime_for_path(Path("x.webp")) == "image/webp"
    assert image_mime_for_path(Path("x.tiff")) == "image/tiff"


def test_image_mime_for_path_defaults_to_png() -> None:
    assert image_mime_for_path(Path("x.unknown")) == "image/png"


def test_default_prompt_mentions_blind_reader() -> None:
    assert "blind reader" in DEFAULT_IMAGE_DESCRIPTION_PROMPT.lower()


def test_openai_body_uses_image_url_data_uri() -> None:
    body = build_image_description_body(
        "openai", "gpt-4o", "Describe", _B64, "image/png", max_tokens=128
    )
    assert body["model"] == "gpt-4o"
    assert body["max_tokens"] == 128
    content = body["messages"][0]["content"]  # type: ignore[index]
    assert content[0] == {"type": "text", "text": "Describe"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"] == f"data:image/png;base64,{_B64}"


def test_claude_body_uses_base64_source_block() -> None:
    body = build_image_description_body(
        "claude", "claude-3-5-sonnet", "Describe", _B64, "image/jpeg"
    )
    assert body["model"] == "claude-3-5-sonnet"
    content = body["messages"][0]["content"]  # type: ignore[index]
    image_part = content[1]
    assert image_part["type"] == "image"
    assert image_part["source"] == {
        "type": "base64",
        "media_type": "image/jpeg",
        "data": _B64,
    }


def test_gemini_body_uses_inline_data() -> None:
    body = build_image_description_body("gemini", "gemini-1.5-pro", "Describe", _B64, "image/png")
    parts = body["contents"][0]["parts"]  # type: ignore[index]
    assert parts[0] == {"text": "Describe"}
    assert parts[1]["inline_data"] == {"mime_type": "image/png", "data": _B64}


def test_ollama_body_attaches_images_array() -> None:
    body = build_image_description_body("ollama", "llava", "Describe", _B64, "image/png")
    message = body["messages"][0]  # type: ignore[index]
    assert message["content"] == "Describe"
    assert message["images"] == [_B64]
    assert body["stream"] is False


def test_provider_match_is_case_insensitive() -> None:
    body = build_image_description_body("  Claude  ", "claude-3", "Describe", _B64, "image/png")
    assert body["messages"][0]["content"][1]["type"] == "image"  # type: ignore[index]


# --- HEIC conversion ---


def test_heic_to_jpeg_bytes_raises_import_error_without_pillow_heif(tmp_path: Path) -> None:
    dummy = tmp_path / "test.heic"
    dummy.write_bytes(b"\x00" * 16)
    with unittest.mock.patch.dict(sys.modules, {"pillow_heif": None}):
        with pytest.raises(ImportError):
            _heic_to_jpeg_bytes(dummy)


def test_heic_to_jpeg_bytes_returns_jpeg_magic(tmp_path: Path) -> None:
    pytest.importorskip("pillow_heif")
    import io

    import pillow_heif
    from PIL import Image

    # Build a minimal valid HEIC in memory and write it to a temp file.
    img = Image.new("RGB", (4, 4), color=(255, 0, 0))
    buf = io.BytesIO()
    pillow_heif.from_pillow(img).save(buf, format="HEIF")
    heic_path = tmp_path / "test.heic"
    heic_path.write_bytes(buf.getvalue())

    result = _heic_to_jpeg_bytes(heic_path)

    # JPEG files start with the SOI marker FF D8.
    assert result[:2] == b"\xff\xd8", "Expected JPEG SOI marker"


# --- Ollama vision pre-flight (dynamic /api/show capability check) ---


def _png(tmp_path: Path) -> Path:
    img = tmp_path / "selfie.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)  # a non-empty dummy image
    return img


def test_describe_image_blocks_text_only_ollama_with_actionable_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.assistant_ai import AssistantConnectionSettings

    monkeypatch.setattr(
        "quill.core.ai.ollama_capabilities.fetch_model_capabilities",
        lambda host, model, **kw: ["completion"],
    )
    settings = AssistantConnectionSettings(
        provider="ollama",
        host="http://localhost:11434",
        model="llama3.2:1b",
    )
    text, error = describe_image(settings, "", _png(tmp_path))
    assert text is None
    assert error is not None
    # The message must name the model, state it cannot read images, and steer
    # the user toward a vision model + AI Hub.
    assert "llama3.2:1b" in error
    assert "llava" in error.lower()
    assert "ai hub" in error.lower()


def test_describe_image_proceeds_for_vision_ollama(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.assistant_ai import AssistantConnectionSettings

    monkeypatch.setattr(
        "quill.core.ai.ollama_capabilities.fetch_model_capabilities",
        lambda host, model, **kw: ["completion", "vision"],
    )
    settings = AssistantConnectionSettings(
        provider="ollama",
        host="http://localhost:11434",
        model="llava:7b",
    )
    with unittest.mock.patch(
        "quill.core.ai.vision._post_chat",
        return_value=("a description", None),
    ) as posted:
        text, error = describe_image(settings, "", _png(tmp_path))
    assert error is None
    assert text == "a description"
    assert posted.called  # the request was actually sent


def test_describe_image_proceeds_when_capabilities_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Unknown capabilities (Ollama down / old version without the field) must
    # NOT block -- proceed and let the server answer. No false negatives.
    from quill.core.assistant_ai import AssistantConnectionSettings

    monkeypatch.setattr(
        "quill.core.ai.ollama_capabilities.fetch_model_capabilities",
        lambda host, model, **kw: None,
    )
    settings = AssistantConnectionSettings(
        provider="ollama",
        host="http://localhost:11434",
        model="some-model",
    )
    with unittest.mock.patch(
        "quill.core.ai.vision._post_chat",
        return_value=("a description", None),
    ):
        text, error = describe_image(settings, "", _png(tmp_path))
    assert error is None
    assert text == "a description"


def test_describe_image_does_not_probe_capabilities_for_non_ollama(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core.assistant_ai import AssistantConnectionSettings

    probed: list[tuple[str, str]] = []

    def _probe(host, model, **kw):
        probed.append((host, model))
        return ["completion", "vision"]

    monkeypatch.setattr("quill.core.ai.ollama_capabilities.fetch_model_capabilities", _probe)
    settings = AssistantConnectionSettings(
        provider="openai",
        host="https://api.openai.com",
        model="gpt-4o-mini",
    )
    with unittest.mock.patch(
        "quill.core.ai.vision._post_chat",
        return_value=("a description", None),
    ):
        describe_image(settings, "key", _png(tmp_path))
    assert probed == []  # the /api/show probe is Ollama-only
