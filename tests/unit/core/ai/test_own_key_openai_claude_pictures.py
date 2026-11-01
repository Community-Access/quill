"""OpenAI and Claude own keys send pictures (2026-11-01, the Image Description Toolkit
proposal, idea 7): the capability claims cite each provider's vision page, the
request path is the shared vision client, and the picture is sized per provider."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from quill.core import assistant_ai
from quill.core.ai import connection_caps as caps
from quill.core.ai import own_key, picture_prep, vision


@pytest.mark.parametrize("provider", ["openai", "claude"])
def test_the_key_describes_through_the_vision_client(monkeypatch, tmp_path, provider) -> None:
    seen: list[tuple[str, str]] = []

    def fake_describe(settings, api_key, image_path, *, prompt, **_kw):
        seen.append((settings.provider, api_key))
        return "A red door.", ""

    monkeypatch.setattr(vision, "describe_image", fake_describe)
    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda p: "sk-test-not-real")
    picture = tmp_path / "door.jpg"
    picture.write_bytes(b"jpg")
    assert own_key.describe_image_with_own_key(picture, "What?", provider=provider) == "A red door."
    assert seen == [(provider, "sk-test-not-real")]


def test_the_request_bodies_carry_the_picture_the_way_each_provider_reads_it() -> None:
    data = base64.b64encode(b"picture").decode("ascii")
    claude = vision.build_image_description_body("claude", "m", "Describe.", data, "image/jpeg")
    block = claude["messages"][0]["content"][1]  # type: ignore[index]
    assert block == {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/jpeg", "data": data},
    }
    openai = vision.build_image_description_body("openai", "m", "Describe.", data, "image/png")
    part = openai["messages"][0]["content"][1]  # type: ignore[index]
    assert part == {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}}


def test_each_provider_gets_the_size_its_page_names() -> None:
    assert picture_prep.longest_side_for("own_key", "claude") == 1568
    assert picture_prep.longest_side_for("own_key", "openai") == 2048
    assert picture_prep.longest_side_for("own_key", "gemini") == 3072


def test_a_claude_key_fits_the_picture_before_it_goes() -> None:
    import io

    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", (4000, 2000), "white").save(out, format="JPEG")
    record = caps.record_for("own_key", own_key_provider="claude")
    prepared = picture_prep.prepare_request([out.getvalue()], record, own_key_provider="claude")
    assert max(prepared.images[0].width, prepared.images[0].height) == 1568


def test_the_switch_offer_and_menu_gate_now_count_these_keys(tmp_path: Path) -> None:
    assert caps.can(caps.record_for("own_key", own_key_provider="openai"), "pictures")
    assert caps.can(caps.record_for("own_key", own_key_provider="claude"), "pictures")
    assert not caps.can(caps.record_for("own_key", own_key_provider="ollama_cloud"), "pictures")
