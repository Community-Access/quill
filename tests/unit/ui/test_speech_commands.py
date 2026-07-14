"""#617 Speech S2 UI: the SpeechCommandsMixin resolves the offline provider."""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.main_frame_speech import SpeechCommandsMixin


class _Host(SpeechCommandsMixin):
    def __init__(self) -> None:
        self.settings = SimpleNamespace(speech_whisper_path="")


def test_speech_provider_is_whispercpp() -> None:
    provider = _Host()._speech_provider()
    assert provider is not None
    assert provider.id == "whispercpp"
    # The provider exposes the model catalog without needing the binary installed.
    assert any(m.id == "small" for m in provider.list_supported_models())


class _Model:
    def __init__(self, model_id: str) -> None:
        self.id = model_id


def test_default_model_id_prefers_the_saved_default_when_installed() -> None:
    host = _Host()
    host.settings.speech_default_model_id = "small"
    installed = [_Model("tiny"), _Model("small"), _Model("base")]
    assert host._default_model_id(installed) == "small"


def test_default_model_id_falls_back_when_the_saved_default_is_not_installed() -> None:
    from quill.core.speech.catalog import RECOMMENDED_MODEL_ID

    host = _Host()
    host.settings.speech_default_model_id = "not-installed-model"
    installed = [_Model("tiny"), _Model(RECOMMENDED_MODEL_ID)]
    assert host._default_model_id(installed) == RECOMMENDED_MODEL_ID


def test_default_model_id_falls_back_when_nothing_is_saved() -> None:
    from quill.core.speech.catalog import RECOMMENDED_MODEL_ID

    host = _Host()
    host.settings.speech_default_model_id = ""
    installed = [_Model("tiny"), _Model(RECOMMENDED_MODEL_ID)]
    assert host._default_model_id(installed) == RECOMMENDED_MODEL_ID
