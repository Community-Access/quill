"""The AI Hub's providers in My own key (codex.md decision 20).

Every provider has a name, a capability record whose every claim names its
source (GATE-CAPS), and the right key rule; Ollama on this computer needs no
key and says "Runs on this computer. Nothing is sent."; the address of a custom
service or a local Ollama is kept per provider; and choosing a provider in My
own key is also what the advanced features use. The Ollama model list comes
from a real local boundary -- ``/api/tags`` then ``/api/show`` -- never a list
kept in QUILL.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core import assistant_ai
from quill.core.ai import connection_caps as caps
from quill.core.ai import connection_words as words
from quill.core.ai import own_key, own_key_models
from quill.core.ai import own_key_providers as okp
from quill.core.ai.picture_consent import consent_sentence

#: The real check, captured before tests/conftest.py stubs it out for every test.
_REAL_HAS_OWN_KEY = own_key.has_own_key


@pytest.fixture
def ai_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(
        assistant_ai, "assistant_connection_path", lambda: tmp_path / "assistant-connection.json"
    )
    caps.clear_model_capabilities()
    yield tmp_path
    caps.clear_model_capabilities()


# -- the table ----------------------------------------------------------------- #


def test_my_own_key_offers_the_ai_hubs_providers_after_its_first_two() -> None:
    assert own_key.OWN_KEY_PROVIDERS == (
        "openai",
        "gemini",
        "claude",
        "openrouter",
        "ollama_cloud",
        "custom",
        "ollama",
    )
    for provider in own_key.OWN_KEY_PROVIDERS:
        assert own_key.provider_name(provider) != provider
        assert own_key.normalize_provider(provider) == provider


def test_every_provider_has_a_capability_record_with_a_source_for_every_claim() -> None:
    records = caps.own_key_records()
    assert set(records) == set(okp.PROVIDERS)
    for provider, record in records.items():
        for capability in caps.CAPABILITIES:
            claim = record.claim(capability)
            assert claim.source.strip(), f"{provider}.{capability} has no source"
        assert record.claim(caps.TEXT).supported


def test_gate_caps_checks_every_own_key_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.tools import connection_caps_audit as audit

    assert audit.claim_findings() == []
    monkeypatch.setitem(caps._SRC_OWN_TEXT, "claude", "")
    found = [str(f) for f in audit.claim_findings()]
    assert any("own_key[claude].text names no source" in line for line in found)


def test_only_ollama_on_this_computer_needs_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(own_key, "has_own_key", _REAL_HAS_OWN_KEY)
    assert [p for p in okp.PROVIDERS if not okp.needs_key(p)] == ["ollama"]
    assert own_key.has_own_key("ollama") is True
    settings = SimpleNamespace(ai_own_key_provider="ollama", ai_own_key_model="")
    assert own_key.own_key_active(settings) is True


def test_ollama_says_it_runs_here_and_sends_nothing() -> None:
    record = caps.record_for(caps.OWN_KEY, own_key_provider="ollama")
    line = words.about_line(record, own_key_provider="ollama")
    assert "Runs on this computer. Nothing is sent." in line
    assert "billed" not in line
    assert "nowhere else" in consent_sentence("QUILL", caps.OWN_KEY, "ollama")
    assert "Nothing is sent" in own_key.conversation_note("ollama")
    from quill.core.ai.connection_usage import _own_key_clause

    assert _own_key_clause("ollama", None) == (
        "no limit and no bill. Runs on this computer. Nothing is sent."
    )
    assert "costs nothing" in own_key.size_warning(
        "a b c", "llama3.2", free_limit_tokens=10, provider="ollama"
    )


def test_a_hub_provider_goes_to_its_own_company() -> None:
    record = caps.record_for(caps.OWN_KEY, own_key_provider="claude")
    assert "Goes to Anthropic" in words.about_line(record, own_key_provider="claude")
    # Claude's models read pictures (2026-11-01, docs.anthropic.com vision); the
    # rest of the Hub's keyed providers are text only on this route.
    assert record.claim(caps.PICTURES).supported
    openrouter = caps.record_for(caps.OWN_KEY, own_key_provider="openrouter")
    assert not openrouter.claim(caps.PICTURES).supported
    assert own_key.key_url("openrouter") == "openrouter.ai/keys"


# -- the address ---------------------------------------------------------------- #


def test_the_address_is_kept_per_provider_and_the_hubs_is_used_until_then(
    ai_files: Path,
) -> None:
    assert okp.host_for("ollama") == "http://localhost:11434"
    assistant_ai.save_assistant_connection_settings(
        assistant_ai.AssistantConnectionSettings(
            provider="custom", host="https://llm.example.test/", model="m"
        )
    )
    assert okp.host_for("custom") == "https://llm.example.test"  # the Hub's, not lost
    okp.save_host("custom", "https://other.example.test")
    assert okp.host_for("custom") == "https://other.example.test"
    okp.save_host("ollama", "http://localhost:11434")  # the default: nothing written
    saved = json.loads(okp.hosts_path().read_text(encoding="utf-8"))
    assert saved == {"schema_version": 1, "hosts": {"custom": "https://other.example.test"}}
    okp.save_host("openai", "https://ignored.example.test")
    assert okp.host_for("openai") == "https://api.openai.com"


def test_choosing_a_provider_is_what_the_advanced_features_use(
    ai_files: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assistant_ai, "save_assistant_api_key", lambda _key: None)
    okp.save_host("ollama", "http://127.0.0.1:11500")
    okp.use_for_advanced_features("ollama", "llama3.2")
    hub = assistant_ai.load_assistant_connection_settings()
    assert (hub.provider, hub.host, hub.model) == ("ollama", "http://127.0.0.1:11500", "llama3.2")


# -- Ollama, at a real local boundary -------------------------------------------- #


class _OllamaLike(BaseHTTPRequestHandler):
    shown: list[str] = []
    chats: list[dict[str, Any]] = []

    def log_message(self, *_args: Any) -> None:
        pass

    def _send(self, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        if self.path == "/api/tags":
            names = ["llava:7b", "llama3.2:1b-instruct-q4_K_M", "mxbai-large"]
            self._send({"models": [{"name": n} for n in names]})
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802 - http.server API
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/show":
            _OllamaLike.shown.append(body["model"])
            table = {
                "llava:7b": ["completion", "vision"],
                "llama3.2:1b-instruct-q4_K_M": ["completion"],
                "mxbai-large": ["embedding"],
            }
            self._send({"capabilities": table[body["model"]]})
            return
        if self.path == "/api/chat":
            _OllamaLike.chats.append(body)
            self._send({"message": {"role": "assistant", "content": "A local summary."}})
            return
        self.send_error(404)


@pytest.fixture
def ollama_host(ai_files: Path) -> Iterator[str]:
    _OllamaLike.shown = []
    _OllamaLike.chats = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _OllamaLike)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host = f"http://127.0.0.1:{server.server_port}"
    okp.save_host("ollama", host)
    from quill.core.ai import ollama_capabilities

    ollama_capabilities._CAPABILITY_CACHE.clear()
    try:
        yield host
    finally:
        server.shutdown()
        server.server_close()


def test_ollama_models_come_from_tags_and_show_never_from_a_list(ollama_host: str) -> None:
    models, error = own_key_models.list_models("", "ollama")
    assert error == ""
    assert "mxbai-large" not in models  # /api/show says it cannot write text
    assert set(models) == {"llava:7b", "llama3.2:1b-instruct-q4_K_M"}  # instruct kept
    assert set(_OllamaLike.shown) >= {"llava:7b", "mxbai-large"}
    sees = caps.record_for(caps.OWN_KEY, own_key_provider="ollama", model="llava:7b")
    assert sees.claim(caps.PICTURES).supported
    assert "api/show" in sees.claim(caps.PICTURES).source
    text_only = caps.record_for(
        caps.OWN_KEY, own_key_provider="ollama", model="llama3.2:1b-instruct-q4_K_M"
    )
    assert not text_only.claim(caps.PICTURES).supported
    assert own_key_models.choice_label("llava:7b", "ollama") == "llava:7b"


def test_a_request_on_ollama_needs_no_key_and_stays_on_this_computer(
    ollama_host: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_key(_provider: str) -> str:
        raise AssertionError("Ollama on this computer must not read a key")

    monkeypatch.setattr(assistant_ai, "load_provider_api_key", no_key)
    answer = own_key.ask_with_own_key(
        "summarize", "The passage.", model="llama3.2:1b-instruct-q4_K_M", provider="ollama"
    )
    assert answer == "A local summary."
    assert "The passage." in json.dumps(_OllamaLike.chats[-1])


def test_a_keyed_hub_provider_with_no_key_sends_nothing(
    ai_files: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda _p: "")
    sent: list[Any] = []
    monkeypatch.setattr(assistant_ai, "generate_assistant_response", lambda *a, **k: sent.append(a))
    with pytest.raises(own_key.OwnKeyError, match="No Anthropic Claude key is saved"):
        own_key.ask_with_own_key("summarize", "x", provider="claude")
    assert sent == []
