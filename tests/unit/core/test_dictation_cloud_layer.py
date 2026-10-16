"""The cloud dictation layer (D-31): providers, secrets, consent, the recogniser.

Nothing here touches the network or the real credential store: the openers are
replaced with recorded fakes (cloud_speech_fakes.install) and the store with a
dictionary (MemoryBackend).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from cloud_speech_fakes import FakeSocket, MemoryBackend, http_error, install

from quill.core.windows_dictation.cloud import consent, credentials, registry, transport
from quill.core.windows_dictation.cloud.errors import (
    CloudAuthError,
    CloudFieldError,
    CloudNetworkError,
    CloudQuotaError,
)
from quill.core.windows_dictation.cloud.types import (
    Capabilities,
    CloudProvider,
    ProviderField,
)
from quill.core.windows_dictation.controller import DictationStartError

_KEY = "dg-test-0123456789abcdefSECRET"


class _FileProvider(CloudProvider):
    id = "fileprov"
    name = "File Provider"
    company = "File Co"

    def fields(self) -> tuple[ProviderField, ...]:
        return (
            ProviderField("key", "Key", "secret"),
            ProviderField("account", "Account file", "file"),
            ProviderField("region", "Region", "text", required=False),
        )


@pytest.fixture
def store(monkeypatch, tmp_path) -> MemoryBackend:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    return MemoryBackend(tmp_path / "speech-providers").install(monkeypatch)


# -- the list and the engine ids ------------------------------------------------ #


def test_every_provider_has_an_engine_id_and_its_facts() -> None:
    for provider in registry.providers():
        assert provider.id and provider.name and provider.company
        engine = registry.engine_id_for(provider.id)
        if provider.id == "openai":
            assert engine == "openai"
            continue
        assert engine == f"cloud-{provider.id}"
        assert registry.provider_for_engine(engine) is provider
        for spec in provider.fields():
            assert spec.help, f"{provider.id}.{spec.key} has no F1 sentence"
            assert spec.kind in ("secret", "text", "choice", "file")


def test_a_cloud_engine_is_kept_by_settings_and_says_where_speech_goes() -> None:
    from quill.core.windows_dictation.engines import cloud_line, coerce_engine, writes_punctuation

    assert coerce_engine("cloud-deepgram") == "cloud-deepgram"
    assert coerce_engine("cloud-nobody") == "moonshine"
    assert cloud_line("cloud-deepgram") == "Speech goes to Deepgram."
    assert writes_punctuation("cloud-groq")
    assert cloud_line("moonshine") == ""


# -- consent ---------------------------------------------------------------------- #


def test_the_consent_is_built_from_the_facts_and_only_claims_real_biasing() -> None:
    deepgram = registry.provider("deepgram")
    assert deepgram is not None
    text = consent.consent_text(deepgram)
    assert "Deepgram" in text and "bills you" in text and "no copy" in text
    assert "Up to 100 of your words" in text
    assert text.rstrip().endswith("?")

    plain = _FileProvider()
    assert "of your words" not in consent.consent_text(plain)


def test_consent_is_kept_per_provider_and_version() -> None:
    deepgram = registry.provider("deepgram")
    assert deepgram is not None
    assert not consent.consented(deepgram, {})
    assert consent.consented(deepgram, {"deepgram": deepgram.consent_version})
    assert not consent.consented(deepgram, {"assemblyai": 9})


def test_safe_mode_a_missing_field_and_no_consent_each_refuse(monkeypatch) -> None:
    deepgram = registry.provider("deepgram")
    assert deepgram is not None
    agreed = {"deepgram": 1}
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    assert "Safe Mode" in consent.start_problem(deepgram, {"key": _KEY}, agreed)
    monkeypatch.delenv("QUILL_SAFE_MODE")
    assert "Fill in Key" in consent.start_problem(deepgram, {"key": ""}, agreed)
    assert "not switched on" in consent.start_problem(deepgram, {"key": _KEY}, {})
    assert consent.start_problem(deepgram, {"key": _KEY}, agreed) == ""


def test_the_newest_words_go_first_and_the_rest_are_counted() -> None:
    terms, left = consent.biasing_terms(["alpha", "beta", "<gamma>", "beta", "delta"], 2)
    assert terms == ["delta", "beta"]  # the newest, each once, angle brackets gone
    assert left == 2
    assert consent.biasing_terms(["<gamma>"], 5) == (["gamma"], 0)
    assert consent.biasing_terms(["a word"], 0) == ([], 1)


def test_the_speech_line_names_the_region_when_there_is_one() -> None:
    assemblyai = registry.provider("assemblyai")
    assert assemblyai is not None
    assert consent.speech_line(assemblyai, {"region": "eu"}) == (
        "Speech goes to AssemblyAI, the European Union."
    )


# -- secrets ---------------------------------------------------------------------- #


def test_a_secret_goes_to_the_store_and_never_into_settings(store, tmp_path) -> None:
    account = tmp_path / "account.json"
    account.write_text(json.dumps({"private_key_id": "pk-id-0123456789"}), encoding="utf-8")
    provider = _FileProvider()
    plain = credentials.save(
        provider, {"key": _KEY, "account": str(account), "region": "westeurope"}
    )
    assert _KEY not in json.dumps(plain)
    assert "pk-id-0123456789" not in json.dumps(plain)
    assert plain["region"] == "westeurope"
    assert plain[credentials.SAVED_MARK] == "yes"
    assert store.secrets[credentials.secret_target("fileprov", "key")] == _KEY
    protected = credentials.protected_file("fileprov", "account")
    assert plain["account"] == str(protected)
    assert "pk-id-0123456789" not in protected.read_text(encoding="utf-8")

    values = credentials.values_for(provider, plain)
    assert values["key"] == _KEY
    assert json.loads(values["account"])["private_key_id"] == "pk-id-0123456789"

    # An empty secret field keeps what is saved; Remove forgets everything.
    credentials.save(provider, {"key": "", "region": "eastus"})
    assert store.secrets[credentials.secret_target("fileprov", "key")] == _KEY
    credentials.remove(provider)
    assert not store.secrets
    assert not protected.exists()


def test_a_saved_secret_is_scrubbed_from_logs_and_crash_bundles(store) -> None:
    from quill.stability.redaction import redact_command_arg, redact_text_for_bundle

    credentials.save(_FileProvider(), {"key": "plainwords-not-a-key-shape"})
    line = "connect failed with plainwords-not-a-key-shape in the header"
    assert "plainwords-not-a-key-shape" not in redact_text_for_bundle(line)
    assert "plainwords-not-a-key-shape" not in redact_command_arg(line)


def test_settings_never_carry_a_secret_shaped_field_back_in() -> None:
    from quill.core.windows_dictation.settings_fields import load_fields

    fields = load_fields({
        "windows_dictation_speech_providers": {
            "azure": {"region": "westeurope", "key": "leaked", "api_token": "leaked"},
            "bad": "not a mapping",
        },
        "windows_dictation_speech_provider_consent": {"azure": "1", "groq": "x"},
    })
    assert fields["windows_dictation_speech_providers"] == {"azure": {"region": "westeurope"}}
    assert fields["windows_dictation_speech_provider_consent"] == {"azure": 1}


# -- failures say which field ------------------------------------------------------ #


@pytest.mark.parametrize(
    ("status", "kind", "words"),
    [
        (401, CloudAuthError, "The key was refused. Check Key."),
        (403, CloudAuthError, "The key was refused. Check Key."),
        (429, CloudQuotaError, "out of credit"),
        (503, CloudNetworkError, "problem of its own"),
    ],
)
def test_a_failed_call_is_one_sentence_naming_the_field(status, kind, words) -> None:
    error = transport.failure(
        "Azure", http_error("https://x", status, b'{"key": "' + _KEY.encode() + b'"}')
    )
    assert isinstance(error, kind)
    assert words in error.args[0]
    assert _KEY not in str(error)
    if status in (401, 403):
        assert error.field == "Key"


def test_an_unreachable_provider_is_a_network_sentence() -> None:
    from urllib.error import URLError

    error = transport.failure("Groq", URLError("no route"))
    assert isinstance(error, CloudNetworkError)
    assert error.args[0] == "Groq could not be reached. Check the internet connection."
    assert error.fatal is False


def test_an_address_outside_the_providers_domain_is_refused() -> None:
    with pytest.raises(CloudFieldError) as caught:
        transport.require_host(
            "https://evil.example.com", (".cognitiveservices.azure.com",), field="Endpoint"
        )
    assert caught.value.field == "Endpoint"
    assert (
        transport.require_host(
            "https://mine.cognitiveservices.azure.com/",
            (".cognitiveservices.azure.com",),
            field="Endpoint",
        )
        == "https://mine.cognitiveservices.azure.com"
    )


# -- Test Connection never sends speech --------------------------------------------- #


def test_test_connection_asks_about_the_account_not_with_speech(monkeypatch) -> None:
    wire = install(monkeypatch)
    wire.answer({"projects": [{"project_id": "p"}]})
    deepgram = registry.provider("deepgram")
    assert deepgram is not None
    assert deepgram.test({"key": _KEY}) == "Deepgram answered: ready, 1 project."
    (request,) = wire.requests
    assert request.get_method() == "GET"
    assert request.data is None  # no audio, nothing of the person's
    assert request.full_url == "https://api.deepgram.com/v1/projects"
    assert not wire.sockets


def test_a_refused_key_on_test_names_the_field_without_the_key(monkeypatch) -> None:
    wire = install(monkeypatch)
    wire.answer(http_error("https://api.groq.com/openai/v1/models", 401))
    groq = registry.provider("groq")
    assert groq is not None
    with pytest.raises(CloudAuthError) as caught:
        groq.test({"key": _KEY})
    assert caught.value.args[0] == "The key was refused. Check Key."
    assert _KEY not in str(caught.value)


# -- the recogniser ---------------------------------------------------------------- #


class _Listener:
    def __init__(self) -> None:
        self.partials: list[str] = []
        self.problems: list[tuple[str, bool]] = []
        self.failures: list[str] = []

    def on_partial(self, text: str) -> None:
        self.partials.append(text)

    def on_engine_problem(self, sentence: str, fatal: bool) -> None:
        self.problems.append((sentence, fatal))

    def on_failure(self, message: str) -> None:
        self.failures.append(message)


def _recognizer(provider_id: str, values: dict[str, str], consents: dict[str, int], **kw: Any):
    from quill.core.windows_dictation.cloud.recognizer import CloudDictationRecognizer

    listener = _Listener()
    provider = registry.provider(provider_id)
    assert provider is not None
    recognizer = CloudDictationRecognizer(
        listener,
        post=lambda fn, *args: fn(*args),
        provider=provider,
        values=values,
        consents=consents,
        **kw,
    )
    return recognizer, listener


def test_with_consent_declined_no_request_is_made(monkeypatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    wire = install(monkeypatch)
    recognizer, _listener = _recognizer("deepgram", {"key": _KEY}, {})
    with pytest.raises(DictationStartError) as caught:
        recognizer._prepare_engine()
    assert "not switched on" in caught.value.args[0]
    assert wire.calls == 0


def test_in_safe_mode_no_request_is_made(monkeypatch) -> None:
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    wire = install(monkeypatch)
    recognizer, _listener = _recognizer("groq", {"key": _KEY}, {"groq": 1})
    with pytest.raises(DictationStartError):
        recognizer._prepare_engine()
    assert wire.calls == 0


def test_a_provider_without_streaming_shows_no_live_preview(monkeypatch) -> None:
    pytest.importorskip("numpy")
    import numpy as np

    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    wire = install(monkeypatch)
    wire.answer({"text": "Hello there."})
    recognizer, listener = _recognizer(
        "groq", {"key": _KEY}, {"groq": 1}, keywords=["Quill", "Jeff"]
    )
    recognizer._prepare_engine()
    assert recognizer._live is None and not recognizer.streaming
    assert recognizer._transcribe_healing(np.zeros(1600, dtype=np.float32)) == "Hello there."
    assert listener.partials == []
    (request,) = wire.requests
    assert b'name="prompt"' in request.data and b"Jeff, Quill" in request.data


def test_losing_the_network_costs_a_phrase_and_never_switches_engine(monkeypatch) -> None:
    pytest.importorskip("numpy")
    from urllib.error import URLError

    import numpy as np

    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    wire = install(monkeypatch)
    wire.answer(URLError("down"))
    recognizer, listener = _recognizer("groq", {"key": _KEY}, {"groq": 1})
    recognizer._prepare_engine()
    recognizer._running.set()
    assert recognizer._transcribe_healing(np.zeros(1600, dtype=np.float32)) == ""
    assert listener.problems == [
        ("Groq could not be reached. Check the internet connection.", False)
    ]
    assert recognizer._running.is_set()  # still listening
    assert recognizer._engine == "cloud-groq"  # and never another engine


def test_a_refused_key_stops_dictation_once(monkeypatch) -> None:
    pytest.importorskip("numpy")
    import numpy as np

    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    wire = install(monkeypatch)
    wire.answer(http_error("u", 401), http_error("u", 401))
    recognizer, listener = _recognizer("groq", {"key": _KEY}, {"groq": 1})
    recognizer._prepare_engine()
    recognizer._running.set()
    recognizer._transcribe_healing(np.zeros(1600, dtype=np.float32))
    recognizer._transcribe_healing(np.zeros(1600, dtype=np.float32))
    assert listener.problems == [("The key was refused. Check Key.", True)]
    assert not recognizer._running.is_set()


def test_a_streaming_provider_previews_and_commits_through_one_socket(monkeypatch) -> None:
    pytest.importorskip("numpy")
    import numpy as np

    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    wire = install(monkeypatch)

    def react(message: Any) -> list[Any]:
        if isinstance(message, bytes):
            return [
                {
                    "type": "Results",
                    "is_final": False,
                    "channel": {"alternatives": [{"transcript": "hello"}]},
                }
            ]
        if json.loads(message).get("type") == "Finalize":
            return [
                {
                    "type": "Results",
                    "is_final": True,
                    "from_finalize": True,
                    "channel": {"alternatives": [{"transcript": "Hello, world."}]},
                }
            ]
        return []

    wire.socket_factory = lambda _url, _headers: FakeSocket(react)
    recognizer, _listener = _recognizer(
        "deepgram", {"key": _KEY}, {"deepgram": 1}, keywords=["QUILL"]
    )
    recognizer._prepare_engine()
    try:
        url, headers, socket = wire.sockets[0]
        assert url.startswith("wss://api.deepgram.com/v1/listen?")
        assert "keyterm=QUILL" in url and _KEY not in url
        assert headers == {"Authorization": f"Token {_KEY}"}
        live = recognizer._live
        live.begin(None)
        partial = ""
        for _ in range(50):
            partial = live.feed(np.zeros(1600, dtype=np.float32), speaking=True)
            if partial:
                break
            import time

            time.sleep(0.01)
        assert partial == "hello"
        assert live.end() == ("", "Hello, world.")
    finally:
        recognizer.stop()
    assert socket.text_sent()[-1] == {"type": "CloseStream"}
    assert socket.closed


def test_a_socket_that_will_not_open_refuses_to_start_with_a_sentence(monkeypatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    wire = install(monkeypatch)

    def refuse(_url: str, _headers: dict[str, str]) -> FakeSocket:
        raise http_error("wss://api.deepgram.com", 401)

    wire.socket_factory = refuse
    recognizer, _listener = _recognizer("deepgram", {"key": _KEY}, {"deepgram": 1})
    with pytest.raises(DictationStartError) as caught:
        recognizer._prepare_engine()
    assert caught.value.args[0] == "The key was refused. Check Key."


def test_the_capability_table_drives_what_is_offered() -> None:
    caps = Capabilities(streaming=False, biasing_limit=0)
    assert not caps.biasing
    for provider in registry.providers():
        capabilities = provider.capabilities()
        assert isinstance(capabilities.streaming, bool)
        assert capabilities.biasing == (capabilities.biasing_limit > 0)
