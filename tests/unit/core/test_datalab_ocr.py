"""Tests for the consent-gated Datalab cloud OCR client (Tier 3, PRD §5.93)."""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path

import pytest

from quill.core import datalab_ocr
from quill.core.datalab_ocr import (
    DatalabCancelled,
    DatalabError,
    convert_with_datalab,
    datalab_configured,
    load_datalab_api_key,
    looks_sensitive,
)


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _opener(responses: list[dict], seen: list[str] | None = None):
    queue = list(responses)

    def _open(request, _timeout):
        if seen is not None:
            seen.append(request.full_url)
        return _FakeResponse(queue.pop(0))

    return _open


def _document(tmp_path: Path) -> Path:
    path = tmp_path / "scan.pdf"
    path.write_bytes(b"%PDF-1.4 pretend")
    return path


def test_happy_path_submits_polls_and_returns_markdown(tmp_path: Path) -> None:
    seen: list[str] = []
    opener = _opener(
        [
            {"request_id": "req-1", "request_check_url": "https://www.datalab.to/api/v1/check/1"},
            {"status": "processing"},
            {"status": "complete", "success": True, "markdown": "# Rescued", "page_count": 3},
        ],
        seen,
    )
    result = convert_with_datalab(
        _document(tmp_path),
        api_key="key",
        opener=opener,
        poll_interval=0.0,
        sleep=lambda _s: None,
    )
    assert result.content == "# Rescued"
    assert result.page_count == 3
    assert result.request_id == "req-1"
    assert seen[0].endswith("/api/v1/convert")
    assert seen[1].endswith("/check/1")


def test_missing_key_is_a_friendly_configuration_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DATALAB_API_KEY", raising=False)
    monkeypatch.setattr(datalab_ocr, "load_datalab_api_key", lambda: "")
    with pytest.raises(DatalabError) as excinfo:
        convert_with_datalab(_document(tmp_path), opener=_opener([]))
    assert "not configured" in str(excinfo.value)


def test_http_401_maps_to_rejected_key_message(tmp_path: Path) -> None:
    def _open(request, _timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "unauthorized", {}, io.BytesIO(b""))

    with pytest.raises(DatalabError) as excinfo:
        convert_with_datalab(_document(tmp_path), api_key="bad", opener=_open)
    assert "rejected the API key" in str(excinfo.value)


def test_non_https_endpoint_is_refused(tmp_path: Path) -> None:
    with pytest.raises(DatalabError) as excinfo:
        convert_with_datalab(
            _document(tmp_path),
            api_key="key",
            endpoint="http://insecure.example",
            opener=_opener([]),
        )
    assert "HTTPS" in str(excinfo.value)


def test_safe_mode_blocks_cloud_ocr(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    with pytest.raises(DatalabError) as excinfo:
        convert_with_datalab(_document(tmp_path), api_key="key", opener=_opener([]))
    assert "Safe Mode" in str(excinfo.value)


def test_cancellation_between_polls(tmp_path: Path) -> None:
    opener = _opener([
        {"request_id": "r", "request_check_url": "https://www.datalab.to/check"},
    ])
    with pytest.raises(DatalabCancelled):
        convert_with_datalab(
            _document(tmp_path),
            api_key="key",
            opener=opener,
            cancel_requested=lambda: True,
        )


def test_failed_job_maps_to_incomplete_result_message(tmp_path: Path) -> None:
    opener = _opener([
        {"request_id": "r", "request_check_url": "https://www.datalab.to/check"},
        {"status": "complete", "success": False, "error": "bad pages"},
    ])
    with pytest.raises(DatalabError) as excinfo:
        convert_with_datalab(
            _document(tmp_path), api_key="key", opener=opener, sleep=lambda _s: None
        )
    assert "incomplete result" in str(excinfo.value)


def test_empty_content_is_an_error_not_a_blank_document(tmp_path: Path) -> None:
    opener = _opener([
        {"request_id": "r", "request_check_url": "https://www.datalab.to/check"},
        {"status": "complete", "success": True, "markdown": ""},
    ])
    with pytest.raises(DatalabError) as excinfo:
        convert_with_datalab(
            _document(tmp_path), api_key="key", opener=opener, sleep=lambda _s: None
        )
    assert "empty result" in str(excinfo.value)


def test_poll_timeout_is_friendly(tmp_path: Path) -> None:
    moments = iter([0.0, 0.0, 1000.0])
    opener = _opener([
        {"request_id": "r", "request_check_url": "https://www.datalab.to/check"},
        {"status": "processing"},
    ])
    with pytest.raises(DatalabError) as excinfo:
        convert_with_datalab(
            _document(tmp_path),
            api_key="key",
            opener=opener,
            poll_timeout=10.0,
            clock=lambda: next(moments),
            sleep=lambda _s: None,
        )
    assert "taking too long" in str(excinfo.value)


def test_key_lookup_falls_back_to_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATALAB_API_KEY", "env-key")

    def _no_vault(*_a, **_k):
        raise RuntimeError("no vault")

    monkeypatch.setattr(
        "quill.platform.windows.credential_manager.load_generic_credential", _no_vault
    )
    assert load_datalab_api_key() == "env-key"


def test_datalab_configured_requires_enabled_and_key(monkeypatch) -> None:
    class _S:
        datalab_enabled = True

    monkeypatch.setattr(datalab_ocr, "load_datalab_api_key", lambda: "key")
    assert datalab_configured(_S()) is True
    monkeypatch.setattr(datalab_ocr, "load_datalab_api_key", lambda: "")
    assert datalab_configured(_S()) is False
    _S.datalab_enabled = False
    monkeypatch.setattr(datalab_ocr, "load_datalab_api_key", lambda: "key")
    assert datalab_configured(_S()) is False


def test_sensitive_filename_heuristic_never_reads_content(tmp_path: Path) -> None:
    assert looks_sensitive(tmp_path / "2025 Tax Return.pdf")
    assert looks_sensitive(tmp_path / "patient-summary.pdf")
    assert not looks_sensitive(tmp_path / "meeting-agenda.pdf")
