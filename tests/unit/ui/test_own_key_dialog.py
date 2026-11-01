"""Use My Own OpenAI Key: the model list, its estimates, and what OK saves."""

from __future__ import annotations

import pytest

from tests.wx_session import patch_call_after, shared_wx_app

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    yield app


class _Settings:
    ai_own_key_model = ""


@pytest.fixture
def dialog_module(monkeypatch):
    import quill.ui.hosted_ai_own_key as module
    import quill.ui.update_download as download

    def run_now(name, work, *, on_success, on_failure):
        on_success(name, work())

    monkeypatch.setattr(download, "thread_submit", run_now)
    patch_call_after(monkeypatch, lambda fn, *args: fn(*args))
    return module


def test_without_a_key_the_list_holds_one_model_with_its_estimate(
    wx_app, dialog_module, monkeypatch
):
    monkeypatch.setattr(dialog_module, "has_own_key", lambda *_a: False)
    dialog = dialog_module.OwnKeyDialog(None, _Settings())
    try:
        assert dialog.model.GetCount() == 1
        assert "(estimate)" in dialog.model.GetString(0)
        assert "not OpenAI's prices" in dialog.cost.GetValue()
    finally:
        dialog.Destroy()


def test_a_saved_key_lists_every_model_on_opening_luna_6_first(wx_app, dialog_module, monkeypatch):
    """So the model can be changed at any time, not only after a test."""
    monkeypatch.setattr(dialog_module, "has_own_key", lambda *_a: True)
    monkeypatch.setattr(
        dialog_module, "list_models", lambda _key, *_a: (["luna-6", "gpt-6", "gpt-4o"], "")
    )
    import quill.core.assistant_ai as assistant_ai

    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda _provider: "sk-test")
    dialog = dialog_module.OwnKeyDialog(None, _Settings())
    try:
        assert dialog.model.GetCount() == 3
        assert dialog._selected_model() == "luna-6"
        dialog.model.SetSelection(2)
        dialog._show_estimate()
        assert "gpt-4o" in dialog.cost.GetValue()
        settings = _Settings()
        dialog.apply(settings)
        assert settings.ai_own_key_model == "gpt-4o"
    finally:
        dialog.Destroy()


def test_a_saved_choice_stays_selected_when_the_list_arrives(wx_app, dialog_module, monkeypatch):
    monkeypatch.setattr(dialog_module, "has_own_key", lambda *_a: True)
    monkeypatch.setattr(
        dialog_module, "list_models", lambda _key, *_a: (["luna-6", "gpt-6", "gpt-4o"], "")
    )
    import quill.core.assistant_ai as assistant_ai

    monkeypatch.setattr(assistant_ai, "load_provider_api_key", lambda _provider: "sk-test")
    settings = _Settings()
    settings.ai_own_key_model = "gpt-6"
    dialog = dialog_module.OwnKeyDialog(None, settings)
    try:
        assert dialog._selected_model() == "gpt-6"
    finally:
        dialog.Destroy()


def test_testing_the_key_lists_the_models_then_asks_the_chosen_one(
    wx_app, dialog_module, monkeypatch
):
    import quill.core.assistant_ai as assistant_ai

    monkeypatch.setattr(dialog_module, "has_own_key", lambda *_a: False)
    monkeypatch.setattr(dialog_module, "list_models", lambda _key, *_a: (["gpt-6", "gpt-4o"], ""))
    asked = []
    monkeypatch.setattr(
        assistant_ai,
        "test_chat",
        lambda connection, _key: (asked.append(connection.model), (True, ""))[1],
    )
    said = []
    dialog = dialog_module.OwnKeyDialog(None, _Settings(), said.append)
    try:
        dialog.key.SetValue("sk-typed")
        dialog._on_test(None)
        assert asked == ["gpt-6"]
        assert dialog.model.GetCount() == 2
        assert said[-1] == "The key works with OpenAI. 2 models are listed, and gpt-6 answered."
    finally:
        dialog.Destroy()


# -- the AI Hub's providers, folded in (decision 20) --------------------------------


def test_ollama_on_this_computer_needs_no_key_and_has_an_address(
    wx_app, dialog_module, monkeypatch
):
    import quill.core.assistant_ai as assistant_ai

    monkeypatch.setattr(
        dialog_module, "has_own_key", lambda provider="openai": provider == "ollama"
    )
    listed = []
    monkeypatch.setattr(
        dialog_module,
        "list_models",
        lambda key, provider, **kw: (listed.append((key, provider, kw)), (["llava:7b"], ""))[1],
    )
    monkeypatch.setattr(assistant_ai, "test_chat", lambda connection, _key: (True, ""))
    settings = _Settings()
    settings.ai_own_key_provider = "ollama"
    said = []
    dialog = dialog_module.OwnKeyDialog(None, settings, said.append)
    try:
        assert dialog.provider.GetStringSelection() == "Ollama on this computer"
        assert dialog.about.GetValue().startswith("Runs on this computer. Nothing is sent.")
        assert not dialog.key.IsEnabled() and dialog.host.IsEnabled()
        assert not dialog.remove.IsEnabled()
        assert dialog.test.GetLabel() == "Test the Connectio&n"
        assert listed and listed[0][0] == ""  # listed on opening, with no key
        dialog.host.SetValue("http://127.0.0.1:11500")
        dialog._on_test(None)
        assert said[-1] == (
            "Ollama on this computer is running. 1 models are listed, and llava:7b answered."
        )
        assert listed[-1][2] == {"host": "http://127.0.0.1:11500"}
        hosts, advanced = [], []
        monkeypatch.setattr(dialog_module, "save_host", lambda p, h: hosts.append((p, h)))
        monkeypatch.setattr(
            dialog_module, "use_for_advanced_features", lambda p, m: advanced.append((p, m))
        )
        outcome = dialog.apply(settings)
        assert (
            outcome
            == "AI help uses Ollama on this computer. Runs on this computer. Nothing is sent."
        )
        assert hosts == [("ollama", "http://127.0.0.1:11500")]
        assert advanced == [("ollama", "llava:7b")]
        assert settings.ai_own_key_provider == "ollama"
    finally:
        dialog.Destroy()


def test_switching_to_a_keyed_hub_provider_turns_the_key_back_on(
    wx_app, dialog_module, monkeypatch
):
    monkeypatch.setattr(dialog_module, "has_own_key", lambda *_a: False)
    dialog = dialog_module.OwnKeyDialog(None, _Settings())
    try:
        dialog.provider.SetStringSelection("Anthropic Claude")
        dialog._on_provider(None)
        assert dialog.key.IsEnabled() and not dialog.host.IsEnabled()
        assert dialog.key_label.GetLabel() == "Anthropic Claude API &key:"
        assert "console.anthropic.com" in dialog.about.GetValue()
        assert dialog.test.GetLabel() == "Test the Ke&y"
    finally:
        dialog.Destroy()
