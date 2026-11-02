"""Choose Your AI's Copilot and Codex rows, and ChatGPT Plan Options (codex.md 10A.3).

The window is real; the service is a stand-in over ConnectionFacts with the
Copilot and Codex fields, so each row's state is the registry's own reading.
"""

from __future__ import annotations

from typing import Any

import pytest
import wx

from quill.core.ai.connection_caps import record_for
from quill.core.ai.connection_choice import ConnectionFacts, in_use, row_states
from quill.ui import hosted_ai_connections as connections
from quill.ui.hosted_ai_connections import ChooseAiFrame, ChooseAiHooks


class _Account:
    def __init__(self, signed_in: bool = False) -> None:
        self.signed_in = signed_in
        self.model = ""
        self.web_search = False
        self.forgotten = 0

    def set_web_search(self, allowed: bool) -> None:
        self.web_search = bool(allowed)

    def forget(self) -> None:
        self.forgotten += 1
        self.signed_in = False

    def access_token(self) -> str:
        return "token"


class _Service:
    own_key_provider = "openai"
    agent_name = "QUILL Lite"

    def __init__(
        self, *, stored="free", plan=False, copilot=False, copilot_here=True, codex_here=True
    ) -> None:
        self.stored = stored
        self.signed_in = True
        self.chatgpt = _Account(plan)
        self.copilot = copilot
        self.copilot_here = copilot_here
        self.codex_here = codex_here
        self.chosen: list[str] = []
        self.changed: list[str] = []
        self.settings: Any = type("S", (), {"ai_copilot_model": ""})()
        self.saved = 0

    def facts(self) -> ConnectionFacts:
        return ConnectionFacts(
            stored=self.stored,
            free_connected=True,
            chatgpt_signed_in=self.chatgpt.signed_in,
            copilot_available=self.copilot_here,
            copilot_signed_in=self.copilot,
            codex_available=self.codex_here,
        )

    def connection_rows(self):
        return row_states(self.facts())

    @property
    def connection_in_use(self) -> str:
        return in_use(self.facts())

    def capability_record(self, connection=""):
        chosen = connection or self.stored
        return record_for(chosen, available=self.facts().available(chosen))

    def connection_model(self, connection=""):
        return ""

    def choose(self, connection: str) -> bool:
        self.chosen.append(connection)
        self.stored = connection
        return True

    def note_readiness(self) -> None:
        pass

    def connection_changed(self, connection: str) -> None:
        self.changed.append(connection)
        if connection == "copilot" and self.copilot:
            self.stored = "copilot"

    def engine_unavailable_about(self, connection: str) -> str:
        from quill.core.ai.connection_words import engine_unavailable_about

        return engine_unavailable_about(connection, registered=False, app_name="QUILL Lite")

    def copilot_models(self):
        return [("auto", "Auto (Copilot Free chooses)")], ""

    def _settings(self):
        return self.settings

    def _save_settings(self) -> None:
        self.saved += 1


@pytest.fixture
def window(wx_session_app, monkeypatch, wx_call_after):
    import quill.core.ai.chatgpt_client as plan
    import quill.ui.update_download as download

    monkeypatch.setattr(plan, "list_models", lambda _token: [])

    def submit(_name, work, *, on_success=None, on_failure=None):
        on_success(_name, work())

    monkeypatch.setattr(download, "thread_submit", submit)
    wx_call_after()
    built: list[ChooseAiFrame] = []

    def make(service, said, select=""):
        hooks = ChooseAiHooks(
            announce=said.append,
            connect_free=lambda: None,
            own_key=lambda: "",
            changed=lambda: said.append("<changed>"),
            app_name="QUILL Lite",
        )
        frame = ChooseAiFrame(None, service, hooks, select=select)
        built.append(frame)
        return frame

    yield make
    for frame in built:
        if frame:
            frame.Destroy()


def test_copilot_without_a_registration_reads_not_available_and_says_why(window) -> None:
    said: list[str] = []
    frame = window(_Service(copilot_here=False), said, select="copilot")

    assert frame._list.GetStringSelection() == "My GitHub Copilot, not available yet"
    assert frame._about.GetValue() == (
        "Not available yet: GitHub sign-in for QUILL Lite has not been registered, "
        "so it comes in a later update."
    )


def test_copilot_sign_in_runs_the_device_step_then_says_it_is_in_use(window, monkeypatch) -> None:
    import quill.ui.copilot_onboarding_dialog as step

    said: list[str] = []
    service = _Service()
    asked: list[Any] = []

    def sign_in(parent, svc, announce):
        asked.append(svc)
        service.copilot = True  # the token is stored; the row is now set up
        return True

    monkeypatch.setattr(step, "copilot_sign_in", sign_in)
    frame = window(service, said, select="copilot")
    assert frame._action.GetLabel() == "&Sign In..."

    frame.do_action()

    assert asked == [service]
    assert service.changed == ["copilot"]
    assert said[-1] == "Signed in to My GitHub Copilot. It is now in use."


def test_cancelling_the_copilot_step_says_nothing(window, monkeypatch) -> None:
    import quill.ui.copilot_onboarding_dialog as step

    said: list[str] = []
    monkeypatch.setattr(step, "copilot_sign_in", lambda *_a: False)
    frame = window(_Service(), said, select="copilot")
    frame.do_action()
    assert said == []


def test_copilot_free_shows_auto_as_its_only_model(window) -> None:
    frame = window(_Service(stored="copilot", copilot=True), [], select="copilot")
    assert frame._model.GetString(0) == "Auto (Copilot Free chooses)"
    assert not frame._model.IsEnabled()


def test_codex_is_one_keypress_on_a_signed_in_plan(window) -> None:
    said: list[str] = []
    service = _Service(plan=True)
    frame = window(service, said, select="codex")
    assert frame._list.GetStringSelection() == "Codex, for tasks, signed in"
    assert frame._action.GetLabel() == "&Use This"

    frame.do_action()

    assert service.chosen == ["codex"]
    assert said[-1] == "Now using Codex, for tasks."


def test_codex_without_the_plan_signs_in_to_the_plan(window, monkeypatch) -> None:
    said: list[str] = []
    service = _Service()

    def show(step, _title):
        assert "approve QUILL Lite on OpenAI's page" in step.status.GetValue()
        service.chatgpt.signed_in = True
        service.stored = "codex"
        return wx.ID_OK

    monkeypatch.setattr(connections, "show_modal_dialog", show)
    frame = window(service, said, select="codex")
    frame.do_action()
    assert service.changed == ["codex"]
    assert said[-1] == "Signed in to Codex, for tasks. It is now in use."


def test_plan_options_show_only_on_a_signed_in_plan_row(window) -> None:
    frame = window(_Service(stored="chatgpt", plan=True), [], select="chatgpt")
    assert frame._options.IsShown()
    frame.select("free")
    assert not frame._options.IsShown()
    frame.select("codex")
    assert frame._options.IsShown()


def test_plan_options_forget_says_so_and_nothing_is_in_use(window, monkeypatch) -> None:
    import quill.ui.hosted_ai_plan_options as options

    said: list[str] = []
    service = _Service(stored="chatgpt", plan=True)
    monkeypatch.setattr(options, "show_modal_dialog", lambda _d, _t: options.FORGOTTEN)
    frame = window(service, said, select="chatgpt")

    frame.plan_options()

    assert service.chatgpt.forgotten == 1
    assert said[-1].startswith("Signed out. No AI is in use until you choose one. Forgotten")


def test_the_web_search_check_box_saves_at_once_and_says_nothing(wx_session_app) -> None:
    from quill.ui.hosted_ai_plan_options import PlanOptionsDialog

    account = _Account(True)
    dialog = PlanOptionsDialog(None, account, "QUILL Lite")
    try:
        dialog.web.SetValue(True)
        event = wx.CommandEvent(wx.wxEVT_CHECKBOX, dialog.web.GetId())
        event.SetInt(1)
        dialog.web.GetEventHandler().ProcessEvent(event)
        assert account.web_search is True
    finally:
        dialog.Destroy()
