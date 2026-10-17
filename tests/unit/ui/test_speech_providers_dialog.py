"""Speech Providers (D-31): the page, its secrets, Test Connection, and the
consent when a provider is chosen in Dictation Settings. In memory only: the
credential store is a dictionary and the network a recorded fake."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.wx_session import patch_call_after, shared_wx_app

wx = pytest.importorskip("wx")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
from cloud_speech_fakes import MemoryBackend, http_error, install  # noqa: E402

_KEY = "deepgram-key-0123456789abcdef"


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    # SetHelpText stores nothing without a help provider (CLAUDE.md, F1).
    wx.HelpProvider.Set(wx.SimpleHelpProvider())
    yield app


@pytest.fixture
def store(monkeypatch, tmp_path) -> MemoryBackend:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)
    return MemoryBackend(tmp_path).install(monkeypatch)


def _choose(dialog, provider_id: str) -> None:
    row = next(i for i, item in enumerate(dialog._providers) if item.id == provider_id)
    dialog.providers.SetSelection(row)
    dialog._show(row)


def test_the_page_lists_every_provider_with_the_list_focused(wx_app, store) -> None:
    from quill.ui.speech_providers_dialog import SpeechProvidersDialog

    dialog = SpeechProvidersDialog(None, {})
    try:
        labels = [dialog.providers.GetString(i) for i in range(dialog.providers.GetCount())]
        assert all(label.endswith(", not set up") for label in labels)
        assert any(label.startswith("Deepgram") for label in labels)
        assert dialog.providers.GetHelpText()
        for button in (dialog.test_button, dialog.save_button, dialog.remove_button):
            assert button.GetHelpText()
    finally:
        dialog.Destroy()


def test_save_keeps_the_key_in_the_store_and_never_in_settings(wx_app, store) -> None:
    from quill.core.windows_dictation.cloud.credentials import secret_target
    from quill.ui.speech_providers_dialog import SpeechProvidersDialog

    said: list[str] = []
    dialog = SpeechProvidersDialog(None, {}, said.append)
    try:
        _choose(dialog, "deepgram")
        key = dialog._controls["key"]
        assert key.HasFlag(wx.TE_PASSWORD) and key.GetHelpText()
        key.SetValue(_KEY)
        dialog._on_save(None)
        assert store.secrets[secret_target("deepgram", "key")] == _KEY
        assert _KEY not in repr(dialog.stored())
        assert "deepgram" in dialog.stored()
        assert key.GetValue() == ""  # a saved secret is never shown again
        assert said[-1].startswith("Deepgram saved.")
        row = dialog.providers.GetSelection()
        assert dialog.providers.GetString(row) == "Deepgram, set up"
    finally:
        dialog.Destroy()


def test_save_with_a_field_missing_names_it(wx_app, store) -> None:
    from quill.ui.speech_providers_dialog import SpeechProvidersDialog

    said: list[str] = []
    dialog = SpeechProvidersDialog(None, {}, said.append)
    try:
        _choose(dialog, "deepgram")
        dialog._on_save(None)
        assert said[-1] == "Not saved. Key is empty. Fill in Key."
        assert not store.secrets
    finally:
        dialog.Destroy()


def test_test_connection_says_what_the_provider_answered(wx_app, store, monkeypatch) -> None:
    from quill.ui.speech_providers_dialog import SpeechProvidersDialog

    wire = install(monkeypatch)
    wire.answer(http_error("https://api.deepgram.com/v1/projects", 401))
    patch_call_after(monkeypatch, lambda fn, *args: fn(*args))

    class _Now:
        def __init__(self, target, **_kw):
            self._target = target

        def start(self):
            self._target()

    import quill.ui.speech_providers_dialog as page

    monkeypatch.setattr(page.threading, "Thread", _Now)
    said: list[str] = []
    dialog = SpeechProvidersDialog(None, {}, said.append)
    try:
        _choose(dialog, "deepgram")
        dialog._controls["key"].SetValue(_KEY)
        dialog._on_test(None)
        assert said[-1] == "The key was refused. Check Key."
        assert dialog.result.GetValue() == said[-1]
        assert _KEY not in " ".join(said)
        assert dialog.test_button.IsEnabled()
        (request,) = wire.requests
        assert request.data is None  # never the person's speech
    finally:
        dialog.Destroy()


def test_remove_forgets_the_provider(wx_app, store, monkeypatch) -> None:
    import quill.ui.speech_providers_dialog as page

    monkeypatch.setattr(page, "show_message_box", lambda *_a, **_k: wx.YES)
    said: list[str] = []
    dialog = page.SpeechProvidersDialog(None, {}, said.append)
    try:
        _choose(dialog, "deepgram")
        dialog._controls["key"].SetValue(_KEY)
        dialog._on_save(None)
        dialog._on_remove(None)
        assert not store.secrets
        assert "deepgram" not in dialog.stored()
        assert said[-1] == "Deepgram removed. Nothing is saved for it now."
    finally:
        dialog.Destroy()


class _Settings:
    pass


def test_dictation_settings_reaches_the_page_and_lists_a_saved_provider(wx_app, store) -> None:
    from quill.core.windows_dictation.cloud.credentials import secret_target
    from quill.ui.windows_dictation_dialog import WindowsDictationDialog

    settings = _Settings()
    settings.windows_dictation_speech_providers = {"deepgram": {"saved": "yes"}}
    store.secrets[secret_target("deepgram", "key")] = _KEY
    dialog = WindowsDictationDialog(None, settings)
    try:
        buttons = [w for w in dialog.GetChildren() if isinstance(w, wx.Button)]
        assert any(b.GetLabel() == "Speech Pro&viders..." for b in buttons)
        assert "cloud-deepgram" in dialog._engine_ids
    finally:
        dialog.Destroy()


def test_choosing_a_provider_asks_first_and_no_keeps_the_engine(wx_app, store, monkeypatch) -> None:
    from quill.core.windows_dictation.cloud.credentials import secret_target
    from quill.ui import dialog_contract
    from quill.ui.windows_dictation_dialog import WindowsDictationDialog

    asked: list[str] = []

    def answer(text, *_a, **_k):
        asked.append(text)
        return wx.NO

    monkeypatch.setattr(dialog_contract, "show_message_box", answer)
    settings = _Settings()
    settings.windows_dictation_speech_providers = {"deepgram": {"saved": "yes"}}
    store.secrets[secret_target("deepgram", "key")] = _KEY
    said: list[str] = []
    dialog = WindowsDictationDialog(None, settings, said.append)
    try:
        before = dialog.engine.GetSelection()
        dialog.engine.SetSelection(dialog._engine_ids.index("cloud-deepgram"))
        dialog._on_engine(None)
        assert "sends what you say to Deepgram" in asked[0]
        assert dialog.engine.GetSelection() == before
        assert said[-1] == "Deepgram was not chosen. Nothing was sent."

        monkeypatch.setattr(dialog_contract, "show_message_box", lambda *_a, **_k: wx.YES)
        dialog.engine.SetSelection(dialog._engine_ids.index("cloud-deepgram"))
        dialog._on_engine(None)
        applied = _Settings()
        dialog.apply(applied)
        assert applied.windows_dictation_engine == "cloud-deepgram"
        assert applied.windows_dictation_speech_provider_consent == {"deepgram": 1}
    finally:
        dialog.Destroy()
