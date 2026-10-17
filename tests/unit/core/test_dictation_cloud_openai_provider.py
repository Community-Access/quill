"""The OpenAI provider wraps the existing OpenAI dictation: no network, no real key."""

from __future__ import annotations

from typing import Any

import pytest
from cloud_speech_fakes import install

from quill.core.windows_dictation import openai_models, openai_transcribe
from quill.core.windows_dictation.cloud.errors import (
    CloudAuthError,
    CloudFieldError,
    CloudNetworkError,
    CloudQuotaError,
    CloudSpeechError,
    said,
)
from quill.core.windows_dictation.cloud.openai_provider import OpenAIProvider

KEY = "sk-openai-secret"


@pytest.fixture
def keyed(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(openai_models, "load_key", lambda: KEY)
    return install(monkeypatch)


def test_facts() -> None:
    provider = OpenAIProvider()
    assert (provider.id, provider.name, provider.short_name, provider.company) == (
        "openai",
        "OpenAI",
        "OpenAI",
        "OpenAI",
    )
    assert provider.console_url == "https://platform.openai.com/usage"
    assert provider.privacy_url == "https://openai.com/policies"
    assert provider.fields() == ()
    assert provider.consent_version == 1
    assert "Use My Own AI Key" in provider.description
    caps = provider.capabilities()
    assert (caps.streaming, caps.biasing_limit, caps.biasing_name) == (True, 100, "keywords")


def test_problem_without_a_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_models, "load_key", lambda: "")
    problem = OpenAIProvider().problem({})
    assert isinstance(problem, CloudFieldError)
    assert said(problem) == "No OpenAI key is saved. Save one in Use My Own AI Key, in the AI menu."
    assert problem.field == ""
    with pytest.raises(CloudFieldError):
        OpenAIProvider().test({})


def test_problem_with_a_key(keyed: Any) -> None:
    assert OpenAIProvider().problem({}) is None


def test_test_counts_models(keyed: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def models(key: str) -> tuple[list[str], str]:
        seen.append(key)
        return ["gpt-live-transcribe", "gpt-transcribe"], ""

    monkeypatch.setattr(openai_models, "list_transcription_models", models)
    assert OpenAIProvider().test({}) == "OpenAI answered: ready, 2 speech models."
    assert seen == [KEY]
    assert keyed.calls == 0


@pytest.mark.parametrize(
    ("sentence", "kind"),
    [
        ("OpenAI did not accept the saved key. Check it in Use My Own AI Key.", CloudAuthError),
        ("OpenAI could not be reached. Check the internet connection.", CloudNetworkError),
        ("OpenAI could not list its models (error 500).", CloudSpeechError),
    ],
)
def test_test_failures(
    keyed: Any, monkeypatch: pytest.MonkeyPatch, sentence: str, kind: type
) -> None:
    monkeypatch.setattr(openai_models, "list_transcription_models", lambda _key: ([], sentence))
    with pytest.raises(kind) as caught:
        OpenAIProvider().test({})
    assert said(caught.value) == sentence
    assert KEY not in str(caught.value)


class _FakeLive:
    made: list[_FakeLive] = []

    def __init__(self, key: str, model: str, **kwargs: Any) -> None:
        self.key, self.model, self.kwargs = key, model, kwargs
        self.calls: list[str] = []
        self.fail: BaseException | None = None
        _FakeLive.made.append(self)

    def _do(self, name: str) -> None:
        self.calls.append(name)
        if self.fail is not None:
            raise self.fail

    def open(self) -> None:
        self._do("open")

    def append(self, samples: Any) -> None:
        self._do("append")

    def commit(self, timeout: float = 15.0) -> str:
        self._do("commit")
        return "Hello."

    def clear(self) -> None:
        self._do("clear")

    def close(self) -> None:
        self._do("close")


def test_live_wraps_live_transcription(keyed: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeLive.made = []
    monkeypatch.setattr(openai_transcribe, "LiveTranscription", _FakeLive)
    deltas: list[str] = []
    session = OpenAIProvider().live({}, language="en", terms=["Quill"], on_delta=deltas.append)
    fake = _FakeLive.made[0]
    assert (fake.key, fake.model) == (KEY, "gpt-live-transcribe")
    assert fake.kwargs["language"] == "en"
    assert list(fake.kwargs["keywords"]) == ["Quill"]
    assert fake.kwargs["on_delta"] == deltas.append
    session.open()
    session.append([0.0])
    assert session.commit(1.0) == "Hello."
    session.clear()
    session.close()
    assert fake.calls == ["open", "append", "commit", "clear", "close"]

    OpenAIProvider().live({"model": "other-live"}, language="en", terms=[])
    assert _FakeLive.made[1].model == "other-live"


@pytest.mark.parametrize(
    ("error", "kind", "field"),
    [
        (openai_transcribe.ModelGoneError("The OpenAI model x is gone."), CloudFieldError, "Model"),
        (
            openai_transcribe.OpenAIDictationError(
                "OpenAI did not accept the saved key. Check it in Use My Own AI Key."
            ),
            CloudAuthError,
            "",
        ),
        (
            openai_transcribe.OpenAIDictationError("OpenAI says the account is out of credit."),
            CloudQuotaError,
            "",
        ),
        (
            openai_transcribe.OpenAIDictationError("The connection to OpenAI was lost."),
            CloudNetworkError,
            "",
        ),
        (
            openai_transcribe.OpenAIDictationError("OpenAI took too long to answer."),
            CloudSpeechError,
            "",
        ),
    ],
)
def test_live_translates_errors(
    keyed: Any, monkeypatch: pytest.MonkeyPatch, error: Exception, kind: type, field: str
) -> None:
    _FakeLive.made = []
    monkeypatch.setattr(openai_transcribe, "LiveTranscription", _FakeLive)
    session = OpenAIProvider().live({}, language="en", terms=[])
    _FakeLive.made[0].fail = error
    with pytest.raises(kind) as caught:
        session.commit()
    assert type(caught.value) is kind
    assert caught.value.field == field
    assert said(caught.value) == error.args[0]


def test_phrase_wraps_transcribe_phrase(keyed: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[Any, ...]] = []

    def phrase(key: str, model: str, samples: Any, **kwargs: Any) -> str:
        seen.append((key, model, samples, kwargs))
        return "Done."

    monkeypatch.setattr(openai_transcribe, "transcribe_phrase", phrase)
    assert OpenAIProvider().phrase({}, [0.0], language="es", terms=["Quill"]) == "Done."
    key, model, samples, kwargs = seen[0]
    assert (key, model, samples) == (KEY, "gpt-transcribe", [0.0])
    assert kwargs["language"] == "es"
    assert list(kwargs["keywords"]) == ["Quill"]
    OpenAIProvider().phrase({"model": "whisper-x"}, [0.0], language="en", terms=[])
    assert seen[1][1] == "whisper-x"


def test_phrase_model_gone_names_model(keyed: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    def gone(*_args: Any, **_kwargs: Any) -> str:
        raise openai_transcribe.ModelGoneError("The OpenAI model gpt-transcribe is gone.")

    monkeypatch.setattr(openai_transcribe, "transcribe_phrase", gone)
    with pytest.raises(CloudFieldError) as caught:
        OpenAIProvider().phrase({}, [0.0], language="en", terms=[])
    assert caught.value.field == "Model"
    assert KEY not in str(caught.value)
