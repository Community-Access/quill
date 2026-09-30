"""The ChatGPT client: the model list, the streamed answer, and images."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from quill.core.ai import chatgpt_client as client
from quill.core.ai.chatgpt_errors import (
    ChatGptError,
    ChatGptLimitError,
    ChatGptSignedOutError,
    ChatGptUnavailableError,
)


def _json_opener(status: int, payload: Any):
    def opener(request):  # noqa: ANN001, ANN202
        return status, json.dumps(payload).encode("utf-8")

    return opener


def _sse(*events: dict[str, Any]) -> list[bytes]:
    lines: list[bytes] = []
    for event in events:
        lines.append(f"event: {event['type']}".encode())
        lines.append(f"data: {json.dumps(event)}".encode())
        lines.append(b"")
    return lines


def _stream_opener(lines: list[bytes]):
    seen: dict[str, Any] = {}

    def opener(request):  # noqa: ANN001, ANN202
        seen["body"] = json.loads(request.data.decode("utf-8"))
        seen["headers"] = dict(request.header_items())
        yield from lines

    opener.seen = seen  # type: ignore[attr-defined]
    return opener


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #


def test_the_plan_shape_lists_visible_models_with_their_display_names() -> None:
    payload = {
        "models": [
            {"slug": "gpt-6", "display_name": "GPT-6", "visibility": "list"},
            {"slug": "gpt-6-luna", "display_name": "Luna 6", "visibility": "list"},
            {"slug": "hidden-thing", "display_name": "Hidden", "visibility": "hidden"},
            {"slug": "whisper-1", "display_name": "Whisper", "visibility": "list"},
        ]
    }
    models = client.list_models("tok", opener=_json_opener(200, payload))
    assert [m.slug for m in models] == ["gpt-6-luna", "gpt-6"]
    assert models[0].label == "Luna 6"


def test_the_ordinary_shape_is_read_too() -> None:
    payload = {"data": [{"id": "gpt-4o"}, {"id": "gpt-6"}, {"id": "text-embedding-3"}]}
    models = client.list_models("tok", opener=_json_opener(200, payload))
    assert [m.slug for m in models] == ["gpt-6", "gpt-4o"]


def test_a_revoked_token_listing_models_says_signed_out() -> None:
    opener = _json_opener(401, {"error": {"message": "Invalid token"}})
    with pytest.raises(ChatGptSignedOutError, match="Invalid token"):
        client.list_models("tok", opener=opener)


# --------------------------------------------------------------------------- #
# One answer
# --------------------------------------------------------------------------- #


def _completed(text_parts: list[str], usage: dict[str, int] | None = None) -> list[bytes]:
    events = [{"type": "response.created"}]
    events += [{"type": "response.output_text.delta", "delta": part} for part in text_parts]
    events.append({"type": "response.completed", "response": {"usage": usage or {}}})
    return _sse(*events)


def test_an_answer_is_streamed_accumulated_and_sent_with_the_required_fields() -> None:
    opener = _stream_opener(
        _completed(["Hello, ", "world."], {"input_tokens": 12, "output_tokens": 3})
    )
    deltas: list[str] = []
    answer = client.respond(
        "tok",
        model="gpt-6",
        items=[{"role": "user", "content": [{"type": "input_text", "text": "Hi"}]}],
        instructions="Be brief.",
        tools=[{"type": "web_search"}],
        on_delta=deltas.append,
        opener=opener,
    )
    assert answer.text == "Hello, world."
    assert deltas == ["Hello, ", "world."]
    assert (answer.input_tokens, answer.output_tokens) == (12, 3)
    body = opener.seen["body"]
    assert body["store"] is False
    assert body["stream"] is True
    assert body["model"] == "gpt-6"
    assert body["instructions"] == "Be brief."
    assert body["tools"] == [{"type": "web_search"}]
    assert opener.seen["headers"]["Authorization"] == "Bearer tok"


def test_no_model_is_refused_before_anything_is_sent() -> None:
    def never(request):  # noqa: ANN001, ANN202
        raise AssertionError("nothing should be sent")
        yield  # pragma: no cover

    with pytest.raises(ChatGptError, match="No model is chosen"):
        client.respond("tok", model="", items=[], opener=never)


def test_a_stream_that_ends_early_is_a_sentence() -> None:
    opener = _stream_opener(_sse({"type": "response.output_text.delta", "delta": "half"}))
    with pytest.raises(ChatGptError, match="before it was complete"):
        client.respond("tok", model="gpt-6", items=[], opener=opener)


def test_an_empty_answer_is_a_sentence() -> None:
    opener = _stream_opener(_completed([]))
    with pytest.raises(ChatGptError, match="empty answer"):
        client.respond("tok", model="gpt-6", items=[], opener=opener)


@pytest.mark.parametrize(
    ("code", "kind"),
    [
        ("subscription_sharing_usage_limit_exceeded", ChatGptLimitError),
        ("subscription_sharing_usage_unavailable", ChatGptUnavailableError),
        ("server_error", ChatGptError),
    ],
)
def test_a_failed_response_becomes_the_right_coded_error(code: str, kind: type) -> None:
    opener = _stream_opener(
        _sse({"type": "response.failed", "response": {"error": {"code": code, "message": "Nope"}}})
    )
    with pytest.raises(kind) as caught:
        client.respond("tok", model="gpt-6", items=[], opener=opener)
    assert caught.value.code.startswith("QUILL-AI-CHATGPT-")


def test_a_refused_request_before_any_event_is_a_coded_error() -> None:
    import urllib.error

    def refusing(request):  # noqa: ANN001, ANN202
        body = json.dumps({
            "error": {"code": "subscription_sharing_usage_limit_exceeded", "message": "Used up."}
        }).encode()
        raise urllib.error.HTTPError(request.full_url, 429, "Too Many", {}, io.BytesIO(body))
        yield  # pragma: no cover

    from quill.core.ai import chatgpt_http

    # The real stream opener is what turns an HTTPError into the coded error.
    def opener(request):  # noqa: ANN001, ANN202
        try:
            yield from refusing(request)
        except urllib.error.HTTPError as error:
            raise chatgpt_http._error_for_status(429, error.read(), request.full_url) from error

    with pytest.raises(ChatGptLimitError, match="Used up"):
        client.respond("tok", model="gpt-6", items=[], opener=opener)


def test_stop_closes_the_stream_and_says_so() -> None:
    opener = _stream_opener(_completed(["a", "b", "c"]))
    with pytest.raises(ChatGptError, match="stopped"):
        client.respond("tok", model="gpt-6", items=[], stop=lambda: True, opener=opener)


def test_a_line_that_is_not_json_does_not_end_the_stream() -> None:
    lines = [b"data: not json", b""] + _completed(["fine"])
    answer = client.respond("tok", model="gpt-6", items=[], opener=_stream_opener(lines))
    assert answer.text == "fine"
    assert "unknown" in answer.events


# --------------------------------------------------------------------------- #
# Images
# --------------------------------------------------------------------------- #


def _png(path: Path, *, mode: str = "RGB") -> Path:
    from PIL import Image

    Image.new(mode, (4, 3), (200, 10, 10) if mode == "RGB" else 0).save(path, format="PNG")
    return path


def test_an_image_becomes_a_typed_data_url(tmp_path) -> None:
    part = client.image_part(_png(tmp_path / "shot.png"))
    assert part["type"] == "input_image"
    assert part["image_url"].startswith("data:image/png;base64,")
    assert part["detail"] == "auto"
    assert not any(key.startswith("_") for key in part)


def test_the_bytes_are_trusted_over_the_extension(tmp_path) -> None:
    path = _png(tmp_path / "actually-a-png.jpg")
    part = client.image_part(path)
    assert part["image_url"].startswith("data:image/png;base64,")


def test_a_jpeg_in_an_odd_mode_is_normalised(tmp_path) -> None:
    from PIL import Image

    path = tmp_path / "cmyk.jpg"
    Image.new("CMYK", (4, 4)).save(path, format="JPEG")
    part = client.image_part(path)
    assert part["image_url"].startswith("data:image/jpeg;base64,")


@pytest.mark.parametrize(
    ("make", "said"),
    [
        (lambda p: p, "no file"),
        (lambda p: (p.write_bytes(b""), p)[1], "is empty"),
        (lambda p: (p.write_text("hello"), p)[1], "not an image"),
    ],
)
def test_a_bad_file_is_a_sentence_not_a_request(tmp_path, make, said) -> None:
    with pytest.raises(ValueError, match=said):
        client.image_part(make(tmp_path / "thing.png"))


def test_a_format_the_api_does_not_take_is_named(tmp_path) -> None:
    from PIL import Image

    path = tmp_path / "picture.bmp"
    Image.new("RGB", (2, 2)).save(path, format="BMP")
    with pytest.raises(ValueError, match="JPEG, PNG, WebP or GIF"):
        client.image_part(path)
