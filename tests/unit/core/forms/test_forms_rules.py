"""The rules evaluator: visibility, calculations, scores, outcomes and missing answers."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from quill.core.forms.bfl_read import read_form
from quill.core.forms.model import Field
from quill.core.forms.rules import evaluate_form, smart_default

FORM = """form "Order"

radio #type "Type"
  + business|Business
  + person|Person

if #type is "business"
  text #company "Company"
    @required

section "Order"
  @when #type is filled

number #qty "Quantity"
  @required
number #price "Price"
text #total "Total"
  @calculate #qty * #price
text #with_tax "With tax"
  @calculate #total * 1.2

page "Quiz"
  @when #type is "person"

radio #capital "Capital of France"
  + paris|Paris
  + lyon|Lyon
  @choice_score paris 2
text #bonus "Bonus"
  @score #bonus is "yes"

outcome "Top marks"
  @when quiz.score >= 3
outcome "Thanks"
  @when true
"""


def test_conditions_show_and_hide() -> None:
    form = read_form(FORM)
    state = evaluate_form(form, {"type": "person"})
    assert not state.is_visible("company")
    assert state.is_visible("qty")
    assert state.is_visible("page_2")
    state = evaluate_form(form, {"type": "business"})
    assert state.is_visible("company")
    assert "page_2" in state.hidden
    assert "capital" in state.hidden  # hidden with its page
    state = evaluate_form(form, {})
    assert "qty" in state.hidden  # hidden with its section


def test_required_only_counts_when_visible() -> None:
    form = read_form(FORM)
    assert evaluate_form(form, {"type": "person"}).missing_required == ["qty"]
    assert evaluate_form(form, {"type": "business", "qty": "2"}).missing_required == ["company"]


def test_calculations_run_in_order() -> None:
    state = evaluate_form(read_form(FORM), {"type": "person", "qty": "3", "price": "2.50"})
    assert state.calculated["total"] == Decimal("7.50")
    assert state.calculated["with_tax"] == Decimal("9.000")


def test_scores_and_outcomes() -> None:
    form = read_form(FORM)
    state = evaluate_form(form, {"type": "person", "capital": "paris", "bonus": "yes"})
    assert state.score == 3
    assert state.outcome == "Top marks"
    state = evaluate_form(form, {"type": "person", "capital": "lyon"})
    assert state.score == 0
    assert state.outcome == "Thanks"
    # A hidden page scores nothing.
    assert evaluate_form(form, {"type": "business", "capital": "paris"}).score == 0


def test_a_broken_rule_hides_and_reports() -> None:
    form = read_form('text #a "A"\n  @calculate 1 / #b\ntext #c "C"\n  @when #a > 1\n')
    state = evaluate_form(form, {"b": "0"})
    assert ("a", "[QUILL-FORMS-EXPR-EVAL] A calculation divides by zero.") in state.problems
    assert "c" in state.hidden


def test_smart_defaults() -> None:
    today = dt.date(2026, 11, 4)
    item = Field(id="d", type="date", default_expr="today + 7")
    assert smart_default(item, today=today) == dt.date(2026, 11, 11)
    user = Field(id="e", type="email", default_expr="user.email", default="none")
    assert smart_default(user, context={"user": {"email": "a@b.org"}}) == "a@b.org"
    broken = Field(id="x", type="text", default_expr="1 / 0", default="fallback")
    assert smart_default(broken) == "fallback"
    assert smart_default(Field(id="y", type="text", default="plain")) == "plain"


def test_baf_smart_default_strings_become_expressions() -> None:
    form = read_form(
        'date #d "D" @smart_default "today+3"\n'
        'email #e "E" @smart_default "user:email"\n'
        'text #g "G" @smart_default "geo"\n'
        'text #o "O" @smart_default "something:odd"\n'
    )
    items = [i for i in form.pages[0].items if isinstance(i, Field)]
    assert [i.default_expr for i in items] == ["today + 3", "user.email", "geo.country", None]
    assert items[3].settings["smart_default"] == "something:odd"
