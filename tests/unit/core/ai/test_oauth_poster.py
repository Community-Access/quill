"""Real OAuth device-flow form poster (AI-19, PRD remaining work #1)."""

from __future__ import annotations

from urllib.parse import parse_qs
from urllib.request import Request

from quill.core.ai.device_login import DeviceFlowConfig, request_device_code
from quill.core.ai.oauth_poster import post_form


def test_posts_urlencoded_body_and_parses_json() -> None:
    seen: dict[str, object] = {}

    def opener(request: Request) -> tuple[int, bytes]:
        seen["url"] = request.full_url
        seen["method"] = request.get_method()
        seen["ctype"] = request.headers.get("Content-type")
        seen["body"] = request.data
        return 200, b'{"device_code": "abc", "user_code": "WXYZ-1234"}'

    result = post_form(
        "https://example.test/device/code",
        {"client_id": "cid", "scope": "read:user"},
        opener=opener,
    )
    assert result == {"device_code": "abc", "user_code": "WXYZ-1234"}
    assert seen["method"] == "POST"
    assert seen["ctype"] == "application/x-www-form-urlencoded"
    # Body is a proper urlencoded form.
    assert parse_qs(seen["body"].decode()) == {"client_id": ["cid"], "scope": ["read:user"]}


def test_parses_error_body_from_http_error_status() -> None:
    # GitHub returns an error *status* with a JSON error body while pending.
    def opener(request: Request) -> tuple[int, bytes]:
        return 400, b'{"error": "authorization_pending"}'

    assert post_form("https://x.test/token", {}, opener=opener) == {
        "error": "authorization_pending"
    }


def test_lenient_urlencoded_reply_is_parsed() -> None:
    def opener(request: Request) -> tuple[int, bytes]:
        return 200, b"access_token=gho_xxx&token_type=bearer"

    result = post_form("https://x.test/token", {}, opener=opener)
    assert result["access_token"] == "gho_xxx"


def test_drives_device_login_state_machine() -> None:
    # The poster plugs straight into the device_login engine.
    config = DeviceFlowConfig(
        client_id="cid",
        device_authorization_url="https://x.test/device",
        token_url="https://x.test/token",
        scope="read:user",
    )

    def opener(request: Request) -> tuple[int, bytes]:
        return (
            200,
            b'{"device_code":"d","user_code":"U-123","verification_uri":"https://x.test/login"}',
        )

    grant = request_device_code(
        config, poster=lambda url, fields: post_form(url, fields, opener=opener)
    )
    assert grant.user_code == "U-123"
    assert grant.verification_uri == "https://x.test/login"
