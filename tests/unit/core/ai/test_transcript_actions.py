"""Tests for the wx-free Transcript Actions core (the Listening Companion)."""

from __future__ import annotations

from quill.core.ai.transcript_actions import (
    BUILTIN_TRANSCRIPT_ACTIONS,
    action_to_skill_source,
    all_actions,
    find_action,
    recommend_actions,
    transcript_has_speakers,
)


def test_builtins_have_unique_ids_and_nonempty_instructions() -> None:
    ids = [a.id for a in BUILTIN_TRANSCRIPT_ACTIONS]
    assert len(ids) == len(set(ids))
    assert all(
        a.name and a.description and a.instruction.strip() for a in BUILTIN_TRANSCRIPT_ACTIONS
    )
    # The seven core experiences are present.
    assert {"meeting-minutes", "action-items", "study-notes", "clean-draft"} <= set(ids)


def test_new_bundled_actions_are_present_and_lead_in_context() -> None:
    ids = {a.id for a in BUILTIN_TRANSCRIPT_ACTIONS}
    assert {"follow-up-email", "key-quotes", "decisions-log"} <= ids
    # A multi-speaker meeting now surfaces decisions and a follow-up email up front.
    meeting = recommend_actions("Speaker 0: we decided X.\nSpeaker 1: I'll send the recap.")
    lead_ids = [a.id for a in meeting[:4]]
    assert "decisions-log" in lead_ids and "follow-up-email" in lead_ids


def test_find_action_is_case_insensitive_and_misses_cleanly() -> None:
    assert find_action("Meeting-Minutes").id == "meeting-minutes"  # type: ignore[union-attr]
    assert find_action("nope") is None


def test_build_prompt_includes_instruction_transcript_and_extra() -> None:
    action = find_action("meeting-minutes")
    assert action is not None
    prompt = action.build_prompt("Alex: hello.", extra_instruction="Keep it under one page.")
    assert "meeting minutes" in prompt.lower()
    assert "Alex: hello." in prompt
    assert "Keep it under one page." in prompt
    assert "Additional instructions from the user" in prompt


def test_build_prompt_without_extra_omits_the_extra_block() -> None:
    action = find_action("clean-draft")
    assert action is not None
    prompt = action.build_prompt("um, so, yeah")
    assert "Additional instructions from the user" not in prompt
    assert "um, so, yeah" in prompt


def test_transcript_has_speakers_detects_diarized_labels() -> None:
    diarized = "Speaker 0: Welcome.\nSpeaker 1: Thanks for having me."
    assert transcript_has_speakers(diarized) is True
    assert transcript_has_speakers("just one long block of text with no labels") is False


def test_recommend_leads_with_minutes_for_multispeaker() -> None:
    diarized = "Speaker 0: Let's decide the budget.\nSpeaker 1: Agreed, I'll own it."
    ranked = recommend_actions(diarized)
    assert ranked[0].id == "meeting-minutes"
    # Every action is still offered, just reordered.
    assert len(ranked) == len(BUILTIN_TRANSCRIPT_ACTIONS)


def test_recommend_leads_with_clean_draft_for_single_voice() -> None:
    monologue = "So today I want to talk about my trip and what I learned along the way."
    ranked = recommend_actions(monologue, has_speakers=False)
    assert ranked[0].id == "clean-draft"


def test_recommend_leads_with_qa_for_question_dense_single_voice() -> None:
    qa = "What is it? It is a tool. How does it work? It listens. Why use it? Because it helps."
    ranked = recommend_actions(qa, has_speakers=False)
    assert ranked[0].id == "qa-extraction"


def test_recommend_limit_truncates() -> None:
    assert len(recommend_actions("hello", limit=3)) == 3
    assert all_actions() == BUILTIN_TRANSCRIPT_ACTIONS


def test_action_to_skill_source_parses_as_a_valid_skill() -> None:
    from quill.core.skill_pack import parse_skill, validate_skill

    src = action_to_skill_source(
        "My Standup Notes", "Summarize today's standup in three bullets.", description="x"
    )
    pack = parse_skill(src)  # raises on invalid source
    assert validate_skill(pack) == []
    assert pack.name == "My Standup Notes"
    # The instruction and the {document} placeholder both land in the step body.
    assert "three bullets" in src
    assert "{document}" in src


def test_action_to_skill_source_weaves_in_a_reference() -> None:
    from quill.core.skill_pack import parse_skill, validate_skill

    src = action_to_skill_source(
        "Minutes Like Last Month",
        "Write meeting minutes.",
        reference_text="## Acme Weekly\n- Attendees:\n- Decisions:",
    )
    assert validate_skill(parse_skill(src)) == []
    assert "REFERENCE:" in src
    assert "Acme Weekly" in src
    # No reference -> no reference block.
    plain = action_to_skill_source("X", "do it")
    assert "REFERENCE:" not in plain
