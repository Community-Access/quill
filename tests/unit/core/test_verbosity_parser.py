"""Tests for the strict verbosity template parser and validator (§12-§13).

Aims for high coverage of quill/core/verbosity/parser.py per the sub-PR 1.1
acceptance (90%+).
"""

from __future__ import annotations

from quill.core.verbosity.parser import (
    LiteralSegment,
    TokenSegment,
    parse,
    render_template,
    validate,
)
from quill.core.verbosity.tokens import TokenSpec, TokenType
from quill.core.verbosity.verbs import Severity, VerbSpec


def _verb(*tokens: TokenSpec) -> VerbSpec:
    return VerbSpec(
        id="test.verb",
        namespace="test",
        human_name="Test",
        firing_context="test",
        supported_tokens=tokens,
        default_template="",
        severity=Severity.ROUTINE,
    )


# --- parse ---------------------------------------------------------------


def test_parse_plain_literal() -> None:
    result = parse("hello world")
    assert result.ok
    assert result.segments == (LiteralSegment("hello world"),)
    assert result.tokens == ()


def test_parse_bare_token() -> None:
    result = parse("Line {line}")
    assert result.ok
    assert result.segments[0] == LiteralSegment("Line ")
    token = result.segments[1]
    assert isinstance(token, TokenSegment)
    assert token.name == "line"
    assert token.filter is None
    assert token.arg is None


def test_parse_filtered_token() -> None:
    result = parse("${upper:word}")
    assert result.ok
    token = result.tokens[0]
    assert token.filter == "upper"
    assert token.arg is None
    assert token.name == "word"


def test_parse_filter_with_arg() -> None:
    result = parse("${pad:3:line}")
    assert result.ok
    token = result.tokens[0]
    assert token.filter == "pad"
    assert token.arg == "3"
    assert token.name == "line"


def test_parse_trailing_literal_after_token() -> None:
    result = parse("{word} found")
    assert result.ok
    assert result.segments[-1] == LiteralSegment(" found")


def test_parse_malformed_too_many_parts() -> None:
    result = parse("${pad:3:line:extra}")
    assert not result.ok
    assert "Malformed placeholder" in result.errors[0].message


def test_parse_empty_filter() -> None:
    result = parse("${:word}")
    assert not result.ok
    assert "Empty filter" in result.errors[0].message


def test_parse_bare_token_with_colon_is_error() -> None:
    result = parse("{pad:line}")
    assert not result.ok
    assert "may not contain" in result.errors[0].message


def test_parse_invalid_token_name() -> None:
    result = parse("{1bad}")
    assert not result.ok
    assert "Invalid token name" in result.errors[0].message


def test_parse_stray_brace_flagged() -> None:
    result = parse("missing close {")
    assert not result.ok
    assert "stray brace" in result.errors[0].message.lower()


def test_parse_position_recorded() -> None:
    result = parse("ab{word}")
    assert result.tokens[0].position == 2


# --- validate ------------------------------------------------------------


def test_validate_ok_template() -> None:
    verb = _verb(TokenSpec("line", TokenType.INT, filters=("ordinal",)))
    report = validate("Line {line}", verb)
    assert report.ok
    assert report.token_count == 1
    assert report.spoken_summary == "Validation: 1 token, 0 warnings, 0 errors."


def test_validate_unknown_token_is_error() -> None:
    verb = _verb(TokenSpec("line", TokenType.INT))
    report = validate("{bogus}", verb)
    assert not report.ok
    assert "Unknown token" in report.errors[0].message


def test_validate_unknown_filter_is_error() -> None:
    verb = _verb(TokenSpec("word", TokenType.STR, filters=("upper",)))
    report = validate("${nope:word}", verb)
    assert not report.ok
    assert "Unknown filter" in report.errors[0].message


def test_validate_filter_not_in_token_allowlist() -> None:
    verb = _verb(TokenSpec("word", TokenType.STR, filters=("upper",)))
    report = validate("${lower:word}", verb)
    assert not report.ok
    assert "not allowed" in report.errors[0].message


def test_validate_filter_wrong_type() -> None:
    # ordinal is numeric-only; declare it allowed on a str token to reach the
    # type check rather than the per-token allowlist check.
    verb = _verb(TokenSpec("word", TokenType.STR, filters=("ordinal",)))
    report = validate("${ordinal:word}", verb)
    assert not report.ok
    assert any("cannot be used on a str" in issue.message for issue in report.errors)


def test_validate_missing_required_arg() -> None:
    verb = _verb(TokenSpec("line", TokenType.INT, filters=("pad",)))
    report = validate("${pad:line}", verb)
    assert not report.ok
    assert any("requires an argument" in issue.message for issue in report.errors)


def test_validate_non_numeric_arg() -> None:
    verb = _verb(TokenSpec("line", TokenType.INT, filters=("pad",)))
    report = validate("${pad:x:line}", verb)
    assert not report.ok
    assert any("must be a number" in issue.message for issue in report.errors)


def test_validate_extra_arg_is_warning() -> None:
    verb = _verb(TokenSpec("word", TokenType.STR, filters=("upper",)))
    report = validate("${upper:3:word}", verb)
    assert report.ok  # warning, not error
    assert len(report.warnings) == 1
    assert "ignores its argument" in report.warnings[0].message


def test_validate_parse_error_propagates() -> None:
    verb = _verb(TokenSpec("word", TokenType.STR))
    report = validate("{1bad}", verb)
    assert not report.ok


def test_spoken_summary_pluralization() -> None:
    verb = _verb(
        TokenSpec("line", TokenType.INT, filters=("ordinal",)),
        TokenSpec("word", TokenType.STR, filters=("upper",)),
    )
    report = validate("{line} {word} {bogus}", verb)
    assert report.token_count == 3
    assert "3 tokens" in report.spoken_summary
    assert "1 error" in report.spoken_summary


# --- render_template -----------------------------------------------------


def test_render_plain_and_filtered() -> None:
    tokens = (
        TokenSpec("line", TokenType.INT, filters=("ordinal",)),
        TokenSpec("word", TokenType.STR, filters=("upper",)),
    )
    out = render_template("Line ${ordinal:line}: ${upper:word}", {"line": 3, "word": "go"}, tokens)
    assert out == "Line 3rd: GO"


def test_render_missing_value_keeps_placeholder() -> None:
    tokens = (TokenSpec("word", TokenType.STR),)
    out = render_template("{word}", {}, tokens)
    assert out == "{word}"


def test_render_unknown_token_keeps_placeholder() -> None:
    out = render_template("{bogus}", {"bogus": "x"}, ())
    assert out == "{bogus}"


def test_render_filter_error_falls_back_to_value() -> None:
    tokens = (TokenSpec("word", TokenType.STR, filters=("date_long",)),)
    # date_long on a str raises TypeError internally; render falls back.
    out = render_template("${date_long:word}", {"word": "notadate"}, tokens)
    assert out == "notadate"


def test_render_bare_token_no_filter() -> None:
    tokens = (TokenSpec("name", TokenType.STR),)
    out = render_template("Saved {name}", {"name": "notes.md"}, tokens)
    assert out == "Saved notes.md"
