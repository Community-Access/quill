"""Which AI Studio asks about a picture: the plan, the provider, or a way to sign in."""

from types import SimpleNamespace

import pytest
import wx

from quill.apps.studio_capture import StudioCaptureMixin
from quill.core.ai.chatgpt_account import ChatGptAccount
from quill.core.ai.chatgpt_state import ChatGptState
from quill.core.studio_plan_vision import PlanConnection
from quill.stability.task_manager import UiLifetimeToken


class Host(StudioCaptureMixin):
    def __init__(self, frame, *, answer=wx.YES, pick=0, safe=False):
        self.frame = frame
        self._safe_mode = safe
        self.answer = answer
        self.pick = pick
        self.boxes = []
        self.said = []
        self.choices = []
        self.opened = []
        self._capture_lifetime = UiLifetimeToken()

    def _show_message_box(self, message, title, _style):
        self.boxes.append((title, message))
        return self.answer

    def _show_modal_dialog(self, dialog, title):
        self.choices.append((title, dialog.GetSelection()))
        if self.pick is None:
            return wx.ID_CANCEL
        dialog.SetSelection(self.pick)
        return wx.ID_OK

    def _announce(self, message, **_kwargs):
        self.said.append(message)

    def open_chatgpt_account(self):
        self.opened.append(True)


@pytest.fixture
def parent(wx_session_app):
    frame = wx.Frame(None)
    yield frame
    frame.Destroy()


@pytest.fixture
def world(tmp_path, monkeypatch):
    """AI on, no provider and no plan, until a test says otherwise."""
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    from quill.core import assistant_ai, studio_plan_vision
    from quill.core.ai import model_manager

    monkeypatch.setattr(model_manager, "load_ai_enabled", lambda: True)
    state = SimpleNamespace(
        provider=SimpleNamespace(provider="off", model="", host=""),
        plan=None,
    )
    monkeypatch.setattr(assistant_ai, "load_assistant_connection_settings", lambda: state.provider)
    monkeypatch.setattr(studio_plan_vision, "find_plan", lambda *_a, **_k: state.plan)
    account = ChatGptAccount(tmp_path, agent_name="QUILL Studio")
    account._state = ChatGptState(client_id="c", subject="s", email="me@example.org", model="m")
    state.signed_in_plan = PlanConnection(account)
    state.key_provider = SimpleNamespace(provider="openai", model="gpt-key", host="")
    return state


def test_the_choices_name_the_plan_and_the_provider(world):
    from quill.apps.studio_vision_route import _describe

    world.provider = world.key_provider
    assert _describe(world.signed_in_plan) == ("Your ChatGPT plan (me@example.org)")
    assert _describe(world.key_provider).startswith("openai (gpt-key)")


def test_a_plan_alone_is_used_without_asking_which(parent, world):
    world.plan = world.signed_in_plan
    host = Host(parent)
    assert host._approve_capture_ai() is world.plan
    assert not host.choices
    title, message = host.boxes[-1]
    assert title == "Send screenshot to AI"
    assert "your ChatGPT plan (me@example.org)?" in message
    assert "straight to OpenAI on your account" in message
    assert "counts toward your ChatGPT plan's own usage" in message
    assert "Service charges may apply" not in message


def test_declining_consent_sends_nothing(parent, world):
    world.plan = world.signed_in_plan
    assert Host(parent, answer=wx.NO)._approve_capture_ai() is None


def test_both_kinds_ask_which_and_remember_the_choice(parent, world):
    from quill.core.studio_capture_ai import load_capture_ai_preferences

    world.plan = world.signed_in_plan
    world.provider = world.key_provider
    host = Host(parent, pick=1)
    assert host._approve_capture_ai() is world.key_provider
    assert host.choices[-1] == ("Choose the AI for this picture", 0)
    assert "Service charges may apply" in host.boxes[-1][1]
    assert load_capture_ai_preferences()["vision_route"] == "provider"
    # Next time the list starts on the last choice.
    again = Host(parent, pick=None)
    assert again._approve_capture_ai() is None
    assert again.choices[-1][1] == 1


def test_no_ai_at_all_offers_the_plan_sign_in(parent, world):
    host = Host(parent, answer=wx.YES)
    assert host._approve_capture_ai() is None
    assert host.boxes[-1][0] == "Sign in with your ChatGPT plan"
    assert host.opened == [True]


def test_refusing_the_sign_in_opens_nothing(parent, world):
    host = Host(parent, answer=wx.NO)
    assert host._approve_capture_ai() is None
    assert not host.opened


def test_safe_mode_refuses_before_looking_for_a_plan(parent, world, monkeypatch):
    from quill.core import studio_plan_vision

    monkeypatch.setattr(
        studio_plan_vision, "find_plan", lambda *_a, **_k: pytest.fail("looked for a plan")
    )
    host = Host(parent, safe=True)
    assert host._approve_capture_ai() is None
    assert "AI is disabled" in host.said[-1] and not host.boxes


def test_automatic_analysis_follows_the_approved_plan(parent, world):
    from quill.core.studio_capture_ai import connection_identity

    world.plan = world.signed_in_plan
    world.provider = world.key_provider
    host = Host(parent)
    approved = {"approved_connection": connection_identity(world.plan)}
    assert host._automatic_vision_connection(approved) is world.plan
    approved = {"approved_connection": connection_identity(world.key_provider)}
    assert host._automatic_vision_connection(approved) is world.key_provider


def test_studio_account_window_is_refused_in_safe_mode(parent, world):
    host = Host(parent, safe=True)
    StudioCaptureMixin.open_chatgpt_account(host)
    assert host.said == ["AI is disabled in Safe Mode."]


def test_studio_account_window_signs_in_as_studio_and_is_not_built_twice(parent, world):
    host = Host(parent)
    StudioCaptureMixin.open_chatgpt_account(host)
    frame = host._chatgpt_frame
    try:
        assert frame.agent == "QUILL Studio"
        StudioCaptureMixin.open_chatgpt_account(host)
        assert host._chatgpt_frame is frame
    finally:
        frame.Destroy()


def test_the_sign_in_offer_says_a_sibling_makes_it_one_allow(parent, world, monkeypatch):
    from quill.core import studio_plan_vision

    monkeypatch.setattr(studio_plan_vision, "siblings_signed_in", lambda _a: ["QUILL"])
    host = Host(parent, answer=wx.NO)
    host._approve_capture_ai()
    message = host.boxes[-1][1]
    assert "signs in on its own, as QUILL Studio" in message
    assert "QUILL is already signed in on this computer" in message


def test_a_used_up_plan_offers_usage_settings_and_nothing_else(parent, world, monkeypatch):
    import webbrowser

    opened = []
    monkeypatch.setattr(webbrowser, "open", opened.append)
    host = Host(parent, answer=wx.YES)
    host._offer_plan_usage("https://chatgpt.com/#settings/Usage")
    assert opened == ["https://chatgpt.com/#settings/Usage"]
    assert host.boxes[-1][0] == "ChatGPT plan usage" and not host.choices
