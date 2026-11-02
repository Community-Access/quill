"""Any AI fallback is said once, and one that changes company asks first (2026-10-16).

Covers the three places a request's destination is resolved: Ask Quill's
backend (``make_default_backend``), the Ask Quill panel that asks the question,
and the hosted AI route (free AI, own key, ChatGPT plan) in both editors. Fakes
only: no provider is reached, no dialog is shown.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.ai import backend_substitution
from quill.core.ai.fallback import FallbackPlan, plan_substitution

# -- the plan --------------------------------------------------------------- #


def test_a_local_substitute_is_announced_without_a_question() -> None:
    plan = plan_substitution(
        chosen="Anthropic", substitute="the on-device model", substitute_is_local=True
    )
    assert plan.offer and not plan.requires_consent
    assert plan.announcement.startswith("Anthropic was not available, so Quill is using")


def test_a_cloud_substitute_is_a_question_naming_who_gets_the_text() -> None:
    plan = plan_substitution(
        chosen="Your own Gemini key",
        substitute="QUILL's free AI",
        substitute_is_local=False,
        destination="QUILL's free AI service",
    )
    assert plan.requires_consent
    assert plan.announcement == (
        "Your own Gemini key is not available right now. Use QUILL's free AI instead? "
        "That sends your text to QUILL's free AI service over the internet. "
        "Choose No and nothing is sent."
    )


def test_the_same_provider_is_no_substitution() -> None:
    assert not plan_substitution(
        chosen="OpenAI", substitute="openai", substitute_is_local=False
    ).offer


# -- Ask Quill's backend resolution ------------------------------------------ #


class _Backend:
    def __init__(self, name: str, available: bool) -> None:
        self.name = name
        self.available = available

    def is_available(self) -> tuple[bool, str]:
        return self.available, ""


def _resolve(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, simple_provider: str) -> Any:
    """Configured connection: Anthropic, unavailable. Ask Quill setup: *simple_provider*."""
    import quill.core.ai.llama_cpp_backend as llama
    import quill.core.ai.provider_backend as providers
    import quill.core.assistant_ai as assistant_ai
    import quill.core.settings as settings_module
    from quill.core.ai import assistant

    connection = tmp_path / "connection.json"
    connection.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(assistant_ai, "assistant_connection_path", lambda: connection)
    monkeypatch.setattr(
        assistant_ai,
        "load_assistant_connection_settings",
        lambda: SimpleNamespace(provider="Anthropic"),
    )
    monkeypatch.setattr(providers, "ProviderChatBackend", lambda _s: _Backend("anthropic", False))
    monkeypatch.setattr(
        providers, "SimpleChatBackend", lambda provider, _model: _Backend(provider, True)
    )
    monkeypatch.setattr(
        settings_module,
        "load_settings",
        lambda: SimpleNamespace(
            ai_chat_default_provider=simple_provider,
            ai_chat_default_model="some-model",
            ai_prompt_default_model="",
        ),
    )
    monkeypatch.setattr(llama, "LlamaCppBackend", lambda: _Backend("local", True))
    monkeypatch.setattr("sys.platform", "win32")  # not macOS: no Foundation Models step
    return assistant.Assistant()


def test_a_different_cloud_provider_is_held_not_used(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    helper = _resolve(monkeypatch, tmp_path, simple_provider="openai")

    # Nothing goes to OpenAI unasked: the assistant answers on-device for now.
    assert helper.backend.name == "local"
    assert helper.backend_plan.requires_consent
    assert "Use openai instead?" in helper.backend_plan.announcement
    # The note still says what happened, for anywhere that announces it.
    assert helper.backend_note.startswith("Anthropic was not available")

    assert helper.accept_substitute() is True
    assert helper.backend.name == "openai"
    assert not helper.backend_plan.offer and helper.backend_note == ""
    assert helper.accept_substitute() is False  # a yes is given once


def test_an_on_device_substitute_is_used_directly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    helper = _resolve(monkeypatch, tmp_path, simple_provider="ollama")

    assert helper.backend.name == "ollama"
    assert not helper.backend_plan.requires_consent


def test_the_question_is_handed_over_once() -> None:
    backend_substitution.reset()
    backend_substitution.fell_past("Anthropic")
    assert backend_substitution.hold_for_consent("openai", object()) is True
    plan, held = backend_substitution.take()
    assert plan.requires_consent and held is not None
    assert backend_substitution.take() == (FallbackPlan.none(), None)


def test_nothing_is_held_without_a_fall_past() -> None:
    backend_substitution.reset()
    assert backend_substitution.hold_for_consent("openai", object()) is False


# -- the Ask Quill panel asks the question ------------------------------------ #


class _Panel:
    def __init__(self, plan: FallbackPlan, answer: bool) -> None:
        from quill.ui.assistant_reply_delivery import AssistantReplyDeliveryMixin

        self.asked: list[str] = []
        self.accepted = 0
        self._answer = answer
        self._assistant = SimpleNamespace(backend_plan=plan, accept_substitute=self._accept)
        self.offer = lambda: AssistantReplyDeliveryMixin._offer_backend_substitute(self)  # type: ignore[arg-type]

    def _accept(self) -> bool:
        self.accepted += 1
        return True

    def _confirm_substitute(self, question: str) -> bool:
        self.asked.append(question)
        return self._answer


def test_the_panel_swaps_only_on_yes() -> None:
    plan = plan_substitution(chosen="Anthropic", substitute="OpenAI", substitute_is_local=False)

    yes = _Panel(plan, answer=True)
    yes.offer()
    no = _Panel(plan, answer=False)
    no.offer()

    assert yes.asked == [plan.announcement] and yes.accepted == 1
    assert no.asked == [plan.announcement] and no.accepted == 0


def test_the_panel_asks_nothing_when_nothing_is_held() -> None:
    panel = _Panel(FallbackPlan.none(), answer=True)
    panel.offer()
    assert panel.asked == [] and panel.accepted == 0


# -- the hosted AI route, both editors ----------------------------------------- #


class _Service:
    def __init__(self, route: str = "own_key", provider: str = "gemini") -> None:
        from quill.ui.hosted_ai_route_guard import RouteGuardMixin

        class _Guarded(RouteGuardMixin):
            pass

        self.guard = _Guarded()
        self.guard.route = route  # type: ignore[misc]
        self.guard.own_key_provider = provider  # type: ignore[misc]
        self.questions: list[str] = []
        self.answer = False
        self.errors: list[str] = []

        def confirm(question: str) -> bool:
            self.questions.append(question)
            return self.answer

        self.guard.confirm_route_change = confirm

    def request(self) -> bool:
        return self.guard.route_allowed(self.errors.append)


def test_the_first_request_and_a_steady_route_ask_nothing() -> None:
    service = _Service()
    assert service.request() and service.request()
    assert service.questions == []


def test_a_route_change_nobody_made_asks_before_sending() -> None:
    service = _Service(route="own_key", provider="gemini")
    service.request()
    service.guard.route = "free"  # the Gemini key went missing from the store

    assert service.request() is False
    assert service.questions == [
        "Your own Google Gemini key is not available right now. Use QUILL's free AI "
        "instead? That sends your text to QUILL's free AI service over the internet. "
        "Choose No and nothing is sent."
    ]
    assert service.errors[0].startswith("Nothing was sent.")

    # Still asked next time, because No is not a choice of the new route.
    assert service.request() is False
    assert len(service.questions) == 2


def test_yes_makes_the_new_route_the_route() -> None:
    service = _Service(route="chatgpt")
    service.request()
    service.guard.route = "own_key"
    service.answer = True

    assert service.request() is True
    assert service.request() is True
    assert len(service.questions) == 1  # said once
    assert "sends your text to Google Gemini" in service.questions[0]


def test_a_route_the_listener_chose_is_never_questioned() -> None:
    service = _Service(route="free")
    service.request()
    service.guard.route = "chatgpt"  # signed in with ChatGPT just now
    service.guard.route_chosen()

    assert service.request() is True
    assert service.questions == []


def test_the_service_sends_nothing_when_the_answer_is_no(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.ui.hosted_ai_service as module

    submitted: list[str] = []
    told: list[str] = []
    monkeypatch.setattr(module, "_submit", lambda name, *_a, **_k: submitted.append(name))
    monkeypatch.setattr(module, "_call_after", lambda func, *args: func(*args))
    monkeypatch.setattr(
        module.AiService,
        "route_allowed",
        lambda _self, on_error: on_error("Nothing was sent.") or False,
    )
    monkeypatch.setattr(module.AiService, "chatgpt_active", property(lambda _s: False))
    # A ready connection that can see, so each request reaches the route guard.
    from quill.core.ai.connection_choice import ConnectionFacts

    facts = ConnectionFacts(stored="chatgpt", chatgpt_signed_in=True)
    monkeypatch.setattr(module.AiService, "connection_facts", lambda _s: facts)
    monkeypatch.setattr(module.AiService, "connection", property(lambda _s: "chatgpt"))
    monkeypatch.setattr(module.AiService, "chatgpt", SimpleNamespace(model=""), raising=False)
    service = module.AiService(SimpleNamespace(data_dir=Path("."), settings=None))

    service.ask("rewrite", "text", None, on_done=lambda *_a: None, on_error=told.append)
    service.converse("hi", None, [], on_done=lambda *_a: None, on_error=told.append)
    service.describe_image(Path("x.png"), "what", on_done=lambda _t: None, on_error=told.append)

    assert submitted == []
    assert told == ["Nothing was sent."] * 3


def test_a_deliberate_change_in_the_ai_menu_marks_the_route_chosen() -> None:
    from quill.ui.hosted_ai_chatgpt_commands import ChatGptAiMixin

    chosen: list[bool] = []
    host = SimpleNamespace(ai_service=SimpleNamespace(route_chosen=lambda: chosen.append(True)))
    commands = SimpleNamespace(_ai_host=lambda: host)

    ChatGptAiMixin._ai_route_changed(commands)  # type: ignore[arg-type]

    assert chosen == [True]
