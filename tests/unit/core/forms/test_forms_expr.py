"""The expression language: reading, canonical text, working out, and sentences."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

import pytest

from quill.core.forms import expr as E
from quill.core.forms.errors import ExpressionError, ExpressionEvalError
from quill.core.forms.expr_eval import evaluate, holds
from quill.core.forms.expr_sentence import Vocabulary, calculation_sentence, rule_sentence, sentence

TODAY = dt.date(2026, 11, 4)


@pytest.mark.parametrize(
    ("text", "canonical"),
    [
        ('#type is "business"', '#type is "business"'),
        ("#a = 1", "#a is 1"),
        ("#a == 1", "#a is 1"),
        ("#a != 'x'", '#a is not "x"'),
        ('#a is not "x"', '#a is not "x"'),
        ("#age greater 17", "#age > 17"),
        ("#age less than 3", "#age < 3"),
        ("#c filled", "#c is filled"),
        ("#c empty", "#c is empty"),
        ('#c starts "a"', '#c starts with "a"'),
        ('#c ends with "z"', '#c ends with "z"'),
        ('#c does not contain "q"', '#c does not contain "q"'),
        ('#c is one of ("a", "b")', '#c is one of ("a", "b")'),
        ("#d is before today + 7", "#d is before today + 7"),
        ("#d after today", "#d is after today"),
        ("#d within 7 days", "#d is within 7 days"),
        ("#d is not within 1 day of #e", "#d is not within 1 days of #e"),
        ("#a or #b and #c", "#a or #b and #c"),
        ("(#a or #b) and #c", "(#a or #b) and #c"),
        ("not (#a or #b)", "not (#a or #b)"),
        ("#a - (#b - #c)", "#a - (#b - #c)"),
        ("(#a + #b) * 2", "(#a + #b) * 2"),
        ("-#a + 2.50", "-#a + 2.50"),
        ("round(#a / 3, 2)", "round(#a / 3, 2)"),
        ("user.email", "user.email"),
        ("TRUE", "true"),
    ],
)
def test_canonical_text(text: str, canonical: str) -> None:
    assert E.normalise(text) == canonical
    assert E.normalise(canonical) == canonical


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "#a is",
        "#a is one of",
        "type is 1",
        "#a +",
        "(#a",
        "#a is 1 1",
        "#a @b",
        "nosuch(1)",
        "#a is within 3",
    ],
)
def test_bad_rules_are_refused_in_a_sentence(bad: str) -> None:
    with pytest.raises(ExpressionError) as caught:
        E.parse(bad)
    assert caught.value.code == "QUILL-FORMS-EXPR-SYNTAX"


def test_embedded_reading_stops_at_bfl_punctuation() -> None:
    text = 'if #a is "x" { more'
    node, end = E.parse_embedded(text, 3)
    assert E.to_text(node) == '#a is "x"'
    assert text[end:].lstrip().startswith("{")
    node, end = E.parse_embedded("#a is 1 @required", 0)
    assert end == 7
    node, end = E.parse_embedded("#a is 1 begin", 0)
    assert end == 7


def test_field_refs() -> None:
    assert E.field_refs(E.parse("#a + #b * #a > #c or #d is one of (#e)")) == [
        "a",
        "b",
        "c",
        "d",
        "e",
    ]


# -- working out ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rule", "answers", "expected"),
    [
        ('#t is "business"', {"t": "business"}, True),
        ('#t is "Business"', {"t": "business"}, False),  # the site compares values exactly
        ("#n is 5", {"n": "5.0"}, True),
        ('#c is "art"', {"c": ["tech", "art"]}, True),  # a check box group
        ('#c contains "art"', {"c": ["tech", "art"]}, True),
        ('#c does not contain "x"', {"c": "abc"}, True),
        ('#t is one of ("a", "b")', {"t": "b"}, True),
        ('#c is not one of ("a", "b")', {"c": ["c"]}, True),
        ("#t is empty", {}, True),
        ("#t is empty", {"t": []}, True),
        ("#t is filled", {"t": "x"}, True),
        ("#age > 17", {"age": "18"}, True),
        ("#age > 17", {"age": "old"}, False),
        ("#age >= 18 and #age <= 65", {"age": 30}, True),
        ('#d is before "2026-12-01"', {"d": "2026-11-30"}, True),
        ("#d is after today", {"d": "2026-11-05"}, True),
        ("#d is within 7 days", {"d": "2026-11-10"}, True),
        ("#d is within 7 days", {"d": "2026-11-12"}, False),
        ('#d is within 2 days of "2026-01-01"', {"d": "2025-12-30"}, True),
        ("#d < today + 30", {"d": dt.date(2026, 11, 20)}, True),
        ('#s starts with "ab"', {"s": "abc"}, True),
        ('not #s ends with "z"', {"s": "abc"}, True),
        ("#a or #b", {"b": "1"}, True),
        ('user.country is "US"', {}, False),
    ],
)
def test_holds(rule: str, answers: dict[str, object], expected: bool) -> None:
    assert holds(rule, answers, today=TODAY) is expected


def test_arithmetic_and_dates() -> None:
    assert evaluate("#q * #p", {"q": "3", "p": "2.50"}) == Decimal("7.50")
    assert evaluate("#q * #p + #missing", {"q": 2, "p": 2}) == Decimal(4)
    assert evaluate("today + 7", {}, today=TODAY) == dt.date(2026, 11, 11)
    assert evaluate("today - #d", {"d": "2026-11-01"}, today=TODAY) == Decimal(3)
    assert evaluate('#first + " " + #last', {"first": "Ada", "last": "Lovelace"}) == "Ada Lovelace"
    assert evaluate("10 % 4", {}) == Decimal(2)
    assert evaluate("-#a", {"a": "2"}) == Decimal(-2)


def test_functions() -> None:
    a = {"x": "1", "y": "2", "z": ["3", "4"]}
    assert evaluate("sum(#x, #y, #z)", a) == Decimal(10)
    assert evaluate("min(#x, #y)", a) == Decimal(1)
    assert evaluate("max(#z)", a) == Decimal(4)
    assert evaluate("round(10 / 3, 2)", a) == Decimal("3.33")
    assert evaluate("abs(0 - 5)", a) == Decimal(5)
    assert evaluate("count(#x, #missing, #z)", a) == Decimal(3)
    assert evaluate('days_between("2026-01-01", "2026-01-31")', a) == Decimal(30)
    assert evaluate('age("2000-11-05")', a, today=TODAY) == Decimal(25)
    assert evaluate('if(#x > 0, "yes", "no")', a) == "yes"


def test_context_values() -> None:
    assert evaluate("user.email", {}, context={"user": {"email": "a@b.org"}}) == "a@b.org"
    assert holds('geo.country is "GB"', {}, context={"geo": {"country": "GB"}})


def test_evaluation_errors_are_coded() -> None:
    with pytest.raises(ExpressionEvalError, match="divides by zero"):
        evaluate("1 / #a", {"a": "0"})
    with pytest.raises(ExpressionEvalError):
        evaluate('#a * "x"', {"a": "2"})
    with pytest.raises(ExpressionEvalError, match="if"):
        evaluate("if(1, 2)", {})


# -- sentences ---------------------------------------------------------------------------

VOCAB = Vocabulary(
    labels={
        "type": "Type",
        "company": "Company name",
        "qty": "Quantity",
        "price": "Price",
        "d": "Start date",
    },
    choices={"type": {"business": "Business", "charity": "Charity"}},
)


def test_the_plan_sentences() -> None:
    assert (
        rule_sentence("Company name", '#type is "business" or #type is "charity"', VOCAB)
        == "Show Company name when Type is Business or Type is Charity."
    )
    assert calculation_sentence("Total", "#qty * #price", VOCAB) == "Total is Quantity times Price."


@pytest.mark.parametrize(
    ("rule", "spoken"),
    [
        ('#type is one of ("business", "charity")', "Type is Business or Charity"),
        ('not #type is "business"', "Type is not Business"),
        ("#company is filled", "Company name is answered"),
        ("not #company is filled", "Company name has no answer"),
        ("#qty >= 3 and #qty < 10", "Quantity is at least 3 and Quantity is less than 10"),
        ('#d is before "2027-01-01"', "Start date is before 1 January 2027"),
        ("#d is after today + 7", "Start date is after 7 days from today"),
        ("#d is within 30 days", "Start date is within 30 days of today"),
        ("#a or #b and #c", "a or both b and c"),
        ("sum(#qty, #price)", "the total of Quantity and Price"),
        ("user.first_name", "the visitor's first name"),
    ],
)
def test_sentences(rule: str, spoken: str) -> None:
    assert sentence(rule, VOCAB) == spoken
