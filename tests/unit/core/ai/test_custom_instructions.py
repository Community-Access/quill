"""Unit tests for quill.core.ai.custom_instructions."""

from __future__ import annotations

import pytest

from quill.core.ai.custom_instructions import (
    _DEFAULT_INSTRUCTIONS,
    _DEFAULT_MAP,
    InstructionSet,
    apply_instruction,
    get_default_instruction,
    load_instructions,
    save_instructions,
    split_instruction,
)

# ---------------------------------------------------------------------------
# InstructionSet
# ---------------------------------------------------------------------------


def test_active_prompt_returns_user_prompt_when_set() -> None:
    inst = InstructionSet(
        task_id="test", title="Test", default_prompt="default", user_prompt="custom"
    )
    assert inst.active_prompt == "custom"


def test_active_prompt_falls_back_to_default_when_user_empty() -> None:
    inst = InstructionSet(task_id="test", title="Test", default_prompt="default", user_prompt="")
    assert inst.active_prompt == "default"


def test_active_prompt_falls_back_when_user_only_whitespace() -> None:
    inst = InstructionSet(task_id="test", title="Test", default_prompt="default", user_prompt="   ")
    assert inst.active_prompt == "default"


def test_is_customised_true_when_user_differs_from_default() -> None:
    inst = InstructionSet(
        task_id="test", title="Test", default_prompt="default", user_prompt="custom"
    )
    assert inst.is_customised() is True


def test_is_customised_false_when_user_empty() -> None:
    inst = InstructionSet(task_id="test", title="Test", default_prompt="default", user_prompt="")
    assert inst.is_customised() is False


def test_is_customised_false_when_user_matches_default() -> None:
    inst = InstructionSet(task_id="test", title="Test", default_prompt="same", user_prompt="same")
    assert inst.is_customised() is False


def test_reset_to_default_clears_user_prompt() -> None:
    inst = InstructionSet(
        task_id="test", title="Test", default_prompt="default", user_prompt="custom"
    )
    inst.reset_to_default()
    assert inst.user_prompt == ""
    assert inst.active_prompt == "default"


def test_to_dict_contains_required_keys() -> None:
    inst = InstructionSet(
        task_id="spell_check",
        title="Spell Check",
        default_prompt="d",
        user_prompt="u",
        enabled=False,
    )
    d = inst.to_dict()
    assert d["task_id"] == "spell_check"
    assert d["user_prompt"] == "u"
    assert d["enabled"] is False


def test_from_dict_restores_fields() -> None:
    base = InstructionSet(task_id="spell_check", title="SC", default_prompt="default")
    restored = InstructionSet.from_dict(base, {"user_prompt": "custom", "enabled": False})
    assert restored.user_prompt == "custom"
    assert restored.enabled is False
    assert restored.default_prompt == "default"


# ---------------------------------------------------------------------------
# Default instructions — quality checks
# ---------------------------------------------------------------------------


def test_all_expected_tasks_have_defaults() -> None:
    expected = {
        "chat",
        "spell_check",
        "grammar_check",
        "rewrite",
        "summarize",
        "expand",
        "toc",
        "translate",
        "thesaurus",
        "document_qa",
        "research",
        "accessibility_agent",
    }
    assert expected.issubset(_DEFAULT_MAP.keys())


def test_default_prompts_are_nonempty() -> None:
    for inst in _DEFAULT_INSTRUCTIONS:
        assert inst.default_prompt.strip(), f"Empty default for {inst.task_id}"


def test_default_titles_are_nonempty() -> None:
    for inst in _DEFAULT_INSTRUCTIONS:
        assert inst.title.strip(), f"Empty title for {inst.task_id}"


def test_defaults_are_enabled_by_default() -> None:
    for inst in _DEFAULT_INSTRUCTIONS:
        assert inst.enabled is True


def test_get_default_instruction_returns_correct_title() -> None:
    inst = get_default_instruction("spell_check")
    assert inst is not None
    assert "spell" in inst.title.lower() or "Spell" in inst.title


def test_get_default_instruction_returns_none_for_unknown() -> None:
    assert get_default_instruction("nonexistent_task_xyz") is None


# ---------------------------------------------------------------------------
# load_instructions / save_instructions round-trip
# ---------------------------------------------------------------------------


def test_load_instructions_includes_all_defaults(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.custom_instructions as ci

    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")
    instructions = load_instructions()
    assert "spell_check" in instructions
    assert "grammar_check" in instructions
    assert "document_qa" in instructions


def test_save_and_reload_preserves_user_prompt(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.custom_instructions as ci

    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")

    instructions = load_instructions()
    instructions["spell_check"].user_prompt = "My custom spell check instructions."
    save_instructions(instructions)

    reloaded = load_instructions()
    assert reloaded["spell_check"].user_prompt == "My custom spell check instructions."


def test_save_and_reload_preserves_enabled_false(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.custom_instructions as ci

    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")

    instructions = load_instructions()
    instructions["grammar_check"].enabled = False
    save_instructions(instructions)

    reloaded = load_instructions()
    assert reloaded["grammar_check"].enabled is False


# ---------------------------------------------------------------------------
# apply_instruction
# ---------------------------------------------------------------------------


def test_apply_instruction_prepends_active_prompt(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.ai.custom_instructions as ci

    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")

    result = apply_instruction("spell_check", "Check this text.")
    assert "Check this text." in result
    # Default prompt should also be there
    default = get_default_instruction("spell_check")
    assert default is not None
    assert default.default_prompt[:30] in result


def test_apply_instruction_returns_base_when_disabled(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.ai.custom_instructions as ci

    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")

    instructions = load_instructions()
    instructions["spell_check"].enabled = False
    save_instructions(instructions)

    result = apply_instruction("spell_check", "Base prompt.")
    assert result == "Base prompt."


def test_apply_instruction_returns_base_for_unknown_task(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.ai.custom_instructions as ci

    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")

    result = apply_instruction("this_task_does_not_exist", "Base prompt.")
    assert result == "Base prompt."


def test_apply_instruction_uses_user_prompt_when_set(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.ai.custom_instructions as ci

    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")

    instructions = load_instructions()
    instructions["thesaurus"].user_prompt = "My thesaurus rules."
    save_instructions(instructions)

    result = apply_instruction("thesaurus", "Find synonyms for happy.")
    assert "My thesaurus rules." in result
    assert "Find synonyms for happy." in result


# ---------------------------------------------------------------------------
# split_instruction (prompt-caching path)
# ---------------------------------------------------------------------------


def test_split_instruction_returns_system_and_user(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.ai.custom_instructions as ci

    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")

    system, user = split_instruction("spell_check", "Check this.")
    default = get_default_instruction("spell_check")
    assert default is not None
    assert default.default_prompt[:20] in system
    assert user == "Check this."


def test_split_instruction_system_and_user_are_separate(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.ai.custom_instructions as ci

    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")

    system, user = split_instruction("spell_check", "My text.")
    assert "My text." not in system
    assert system not in user


def test_split_instruction_returns_empty_system_when_disabled(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.ai.custom_instructions as ci

    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")

    instructions = load_instructions()
    instructions["spell_check"].enabled = False
    save_instructions(instructions)

    system, user = split_instruction("spell_check", "Base prompt.")
    assert system == ""
    assert user == "Base prompt."


def test_split_instruction_returns_empty_system_for_unknown_task(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.ai.custom_instructions as ci

    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")

    system, user = split_instruction("no_such_task_xyz", "Base prompt.")
    assert system == ""
    assert user == "Base prompt."


def test_split_instruction_uses_user_override(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import quill.core.ai.custom_instructions as ci

    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")

    instructions = load_instructions()
    instructions["grammar_check"].user_prompt = "Custom grammar rules."
    save_instructions(instructions)

    system, user = split_instruction("grammar_check", "Analyze this text.")
    assert system == "Custom grammar rules."
    assert user == "Analyze this text."


def test_apply_instruction_consistent_with_split_instruction(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import quill.core.ai.custom_instructions as ci

    monkeypatch.setattr(ci, "_instructions_path", lambda: tmp_path / "inst.json")

    base = "Do the thing."
    combined = apply_instruction("spell_check", base)
    system, user = split_instruction("spell_check", base)

    assert user == base
    if system:
        assert combined == f"{system}\n\n{user}"
    else:
        assert combined == base
