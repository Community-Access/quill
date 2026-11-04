"""Fill It In Yourself's evaluator: calculations, rules, required answers, smart defaults."""

from __future__ import annotations

from quill.core.forms import model as M
from quill.core.forms.bfl_read import read
from quill.core.forms.rules import evaluate_form, smart_default

FORM = """bfl 1
form "Order"

page #about "About you"
  radio #type "Type"
    @required
    + business|Business
    + person|Person
  text #company "Company"
    @required
    @when #type is "business"
  number #qty "Quantity"
  number #price "Price"
  calculation #total "Total"
    @calculate #qty * #price
  calculation #with_tax "With tax"
    @calculate round(#total * 1.2, 2)
  text #discount "Discount"

page #extra "Extra"
  @when #type is "person"
  text #why "Why"

rule set #discount
  @value #total * 0.1
  @when #qty > 10

rule require #why
  @when #qty > 5

rule skip_to #extra
  @when #type is "person"
"""


def test_the_form_reads_cleanly() -> None:
    result = read(FORM)
    assert result.errors == [] and result.warnings == []
    assert M.validate(result.model) == []


def test_calculations_rules_and_visibility() -> None:
    model = read(FORM).model
    state = evaluate_form(model, {"type": "business", "qty": "12", "price": "2.50"})
    assert state.calculated == {"total": 30, "with_tax": 36}
    assert state.values["discount"] == 3
    assert "company" in state.shown and "extra" in state.hidden and "why" in state.hidden
    assert state.missing_required == ["company"]
    assert state.skip_to is None
    state = evaluate_form(model, {"type": "person", "qty": "6"})
    assert "company" in state.hidden and "why" in state.shown
    assert state.missing_required == ["why"]
    assert state.skip_to == "extra"


def test_smart_defaults() -> None:
    assert smart_default({"smart_default": "today() + 7"}, {"today": "2026-11-04"}) == "2026-11-11"
    assert (
        smart_default({"smart_default": 'user("email")'}, {"user": {"email": "a@b.org"}})
        == "a@b.org"
    )
    assert smart_default({"default": "plain"}) == "plain"
