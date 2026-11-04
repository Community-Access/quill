"""The expression language beyond BAF's shared cases: the plan's sentences, errors, edges."""

from __future__ import annotations

import pytest

from quill.core.forms import expr as E
from quill.core.forms.errors import ExpressionError
from quill.core.forms.expr_eval import evaluate, holds, is_empty, truthy
from quill.core.forms.expr_sentence import calculation_sentence, rule_sentence, sentence

LABELS = {
    "type": "Type",
    "company": "Company name",
    "qty": "Quantity",
    "price": "Price",
    "start": "Start date",
}
CHOICES = {"type": {"business": "Business", "charity": "Charity"}}


def test_the_plans_sentences() -> None:
    assert (
        rule_sentence("Company name", '#type is "business" or #type is "charity"', LABELS, CHOICES)
        == "Show Company name when Type is Business or Type is Charity."
    )
    assert (
        calculation_sentence("Total", "#qty * #price", LABELS) == "Total is Quantity times Price."
    )


@pytest.mark.parametrize(
    ("text", "canonical"),
    [
        ("(#a or #b) or #c", "#a or #b or #c"),
        ("#a and (#b or #c)", "#a and (#b or #c)"),
        ("#a - (#b - #c)", "#a - (#b - #c)"),
        ("#a + (#b + #c)", "#a + (#b + #c)"),
        ("(#a + #b) * 2", "(#a + #b) * 2"),
        ("2.50 + -5", "2.5 + -5"),
        ("10.0", "10.0"),
        ("{qty} * {price}", "#qty * #price"),
        ("today + 30", "today() + 30"),
        ("#pay is Email", '#pay is "Email"'),
        ("'it\\'s'", '"it\'s"'),
        ('"caf\\u00e9 / x"', '"café / x"'),
        ("not (#a is 1)", "not #a is 1"),
    ],
)
def test_canonical_text(text: str, canonical: str) -> None:
    assert E.canonical(text) == canonical
    assert E.canonical(canonical) == canonical


@pytest.mark.parametrize(
    "bad", ["", "#a is", "#a is 1 is 2", "nosuch(1)", "round()", "#", "{a", "#a @ 1", "'open"]
)
def test_errors_carry_an_offset_and_a_code(bad: str) -> None:
    with pytest.raises(ExpressionError) as caught:
        E.parse(bad)
    assert caught.value.code == "QUILL-FORMS-EXPR-SYNTAX"
    assert 0 <= caught.value.position <= len(bad)


def test_refs_and_ast_shape() -> None:
    node = E.parse("#a + #b * #a > #c or #d is one of [#e]")
    assert E.refs(node) == ["a", "b", "c", "d", "e"]
    assert E.parse("-5") == {"type": "literal", "value": -5}
    assert E.parse("score") == {"type": "var", "name": "score"}


def test_truth_and_emptiness_follow_baf() -> None:
    assert truthy("0") and not truthy(0) and not truthy("") and not truthy([])
    assert is_empty("  ") and is_empty(["", None]) and not is_empty(0) and not is_empty(False)


def test_evaluation_edges() -> None:
    ctx = {"values": {"q": "3", "p": "2.50", "d": "2026-02-28"}, "today": "2026-11-04"}
    assert evaluate("#q * #p", ctx) == 7.5
    assert evaluate("6 / 2", ctx) == 3 and isinstance(evaluate("6 / 2", ctx), int)
    assert evaluate("1 / 0", ctx) is None
    assert evaluate("#d + 1", ctx) == "2026-03-01"
    assert evaluate('date("2023-02-29")', ctx) is None
    assert evaluate("round(2.5)", ctx) == 3 and evaluate("round(-2.5)", ctx) == -3
    assert evaluate('length("café")', ctx) == 4
    assert holds('#q is "3.0"', ctx)


def test_sentence_parenthesises_groups() -> None:
    assert sentence("#a and (#b or #c)") == "a and (b or c)"
    assert sentence("not #a is filled") == "a is empty"
