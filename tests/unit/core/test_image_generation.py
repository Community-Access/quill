"""Make a picture with AI: requests, answers and refusals, with no network (roadmap V1)."""

from __future__ import annotations

import base64
import io
import json
from urllib.error import HTTPError

import pytest

from quill.core.ai.image_generation import (
    ImageGenerationError,
    ImageRequest,
    build_request,
    conversation_prompt,
    generate_image,
    image_provider_for,
    parse_image,
)

PNG = b"\x89PNG\r\n\x1a\nfake"


class _Reply(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def test_openai_request_shape():
    endpoint, headers, body = build_request(
        ImageRequest("openai", "sk-test", "A suitcase and a cane", size="square")
    )
    assert endpoint == "https://api.openai.com/v1/images/generations"
    assert headers["Authorization"] == "Bearer sk-test"
    data = json.loads(body)
    assert data == {
        "model": "gpt-image-1",
        "prompt": "A suitcase and a cane",
        "size": "1024x1024",
        "n": 1,
    }


def test_gemini_request_shape():
    endpoint, headers, body = build_request(
        ImageRequest("gemini", "g-key", "A cover", size="portrait")
    )
    assert endpoint.endswith("/v1beta/models/imagen-4.0-generate-001:predict")
    assert headers["x-goog-api-key"] == "g-key"
    assert json.loads(body)["parameters"]["aspectRatio"] == "9:16"


def test_refuses_without_key_or_over_plain_http():
    with pytest.raises(ImageGenerationError, match="No key"):
        build_request(ImageRequest("openai", "", "x"))
    with pytest.raises(ImageGenerationError, match="secure"):
        build_request(ImageRequest("openai", "k", "x", host="http://example.test"))


def test_answers_are_parsed_and_refusals_explained():
    encoded = base64.b64encode(PNG).decode()
    assert parse_image("openai", {"data": [{"b64_json": encoded}]}) == PNG
    assert parse_image("gemini", {"predictions": [{"bytesBase64Encoded": encoded}]}) == PNG
    with pytest.raises(ImageGenerationError, match="without a picture"):
        parse_image("openai", {"data": []})


def test_generate_uses_the_opener_and_reports_http_errors():
    encoded = base64.b64encode(PNG).decode()
    sent = []

    def opener(request, timeout, context):
        sent.append(request.full_url)
        return _Reply(json.dumps({"data": [{"b64_json": encoded}]}).encode())

    assert generate_image(ImageRequest("openai", "k", "x"), opener=opener) == PNG
    assert sent == ["https://api.openai.com/v1/images/generations"]

    def refusing(request, timeout, context):
        raise HTTPError(
            request.full_url, 400, "Bad", {}, io.BytesIO(b'{"error": {"message": "safety"}}')
        )

    with pytest.raises(ImageGenerationError, match=r"refused the request \(400\): safety"):
        generate_image(ImageRequest("openai", "k", "x"), opener=refusing)


def test_conversation_keeps_every_change():
    assert conversation_prompt(["A cover"]) == "A cover"
    prompt = conversation_prompt(["A cover", "darker background", " ", "add the title"])
    assert prompt.startswith("A cover") and "- darker background\n- add the title" in prompt
    with pytest.raises(ImageGenerationError):
        conversation_prompt([" "])


def test_only_providers_that_make_pictures_are_offered():
    assert image_provider_for("OpenAI") == "openai"
    assert image_provider_for("gemini") == "gemini"
    assert image_provider_for("anthropic") is None and image_provider_for("ollama") is None
