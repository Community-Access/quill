"""The rules evaluator: what a form shows, works out and scores for some answers.

Fill It In Yourself runs this after every answer, so the window behaves as
the site will: a page, section, columns layout or field whose ``visible_when``
does not hold is hidden, and so is everything inside it. Calculations run in
document order, so one can use another worked out above it. A rule that
cannot be worked out (a typo'd date, a divide by zero) hides its field and is
reported, rather than stopping the form.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from quill.core.forms import expr_eval
from quill.core.forms.errors import ExpressionError, ExpressionEvalError
from quill.core.forms.expr_eval import Value
from quill.core.forms.model import Columns, Field, Form, Item, Section


@dataclass
class FormState:
    """Everything the evaluator worked out for one set of answers."""

    visible: set[str] = field(
        default_factory=set
    )  # ids of visible pages, sections, columns, fields
    hidden: set[str] = field(default_factory=set)
    values: dict[str, Any] = field(default_factory=dict)  # answers plus calculations
    calculated: dict[str, Value] = field(default_factory=dict)
    score: Decimal = Decimal(0)
    outcome: str | None = None
    missing_required: list[str] = field(default_factory=list)
    #: (id, sentence) for every rule that could not be worked out.
    problems: list[tuple[str, str]] = field(default_factory=list)

    def is_visible(self, item_id: str) -> bool:
        return item_id in self.visible


class _Run:
    def __init__(
        self,
        form: Form,
        answers: Mapping[str, Any],
        today: dt.date | None,
        context: Mapping[str, Any],
    ) -> None:
        self.form = form
        self.today = today
        self.context = dict(context)
        self.state = FormState(values=dict(answers))

    def holds(self, owner: str, expression: str | None) -> bool:
        if not expression:
            return True
        try:
            return expr_eval.holds(
                expression, self.state.values, today=self.today, context=self.context
            )
        except (ExpressionError, ExpressionEvalError) as exc:
            self.state.problems.append((owner, str(exc)))
            return False

    def walk(self, items: list[Item], shown: bool) -> None:
        for item in items:
            if isinstance(item, Field):
                self.field(item, shown)
            elif isinstance(item, (Section, Columns)):
                ok = shown and self.holds(item.id, item.visible_when)
                (self.state.visible if ok else self.state.hidden).add(item.id)
                if isinstance(item, Section):
                    self.walk(item.items, ok)
                else:
                    for column in item.columns:
                        self.walk(column, ok)

    def field(self, item: Field, shown: bool) -> None:
        ok = shown and self.holds(item.id, item.visible_when)
        (self.state.visible if ok else self.state.hidden).add(item.id)
        if item.calculate:
            try:
                value = expr_eval.evaluate(
                    item.calculate, self.state.values, today=self.today, context=self.context
                )
            except (ExpressionError, ExpressionEvalError) as exc:
                self.state.problems.append((item.id, str(exc)))
                value = None
            self.state.calculated[item.id] = value
            self.state.values[item.id] = value
        if ok:
            self.score(item)
            answer = self.state.values.get(item.id)
            if item.required and not expr_eval.truthy(expr_eval.normal(answer)):
                self.state.missing_required.append(item.id)
        for child in item.fields:
            self.field(child, ok)

    def score(self, item: Field) -> None:
        answer = self.state.values.get(item.id)
        picked = answer if isinstance(answer, (list, tuple)) else [answer]
        for choice in item.choices:
            if choice.score is not None and choice.value in [expr_eval.as_text(p) for p in picked]:
                self.state.score += Decimal(str(choice.score))
        if item.score:
            try:
                value = expr_eval.evaluate(
                    item.score, self.state.values, today=self.today, context=self.context
                )
            except (ExpressionError, ExpressionEvalError) as exc:
                self.state.problems.append((item.id, str(exc)))
                return
            if isinstance(value, bool):
                self.state.score += 1 if value else 0
            else:
                self.state.score += expr_eval.to_number(value) or 0


def evaluate_form(
    form: Form,
    answers: Mapping[str, Any],
    *,
    today: dt.date | None = None,
    context: Mapping[str, Any] | None = None,
) -> FormState:
    """Visibility, calculations, score, outcome and missing answers."""
    run = _Run(form, answers, today, context or {})
    for page in form.pages:
        ok = run.holds(page.id, page.visible_when)
        (run.state.visible if ok else run.state.hidden).add(page.id)
        run.walk(page.items, ok)
    run.context.setdefault("quiz", {})["score"] = run.state.score
    for outcome in form.outcomes:
        if run.holds("outcome", outcome.when):
            run.state.outcome = outcome.message
            break
    return run.state


def smart_default(
    item: Field, *, today: dt.date | None = None, context: Mapping[str, Any] | None = None
) -> Value:
    """A field's starting value: its smart default worked out, else its default."""
    if item.default_expr:
        try:
            return expr_eval.evaluate(item.default_expr, {}, today=today, context=context)
        except (ExpressionError, ExpressionEvalError):
            return item.default
    return item.default
