"""Unit tests for quill.core.ai.vision_prompts."""

from __future__ import annotations

from quill.core.ai.vision_prompts import (
    BUILTIN_PROMPT_BY_ID,
    BUILTIN_PROMPT_STYLES,
    BUILTIN_STYLE_IDS,
    BUILTIN_TITLE_BY_ID,
    PROMPT_ACCESSIBILITY,
    enabled_style_choices,
    resolve_prompt_text,
)


def test_all_twelve_styles_present() -> None:
    """All 12 IDT prompt styles are in the registry."""
    assert len(BUILTIN_PROMPT_STYLES) == 12


def test_style_ids_are_unique() -> None:
    """No duplicate style IDs in the built-in registry."""
    ids = [s["id"] for s in BUILTIN_PROMPT_STYLES]
    assert len(ids) == len(set(ids))


def test_accessibility_is_in_registry() -> None:
    """The default 'accessibility' style is present."""
    assert "accessibility" in BUILTIN_STYLE_IDS
    assert "accessibility" in BUILTIN_PROMPT_BY_ID
    assert BUILTIN_TITLE_BY_ID["accessibility"] == "Accessibility"


def test_every_style_has_id_title_prompt() -> None:
    """Every built-in style entry has all three required keys."""
    for style in BUILTIN_PROMPT_STYLES:
        assert isinstance(style["id"], str) and style["id"]
        assert isinstance(style["title"], str) and style["title"]
        assert isinstance(style["prompt"], str) and style["prompt"]


def test_builtin_style_ids_frozenset_matches() -> None:
    """BUILTIN_STYLE_IDS matches the IDs in BUILTIN_PROMPT_STYLES."""
    expected = {s["id"] for s in BUILTIN_PROMPT_STYLES}
    assert BUILTIN_STYLE_IDS == frozenset(expected)


def test_resolve_prompt_text_known_builtin() -> None:
    """resolve_prompt_text returns the correct prompt for a known built-in."""
    text = resolve_prompt_text("concise")
    assert "two to three sentences" in text


def test_resolve_prompt_text_unknown_falls_back() -> None:
    """resolve_prompt_text returns the fallback for an unknown style ID."""
    text = resolve_prompt_text("nonexistent")
    assert text == PROMPT_ACCESSIBILITY


def test_resolve_prompt_text_custom_prompt() -> None:
    """resolve_prompt_text finds a custom prompt by ID."""
    custom = [{"id": "my-style", "title": "My Style", "prompt": "Custom prompt text"}]
    text = resolve_prompt_text("my-style", custom_prompts=custom)
    assert text == "Custom prompt text"


def test_resolve_prompt_text_custom_not_found_falls_back() -> None:
    """resolve_prompt_text falls back when custom prompt ID not found."""
    custom = [{"id": "other", "title": "Other", "prompt": "Other text"}]
    text = resolve_prompt_text("missing", custom_prompts=custom)
    assert text == PROMPT_ACCESSIBILITY


def test_enabled_style_choices_all_enabled() -> None:
    """enabled_style_choices returns all 12 when nothing is disabled."""
    choices = enabled_style_choices()
    assert len(choices) == 12
    assert choices[0]["id"] == "narrative"


def test_enabled_style_choices_with_disabled() -> None:
    """enabled_style_choices skips disabled built-in styles."""
    choices = enabled_style_choices(disabled_builtins=["mood", "colorful"])
    ids = [c["id"] for c in choices]
    assert "mood" not in ids
    assert "colorful" not in ids
    assert len(choices) == 10


def test_enabled_style_choices_with_custom() -> None:
    """enabled_style_choices appends custom prompts after built-ins."""
    custom = [{"id": "custom1", "title": "Custom One", "prompt": "p1"}]
    choices = enabled_style_choices(custom_prompts=custom)
    assert len(choices) == 13
    assert choices[-1]["id"] == "custom1"
    assert choices[-1]["title"] == "Custom One"


def test_enabled_style_choices_skips_empty_id_custom() -> None:
    """enabled_style_choices skips custom entries with empty IDs."""
    custom = [{"id": "", "title": "Bad", "prompt": "x"}]
    choices = enabled_style_choices(custom_prompts=custom)
    assert len(choices) == 12  # only built-ins


def test_enabled_style_choices_all_disabled_returns_empty() -> None:
    """enabled_style_choices returns [] when every built-in style is disabled."""
    all_ids = [s["id"] for s in BUILTIN_PROMPT_STYLES]
    choices = enabled_style_choices(disabled_builtins=all_ids)
    assert choices == []


def test_builtin_prompt_by_id_coverage() -> None:
    """BUILTIN_PROMPT_BY_ID has an entry for every style."""
    for style in BUILTIN_PROMPT_STYLES:
        assert style["id"] in BUILTIN_PROMPT_BY_ID
        assert BUILTIN_PROMPT_BY_ID[style["id"]] == style["prompt"]


def test_builtin_title_by_id_coverage() -> None:
    """BUILTIN_TITLE_BY_ID has an entry for every style."""
    for style in BUILTIN_PROMPT_STYLES:
        assert style["id"] in BUILTIN_TITLE_BY_ID
        assert BUILTIN_TITLE_BY_ID[style["id"]] == style["title"]
