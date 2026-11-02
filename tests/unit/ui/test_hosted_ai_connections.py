"""Choose Your AI in the shared service (codex.md 10A): the stored choice, no
fall-through, the sentences of 10A.5, and GATE-CAPS on every request.

Real :class:`AiService`, real settings object, real capability registry; only
the network edge (the worker submit and ``wx.CallAfter``) and the credential
store are replaced.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.ai import own_key
from quill.core.ai.chatgpt_errors import (
    ChatGptBusyError,
    ChatGptLimitError,
    ChatGptSignedOutError,
    ChatGptUsageUnavailableError,
)
from quill.core.ai.connection_caps import CAPABILITIES, Claim, ConnectionRecord
from quill.ui import hosted_ai_connection_route as route_module
from quill.ui import hosted_ai_service as service_module
from quill.ui.hosted_ai_service import AiService


class _Account:
    def __init__(self, *, signed_in: bool = False, ended: bool = False) -> None:
        self.signed_in = signed_in
        self.ended_by_openai = ended
        self.model = "gpt-6"
        self.web_search = False
        self.slug = "quill"
        self.marked = 0

    def mark_ended_by_openai(self) -> None:
        self.marked += 1
        self.signed_in = False
        self.ended_by_openai = True


class _App:
    ai_agent_name = "QUILL"

    def __init__(self, data_dir: Path, connection: str = "") -> None:
        self.data_dir = data_dir
        self.settings = SimpleNamespace(
            ai_connection=connection,
            ai_own_key_model="",
            ai_own_key_provider="openai",
            ai_copilot_model="",
            ai_codex_model="",
        )
        self.saves = 0

    def save_settings(self) -> None:
        self.saves += 1


@pytest.fixture
def world(tmp_path, monkeypatch):
    submitted: list[tuple[str, Any, Any, Any]] = []
    key = {"saved": False}
    monkeypatch.setattr(own_key, "has_own_key", lambda *_a: key["saved"])
    monkeypatch.setattr(
        service_module,
        "_submit",
        lambda name, func, *, on_success, on_failure: submitted.append((
            name,
            func,
            on_success,
            on_failure,
        )),
    )
    monkeypatch.setattr(service_module, "_call_after", lambda func, *args: func(*args))

    def make(connection: str = "", *, account: _Account | None = None) -> AiService:
        service = AiService(_App(tmp_path, connection))
        service._chatgpt = account or _Account()
        service.confirm_route_change = lambda _q: True
        return service

    return SimpleNamespace(make=make, submitted=submitted, key=key)


def _ask(service: AiService, **kwargs: Any) -> list[str]:
    told: list[str] = []
    service.ask("rewrite", "text", None, on_done=lambda *_a: None, on_error=told.append, **kwargs)
    return told


# -- the stored choice -------------------------------------------------------------- #


def test_the_first_read_migrates_once_and_saves(world) -> None:
    world.key["saved"] = True
    service = world.make("", account=_Account(signed_in=True))
    assert service.connection == "chatgpt"
    assert service._app.settings.ai_connection == "chatgpt"
    assert service._app.saves == 1
    service._chatgpt.signed_in = False  # the stored choice now stands on its own
    assert service.connection == "chatgpt" and service._app.saves == 1


def test_a_stored_choice_beats_the_old_precedence(world) -> None:
    world.key["saved"] = True
    service = world.make("own_key", account=_Account(signed_in=True))
    assert service.route == "own_key"
    assert service.own_key_active and not service.chatgpt_active


def test_signing_out_of_the_row_in_use_never_falls_through(world) -> None:
    service = world.make("own_key")  # no key saved any more
    assert _ask(service) == ["No AI is in use. Choose one."]
    assert world.submitted == []


def test_a_revoked_plan_fails_with_the_sentence_and_sends_nothing(world) -> None:
    service = world.make("chatgpt", account=_Account(signed_in=False, ended=True))
    told = _ask(service)
    assert told == [
        "Your ChatGPT plan sign-in has ended. Nothing was sent. "
        "Press Ctrl+4 to sign in again or choose another."
    ]
    assert world.submitted == []
    rows = {row.connection: row.text for row in service.connection_rows()}
    assert rows["chatgpt"] == "My ChatGPT plan, signed out by OpenAI"


def test_copilot_and_codex_say_not_available_yet(world) -> None:
    assert _ask(world.make("copilot"))[0].startswith("My GitHub Copilot is not available yet.")
    signed = _Account(signed_in=True)
    assert _ask(world.make("codex", account=signed))[0].startswith("Codex is not available yet.")
    assert world.submitted == []


def test_codex_single_requests_ride_the_plan_once_available(world) -> None:
    service = world.make("codex", account=_Account(signed_in=True))
    assert service.route == "chatgpt" and service.chatgpt_active


def test_choose_needs_a_ready_connection_and_marks_the_choice(world) -> None:
    service = world.make("free")
    assert not service.choose("chatgpt")
    assert service._app.settings.ai_connection == "free"
    service._chatgpt.signed_in = True
    assert service.choose("chatgpt")
    assert service._app.settings.ai_connection == "chatgpt"
    assert service._route_in_use[0] == "chatgpt"


def test_signing_in_is_choosing_but_a_model_change_is_not(world) -> None:
    service = world.make("free")
    service.note_readiness()
    service._chatgpt.signed_in = True  # the window signed in
    service.connection_changed("chatgpt")
    assert service._app.settings.ai_connection == "chatgpt"
    # Back to free deliberately; a model change in the ChatGPT window keeps it.
    service.choose("free")
    service.note_readiness()
    service.connection_changed("chatgpt")
    assert service._app.settings.ai_connection == "free"


def test_saving_a_key_chooses_it(world) -> None:
    service = world.make("free")
    service.note_readiness()
    world.key["saved"] = True
    service.connection_changed("own_key")
    assert service.connection == "own_key"


# -- GATE-CAPS, behaviourally ------------------------------------------------------- #


def _lacking(*missing: str):
    def record_for(connection: str, **_kw: Any) -> ConnectionRecord:
        claims = {cap: Claim(cap not in missing, "test record") for cap in CAPABILITIES}
        return ConnectionRecord(connection, claims)

    return record_for


@pytest.mark.parametrize("connection", ["free", "chatgpt", "own_key"])
@pytest.mark.parametrize("capability", ["text", "pictures"])
def test_no_request_reaches_a_connection_lacking_the_capability(
    world, monkeypatch, connection, capability
) -> None:
    world.key["saved"] = True
    service = world.make(connection, account=_Account(signed_in=True))
    monkeypatch.setattr(route_module, "record_for", _lacking(capability))
    told: list[str] = []
    service.ask(
        "rewrite", "t", None, on_done=lambda *_a: None, on_error=told.append, requires=(capability,)
    )
    service.converse(
        "hi", None, [], on_done=lambda *_a: None, on_error=told.append, requires=(capability,)
    )
    service.describe_image(Path("x.png"), "q", on_done=lambda _t: None, on_error=told.append)
    assert world.submitted == []
    assert len(told) == 3 and all("Nothing was sent." in said for said in told)


def test_a_request_the_connection_can_do_goes_out(world, monkeypatch) -> None:
    service = world.make("chatgpt", account=_Account(signed_in=True))
    monkeypatch.setattr(route_module, "record_for", _lacking())
    assert _ask(service) == []
    assert [name for name, *_ in world.submitted] == ["quill-ai-ask"]


def test_the_free_ai_cannot_take_a_picture(world) -> None:
    told: list[str] = []
    world.make("free").describe_image(
        Path("x.png"), "q", on_done=lambda _t: None, on_error=told.append
    )
    assert told == ["Pictures need a connection that can see. Nothing was sent."]
    assert world.submitted == []


def test_the_offer_and_label_come_from_the_registry(world) -> None:
    service = world.make("free", account=_Account(signed_in=True))
    assert service.needs_label("pictures") == "(needs a connection that sees)"
    assert service.capability_offer("pictures").target == "chatgpt"
    assert service.needs_label("text") == ""


# -- failures on the plan (10A.5) ---------------------------------------------------- #


def test_a_401_marks_the_plan_signed_out_by_openai_and_is_not_retried(world) -> None:
    account = _Account(signed_in=True)
    service = world.make("chatgpt", account=account)
    told: list[str] = []
    service.ask("rewrite", "t", None, on_done=lambda *_a: None, on_error=told.append)
    world.submitted[-1][3]("quill-ai-ask", ChatGptSignedOutError("gone"))
    assert told == [
        "Your ChatGPT plan sign-in has ended. Nothing was sent. "
        "Press Ctrl+4 to sign in again or choose another."
    ]
    assert account.marked == 1 and len(world.submitted) == 1
    # The next request says the same without sending anything.
    assert _ask(service)[0].startswith("Your ChatGPT plan sign-in has ended.")
    assert len(world.submitted) == 1


@pytest.mark.parametrize(
    ("error", "limit"),
    [
        (ChatGptLimitError("used up"), True),
        (ChatGptUsageUnavailableError("unavailable"), True),
        (ChatGptBusyError("slow down"), False),
    ],
)
def test_a_plan_limit_is_said_once_and_never_switched(world, error, limit) -> None:
    service = world.make("chatgpt", account=_Account(signed_in=True))
    told: list[str] = []
    service.ask("rewrite", "t", None, on_done=lambda *_a: None, on_error=told.append)
    world.submitted[-1][3]("quill-ai-ask", error)
    sentence = (
        "Your ChatGPT plan's limit for QUILL is reached. Nothing was sent. "
        "Manage usage is in the Usage window."
    )
    assert (told == [sentence]) is limit
    assert len(told) == 1 and len(world.submitted) == 1
    assert service.connection == "chatgpt"


def test_answers_are_delivered_as_text(world) -> None:
    service = world.make("chatgpt", account=_Account(signed_in=True))
    got: list[str] = []
    service.ask("rewrite", "t", None, on_done=lambda text, _q: got.append(text), on_error=print)
    world.submitted[-1][2]("quill-ai-ask", ("```mermaid\ngraph TD\n```", None))
    assert got == ["```text\ngraph TD\n```"]


def test_which_ai_and_usage_read_the_live_state(world, tmp_path) -> None:
    from quill.core.ai.chatgpt_usage import record_request

    record_request(tmp_path, "quill", input_tokens=3, output_tokens=2)
    service = world.make("chatgpt", account=_Account(signed_in=True))
    assert service.which_ai() == (
        "My ChatGPT plan, gpt-6. 1 request today from QUILL, counted on this computer."
    )
    assert service.status_cell() == "AI: ChatGPT plan"
    sentences = [row.sentence for row in service.usage_rows()]
    assert sentences[1].startswith("My ChatGPT plan: 1 request today from QUILL")
