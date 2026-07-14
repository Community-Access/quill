"""Unit tests for quill.core.ai_chat.

Covers connectivity helpers and provider logic using mock HTTP.
All tests are offline-safe — no real network calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


def _make_mock_response(body: bytes, status: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.read.return_value = body
    mock.status = status
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class TestListModels:
    def test_openrouter_parses_model_list(self) -> None:
        from quill.core.ai_chat import list_models

        payload = json.dumps({
            "data": [
                {"id": "anthropic/claude-3-5-sonnet"},
                {"id": "openai/gpt-4o"},
                {"id": "~filtered/model"},  # tilde prefix must be filtered
            ]
        }).encode()
        mock_resp = _make_mock_response(payload)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            models = list_models("openrouter", api_key="test-key")
        ids = [m.id for m in models]
        assert "anthropic/claude-3-5-sonnet" in ids
        assert "openai/gpt-4o" in ids
        assert not any(m.id.startswith("~") for m in models), "tilde models must be filtered"

    def test_ollama_parses_tags(self) -> None:
        from quill.core.ai_chat import list_models

        payload = json.dumps({
            "models": [
                {"name": "gemma3:4b"},
                {"name": "qwen3:8b"},
            ]
        }).encode()
        mock_resp = _make_mock_response(payload)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            models = list_models("ollama_local")
        assert [m.id for m in models] == ["gemma3:4b", "qwen3:8b"]

    def test_missing_key_raises_credential_error(self) -> None:
        import pytest

        from quill.core.ai_chat import AIChatCredentialError, list_models

        with pytest.raises(AIChatCredentialError):
            list_models("openrouter", api_key="")

    def test_openai_parses_gpt_models(self) -> None:
        from quill.core.ai_chat import list_models

        payload = json.dumps({
            "data": [
                {"id": "gpt-4o"},
                {"id": "gpt-4o-mini"},
                {"id": "davinci-002"},  # older model, still returned
            ]
        }).encode()
        mock_resp = _make_mock_response(payload)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            models = list_models("openai", api_key="test-key")
        ids = [m.id for m in models]
        assert "gpt-4o" in ids
        assert "gpt-4o-mini" in ids


class TestSendPrompt:
    def test_openrouter_returns_content(self) -> None:
        from quill.core.ai_chat import send_prompt

        payload = json.dumps({"choices": [{"message": {"content": "Hello from mock"}}]}).encode()
        mock_resp = _make_mock_response(payload)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = send_prompt("openrouter", "some/model", "hi", api_key="key")
        assert result == "Hello from mock"

    def test_ollama_returns_content(self) -> None:
        from quill.core.ai_chat import send_prompt

        payload = json.dumps({"message": {"content": "Ollama says hi"}}).encode()
        mock_resp = _make_mock_response(payload)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = send_prompt("ollama_local", "gemma3:4b", "hi")
        assert result == "Ollama says hi"

    def test_reasoning_model_empty_content_falls_back_to_reasoning(self) -> None:
        from quill.core.ai_chat import send_prompt

        # gpt-oss-style: empty content, answer on the reasoning channel.
        payload = json.dumps({
            "choices": [{"message": {"content": "", "reasoning_content": "the answer"}}]
        }).encode()
        mock_resp = _make_mock_response(payload)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = send_prompt("openrouter", "some/model", "hi", api_key="key")
        assert result == "the answer"

    def test_openai_returns_content(self) -> None:
        from quill.core.ai_chat import send_prompt

        payload = json.dumps({"choices": [{"message": {"content": "OpenAI says hi"}}]}).encode()
        mock_resp = _make_mock_response(payload)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = send_prompt("openai", "gpt-4o-mini", "hi", api_key="key")
        assert result == "OpenAI says hi"

    def test_missing_key_raises_credential_error(self) -> None:
        import pytest

        from quill.core.ai_chat import AIChatCredentialError, send_prompt

        with pytest.raises(AIChatCredentialError):
            send_prompt("openrouter", "some/model", "hi", api_key="")

    def test_http_error_raises_provider_error(self) -> None:
        import urllib.error

        import pytest

        from quill.core.ai_chat import AIChatProviderError, send_prompt

        err = urllib.error.HTTPError(
            url="https://example.com", code=429, msg="Too Many Requests", hdrs=MagicMock(), fp=None
        )
        err.read = lambda: b'{"error":"quota"}'
        with patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(AIChatProviderError):
                send_prompt("openai", "gpt-4o-mini", "hi", api_key="key")

    def test_empty_choices_raises_provider_error(self) -> None:
        import pytest

        from quill.core.ai_chat import AIChatProviderError, send_prompt

        payload = json.dumps({"choices": []}).encode()
        mock_resp = _make_mock_response(payload)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(AIChatProviderError):
                send_prompt("openrouter", "some/model", "hi", api_key="key")

    def test_unknown_provider_raises(self) -> None:
        import pytest

        from quill.core.ai_chat import AIChatProviderError, send_prompt

        with pytest.raises(AIChatProviderError):
            send_prompt("nonexistent", "model", "hi")


class TestDialogContract:
    # The former Ask AI chat dialog was retired into the unified Ask Quill
    # companion; ai_chat_dialog.py now holds only the read-only AIResponseDialog.
    def test_ai_response_dialog_in_inventory(self) -> None:
        import json
        from pathlib import Path

        inv_path = Path(__file__).parent.parent / "ui" / "fixtures" / "dialog_inventory.json"
        inv = json.loads(inv_path.read_text(encoding="utf-8"))
        key = "quill/ui/ai_chat_dialog.py::AIResponseDialog.__init__::wx.Dialog"
        assert key in inv, f"AIResponseDialog not in dialog inventory: {key}"

    def test_apply_modal_ids_called(self) -> None:
        from pathlib import Path

        src = (
            Path(__file__).parent.parent.parent.parent / "quill" / "ui" / "ai_chat_dialog.py"
        ).read_text(encoding="utf-8")
        assert "apply_modal_ids" in src, "AIResponseDialog must call apply_modal_ids"

    def test_show_and_close_exposed(self) -> None:
        from pathlib import Path

        src = (
            Path(__file__).parent.parent.parent.parent / "quill" / "ui" / "ai_chat_dialog.py"
        ).read_text(encoding="utf-8")
        assert "def show(self)" in src
        assert "def close(self)" in src
