"""AI word tools: prompts that carry the sentence and nothing else, and answers read safely."""

from __future__ import annotations

from quill.core.ai import own_key, word_tools
from quill.core.ai.word_tools import (
    EXPLORE,
    FEATURE,
    FIND_WORD,
    MAX_CHOICES,
    TOOLS,
    TOOLS_BY_ID,
    WordChoice,
    find_word_prompt,
    parse_answer,
    word_prompt,
)


def test_the_feature_runs_on_own_key_and_chatgpt_with_its_own_instruction() -> None:
    system, user = own_key.request_for(FEATURE, "Task: x")
    assert system == word_tools.INSTRUCTIONS
    assert user == "Task: x"


def test_the_feature_is_not_a_gateway_template() -> None:
    # Scope (Jeff, 2026-10-01): never the free hosted AI. The gateway's
    # shipped list must not gain it by accident.
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[4] / "quill-ai-gateway" / "app" / "prompts.py"
    spec = importlib.util.spec_from_file_location("_gateway_prompts_words", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.SHIPPED_FEATURES and FEATURE not in module.SHIPPED_FEATURES


def test_every_tool_has_a_unique_id_and_access_key() -> None:
    ids = [tool.id for tool in (*TOOLS, FIND_WORD, EXPLORE)]
    assert len(ids) == len(set(ids)) == len(TOOLS_BY_ID)
    keys = [tool.label[tool.label.index("&") + 1].lower() for tool in TOOLS]
    assert len(keys) == len(set(keys)), keys


def test_a_prompt_carries_the_word_and_its_sentence_only() -> None:
    prompt = word_prompt(TOOLS_BY_ID["synonyms"], "bank", "We sat on the river bank.")
    assert "Word: bank" in prompt
    assert "Sentence: We sat on the river bank." in prompt
    assert f"At most {MAX_CHOICES} choices." in prompt


def test_the_reverse_dictionary_prompt_carries_the_description() -> None:
    prompt = find_word_prompt("fear of long words", "I have a terrible ___.")
    assert "Description: fear of long words" in prompt
    assert "It will go into this sentence: I have a terrible ___." in prompt
    assert "It will go into" not in find_word_prompt("a word for joy")


def test_a_json_answer_is_read_with_its_choices() -> None:
    raw = (
        '```json\n{"answer": "**Bank** here means the side of a river.", '
        '"choices": [{"text": "shore", "note": "general"}, {"text": "Shore"}, '
        '{"text": "riverside", "note": "formal"}, {"text": ""}]}\n```'
    )
    answer = parse_answer(raw)
    assert answer.answer == "Bank here means the side of a river."
    assert answer.choices == (WordChoice("shore", "general"), WordChoice("riverside", "formal"))
    assert answer.choices[0].spoken() == "shore -- general"


def test_prose_around_json_is_tolerated_and_plain_prose_is_kept_without_choices() -> None:
    wrapped = parse_answer('Sure! {"answer": "Yes.", "choices": ["glad"]} Hope that helps.')
    assert wrapped.answer == "Yes." and wrapped.choices == (WordChoice("glad"),)
    prose = parse_answer("It means happy.\n- glad\n- joyful")
    assert prose.choices == ()
    assert "glad" in prose.answer and "-" not in prose.answer.splitlines()[1]


def test_choices_are_capped_and_multi_line_choices_dropped() -> None:
    many = ",".join(f'{{"text": "w{n}"}}' for n in range(30))
    answer = parse_answer(f'{{"answer": "", "choices": [{many}, {{"text": "a\\nb"}}]}}')
    assert len(answer.choices) == MAX_CHOICES
    assert parse_answer("").answer == ""
