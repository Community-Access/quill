"""Tests for voice utterance routing (Hey QUILL Phase 4)."""

from __future__ import annotations

import pytest

from quill.core.speech.voice_routing import (
    CANCEL,
    COMMAND,
    QUESTION,
    classify,
    question_text,
)


@pytest.mark.parametrize(
    "text",
    [
        "what is a heading",
        "how do I save my document",
        "why did that happen",
        "explain markdown to me",
        "summarize the selection",  # question-shaped verb
        "define accessibility",
        "who wrote this",
    ],
)
def test_question_shapes_route_to_ask_quill(text: str) -> None:
    assert classify(text) == QUESTION


@pytest.mark.parametrize(
    "text",
    [
        "ask what a screen reader is",
        "ask quill to draft an intro",
        "question how many words are there",
    ],
)
def test_explicit_ask_prefix_routes_to_question(text: str) -> None:
    assert classify(text) == QUESTION


@pytest.mark.parametrize("text", ["save file", "next heading", "word count", "bold"])
def test_commands_are_not_questions(text: str) -> None:
    assert classify(text) == COMMAND


@pytest.mark.parametrize("text", ["cancel", "never mind", "stop", "dismiss"])
def test_cancel_phrases_route_to_cancel(text: str) -> None:
    assert classify(text) == CANCEL


def test_question_text_strips_the_ask_prefix() -> None:
    assert question_text("ask what a heading is") == "what a heading is"
    assert question_text("ask quill to summarize this") == "to summarize this"


def test_question_text_keeps_a_bare_question() -> None:
    assert question_text("how do I save") == "how do i save"


def test_question_text_empty_for_a_command() -> None:
    assert question_text("save file") == ""


def test_bare_ask_falls_back_to_raw_transcript() -> None:
    # "ask" with nothing after it should not hand an empty prompt to Ask Quill.
    assert question_text("ask") == "ask"


def test_empty_is_treated_as_command_not_question() -> None:
    assert classify("") == COMMAND
    assert classify("   ") == COMMAND
