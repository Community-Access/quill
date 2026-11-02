"""My GitHub Copilot and Codex in the shared AI service (codex.md 10A.12, 10A.13).

Real :class:`AiService`, real settings, real capability registry; a fake
:class:`CopilotChat` stands in for the SDK, and the worker submit and
``wx.CallAfter`` run inline so the order of events is the order asserted.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.ai.copilot_chat import CopilotAnswer, CopilotLimitReached, CopilotModelList
from quill.core.ai.copilot_chat_parts import CopilotModel
from quill.core.ai.copilot_quota import CopilotQuota, QuotaBucket
from quill.core.ai.copilot_state import CopilotReadiness
from quill.ui import hosted_ai_copilot_route as route
from quill.ui import hosted_ai_service as service_module
from quill.ui.hosted_ai_service import AiService


class _Account:
    def __init__(self, signed_in: bool = False) -> None:
        self.signed_in = signed_in
        self.ended_by_openai = False
        self.model = "gpt-6"
        self.slug = "quill"
        self.tokens = 0

    def access_token(self) -> str:
        self.tokens += 1
        return "this-apps-token"


class _Chat:
    """A CopilotChat stand-in that records every call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.fail: BaseException | None = None

    def _answer(self, kind: str, payload: Any) -> CopilotAnswer:
        self.calls.append((kind, payload))
        if self.fail is not None:
            raise self.fail
        return CopilotAnswer(text=f"{kind} answer")

    def stream(self, prompt: str, *, on_delta, system: str = "", stop=None, **_k) -> CopilotAnswer:
        return self._answer("stream", {"prompt": prompt, "system": system})

    def ask(self, prompt: str, *, system: str = "", images=(), **_k) -> CopilotAnswer:
        return self._answer("ask", {"prompt": prompt, "images": tuple(images)})

    def converse(self, history, prompt: str, **_k) -> CopilotAnswer:
        return self._answer("converse", {"history": list(history), "prompt": prompt})

    def list_models(self) -> CopilotModelList:
        return CopilotModelList((CopilotModel("auto", "Auto (Copilot Free chooses)"),), True)

    def quota(self) -> CopilotQuota:
        bucket = QuotaBucket(entitlement=300, used=41, remaining_percent=86.0)
        return CopilotQuota(buckets={"premium_interactions": bucket})


class _App:
    ai_agent_name = "QUILL Lite"

    def __init__(self, data_dir: Path, connection: str) -> None:
        self.data_dir = data_dir
        self.settings = SimpleNamespace(
            ai_connection=connection,
            ai_own_key_model="",
            ai_own_key_provider="openai",
            ai_copilot_model="",
            ai_codex_model="gpt-codex",
        )

    def save_settings(self) -> None:
        pass


@pytest.fixture
def world(tmp_path, monkeypatch):
    jobs: list[str] = []

    def submit(name, func, *, on_success, on_failure):
        jobs.append(name)
        try:
            result = func()
        except BaseException as error:  # noqa: BLE001 - as the worker would
            on_failure(name, error)
        else:
            on_success(name, result)

    monkeypatch.setattr(service_module, "_submit", submit)
    monkeypatch.setattr(service_module, "_call_after", lambda func, *args: func(*args))
    chat = _Chat()
    monkeypatch.setattr(route.CopilotRouteMixin, "copilot_chat", lambda _self: chat)
    ready = CopilotReadiness(client_id=True, sdk=True, cli=True, signed_in=True)
    monkeypatch.setattr(route.CopilotRouteMixin, "copilot_readiness", lambda _self: ready)
    monkeypatch.setattr(route.CopilotRouteMixin, "codex_available", property(lambda _s: True))

    def make(connection: str, *, plan: bool = False) -> AiService:
        service = AiService(_App(tmp_path, connection))
        service._chatgpt = _Account(signed_in=plan)
        service.confirm_route_change = lambda _q: True
        return service

    return SimpleNamespace(make=make, chat=chat, jobs=jobs)


def test_a_single_request_goes_to_copilot_on_a_worker(world) -> None:
    service = world.make("copilot")
    got: list[str] = []

    service.ask(
        "summarize",
        "Some text.",
        None,
        on_done=lambda text, _q: got.append(text),
        on_error=got.append,
    )

    assert world.jobs == ["quill-ai-ask"]
    assert got == ["stream answer"]
    kind, payload = world.chat.calls[0]
    assert kind == "stream" and "Some text." in payload["prompt"]
    assert payload["system"]  # the feature's own instructions, as on every route


def test_a_conversation_turn_carries_the_local_history(world) -> None:
    service = world.make("copilot")
    got: list[str] = []

    service.converse(
        "And then?",
        ["An excerpt."],
        [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello"}],
        on_done=lambda text, _q, dropped: got.append(f"{text}/{dropped}"),
        on_error=got.append,
    )

    assert got == ["converse answer/0"]
    _kind, payload = world.chat.calls[0]
    assert [turn.role for turn in payload["history"]] == ["user", "assistant"]
    assert "An excerpt." in payload["prompt"] and payload["prompt"].endswith("And then?")


def test_a_picture_goes_as_an_attachment_when_the_model_sees(world, monkeypatch, tmp_path) -> None:
    import quill.core.ai.copilot_ai_help as help_module
    from quill.core.ai.copilot_chat import CopilotImage

    monkeypatch.setattr(
        help_module, "copilot_image", lambda path: CopilotImage(b"png", "image/png", "a.png")
    )
    from quill.core.ai.connection_caps import clear_model_capabilities, set_model_capabilities

    set_model_capabilities("copilot", "vision-1", {"pictures": True}, source="test models.list")
    try:
        service = world.make("copilot")
        service._app.settings.ai_copilot_model = "vision-1"
        got: list[str] = []
        service.describe_image(
            tmp_path / "a.png", "What is it?", on_done=got.append, on_error=got.append
        )
    finally:
        clear_model_capabilities()

    assert got == ["ask answer"]
    _kind, payload = world.chat.calls[0]
    assert payload["prompt"] == "What is it?" and payload["images"][0].mime_type == "image/png"


def test_a_copilot_failure_is_said_once_with_its_sentence(world) -> None:
    service = world.make("copilot")
    world.chat.fail = CopilotLimitReached("Your GitHub Copilot limit for QUILL Lite is reached.")
    told: list[str] = []

    service.ask("summarize", "x", None, on_done=lambda *_a: None, on_error=told.append)

    assert told == ["Your GitHub Copilot limit for QUILL Lite is reached."]
    assert len(world.chat.calls) == 1  # never retried, never switched


def test_the_copilot_row_reads_signed_in_and_names_githubs_count(world) -> None:
    service = world.make("copilot")
    rows = {row.connection: row.text for row in service.connection_rows()}
    assert rows["copilot"] == "My GitHub Copilot, in use"
    said: list[str] = []

    service.which_ai_later(said.append)  # no count yet: the line waits for GitHub's

    assert world.jobs == ["quill-ai-copilot-quota"]
    assert said == ["My GitHub Copilot. 41 of 300 premium requests this month, by GitHub's count."]
    usage = {row.connection: row.sentence for row in service.usage_rows()}
    assert usage["copilot"] == (
        "My GitHub Copilot: 41 of 300 premium requests this month, by GitHub's count."
    )
    service.which_ai_later(said.append)  # a count is kept: said at once, refreshed quietly
    assert len(said) == 2 and world.jobs.count("quill-ai-copilot-quota") == 2


def test_codex_is_one_keypress_once_the_plan_is_signed_in(world) -> None:
    service = world.make("free", plan=True)
    rows = {row.connection: row.state for row in service.connection_rows()}
    assert rows["codex"] == "signed_in"
    assert service.choose("codex") is True
    assert service.which_ai().startswith(
        "Codex, on your ChatGPT plan. Single requests go to the plan directly."
    )


def test_codex_single_requests_take_the_plans_direct_route(world, monkeypatch) -> None:
    import quill.core.ai.chatgpt_ai_help as plan

    seen: list[Any] = []
    monkeypatch.setattr(
        plan, "ask_with_chatgpt", lambda account, *a, **k: seen.append(account) or "plan answer"
    )
    service = world.make("codex", plan=True)
    got: list[str] = []

    service.ask(
        "rewrite", "x", None, on_done=lambda text, _q: got.append(text), on_error=got.append
    )

    assert got == ["plan answer"]
    assert seen == [service.chatgpt]  # this app's own sign-in (decision 21)
    assert world.chat.calls == []  # no Codex process, no Copilot


def test_codex_tasks_get_this_apps_own_plan_token(world) -> None:
    service = world.make("codex", plan=True)
    harness = service.agent_harness()
    inner = harness._harness

    assert inner.id == "codex" and inner.agent_name == "QUILL Lite"
    assert inner._token_provider() == "this-apps-token"
    assert service.chatgpt.tokens == 1
    assert harness._model == "gpt-codex"


def test_copilot_tasks_run_copilots_tool_harness_under_this_apps_name(world) -> None:
    harness = world.make("copilot").agent_harness()
    assert harness.id == "copilot"
    assert harness._harness.agent_name == "QUILL Lite"
    assert world.make("free").agent_harness() is None


def test_copilot_free_lists_only_auto(world) -> None:
    models, error = world.make("copilot").copilot_models()
    assert error == "" and models == [("auto", "Auto (Copilot Free chooses)")]
