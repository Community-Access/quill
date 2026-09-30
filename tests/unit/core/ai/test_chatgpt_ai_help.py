"""AI help on a ChatGPT plan: the same instructions, shaped for the Responses API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quill.core.ai import chatgpt_ai_help as help_mod
from quill.core.ai.chatgpt_ai_help import (
    CHATGPT_LIMITS,
    IMAGE_FEATURE,
    IMAGE_INSTRUCTIONS,
    ask_with_chatgpt,
    converse_with_chatgpt,
    describe_image_with_chatgpt,
    size_note,
)
from quill.core.ai.chatgpt_errors import ChatGptError
from quill.core.ai.own_key import INSTRUCTIONS


class _Account:
    def __init__(self, *, model: str = "gpt-6", web_search: bool = False) -> None:
        self.model = model
        self.web_search = web_search

    def access_token(self) -> str:
        return "tok"


@pytest.fixture
def sent(monkeypatch):
    calls: list[dict[str, Any]] = []

    def fake_respond(token: str, **kwargs: Any):
        calls.append({"token": token, **kwargs})

        class Answer:
            text = "An answer."

        return Answer()

    monkeypatch.setattr(help_mod, "respond", fake_respond)
    return calls


def test_a_request_carries_the_gateways_instructions_and_the_users_text(sent) -> None:
    text = ask_with_chatgpt(_Account(), "summarize", "Long text here")
    assert text == "An answer."
    call = sent[0]
    assert call["token"] == "tok"
    assert call["model"] == "gpt-6"
    assert call["instructions"] == INSTRUCTIONS["summarize"]
    assert call["items"] == [
        {"role": "user", "content": [{"type": "input_text", "text": "Long text here"}]}
    ]
    assert call["tools"] == []


def test_web_search_is_offered_only_when_switched_on(sent) -> None:
    ask_with_chatgpt(_Account(web_search=True), "ask", "What is new?")
    assert sent[0]["tools"] == [{"type": "web_search"}]


def test_a_question_about_the_document_carries_the_excerpts(sent) -> None:
    ask_with_chatgpt(_Account(), "document_qna", "Who?", ["ONE", "TWO"])
    text = sent[0]["items"][0]["content"][0]["text"]
    assert text.startswith("Excerpts:\nONE")
    assert text.endswith("Question: Who?")


def test_translate_names_the_language(sent) -> None:
    ask_with_chatgpt(_Account(), "translate", "Hello", language="French")
    assert "French" in sent[0]["instructions"]


def test_an_unknown_feature_is_a_coded_sentence(sent) -> None:
    with pytest.raises(ChatGptError, match="not available"):
        ask_with_chatgpt(_Account(), "juggle", "x")


def test_a_conversation_goes_as_real_turns(sent) -> None:
    history = [
        {"role": "user", "content": "First"},
        {"role": "assistant", "content": "Reply"},
    ]
    converse_with_chatgpt(_Account(), "Second", ["Excerpt"], history)
    items = sent[0]["items"]
    assert items[0]["content"][0]["text"].startswith("Excerpts from the user's document")
    assert items[1] == {"role": "user", "content": [{"type": "input_text", "text": "First"}]}
    assert items[2] == {
        "role": "assistant",
        "content": [{"type": "output_text", "text": "Reply"}],
    }
    assert items[3]["content"][0]["text"] == "Second"
    assert sent[0]["instructions"] == INSTRUCTIONS["chat"]


def test_an_app_can_bring_its_own_conversation_instructions(sent) -> None:
    converse_with_chatgpt(_Account(), "Hi", None, [], instructions="You are Quill Radio.")
    assert sent[0]["instructions"] == "You are Quill Radio."


def test_an_image_goes_with_its_question_or_a_plain_request(sent, tmp_path) -> None:
    from PIL import Image

    path = tmp_path / "pic.png"
    Image.new("RGB", (2, 2)).save(path, format="PNG")
    describe_image_with_chatgpt(_Account(), path, "What colour is it?")
    content = sent[0]["items"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "What colour is it?"}
    assert content[1]["type"] == "input_image"
    assert sent[0]["instructions"] == IMAGE_INSTRUCTIONS

    describe_image_with_chatgpt(_Account(), path)
    assert sent[1]["items"][0]["content"][0]["text"] == "Describe this image."


def test_a_missing_image_is_a_sentence_and_nothing_is_sent(sent) -> None:
    with pytest.raises(ValueError, match="no file"):
        describe_image_with_chatgpt(_Account(), Path("nowhere.png"))
    assert sent == []


def test_the_plan_has_no_quill_limit_and_images_are_on() -> None:
    assert CHATGPT_LIMITS.max_input_tokens > 50_000
    assert CHATGPT_LIMITS.feature_available(IMAGE_FEATURE)
    for feature in INSTRUCTIONS:
        assert CHATGPT_LIMITS.feature_available(feature)


def test_the_size_note_never_prices_and_warns_only_when_true() -> None:
    small = size_note("a few words", "gpt-6", free_limit_tokens=1500)
    assert "count toward your plan" in small
    assert "$" not in small
    assert "more than QUILL's free AI" not in small
    big = size_note("word " * 5_000, "gpt-6", free_limit_tokens=1500)
    assert "more than QUILL's free AI" in big
    assert "read at once" not in big
    huge = size_note("word " * 200_000, "gpt-6", free_limit_tokens=1500)
    assert "read at once" in huge
