"""Choose Your AI's words (codex.md 10A.3) and Ask's facts (10C.3), wx-free."""

from __future__ import annotations

from quill.core.ai import connection_words as words
from quill.core.ai.ask_context import ask_context, facts_block
from quill.core.ai.connection_caps import record_for
from quill.core.ai.connection_choice import ConnectionFacts, row_states


def _rows(**facts):
    return {row.connection: row for row in row_states(ConnectionFacts(**facts))}


def test_the_action_follows_the_row() -> None:
    rows = _rows(stored="chatgpt", chatgpt_signed_in=True, own_key_ready=True)
    assert words.row_action(rows["chatgpt"], free_connected=False) == words.SIGN_OUT
    assert words.row_action(rows["own_key"], free_connected=False) == words.USE
    assert words.row_action(rows["copilot"], free_connected=False) == words.SIGN_IN


def test_the_free_ai_in_use_but_not_connected_connects_rather_than_signs_out() -> None:
    rows = _rows(stored="free")
    assert words.row_action(rows["free"], free_connected=False) == words.SIGN_IN
    assert words.row_action(rows["free"], free_connected=True) == words.SIGN_OUT


def test_the_three_labels_carry_three_distinct_access_keys() -> None:
    letters = [label[label.index("&") + 1].lower() for label in words.ACTION_LABELS.values()]
    assert sorted(letters) == ["o", "s", "u"]


def test_the_about_line_comes_from_the_registry() -> None:
    assert words.about_line(record_for("free")).startswith("Text only. Agent tasks: no.")
    assert words.about_line(record_for("copilot")).startswith("Not available yet")
    gemini = words.about_line(
        record_for("own_key", own_key_provider="gemini"), own_key_provider="gemini"
    )
    assert gemini.startswith("Text and pictures.")
    assert "Google" in gemini


def test_the_outcome_sentences() -> None:
    assert words.now_using("chatgpt") == "Now using My ChatGPT plan."
    assert words.signed_in_sentence("own_key") == "Signed in to My own key. It is now in use."
    assert words.signed_out_sentence("chatgpt", was_in_use=True) == (
        "Signed out. No AI is in use until you choose one."
    )
    assert (
        words.signed_out_sentence("chatgpt", was_in_use=False) == "Signed out of My ChatGPT plan."
    )
    assert words.sign_in_sentence("chatgpt", "QUILL Lite") == (
        "To use My ChatGPT plan, approve QUILL Lite on OpenAI's page."
    )
    assert words.asking_sentence("chatgpt") == "Asking My ChatGPT plan about this document."


def test_the_recommended_model_is_the_services_first() -> None:
    assert words.model_items(["a", "b"]) == ["a (recommended)", "b"]
    assert words.model_items([]) == []


def test_a_needs_label_goes_after_the_name_and_before_the_ellipsis() -> None:
    assert words.with_needs("Ask About an Image...", "(needs a connection that sees)") == (
        "Ask About an Image (needs a connection that sees)..."
    )
    assert words.with_needs("Web Searches Left", "(needs web search)") == (
        "Web Searches Left (needs web search)"
    )
    assert words.with_needs("Same", "") == "Same"


def test_ask_sends_the_selection_else_the_paragraph_plus_title_and_outline() -> None:
    text = "# Plan\n\nFirst idea.\n\n## Costs\n\nNumbers here.\n"
    chosen = ask_context(text, "First idea.", 8, "Notes")
    assert chosen.scope == "selection"
    assert chosen.outline == ("Plan", "  Costs")
    block = facts_block(chosen)
    assert block[0].startswith("Document title: Notes\nOutline:")
    assert block[1] == "The selected text:\nFirst idea."

    paragraph = ask_context(text, "", text.index("Numbers"), "")
    assert paragraph.scope == "paragraph"
    assert paragraph.passage == "Numbers here."


def test_a_huge_section_is_cut_rather_than_sent_whole() -> None:
    facts = ask_context("word " * 5000, "", 3, "")
    assert len(facts.passage) < 6100
    assert facts.passage.endswith("...")
