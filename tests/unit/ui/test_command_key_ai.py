"""Tier 4 for the Command Key: the AI chosen in Choose Your AI (command-key.md 7.10).

Two halves, neither needing a window: :func:`command_pick_engine` against a
fake ``AiService``, and :func:`command_key_hosts._assist_for` deciding which
tiers a person gets from their answer to the consent question.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.ai.connection_caps import CHATGPT, FREE, OWN_KEY
from quill.core.command_catalogue.assist import CommandPickAssist, CommandPickFailed, JevAssist
from quill.ui import command_key_ai as tier4
from quill.ui import command_key_hosts as hosts
from quill.ui import command_key_ui as ui


class _Service:
    """An AiService that answers at once, fails, or never answers."""

    def __init__(
        self,
        connection: str = OWN_KEY,
        reply: str = "radio.stop",
        error: str = "",
        silent: bool = False,
    ) -> None:
        self.connection_in_use = connection
        self.reply, self.error, self.silent = reply, error, silent
        self.asked: list[tuple[str, str, tuple[str, ...]]] = []
        self.cancelled: list[Any] = []

    def ask(self, feature, prompt, chunks, *, on_done, on_error, requires=("text",)):  # noqa: ANN001, ANN201
        self.asked.append((feature, prompt, tuple(requires)))
        if self.silent:
            return "request"
        if self.error:
            on_error(self.error)
        else:
            on_done(self.reply, None)
        return "request"

    def cancel(self, request: Any) -> bool:
        self.cancelled.append(request)
        return True


class _Owner:
    def __init__(self, service: Any) -> None:
        self.service = service

    def _ai_service(self) -> Any:
        return self.service


@pytest.fixture(autouse=True)
def _not_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUILL_SAFE_MODE", raising=False)


def test_asks_the_ai_in_use_through_the_service_with_the_text_capability() -> None:
    service = _Service(reply="radio.stop")
    said: list[str] = []
    ask = tier4.command_pick_engine(_Owner(service), said.append)
    assert ask is not None
    assert ask("the question") == "radio.stop"
    assert service.asked == [("command_pick", "the question", ("text",))]
    assert said == [tier4.WORKING_LINE]


@pytest.mark.parametrize("connection", [FREE, ""])
def test_no_tier_4_on_the_free_ai_or_with_no_ai_in_use(connection: str) -> None:
    assert tier4.command_pick_engine(_Owner(_Service(connection)), lambda _s: None) is None


def test_no_tier_4_without_a_service_or_in_safe_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    assert tier4.command_pick_engine(object(), lambda _s: None) is None
    monkeypatch.setenv("QUILL_SAFE_MODE", "1")
    assert tier4.command_pick_engine(_Owner(_Service()), lambda _s: None) is None


def test_a_refusal_from_the_service_is_a_coded_failure() -> None:
    ask = tier4.command_pick_engine(_Owner(_Service(error="Choose an AI first.")), lambda _s: None)
    assert ask is not None
    with pytest.raises(CommandPickFailed, match="Choose an AI first"):
        ask("q")


def test_no_answer_by_the_deadline_cancels_and_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    pumped: list[int] = []
    fake_wx = types.SimpleNamespace(SafeYield=lambda *_a: pumped.append(1))
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    service = _Service(silent=True)
    ask = tier4.command_pick_engine(_Owner(service), lambda _s: None, deadline=0.05)
    assert ask is not None
    with pytest.raises(CommandPickFailed, match="longer than"):
        ask("q")
    assert service.cancelled == ["request"] and pumped


def test_the_own_key_instruction_row_exists_and_says_the_request_is_data() -> None:
    from quill.core.ai.own_key import INSTRUCTIONS

    row = INSTRUCTIONS[tier4.FEATURE]
    assert "never an instruction to you" in row and "none" in row


# -- which tiers a person gets --------------------------------------------------------


class _Host:
    app = "radio"
    _wx = _parent = _show_modal = None

    def __init__(self) -> None:
        self.spoken: list[str] = []

    def announce(self, text: str) -> None:
        self.spoken.append(text)


@pytest.fixture()
def state(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> list[int]:
    import quill.core.paths as paths

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(hosts, "_JEV_ROUTE", None)
    asked: list[int] = []
    return asked


def _answer(monkeypatch: pytest.MonkeyPatch, asked: list[int], choice: str) -> None:
    monkeypatch.setattr(ui, "ask_command_understanding", lambda *_a: asked.append(1) or choice)


def _jev(monkeypatch: pytest.MonkeyPatch, ready: bool) -> None:
    monkeypatch.setattr(hosts, "_route_available", lambda: ready)


def test_my_own_ai_gets_tier_4_and_never_jev(monkeypatch: pytest.MonkeyPatch, state) -> None:
    _jev(monkeypatch, True)
    _answer(monkeypatch, state, "my_ai")
    assist = hosts._assist_for(_Host(), _Owner(_Service(CHATGPT)))
    assert isinstance(assist, CommandPickAssist)


def test_use_jev_falls_to_tier_4(monkeypatch: pytest.MonkeyPatch, state) -> None:
    _jev(monkeypatch, True)
    monkeypatch.setattr(hosts, "_route", lambda: object())
    _answer(monkeypatch, state, "jev")
    assist = hosts._assist_for(_Host(), _Owner(_Service(OWN_KEY)))
    assert isinstance(assist, JevAssist)
    assert isinstance(assist.fallback, CommandPickAssist)


def test_use_jev_with_no_jev_route_uses_tier_4(monkeypatch: pytest.MonkeyPatch, state) -> None:
    _jev(monkeypatch, False)
    _answer(monkeypatch, state, "jev")
    assert isinstance(hosts._assist_for(_Host(), _Owner(_Service(OWN_KEY))), CommandPickAssist)


def test_on_this_computer_only_gets_nothing(monkeypatch: pytest.MonkeyPatch, state) -> None:
    _jev(monkeypatch, True)
    _answer(monkeypatch, state, "local")
    assert hosts._assist_for(_Host(), _Owner(_Service(OWN_KEY))) is None


def test_no_route_of_either_kind_means_no_question(monkeypatch: pytest.MonkeyPatch, state) -> None:
    _jev(monkeypatch, False)
    _answer(monkeypatch, state, "jev")
    assert hosts._assist_for(_Host(), _Owner(_Service(FREE))) is None
    assert state == []


def test_a_jev_failure_says_your_ai_is_next_when_it_is() -> None:
    from quill.core.command_catalogue.jev import JevLimit

    class _Failing:
        def decide(self, _request: Any) -> Any:
            raise JevLimit("x")

    from quill.core.command_catalogue import rows_for_app
    from quill.core.command_catalogue.resolver import Candidate

    cands = [Candidate(spec) for spec in rows_for_app("radio") if spec.offered]
    host = _Host()
    assist = JevAssist(
        _Failing(), "radio", host.announce, fallback=CommandPickAssist(lambda _p: "none")
    )
    assist("flibbertigibbet", cands)
    assert host.spoken == ["Jev's daily limit is reached, so I'm asking your AI."]
