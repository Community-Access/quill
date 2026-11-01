"""Quill Weather's AI, in the real window (codex.md Phase 3, 10E.9, decision 22).

Its own "QUILL Weather" sign-in, the AI menu on the Window-menu fallback keys,
Ask about the forecast, Should I Go Out?, the AI line and Safe Mode. The AI is
a stand-in on the real service and the forecast is a fixture, so nothing
leaves the machine.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

wx = pytest.importorskip("wx")

#: A real window with its machine-wide doors closed (closed_machine_doors in conftest).
pytestmark = pytest.mark.usefixtures("closed_machine_doors")


class _Account:
    def __init__(self, signed_in: bool = True) -> None:
        self.signed_in = signed_in
        self.model = ""
        self.slug = "quill-weather"
        self.web_search = False
        self.ended_by_openai = False


def _report():
    from quill.core.weather.models import (
        CurrentConditions,
        WeatherAlert,
        WeatherLocation,
        WeatherReport,
    )

    location = WeatherLocation("Tucson, AZ", 32.2217, -110.9265, resolved_name="Tucson, AZ")
    return WeatherReport(
        location=location,
        current=CurrentConditions(text_description="Sunny", temperature_f=72.0),
        alerts=[WeatherAlert("a1", "Heat Advisory", headline="Heat Advisory until 8 PM")],
    )


@pytest.fixture
def weather(quill_data_dir: Path, wx_session_app, monkeypatch: pytest.MonkeyPatch):
    from quill.apps.weather import WeatherAppFrame

    # No alert watch, and so no Add Location, when a later test pumps events.
    monkeypatch.setattr(WeatherAppFrame, "_weather_app_startup_monitoring", lambda self: None)
    frame = WeatherAppFrame(safe_mode=True)  # no network at startup
    frame._safe_mode = False
    said: list[str] = []
    frame._announce = lambda message, **_kw: said.append(str(message))
    frame.said = said
    service = frame._ai_service()
    monkeypatch.setattr(type(service), "refresh_limits", lambda self, on_done=None: None)
    frame.sent = []

    def ask(feature, prompt, chunks, *, on_done, on_error, language="", requires=("text",)):
        frame.sent.append((feature, prompt, requires))
        on_done("Yes, a light jacket will do.", None)

    def converse(message, excerpts, history, *, on_done, on_error, requires=("text",)):
        frame.sent.append(("converse", message, list(excerpts)))
        on_done("An answer.", None, 0)

    service.ask = ask
    service.converse = converse
    service._chatgpt = _Account(signed_in=True)
    frame._ai_host().settings.ai_connection = "chatgpt"
    frame.shown = []
    monkeypatch.setattr(frame, "_show_ai_window", lambda window: frame.shown.append(window))
    try:
        yield frame
    finally:
        for window in [*getattr(frame, "_ai_windows", {}).values(), *frame.shown]:
            if window:
                window.Destroy()
        WeatherAppFrame._weather_app_shutdown(frame)
        frame.frame.Destroy()


def _menu(frame, name: str):
    bar = frame.frame.GetMenuBar()
    return bar.GetMenu(bar.FindMenu(name))


def _places(monkeypatch, primary) -> None:
    from types import SimpleNamespace

    from quill.core.weather import locations as loc_store

    monkeypatch.setattr(
        loc_store, "load_locations", lambda _d: SimpleNamespace(primary=lambda: primary)
    )


def _fresh(frame) -> None:
    frame._weather_ai_report = _report()
    frame._weather_ai_report_at = time.monotonic()


def test_the_ai_menu_sits_after_options_on_the_fallback_keys(weather) -> None:
    bar = weather.frame.GetMenuBar()
    titles = [bar.GetMenuLabel(i) for i in range(bar.GetMenuCount())]
    assert titles.index("A&I") == titles.index("&Options") + 1
    labels = [i.GetItemLabel() for i in _menu(weather, "AI").GetMenuItems() if not i.IsSeparator()]
    assert labels == [
        "&Ask...\tCtrl+Shift+8",
        "&Which AI Am I Using\tCtrl+F8",
        "&Choose Your AI...\tCtrl+Shift+F8",
        "Should I &Go Out?\tCtrl+Shift+G",
        "Use My C&hatGPT Subscription...\tAlt+F5",
        "Use My &Own AI Key...\tAlt+F2",
        "AI U&sage...\tCtrl+Alt+Shift+F2",
        "&Privacy Agreement...\tCtrl+Alt+Shift+K",
    ]
    assert weather.commands.get("weather.ai_go_out") is not None


def test_weather_signs_in_as_itself(weather) -> None:
    service = weather._ai_service()
    assert service._app.ai_agent_name == "QUILL Weather"
    del service._chatgpt
    assert service.chatgpt.agent_name == "QUILL Weather"


def test_the_choice_is_kept_in_weathers_own_file(weather, quill_data_dir) -> None:
    from quill.core.paths import app_data_dir

    weather._ai_host().save_settings()
    saved = json.loads((app_data_dir() / "weather-ai.json").read_text(encoding="utf-8"))
    assert saved["ai_connection"] == "chatgpt"


def test_should_i_go_out_puts_the_alert_in_its_own_words_first(weather) -> None:
    _fresh(weather)
    weather.cmd_weather_go_out()
    feature, prompt, requires = weather.sent[0]
    assert requires == ("text",)
    assert "Place: Tucson, AZ" in prompt and "Sunny, 72 F" in prompt
    assert "32.22" not in prompt and "-110.9" not in prompt  # never coordinates
    window = weather.shown[0]
    assert window.GetTitle() == "Should I Go Out?"
    assert window._text.startswith(
        "Active alert, as the Weather Service wrote it: Heat Advisory: Heat Advisory until 8 PM."
    )
    assert window._text.endswith("Yes, a light jacket will do.")


def test_should_i_go_out_fetches_the_forecast_when_it_is_old(weather, monkeypatch) -> None:
    fetched: list[str] = []

    def submit(name, work, *, on_success, on_failure=None, **_kw):
        fetched.append(name)
        on_success(name, _report())

    monkeypatch.setattr(weather._task_manager, "submit", submit)
    monkeypatch.setattr(weather, "_weather_ai_call_after", lambda func, *args: func(*args))
    _places(monkeypatch, _report().location)
    weather.cmd_weather_go_out()
    assert fetched == ["weather-ai-report"]
    assert weather.sent and weather.sent[0][0] == "ask"


def test_should_i_go_out_with_no_place_opens_add_location(weather, monkeypatch) -> None:
    _places(monkeypatch, None)
    opened: list[str] = []
    monkeypatch.setattr(weather, "open_weather_add_location", lambda: opened.append("x"))
    weather.cmd_weather_go_out()
    assert opened == ["x"] and weather.sent == []


def test_ask_sends_the_forecast_by_place_name(weather) -> None:
    from quill.ui.hosted_ai_app_ask import AppAskFrame

    _fresh(weather)
    weather.cmd_ai_chat_key()
    frame = weather._ai_windows["ask"]
    assert isinstance(frame, AppAskFrame)
    assert frame._about.GetValue().startswith("Asking My ChatGPT plan about this forecast.")
    frame._message.SetValue("Will it rain?")
    frame._send()
    facts = weather.sent[0][2][0]
    assert "Place: Tucson, AZ" in facts and "Heat Advisory" in facts
    assert "32.2217" not in facts


def test_safe_mode_refuses_every_ai_command(weather) -> None:
    weather._safe_mode = True
    for command in (
        lambda w: w.cmd_ai_chat_key(),
        lambda w: w.cmd_ai_which(),
        lambda w: w.cmd_ai_choose(),
        lambda w: w.cmd_ai_usage(),
        lambda w: w.cmd_ai_chatgpt(),
        lambda w: w.cmd_weather_go_out(),
    ):
        weather.said.clear()
        command(weather)
        assert weather.said == ["AI is off in Safe Mode."]
    assert weather.sent == []


def test_the_ai_line_says_which_ai_and_enter_opens_choose(weather, monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(type(weather), "cmd_ai_choose", lambda self: opened.append("x"))
    assert weather._ai_text.GetValue().startswith("AI")
    assert "Choose Your AI" in weather._ai_text.GetHelpText()
    event = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
    event.SetKeyCode(wx.WXK_RETURN)
    weather._on_ai_line_key(event)
    assert opened == ["x"]


def test_the_adapter_has_no_command_of_its_own() -> None:
    from quill.apps.weather_ai import WeatherAiMixin
    from quill.ui.hosted_ai_app_adapter import AppAiHost, AppAiMixin

    for cls in (WeatherAiMixin, AppAiMixin, AppAiHost):
        assert [name for name in vars(cls) if name.startswith("cmd_")] == []
