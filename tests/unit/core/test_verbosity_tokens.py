"""Tests for the verbosity token model (§12)."""

from __future__ import annotations

from quill.core.verbosity.tokens import (
    FILTERS,
    NUMERIC_TYPES,
    TokenSpec,
    TokenType,
    filter_allowed_for_type,
    get_filter,
)


def test_token_spec_is_frozen() -> None:
    spec = TokenSpec("line", TokenType.INT)
    try:
        spec.name = "other"  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("TokenSpec should be frozen")


def test_exactly_twelve_engine_filters() -> None:
    assert len(FILTERS) == 12
    expected = {
        "upper",
        "lower",
        "title",
        "ordinal",
        "pad",
        "pluralize",
        "singular",
        "duration_human",
        "date_long",
        "date_short",
        "time",
        "truncate",
    }
    assert set(FILTERS) == expected


def test_get_filter_unknown_returns_none() -> None:
    assert get_filter("nope") is None
    assert get_filter("upper") is not None


def test_numeric_filters_restricted_to_numeric_types() -> None:
    ordinal = FILTERS["ordinal"]
    assert filter_allowed_for_type(ordinal, TokenType.INT)
    assert not filter_allowed_for_type(ordinal, TokenType.STR)


def test_untyped_filters_allow_any_type() -> None:
    upper = FILTERS["upper"]
    assert filter_allowed_for_type(upper, TokenType.STR)
    assert filter_allowed_for_type(upper, TokenType.DATETIME)


def test_date_filters_require_datetime() -> None:
    for name in ("date_long", "date_short", "time"):
        spec = FILTERS[name]
        assert filter_allowed_for_type(spec, TokenType.DATETIME)
        assert not filter_allowed_for_type(spec, TokenType.STR)


def test_numeric_types_constant() -> None:
    assert NUMERIC_TYPES == frozenset({TokenType.INT, TokenType.FLOAT})


def test_arg_taking_filters_flagged() -> None:
    assert FILTERS["pad"].requires_arg
    assert FILTERS["truncate"].requires_arg
    assert not FILTERS["upper"].requires_arg
