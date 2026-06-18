"""Unit tests for quill.core.hygiene rules and engine."""

from __future__ import annotations

from quill.core.hygiene.engine import HygieneEngine
from quill.core.hygiene.findings import HygieneSettings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check(text: str, *, min_confidence: str = "low", **kwargs) -> list:
    engine = HygieneEngine()
    settings = HygieneSettings(min_confidence=min_confidence)  # type: ignore[arg-type]
    return engine.check(text, settings=settings, **kwargs)


def _rule_ids(text: str, **kwargs) -> set[str]:
    return {f.rule_id for f in _check(text, **kwargs)}


# ---------------------------------------------------------------------------
# Multiple spaces
# ---------------------------------------------------------------------------


class TestMultipleSpacesRule:
    def test_detects_double_space(self):
        f = _check("Hello  world.")
        assert any(f.rule_id == "prose.multiple_spaces" for f in f)

    def test_no_false_positive_single_space(self):
        assert "prose.multiple_spaces" not in _rule_ids("Hello world.")

    def test_correct_offset(self):
        findings = _check("Hello  world.")
        ms = [f for f in findings if f.rule_id == "prose.multiple_spaces"]
        assert ms
        assert ms[0].start_offset == 5

    def test_suggested_fix_is_single_space(self):
        findings = _check("Hello  world.")
        ms = [f for f in findings if f.rule_id == "prose.multiple_spaces"]
        assert ms[0].suggested_text == " "

    def test_allow_double_space_after_period(self):
        settings = HygieneSettings(min_confidence="low", allow_double_space_after_period=True)
        text = "Hello.  World."
        engine = HygieneEngine()
        findings = engine.check(text, settings=settings)
        ms = [f for f in findings if f.rule_id == "prose.multiple_spaces"]
        assert not ms

    def test_url_interior_not_flagged(self):
        # Spaces inside a URL do not exist — the URL regex stops at whitespace.
        # Verify that text *before* the URL with two spaces is correctly flagged.
        assert "prose.multiple_spaces" in _rule_ids("See  https://example.com for details")

    def test_three_spaces(self):
        findings = _check("a   b")
        ms = [f for f in findings if f.rule_id == "prose.multiple_spaces"]
        assert ms
        assert ms[0].original_text == "   "


# ---------------------------------------------------------------------------
# Trailing spaces
# ---------------------------------------------------------------------------


class TestTrailingSpacesRule:
    def test_detects_trailing_space(self):
        assert "prose.trailing_spaces" in _rule_ids("Hello   \nworld")

    def test_no_false_positive(self):
        assert "prose.trailing_spaces" not in _rule_ids("Hello world\n")

    def test_trailing_tab(self):
        assert "prose.trailing_spaces" in _rule_ids("Hello\t\nworld")

    def test_suggested_fix_is_empty(self):
        findings = _check("Hello   \n")
        ts = [f for f in findings if f.rule_id == "prose.trailing_spaces"]
        assert ts[0].suggested_text == ""


# ---------------------------------------------------------------------------
# Space before punctuation
# ---------------------------------------------------------------------------


class TestSpaceBeforePunctuationRule:
    def test_detects_space_before_comma(self):
        assert "prose.space_before_punctuation" in _rule_ids("Hello , world")

    def test_detects_space_before_period(self):
        assert "prose.space_before_punctuation" in _rule_ids("Hello .")

    def test_no_false_positive(self):
        assert "prose.space_before_punctuation" not in _rule_ids("Hello, world.")

    def test_fix_removes_space(self):
        findings = _check("Hello , world")
        sp = [f for f in findings if f.rule_id == "prose.space_before_punctuation"]
        assert sp
        assert sp[0].suggested_text == ","


# ---------------------------------------------------------------------------
# Missing space after sentence punctuation
# ---------------------------------------------------------------------------


class TestMissingSpaceAfterSentencePunctuationRule:
    def test_detects_missing_space(self):
        assert "prose.missing_space_after_sentence_punct" in _rule_ids("Hello.World")

    def test_no_false_positive_decimal(self):
        # "3.14" should not trigger (digits around dot)
        assert "prose.missing_space_after_sentence_punct" not in _rule_ids("Pi is 3.14.")

    def test_no_false_positive_with_space(self):
        assert "prose.missing_space_after_sentence_punct" not in _rule_ids("Hello. World")

    def test_exclamation_mark(self):
        assert "prose.missing_space_after_sentence_punct" in _rule_ids("Stop!Go.")


# ---------------------------------------------------------------------------
# Missing space after comma
# ---------------------------------------------------------------------------


class TestMissingSpaceAfterCommaRule:
    def test_detects_missing_space_comma(self):
        assert "prose.missing_space_after_comma" in _rule_ids("apples,oranges")

    def test_no_false_positive_time(self):
        # "10:30" - colon before digit, not letter
        assert "prose.missing_space_after_comma" not in _rule_ids("Meet at 10:30 today")

    def test_no_false_positive_with_space(self):
        assert "prose.missing_space_after_comma" not in _rule_ids("apples, oranges")


# ---------------------------------------------------------------------------
# Excessive blank lines
# ---------------------------------------------------------------------------


class TestExcessiveBlankLinesRule:
    def test_detects_three_blank_lines(self):
        text = "Para one.\n\n\n\nPara two."
        assert "prose.excessive_blank_lines" in _rule_ids(text)

    def test_two_blank_lines_ok(self):
        text = "Para one.\n\n\nPara two."
        assert "prose.excessive_blank_lines" not in _rule_ids(text)

    def test_custom_threshold(self):
        settings = HygieneSettings(min_confidence="low", max_blank_lines=1)
        engine = HygieneEngine()
        text = "One.\n\n\nTwo."
        findings = engine.check(text, settings=settings)
        assert any(f.rule_id == "prose.excessive_blank_lines" for f in findings)

    def test_suggested_fix(self):
        text = "One.\n\n\n\nTwo."
        findings = _check(text)
        eb = [f for f in findings if f.rule_id == "prose.excessive_blank_lines"]
        assert eb
        # suggested text should have fewer newlines
        assert eb[0].suggested_text is not None
        assert eb[0].suggested_text.count("\n") < eb[0].original_text.count("\n")


# ---------------------------------------------------------------------------
# Lowercase sentence start
# ---------------------------------------------------------------------------


class TestLowercaseSentenceStartRule:
    def test_after_period_space(self):
        assert "prose.lowercase_sentence_start" in _rule_ids(
            "Hello world. this should be uppercase."
        )

    def test_no_false_positive_correct(self):
        assert "prose.lowercase_sentence_start" not in _rule_ids("Hello world. This is correct.")

    def test_paragraph_start(self):
        text = "First paragraph.\n\nthis starts lowercase."
        assert "prose.lowercase_sentence_start" in _rule_ids(text)

    def test_suggested_fix_is_uppercase(self):
        findings = _check("Hello. this is wrong.")
        lc = [f for f in findings if f.rule_id == "prose.lowercase_sentence_start"]
        assert lc
        assert lc[0].suggested_text == lc[0].original_text.upper()


# ---------------------------------------------------------------------------
# Engine: code file suppression
# ---------------------------------------------------------------------------


class TestEngineCodeFileSuppression:
    def test_prose_rules_disabled_for_py(self):
        text = "x  =  1\n"
        ids = _rule_ids(text, file_ext="py")
        # Multiple spaces rule should NOT fire for code files
        assert "prose.multiple_spaces" not in ids

    def test_safe_only_allows_trailing_spaces(self):
        engine = HygieneEngine()
        text = "x = 1   \n"
        findings = engine.check(text, file_ext="py", safe_only=True)
        assert any(f.rule_id == "prose.trailing_spaces" for f in findings)

    def test_safe_only_suppresses_prose_rules(self):
        engine = HygieneEngine()
        text = "Hello  world."
        findings = engine.check(text, file_ext="py", safe_only=True)
        assert not any(f.rule_id == "prose.multiple_spaces" for f in findings)

    def test_markdown_prose_rules_enabled(self):
        text = "Hello  world.\n"
        assert "prose.multiple_spaces" in _rule_ids(text, file_ext="md")


# ---------------------------------------------------------------------------
# Engine: apply_fix
# ---------------------------------------------------------------------------


class TestApplyFix:
    def test_apply_double_space_fix(self):
        text = "Hello  world."
        engine = HygieneEngine()
        findings = engine.check(text, settings=HygieneSettings(min_confidence="low"))
        ms = [f for f in findings if f.rule_id == "prose.multiple_spaces"]
        assert ms
        result = engine.apply_fix(text, ms[0])
        assert result == "Hello world."

    def test_apply_fix_returns_none_when_text_changed(self):
        text = "Hello  world."
        engine = HygieneEngine()
        findings = engine.check(text, settings=HygieneSettings(min_confidence="low"))
        ms = [f for f in findings if f.rule_id == "prose.multiple_spaces"]
        assert ms
        changed_text = "Hello world."  # already fixed
        result = engine.apply_fix(changed_text, ms[0])
        assert result is None


# ---------------------------------------------------------------------------
# Engine: scope
# ---------------------------------------------------------------------------


class TestEngineScope:
    def test_scope_limits_findings(self):
        text = "Hello  world.\n\nHello  again."
        engine = HygieneEngine()
        settings = HygieneSettings(min_confidence="low")
        # Only scan the first sentence
        findings = engine.check(text, settings=settings, scope_start=0, scope_end=13)
        for f in findings:
            assert f.start_offset < 13

    def test_offsets_are_absolute(self):
        text = "Start.\n\nHello  world."
        engine = HygieneEngine()
        settings = HygieneSettings(min_confidence="low")
        findings = engine.check(text, settings=settings, scope_start=8)
        ms = [f for f in findings if f.rule_id == "prose.multiple_spaces"]
        assert ms
        # Offset should be relative to full text, not scoped text
        assert ms[0].start_offset >= 8


# ---------------------------------------------------------------------------
# Ignored ranges: URLs
# ---------------------------------------------------------------------------


class TestIgnoredRanges:
    def test_url_not_flagged_for_space_before_punct(self):
        text = "Visit https://example.com/path?a=1&b=2 for info."
        assert "prose.space_before_punctuation" not in _rule_ids(text)

    def test_decimal_not_flagged_as_missing_space_after_punct(self):
        text = "The ratio is 3.14 approximately."
        assert "prose.missing_space_after_sentence_punct" not in _rule_ids(text)

    def test_markdown_code_block_ignored(self):
        text = "```python\nx  =  1\n```\nSome prose."
        # Multiple spaces inside code block must NOT be flagged
        findings = _check(text, file_ext="md")
        ms = [f for f in findings if f.rule_id == "prose.multiple_spaces"]
        for f in ms:
            assert f.start_offset >= text.index("```python\n") + len("```python\n") + len(
                "x  =  1\n```\n"
            )
