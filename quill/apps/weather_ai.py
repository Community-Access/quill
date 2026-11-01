"""Quill Weather reaches the family's AI through the shared small-app adapter.

codex.md Phase 3 (10E.9, 6.9, decision 22). Quill Weather had no AI. Now it
runs the shared hosted AI through :class:`~quill.ui.hosted_ai_app_adapter.AppAiMixin`
-- hooks only -- with its own "QUILL Weather" sign-in, so Choose Your AI, Which
AI Am I Using, the one AI Usage list, the AI line in the main window and Safe
Mode's refusal all come from the code every app shares.

What Quill Weather *does* with AI is :class:`WeatherAiFeaturesMixin`:

* **Ask** (Ctrl+Shift+8, AI > Ask...) about the forecast: the primary place's
  name -- never its coordinates -- the current conditions, the next hours, the
  forecast and the active alerts by the Weather Service's own names
  (``app_ask_context.weather_context``), read fresh for each question.
* **Should I Go Out?** (Ctrl+Shift+G): one request, answered in plain words.
  An alert is never paraphrased by a model: each active alert's own words are
  put in front of the answer, and the prompt forbids rewording it
  (:func:`quill.core.ai.app_requests.alerts_preface`).

**Text only (decision 22).** No radar, no map, no picture of any kind is sent.
The alert watch (``headless_check.py``) stays model-free, and nothing here runs
on a timer: the forecast is fetched from the Weather Service only when somebody
asks, the same request Weather Now makes, and kept ten minutes.

**Keys.** Ctrl+1 to Ctrl+9 are the Window menu's, so Ask is Ctrl+Shift+8, Which
AI Ctrl+F8 and Choose Your AI Ctrl+Shift+F8, as in Quill Radio, QUILL Cast and
QUILL Transcribe (``app_keymaps.py``, ``app_ai_keys.py``).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from quill.ui.hosted_ai_app_adapter import AppAiMixin

__all__ = ["AGENT_NAME", "AI_ROWS", "GO_OUT_TITLE", "WeatherAiFeaturesMixin", "WeatherAiMixin"]

#: What OpenAI and GitHub show on their consent pages for this app.
AGENT_NAME = "QUILL Weather"
GO_OUT_TITLE = "Should I Go Out?"

#: How long a fetched forecast answers questions before it is fetched again.
_FRESH_SECONDS = 600.0

#: The AI menu: command id, label, handler name; "" is a separator. Letters are
#: unique within the menu (A W C G H O S P).
AI_ROWS: tuple[tuple[str, str, str], ...] = (
    ("tools.hosted_ai_chat_key", "&Ask...", "cmd_ai_chat_key"),
    ("tools.hosted_ai_which", "&Which AI Am I Using", "cmd_ai_which"),
    ("tools.hosted_ai_choose", "&Choose Your AI...", "cmd_ai_choose"),
    ("", "", ""),
    ("weather.ai_go_out", "Should I &Go Out?", "cmd_weather_go_out"),
    ("", "", ""),
    ("tools.hosted_ai_chatgpt", "Use My C&hatGPT Subscription...", "cmd_ai_chatgpt"),
    ("tools.hosted_ai_own_key", "Use My &Own AI Key...", "cmd_ai_own_key"),
    ("tools.hosted_ai_usage", "AI U&sage...", "cmd_ai_usage"),
    ("tools.hosted_ai_privacy", "&Privacy Agreement...", "cmd_ai_privacy"),
)


class WeatherAiFeaturesMixin:
    """Should I Go Out? and the forecast Ask reads. Mixed in through ``WeatherAiMixin``."""

    def cmd_weather_go_out(self) -> None:
        """Should I Go Out? (Ctrl+Shift+G): the forecast, in plain words."""
        if not self._ai_ready() or not self._ai_capable("text"):  # type: ignore[attr-defined]
            return
        self._weather_ai_with_report(self._weather_go_out_with)

    def _weather_go_out_with(self, report: Any) -> None:
        from quill.core.ai.app_ask_context import facts_text, weather_context
        from quill.core.ai.app_requests import alerts_preface, go_out_prompt

        preface = alerts_preface((a.event, a.headline) for a in report.alerts)

        def answered(text: str) -> None:
            answer = f"{preface} {text}".strip() if preface else text
            self._app_ai_show(answer or "No answer came back.", title=GO_OUT_TITLE)  # type: ignore[attr-defined]

        self._app_ai_request(  # type: ignore[attr-defined]
            go_out_prompt(facts_text(weather_context(report))),
            answered,
            working=f"Asking about the weather for {report.location.label}.",
        )

    # -- the forecast, fetched only when asked --------------------------------- #

    def _weather_ai_fresh_report(self) -> Any:
        """The forecast fetched for AI in the last ten minutes, or None."""
        report = getattr(self, "_weather_ai_report", None)
        at = float(getattr(self, "_weather_ai_report_at", 0.0) or 0.0)
        if report is None or time.monotonic() - at > _FRESH_SECONDS:
            return None
        return report

    def _weather_ai_with_report(self, then: Callable[[Any], None]) -> None:
        """Run *then* with the primary place's forecast, fetching it if it is old."""
        report = self._weather_ai_fresh_report()
        if report is not None:
            then(report)
            return
        from quill.core.weather import locations as loc_store
        from quill.core.weather import nws
        from quill.core.weather import settings as settings_mod

        data_dir = self._weather_data_dir()  # type: ignore[attr-defined]
        location = loc_store.load_locations(data_dir).primary()
        if location is None:
            self._announce("No weather location yet. Opening Add Location.")  # type: ignore[attr-defined]
            self.open_weather_add_location()  # type: ignore[attr-defined]
            return
        unit = settings_mod.load_settings(data_dir).temperature_unit
        self._announce(f"Getting weather for {location.label}.")  # type: ignore[attr-defined]

        def work(**_kwargs: Any) -> object:
            try:
                return nws.fetch_report_worldwide(
                    location,
                    safe_mode=bool(getattr(self, "_safe_mode", False)),
                    hourly_hours=12,
                    temperature_unit=unit,
                )
            except nws.WeatherError as error:
                return error

        def fetched(_op: str, result: object) -> None:
            self._weather_ai_call_after(self._weather_ai_fetched, result, then)

        self._task_manager.submit("weather-ai-report", work, on_success=fetched, on_failure=None)  # type: ignore[attr-defined]

    def _weather_ai_call_after(self, func: Any, *args: Any) -> None:
        import wx

        if wx.GetApp() is not None:
            wx.CallAfter(func, *args)
        else:
            func(*args)

    def _weather_ai_fetched(self, result: object, then: Callable[[Any], None] | None) -> None:
        from quill.core.weather.models import WeatherReport

        if not isinstance(result, WeatherReport):
            self._announce(f"Could not get weather. {result}")  # type: ignore[attr-defined]
            return
        self._weather_ai_report = result
        self._weather_ai_report_at = time.monotonic()
        if then is not None:
            then(result)


class WeatherAiMixin(WeatherAiFeaturesMixin, AppAiMixin):
    """The shared hosted-AI commands on Quill Weather's frame: hooks, no commands."""

    _AI_APP = "weather"
    _AI_AGENT_NAME = AGENT_NAME
    _AI_ROWS = AI_ROWS
    _AI_SUBJECT = "this forecast"
    _AI_ABOUT_FACTS = (
        "your primary place's name, never its coordinates, the current conditions, the "
        "next hours, the forecast and the active alerts by their official names"
    )

    def _ai_app_ask(self) -> None:
        """Ask (Ctrl+Shift+8): fetch the forecast first when there is none yet."""
        if not self._ai_ready() or not self._ai_capable("text"):
            return
        self._weather_ai_with_report(lambda _report: AppAiMixin._ai_app_ask(self))

    def _app_ask_facts(self, question: str, needs: str) -> Any:
        """This turn's facts: the forecast fetched for AI, refreshed when it is old."""
        del question, needs
        from quill.core.ai.app_ask_context import AppFacts, Fact, weather_context

        report = self._weather_ai_fresh_report()
        if report is None:
            stale = getattr(self, "_weather_ai_report", None)
            self._weather_ai_with_report(lambda _report: None)  # fresh for the next turn
            if stale is None:
                return AppFacts("weather", (Fact("Forecast", "not fetched yet"),))
            report = stale
        return weather_context(report)

    def _app_ai_purpose(self) -> str:
        from quill.core.weather.surface_help import purpose_for_title

        return purpose_for_title("Quill Weather")
