import pytest

from quill.core.radio.wxindex_http import WxIndexError, http_json, refuse_in_safe_mode


def test_http_json_parses_via_injected_fetcher():
    calls = []

    def fake(url: str) -> str:
        calls.append(url)
        return '{"ok": true}'

    assert http_json("/v1/states", fetcher=fake) == {"ok": True}
    assert calls == ["https://api.wxindex.org/v1/states"]


def test_refuse_in_safe_mode_raises():
    with pytest.raises(WxIndexError):
        refuse_in_safe_mode(True)
    refuse_in_safe_mode(False)  # no raise


def test_http_json_wraps_bad_json():
    with pytest.raises(WxIndexError):
        http_json("/v1/states", fetcher=lambda url: "not json")
