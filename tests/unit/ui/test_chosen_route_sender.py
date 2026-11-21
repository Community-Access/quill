"""QUILL's sender for the AI chosen in Choose Your AI, and the gate that keeps it the one route.

The sender (``quill/ui/chosen_route_sender.py``) is where every advanced AI
request lands. It must ask the shared route first -- the same refusal, the same
"Send to a Different AI?", the same Auto announcement and picture consent -- and
then send only to the connection that route allowed. The gate at the bottom
freezes the places in QUILL's windows that still read the older choice, so a new
command cannot quietly reach around the route. Fakes only.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import quill.core.assistant_ai as aai
from quill.core.ai import chosen_route

# -- the sender ----------------------------------------------------------------- #


class _Service:
    def __init__(self, connection: str, *, refusal: str = "") -> None:
        self.connection = connection
        self.refusal = refusal
        self.asked: list[tuple[str, ...]] = []
        self.own_key_provider = "claude"
        self.own_key_model = "a-model"
        self.chatgpt = object()

    def request_connection(self, requires: tuple[str, ...], on_error: Any) -> str:
        self.asked.append(requires)
        if self.refusal:
            on_error(self.refusal)
            return ""
        return self.connection

    def capability_record(self, connection: str) -> Any:
        from quill.core.ai.connection_caps import record_for

        return record_for(connection, own_key_provider=self.own_key_provider)

    def _failure_sentence(self, error: BaseException, _connection: str) -> str:
        return f"failed: {error}"

    def status_cell(self) -> str:
        return "My own key, Anthropic Claude"

    def client(self) -> Any:
        return SimpleNamespace(converse=lambda prompt, _c, _h: (f"free:{prompt}", None, 0))


class _Frame:
    def __init__(self, service: _Service, *, ready: bool = True) -> None:
        self.service = service
        self.ready = ready
        self.opened = 0

    def _ai_service(self) -> _Service:
        return self.service

    def _ai_ready(self) -> bool:
        return self.ready

    def _ai_open_choose(self) -> None:
        self.opened += 1


def _sender(service: _Service, **kwargs: Any) -> Any:
    from quill.ui.chosen_route_sender import ChosenRouteSender

    return ChosenRouteSender(_Frame(service, **kwargs))


def test_the_shared_route_is_asked_before_anything_is_sent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[Any] = []
    monkeypatch.setattr(
        aai, "generate_assistant_response", lambda s, k, p, **_kw: (sent.append(s), ("ok", None))[1]
    )
    monkeypatch.setattr(aai, "load_provider_api_key", lambda _p: "fake-claude-key")
    service = _Service("own_key")

    assert _sender(service)("Fix this.") == "ok"
    assert service.asked == [("text",)]
    assert sent[0].provider == "claude"  # the own key's company, nowhere else


def test_a_refusal_sends_nothing_and_is_the_routes_sentence() -> None:
    from quill.core.ai.chosen_route import ChosenRouteError

    service = _Service("", refusal="No AI is in use. Choose one.")
    with pytest.raises(ChosenRouteError, match="No AI is in use"):
        _sender(service)("Fix this.")


def test_without_the_agreement_nothing_is_sent() -> None:
    from quill.core.ai.chosen_route import ChosenRouteError

    service = _Service("free")
    with pytest.raises(ChosenRouteError):
        _sender(service, ready=False)("Fix this.")
    assert service.asked == []


def test_the_free_ai_gets_the_whole_prompt() -> None:
    assert _sender(_Service("free"))("Fix this.", "Be brief.") == "free:Be brief.\n\nFix this."


def test_a_picture_asks_the_first_picture_question(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.ui.hosted_ai_picture_consent as consent
    from quill.core.ai.chosen_route import ChosenRouteError

    asked: list[str] = []
    monkeypatch.setattr(consent, "ask_picture_consent", lambda _f, c: asked.append(c) or False)
    service = _Service("own_key")

    with pytest.raises(ChosenRouteError, match="Nothing was sent"):
        _sender(service).picture(Path("door.png"), "Describe it.")
    assert asked == ["own_key"]
    assert service.asked == [("text", "pictures")]


def test_a_connection_the_registry_says_cannot_do_it_is_sent_nothing() -> None:
    from dataclasses import replace

    from quill.core.ai.chosen_route import ChosenRouteError

    class _Unready(_Service):
        def capability_record(self, connection: str) -> Any:
            return replace(super().capability_record(connection), available=False)

        def client(self) -> Any:
            raise AssertionError("nothing may be sent")

    with pytest.raises(ChosenRouteError):
        _sender(_Unready("free"))("Fix this.")


def test_ask_quill_describes_and_opens_choose_your_ai() -> None:
    service = _Service("own_key")
    sender = _sender(service)
    chosen_route.set_sender(sender)

    assert chosen_route.describe() == "My own key, Anthropic Claude"
    assert chosen_route.choose() is True
    assert sender._frame.opened == 1


# -- the choke point every keyed command uses ------------------------------------ #


def test_ai_require_connection_hands_out_the_route() -> None:
    import quill.ui.main_frame as main_frame

    frame = SimpleNamespace(
        _ai_ready=lambda: True,
        _ai_capable=lambda capability: capability == "text",
    )
    chosen_route.set_sender(lambda p, s="": p)

    result = main_frame.MainFrame._ai_require_connection(frame)

    assert result is not None
    assert result[0].provider == chosen_route.ROUTE_PROVIDER
    assert main_frame.MainFrame._ai_require_connection(frame, "pictures") is None


# -- the one-time move of the older choice ------------------------------------------ #


class _Store:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def load(self, name: str) -> str:
        return self.data.get(name, "")

    def save(self, name: str, value: str) -> None:
        self.data[name] = value

    def delete(self, name: str) -> None:
        self.data.pop(name, None)


def test_the_older_choice_moves_once_and_is_said_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from quill.core.ai import own_key
    from quill.ui.chosen_route_sender import MOVED_SENTENCE, migrate_older_choice

    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    store = _Store()
    monkeypatch.setattr(aai, "_cs_load", store.load)
    monkeypatch.setattr(aai, "_cs_save", store.save)
    monkeypatch.setattr(aai, "_cs_delete", store.delete)
    monkeypatch.setattr(own_key, "own_key_active", lambda _s=None: False)
    aai.set_active_provider(
        aai.AssistantConnectionSettings(provider="claude", host="", model="a-model"),
        "fake-claude-key",
    )
    settings = SimpleNamespace(ai_connection="", ai_own_key_provider="", ai_own_key_model="")
    saved: list[int] = []

    said = migrate_older_choice(settings, lambda: saved.append(1))

    assert said.startswith(MOVED_SENTENCE)
    assert "Anthropic Claude" in said
    assert settings.ai_own_key_provider == "claude"
    assert settings.ai_connection == "own_key"
    assert aai.stored_provider_api_key("claude") == "fake-claude-key"
    assert saved
    assert migrate_older_choice(settings, lambda: None) == ""  # once


# -- a new app's first request asks first ------------------------------------------- #


def _route_service(answer: bool) -> Any:
    from quill.ui.hosted_ai_connection_route import ConnectionRouteMixin
    from quill.ui.hosted_ai_route_guard import RouteGuardMixin

    class _Service(ConnectionRouteMixin, RouteGuardMixin):
        own_key_ready = True
        own_key_provider = "gemini"
        own_key_model = "a-model"
        signed_in = False
        _limits = None

        def __init__(self) -> None:
            self.settings = SimpleNamespace(ai_connection="", ai_own_key_provider="gemini")
            self._app = SimpleNamespace(
                settings=self.settings, save_settings=lambda: None, ai_agent_name="Quill Weather"
            )
            self.chatgpt = SimpleNamespace(signed_in=False)
            self.questions: list[str] = []
            self.confirm_route_change = lambda q: self.questions.append(q) or answer

    return _Service()


def test_a_new_apps_first_request_asks_and_no_sends_nothing() -> None:
    service = _route_service(False)
    said: list[str] = []

    assert service.request_connection(("text",), said.append) == ""
    assert len(service.questions) == 1
    assert "Quill Weather" in service.questions[0] and "Google Gemini" in service.questions[0]
    assert service.settings.ai_connection == ""
    assert said and said[0].startswith("Nothing was sent")


def test_yes_to_the_first_request_stores_the_choice() -> None:
    service = _route_service(True)

    assert service.request_connection(("text",), lambda _s: None) == "own_key"
    assert service.settings.ai_connection == "own_key"
    service.request_connection(("text",), lambda _s: None)
    assert len(service.questions) == 1  # after that, it follows the choice


# -- the gate: nothing in QUILL's windows reaches around the route ----------------- #

#: Places in ``quill/ui`` that still read the older choice, each with why that is
#: not a way around Choose Your AI. A new one fails until it is routed or added
#: here with a reason -- which is the review.
_OLDER_CHOICE_READERS: dict[str, str] = {
    "agent_editor_host.py": "the companion's step budget from a model name; sends nothing",
    "ai_hub_dialog.py": "the AI Hub's own settings page, which edits the older file",
    "ai_setup_wizard.py": "the setup wizard's own page, which edits the older file",
    "assistant_panel.py": "Ask Quill's status line outside QUILL, when no route is active",
    "assistant_tools.py": "the AI Hub's connection pages, which edit the older file",
    "chosen_route_sender.py": "the one-time move of the older choice into Choose Your AI",
    "batch_speech_runner.py": "cloud voices for Export as Audio: a voice, not an AI request",
    "main_frame.py": "Forget API Key's menu state, and Read Aloud's cloud voices",
}
_READS = {"load_assistant_api_key", "load_assistant_connection_settings"}


def _readers() -> set[str]:
    root = Path(__file__).resolve().parents[3] / "quill" / "ui"
    found: set[str] = set()
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                if name in _READS:
                    found.add(path.relative_to(root).as_posix())
    return found


def test_no_window_reads_the_older_choice_to_send() -> None:
    readers = _readers()
    unexplained = sorted(readers - set(_OLDER_CHOICE_READERS))
    assert not unexplained, (
        "These read assistant-connection.json directly. Send through "
        "_ai_require_connection or ProviderChatBackend() so the request follows "
        f"Choose Your AI, or add the file here with the reason: {unexplained}"
    )
    stale = sorted(set(_OLDER_CHOICE_READERS) - readers)
    assert not stale, f"No longer reads the older choice; remove from the list: {stale}"
