"""AI text tools keep Markdown when the document is Markdown (2026-10-16).

Behavioural: each tool is run against a fake provider that records the system
prompt it was sent, so these tests prove the clause actually reaches the model,
not only that a helper can build it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import quill.core.ai.custom_instructions as ci
from quill.core.ai.custom_instructions import (
    MARKDOWN_PRESERVATION,
    MARKDOWN_TEXT_TASKS,
    apply_instruction,
    load_instructions,
    save_instructions,
    split_instruction,
)


@pytest.fixture(autouse=True)
def _private_instructions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")


@pytest.mark.parametrize(
    "task", ["rewrite", "grammar_check", "spell_check", "expand", "summarize", "translate"]
)
def test_every_text_tool_gets_the_clause_for_markdown(task: str) -> None:
    system, user = split_instruction(task, "the text", markdown=True)
    assert system.endswith(MARKDOWN_PRESERVATION)
    assert user == "the text"


@pytest.mark.parametrize("task", ["rewrite", "grammar_check", "spell_check", "expand"])
def test_plain_text_gets_no_clause(task: str) -> None:
    system, _user = split_instruction(task, "the text")
    assert MARKDOWN_PRESERVATION not in system


@pytest.mark.parametrize("task", ["document_qa", "thesaurus", "research", "chat"])
def test_answers_about_a_document_are_not_text_tools(task: str) -> None:
    assert task not in MARKDOWN_TEXT_TASKS
    system, _user = split_instruction(task, "q", markdown=True)
    assert MARKDOWN_PRESERVATION not in system


def test_a_customised_instruction_still_keeps_the_markdown() -> None:
    instructions = load_instructions()
    instructions["rewrite"].user_prompt = "Make it punchy."
    save_instructions(instructions)

    system, _user = split_instruction("rewrite", "x", markdown=True)

    assert system == f"Make it punchy.\n\n{MARKDOWN_PRESERVATION}"


def test_a_disabled_instruction_still_keeps_the_markdown() -> None:
    instructions = load_instructions()
    instructions["grammar_check"].enabled = False
    save_instructions(instructions)

    system, _user = split_instruction("grammar_check", "x", markdown=True)

    assert system == MARKDOWN_PRESERVATION


def test_the_legacy_combiner_carries_it_too() -> None:
    assert MARKDOWN_PRESERVATION in apply_instruction("expand", "base", markdown=True)
    assert MARKDOWN_PRESERVATION not in apply_instruction("expand", "base")


class _Provider:
    """Stands in for generate_assistant_response; records the system prompt."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.systems: list[str] = []

    def __call__(self, _conn: Any, _key: str, _prompt: str, **kwargs: Any) -> tuple[str, str]:
        self.systems.append(str(kwargs.get("system_prompt", "")))
        return self.reply, ""


def test_spell_check_sends_the_clause_for_a_markdown_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quill.core.ai.spell_check as module

    provider = _Provider("[]")
    monkeypatch.setattr(module, "generate_assistant_response", provider)

    module.ai_spell_check("# Helo\n\n**wrold**", object(), markdown=True)  # type: ignore[arg-type]
    module.ai_spell_check("Helo wrold", object())  # type: ignore[arg-type]

    assert MARKDOWN_PRESERVATION in provider.systems[0]
    assert MARKDOWN_PRESERVATION not in provider.systems[1]


def test_grammar_check_sends_the_clause_for_a_markdown_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quill.core.ai.grammar_check as module

    provider = _Provider("[]")
    monkeypatch.setattr(module, "generate_assistant_response", provider)

    module.ai_grammar_check("- item one\n- item two", object(), markdown=True)  # type: ignore[arg-type]

    assert MARKDOWN_PRESERVATION in provider.systems[0]


def test_translate_sends_the_clause_for_a_markdown_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import quill.core.ai.translation as module

    provider = _Provider('{"translation": "# Hola", "detected_language": "en"}')
    monkeypatch.setattr(module, "generate_assistant_response", provider)

    module.translate_text("# Hello", "Spanish", object(), markdown=True)  # type: ignore[arg-type]

    assert MARKDOWN_PRESERVATION in provider.systems[0]


def test_rewrite_and_expand_agents_send_the_clause(monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.agent_session as module
    from quill.core.assistant_agents import build_agent_plan

    provider = _Provider("## Kept heading")
    monkeypatch.setattr(module, "generate_assistant_response", provider)

    for agent_id in ("rewrite", "expand"):
        plan = build_agent_plan(agent_id, selection_text="## Heading", document_text="")
        assert plan is not None
        ctx = module.AgentContext(plan=plan, connection=object(), markdown=True)  # type: ignore[arg-type]
        module.run_agent(ctx)
    plan = build_agent_plan("rewrite", selection_text="plain", document_text="")
    assert plan is not None
    module.run_agent(module.AgentContext(plan=plan, connection=object()))  # type: ignore[arg-type]

    assert all(MARKDOWN_PRESERVATION in system for system in provider.systems[:2])
    assert MARKDOWN_PRESERVATION not in provider.systems[2]
