"""Every AI entry point goes through the one route: the AI chosen in Choose Your AI.

Jeff's decision (2026-11-20): QUILL's older, advanced AI commands follow the
one stored choice, ``ai_connection``, like every AI-menu command. They all
reach a provider through ``generate_assistant_response`` (or ``describe_image``
for a picture), so these tests give each one the route's settings and check the
request arrives at the registered sender -- the shared route -- and nowhere
else. ``urlopen`` raises: no network is ever reached. Fakes only.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import quill.core.assistant_ai as aai
from quill.core.ai import chosen_route


class _Sender:
    """The shared route, as a fake: records what was sent, answers *reply*."""

    def __init__(self, reply: str = "[]") -> None:
        self.reply = reply
        self.prompts: list[str] = []
        self.pictures: list[tuple[Path, str]] = []

    def __call__(self, prompt: str, system_prompt: str = "") -> str:
        self.prompts.append(f"{system_prompt}\n{prompt}")
        return self.reply

    def picture(self, path: Path, prompt: str) -> str:
        self.pictures.append((path, prompt))
        return "A red door."


@pytest.fixture
def sender(monkeypatch: pytest.MonkeyPatch) -> _Sender:
    def no_network(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("a request left the shared route")

    monkeypatch.setattr(aai, "urlopen", no_network)
    fake = _Sender()
    chosen_route.set_sender(fake)
    return fake


def _route() -> Any:
    return chosen_route.route_settings()


# -- the seam ------------------------------------------------------------------ #


def test_without_a_sender_nothing_is_sent_and_it_says_so() -> None:
    text, error = aai.generate_assistant_response(_route(), "", "hello")
    assert text is None
    assert error is not None and "Ctrl+4" in error


def test_a_refusal_is_the_routes_own_sentence(sender: _Sender) -> None:
    def refuse(_prompt: str, _system: str = "") -> str:
        raise chosen_route.ChosenRouteError(
            "Your ChatGPT plan sign-in has ended. Nothing was sent."
        )

    chosen_route.set_sender(refuse)
    assert aai.generate_assistant_response(_route(), "", "hi") == (
        None,
        "Your ChatGPT plan sign-in has ended. Nothing was sent.",
    )


def test_streaming_on_the_route_delivers_the_answer_once(sender: _Sender) -> None:
    sender.reply = "whole answer"
    deltas: list[str] = []
    text, error = aai.generate_assistant_response_stream(_route(), "", "hi", deltas.append)
    assert (text, error) == ("whole answer", None)
    assert deltas == ["whole answer"]


# -- every entry point reaches the route --------------------------------------- #


def _spell() -> object:
    from quill.core.ai.spell_check import ai_spell_check

    return ai_spell_check("Teh cat.", _route())


def _grammar() -> object:
    from quill.core.ai.grammar_check import ai_grammar_check

    return ai_grammar_check("Him go home.", _route())


def _translate() -> object:
    from quill.core.ai.translation import translate_text

    return translate_text("Hello.", "French", _route())


def _metadata() -> object:
    from quill.core.ai.metadata_suggest import suggest_document_metadata

    return suggest_document_metadata("A report about birds.", _route())


def _thesaurus() -> object:
    from quill.core.ai.thesaurus import get_synonyms

    return get_synonyms("happy", _route())


def _summarize_discussion() -> object:
    from quill.core.github.thread_summary import summarize_thread

    return summarize_thread(_route(), "", "Title: a bug\n\nIt crashes.")


def _explain_change() -> object:
    from quill.core.github.thread_summary import ask_whole_prompt

    return ask_whole_prompt(_route(), "", "Explain this diff: +a -b")


def _provider_backend() -> object:
    from quill.core.ai.provider_backend import ProviderChatBackend

    return ProviderChatBackend().respond("Rewrite this.")


def _default_backend() -> object:
    from quill.core.ai.assistant import make_default_backend

    return make_default_backend().respond("Summarize this.")


ENTRY_POINTS: list[tuple[str, Callable[[], object]]] = [
    ("spell check", _spell),
    ("grammar", _grammar),
    ("translate", _translate),
    ("metadata", _metadata),
    ("thesaurus", _thesaurus),
    ("GitHub Summarize Discussion", _summarize_discussion),
    ("GitHub Explain Selected Change", _explain_change),
    ("agents, AI Library, Transcript Actions (ProviderChatBackend)", _provider_backend),
    ("Ask Quill, Improve Reading Order, watch folder, Train Writing Style", _default_backend),
]


@pytest.mark.parametrize(("name", "call"), ENTRY_POINTS, ids=[n for n, _ in ENTRY_POINTS])
def test_every_entry_point_sends_on_the_chosen_ai(
    sender: _Sender, name: str, call: Callable[[], object]
) -> None:
    try:
        call()
    except Exception:  # noqa: BLE001 - a fake answer may not parse; the send is the point
        pass
    assert sender.prompts, f"{name} did not go through the shared route"


def test_document_qa_sends_on_the_chosen_ai(sender: _Sender) -> None:
    from quill.core.ai.document_qa import ask_document

    sender.reply = json.dumps({"answer": "Yes.", "confidence": "high", "quotes": []})
    try:
        ask_document("Is it red?", "The door is red.", _route())
    except Exception:  # noqa: BLE001
        pass
    assert sender.prompts


def test_describe_image_goes_to_the_routes_picture_path(sender: _Sender, tmp_path: Path) -> None:
    from quill.core.ai.vision import describe_image

    picture = tmp_path / "door.png"
    picture.write_bytes(b"png")

    assert describe_image(_route(), "", picture, prompt="Describe it.") == ("A red door.", None)
    assert sender.pictures == [(picture, "Describe it.")]


def test_explain_selected_change_is_not_wrapped_in_the_summary_prompt(sender: _Sender) -> None:
    from quill.core.github.thread_summary import ask_whole_prompt

    sender.reply = "It renames a function."
    ask_whole_prompt(_route(), "", "Explain this diff: +a -b")

    assert "Explain this diff: +a -b" in sender.prompts[0]
    assert "discussion" not in sender.prompts[0].lower()


def test_setup_offers_ask_choose_your_ais_own_question(sender: _Sender) -> None:
    """Ask Quill, the AI Library and Transcript Actions ask what every AI command asks."""
    from types import SimpleNamespace

    from quill.ui.ai_setup_wizard import maybe_offer_ai_setup

    asked: list[str] = []
    controller = SimpleNamespace(
        _ai_ready=lambda: True, _ai_capable=lambda c: asked.append(c) or False
    )

    assert maybe_offer_ai_setup(controller) is False
    assert asked == ["text"]


# -- Picture Maker ---------------------------------------------------------------- #


def test_picture_maker_never_falls_back_to_the_older_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from quill.core.ai import picture_maker

    monkeypatch.setattr(
        aai,
        "load_assistant_connection_settings",
        lambda: aai.AssistantConnectionSettings(provider="openai", host="", model="m"),
    )
    monkeypatch.setattr(picture_maker, "_key_for", lambda _p: "fake-key")

    said = picture_maker.picture_connection(own_key_provider="", follows_choice=True)

    assert said == picture_maker.NEEDS_OWN_PICTURE_KEY


# -- a new app's first request ------------------------------------------------------ #


def test_a_new_apps_inherited_choice_is_not_stored_silently() -> None:
    from types import SimpleNamespace

    from quill.core.ai.connection_choice import migrate_choice

    settings = SimpleNamespace(ai_connection="")
    chosen = migrate_choice(
        settings,
        chatgpt_signed_in=lambda: False,
        own_key_ready=lambda: True,
        ask_first=("chatgpt", "own_key"),
    )

    assert chosen == "own_key"
    assert settings.ai_connection == ""  # asked at the first request instead


def test_the_first_request_question_names_the_ai_and_says_no_sends_nothing() -> None:
    from quill.core.ai.connection_words import first_request_question

    said = first_request_question("Quill Weather", "your own Google Gemini key", "Google Gemini")
    assert "Quill Weather" in said and "Google Gemini" in said
    assert "If you choose No, nothing is sent" in said and said.endswith("Send it?")
