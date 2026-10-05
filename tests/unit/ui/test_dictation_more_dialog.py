"""More Dictation Settings, and OpenAI's consent in Dictation Settings."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    yield app


class _Settings:
    pass


def _dialog(**kwargs: Any) -> Any:
    from quill.ui.dictation_more_dialog import MoreDictationDialog

    said: list[str] = []
    dialog = MoreDictationDialog(None, _Settings(), said.append, load_models=False, **kwargs)
    return dialog, said


def test_the_defaults_and_every_choice_come_back_under_the_settings_names(wx_app) -> None:
    dialog, _said = _dialog()
    try:
        values = dialog.values()
        assert values["windows_dictation_hold_to_talk"] is True
        assert values["windows_dictation_preview"] == "show"
        assert values["windows_dictation_ai_send"] == "pause"
        assert values["windows_dictation_ai_pause"] == "long"
        assert values["windows_dictation_openai_consent"] is False
        dialog.hold.SetValue(False)
        dialog.preview.SetSelection(1)
        dialog.send.SetSelection(1)
        dialog.consent.SetValue(True)
        values = dialog.values()
        assert values["windows_dictation_hold_to_talk"] is False
        assert values["windows_dictation_preview"] == "speak"
        assert values["windows_dictation_ai_send"] == "enter"
        assert values["windows_dictation_openai_consent"] is True
    finally:
        dialog.Destroy()


def test_the_newest_model_is_preselected_from_openais_list(wx_app) -> None:
    dialog, said = _dialog()
    try:
        dialog.show_models(["gpt-live-transcribe", "gpt-transcribe"], "")
        assert dialog.values()["windows_dictation_openai_model"] == "gpt-live-transcribe"
        assert "2 speech models" in dialog.model_status.GetValue()
        assert said == []
    finally:
        dialog.Destroy()


def test_a_chosen_model_that_went_away_is_said_once_and_not_replaced(wx_app) -> None:
    dialog, said = _dialog(pending={"windows_dictation_openai_model": "gpt-4o-transcribe"})
    try:
        dialog.show_models(["gpt-live-transcribe", "gpt-transcribe"], "")
        assert len(said) == 1 and "gpt-4o-transcribe" in said[0]
        assert dialog.model.GetSelection() == wx.NOT_FOUND
        assert dialog.values()["windows_dictation_openai_model"] == ""  # never a silent switch
        dialog.model.SetSelection(1)
        assert dialog.values()["windows_dictation_openai_model"] == "gpt-transcribe"
    finally:
        dialog.Destroy()


def test_a_list_that_could_not_be_read_says_why(wx_app) -> None:
    dialog, _said = _dialog()
    try:
        dialog.show_models([], "OpenAI could not be reached. Check the internet connection.")
        assert "could not be reached" in dialog.model_status.GetValue()
    finally:
        dialog.Destroy()


def test_choosing_openai_asks_first_and_no_puts_the_engine_back(wx_app, monkeypatch) -> None:
    from quill.core.windows_dictation import engines, openai_models
    from quill.ui import windows_dictation_dialog as module

    monkeypatch.setattr(openai_models, "cloud_problem", lambda **_k: "")
    monkeypatch.setattr(
        engines,
        "engine_choices",
        lambda saved="": [("moonshine", "Moonshine"), ("openai", "OpenAI")],
    )
    monkeypatch.setattr(module, "engine_choices", engines.engine_choices)
    asked: list[str] = []
    answers = iter([wx.NO, wx.YES])
    monkeypatch.setattr(
        module, "show_message_box", lambda text, *_a, **_k: asked.append(text) or next(answers)
    )
    opened: list[bool] = []
    said: list[str] = []
    dialog = module.WindowsDictationDialog(None, _Settings(), said.append)
    monkeypatch.setattr(dialog, "open_more", lambda **kwargs: opened.append(kwargs["focus_model"]))
    try:
        dialog.engine.SetSelection(1)
        dialog._on_engine(None)
        assert "sends what you say to OpenAI" in asked[0]
        assert dialog.engine.GetSelection() == 0 and "Nothing was sent" in said[-1]
        dialog.engine.SetSelection(1)
        dialog._on_engine(None)
        assert opened == [True]
        settings = _Settings()
        dialog.apply(settings)
        assert settings.windows_dictation_engine == "openai"
        assert settings.windows_dictation_openai_consent is True
    finally:
        dialog.Destroy()


def test_more_dictation_settings_is_reachable_from_dictation_settings(wx_app) -> None:
    from quill.ui.windows_dictation_dialog import WindowsDictationDialog

    dialog = WindowsDictationDialog(None, _Settings())
    try:
        assert dialog.more_button.GetLabel() == "More Dict&ation Settings..."
    finally:
        dialog.Destroy()
