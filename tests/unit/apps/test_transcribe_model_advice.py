"""D-22 in QUILL Transcribe: Choose Model and Set Up show the recommendation
for this computer as text to read, and each model's tier. Nothing is chosen
for the person."""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def wx_app():
    app = wx.App()
    wx.HelpProvider.Set(wx.SimpleHelpProvider())
    yield app


@pytest.fixture
def advised(monkeypatch):
    """An 8 GB, four-core computer, whatever this one is."""
    from quill.apps import transcribe_dialogs
    from quill.core.windows_dictation.model_advice import recommend
    from quill.core.windows_dictation.speed_check import SpeedCheck

    check = SpeedCheck(tiny=0.05, cores=4, memory_gb=7.8)
    languages: list[str] = []

    def advice(language: str) -> Any:
        languages.append(language)
        return recommend(check, language)

    monkeypatch.setattr(transcribe_dialogs, "_advice", advice)
    monkeypatch.setattr(
        transcribe_dialogs, "_microphones", lambda: ([], "Windows default microphone")
    )
    return languages


def test_choose_model_shows_the_recommendation_and_tiers(wx_app, advised) -> None:
    from quill.apps.transcribe_dialogs import ChooseModelDialog

    dialog = ChooseModelDialog(None, current="moonshine", open_library=lambda: None, language="es")
    try:
        text = dialog.advice.GetValue()
        assert text.startswith("Recommended for this computer: Whisper (built in), Lightweight:")
        assert "measured in English only" in text
        assert advised == ["es"]
        assert dialog.advice.GetHelpText()
        assert "Lightweight" in dialog.list.GetString(0)
        assert "Tier: Lightweight:" in dialog.details.GetValue()
        assert dialog.chosen == ""
    finally:
        dialog.Destroy()


def test_setup_shows_the_one_line_recommendation(wx_app, advised) -> None:
    from quill.apps.transcribe_dialogs import SetupDialog

    dialog = SetupDialog(
        None,
        microphone="",
        engine="moonshine",
        key="",
        at_login=False,
        test_microphone=lambda *_a: None,
        show_modal=lambda *_a: wx.ID_CANCEL,
    )
    try:
        assert dialog.advice.GetValue().startswith("Moonshine base, Lightweight: keeps up")
        assert dialog.advice.GetHelpText()
        # Advice, never a switch: the model box still holds what was there.
        ready = [row.id for row in dialog._rows]
        assert dialog.chosen_engine() == ("moonshine" if "moonshine" in ready else ready[0])
    finally:
        dialog.Destroy()
