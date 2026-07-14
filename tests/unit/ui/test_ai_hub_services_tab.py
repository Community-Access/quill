"""Source contracts for the AI Hub Services tab (OCR PRD §8–§10).

Headless CI cannot import wx, so these pin the wiring that keeps the
customer-facing services surface honest: the tab exists, the API key goes to
the credential vault (never a settings file), Test Connection uploads
nothing, every provider link announces that it opens in the browser, the
service summary excludes the key, and the endpoint stays HTTPS-only.
"""

from __future__ import annotations

from pathlib import Path


def _source() -> str:
    return Path("quill/ui/ai_hub_dialog.py").read_text(encoding="utf-8")


def test_services_tab_is_registered_in_the_notebook() -> None:
    source = _source()
    assert "_build_services_tab" in source
    assert 'str(_("Services"))' in source


def _services_body() -> str:
    source = _source()
    start = source.index("def _build_services_tab")
    end = source.index("def _build_audio_tab")
    return source[start:end]


def test_api_key_goes_to_the_credential_vault_not_settings() -> None:
    body = _services_body()
    assert "save_datalab_api_key" in body
    assert "load_datalab_api_key" in body
    # The key must never be written onto the Settings object.
    assert "datalab_api_key" not in Path("quill/core/settings.py").read_text(encoding="utf-8")


def test_test_connection_never_uploads_a_document() -> None:
    body = _services_body()
    assert "no document is uploaded" in body


def test_every_provider_link_announces_the_browser() -> None:
    body = _services_body()
    assert "(opens in your browser)" in body
    for link_key in ("website", "api_keys", "pricing", "privacy", "docs", "file_types"):
        assert f'"{link_key}"' in body


def test_service_summary_excludes_the_key() -> None:
    body = _services_body()
    assert "API key value: Not included" in body


def test_endpoint_is_https_only() -> None:
    body = _services_body()
    assert "https://" in body
    assert "must start with https://" in body


def test_consent_is_described_as_every_time() -> None:
    body = _services_body()
    assert "asking you first, every time" in body or "consent" in body.lower()


def test_ai_hub_reload_folds_datalab_settings_back_into_the_live_object() -> None:
    frame = Path("quill/ui/main_frame.py").read_text(encoding="utf-8")
    start = frame.index("def open_ai_hub(")
    body = frame[start : frame.index("def open_ocr_service_settings")]
    for field_name in (
        "datalab_enabled",
        "datalab_endpoint",
        "datalab_mode",
        "datalab_output",
        "datalab_paginate",
    ):
        assert field_name in body
