"""What the current settings actually cost, in dollars, on this page.

The console could always show an operator *what* a limit was. It could never
show them what changing it would do, which is the question they are actually
asking. This module answers it.

Everything here derives from two sources and no others: the live
``gateway_config`` values (through :func:`app.limits.resolve_limit`) and the
default model's price columns. That second dependency is worth naming out loud
wherever these numbers are displayed: **the price columns are what somebody
told the gateway the provider charges, not what the provider charges.** If a
provider changes its prices and nobody updates the row, every figure this
module produces is confidently wrong, and the budget cap stops protecting
anything. See :func:`pricing_caveat`.

There is no live recalculation in the browser: the console is server-rendered
with no JavaScript, so a figure changes when the page is rendered again, which
happens on every save.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "CostModel",
    "ProjectionRow",
    "describe_change",
    "load_cost_model",
    "pricing_caveat",
]

#: The scenarios the overview table shows. "Everyone uses everything" is the
#: worst case that the caps actually permit; a third is what real usage has
#: looked like for comparable free tiers, and is the number to plan against.
_PEOPLE_SCENARIOS: tuple[int, ...] = (100, 500, 1_000)
_REALISTIC_UTILIZATION = 0.30

PRICING_CAVEAT = (
    "Every figure on this page comes from the price columns on the Models "
    "page, which are what this gateway was told the provider charges — not "
    "what it actually charges. If the provider changes its prices and nobody "
    "updates the row, these numbers are wrong and the budget cap stops "
    "protecting anything. Check them when you change models, and once a month "
    "otherwise."
)


def pricing_caveat() -> str:
    return PRICING_CAVEAT


@dataclass(frozen=True, slots=True)
class ProjectionRow:
    people: int
    full_use_usd: float
    realistic_usd: float


@dataclass(frozen=True, slots=True)
class CostModel:
    """A snapshot of what the live settings imply about cost."""

    model_id: str
    model_label: str
    input_per_million_usd: float
    output_per_million_usd: float
    max_input_tokens: int
    max_output_tokens: int
    monthly_request_cap: int

    @property
    def per_request_usd(self) -> float:
        """What one request costs if it uses every token it is allowed to.

        The worst case, deliberately: a projection built on the average of
        hoped-for usage is a projection that is only correct while nothing
        goes wrong.
        """
        return (
            self.max_input_tokens / 1_000_000 * self.input_per_million_usd
            + self.max_output_tokens / 1_000_000 * self.output_per_million_usd
        )

    @property
    def per_person_month_usd(self) -> float:
        return self.per_request_usd * self.monthly_request_cap

    def for_people(self, people: int) -> ProjectionRow:
        full = self.per_person_month_usd * people
        return ProjectionRow(
            people=people,
            full_use_usd=full,
            realistic_usd=full * _REALISTIC_UTILIZATION,
        )

    def projections(self) -> list[ProjectionRow]:
        return [self.for_people(n) for n in _PEOPLE_SCENARIOS]

    def headroom_sentence(self, budget_cap_usd: float) -> str:
        """One sentence putting the budget cap next to what it has to cover."""
        if budget_cap_usd <= 0:
            return (
                "There is no budget cap set, so nothing will switch the service "
                "off if spending runs away. Set one."
            )
        if self.per_person_month_usd <= 0:
            return f"The budget cap is ${budget_cap_usd:,.2f} a month."
        covered_full = int(budget_cap_usd / self.per_person_month_usd)
        covered_realistic = int(covered_full / _REALISTIC_UTILIZATION)
        return (
            f"The budget cap is ${budget_cap_usd:,.2f} a month, which covers "
            f"{covered_full:,} people using everything they are allowed, or "
            f"about {covered_realistic:,} people at the usage a free tier "
            f"normally sees."
        )


def load_cost_model(app) -> CostModel | None:
    """Build a :class:`CostModel` from the live config and default model.

    Returns ``None`` when no enabled model is marked default — the console must
    then say so rather than print zeroes, because a page full of ``$0.00`` reads
    as "this is free" when it actually means "this is broken".
    """
    from app.limits import resolve_limit
    from app.model_registry import NoDefaultModel, resolve_default_model
    from app.models import GatewayModel, db

    try:
        resolved = resolve_default_model()
    except NoDefaultModel:
        return None

    row = db.session.get(GatewayModel, resolved.model_id)
    label = row.label if row is not None else resolved.model_id

    return CostModel(
        model_id=resolved.model_id,
        model_label=label,
        input_per_million_usd=resolved.input_cost_per_million_usd,
        output_per_million_usd=resolved.output_cost_per_million_usd,
        max_input_tokens=int(resolve_limit(app, "max_input_tokens")),
        max_output_tokens=int(resolve_limit(app, "max_output_tokens")),
        monthly_request_cap=int(resolve_limit(app, "monthly_request_cap")),
    )


def _model_with(model: CostModel, key: str, value: float) -> CostModel:
    """*model* as it would be if *key* were set to *value*."""
    if key == "max_input_tokens":
        return CostModel(**{**_as_dict(model), "max_input_tokens": int(value)})
    if key == "max_output_tokens":
        return CostModel(**{**_as_dict(model), "max_output_tokens": int(value)})
    if key == "monthly_request_cap":
        return CostModel(**{**_as_dict(model), "monthly_request_cap": int(value)})
    return model


def _as_dict(model: CostModel) -> dict:
    return {
        "model_id": model.model_id,
        "model_label": model.model_label,
        "input_per_million_usd": model.input_per_million_usd,
        "output_per_million_usd": model.output_per_million_usd,
        "max_input_tokens": model.max_input_tokens,
        "max_output_tokens": model.max_output_tokens,
        "monthly_request_cap": model.monthly_request_cap,
    }


@dataclass(frozen=True, slots=True)
class ChangeImpact:
    """What a proposed config change does to the modelled bill."""

    before_usd: float
    after_usd: float
    people: int
    budget_cap_usd: float

    @property
    def multiple(self) -> float:
        if self.before_usd <= 0:
            return float("inf") if self.after_usd > 0 else 1.0
        return self.after_usd / self.before_usd

    @property
    def needs_confirmation(self) -> bool:
        """True when this change more than doubles the modelled bill.

        A doubling is the threshold because it is well past any plausible
        deliberate tuning step and squarely in the territory of a mistyped
        decimal point — which is the specific accident this exists to catch.
        """
        return self.multiple > 2.0

    @property
    def exceeds_budget(self) -> bool:
        return self.budget_cap_usd > 0 and self.after_usd > self.budget_cap_usd

    def sentence(self) -> str:
        text = (
            f"{self.people:,} people at full use: "
            f"${self.before_usd:,.2f} → ${self.after_usd:,.2f} a month."
        )
        if self.exceeds_budget:
            text += (
                f" Your budget cap is ${self.budget_cap_usd:,.2f}, which this now "
                "exceeds — raise the cap, or the service will pause partway "
                "through the month."
            )
        return text


def describe_change(app, key: str, new_value: float, *, people: int = 500) -> ChangeImpact | None:
    """What setting *key* to *new_value* does to the modelled monthly bill.

    ``None`` when the key does not affect cost, or when there is no default
    model to price against. *people* is the scenario size the sentence is
    phrased in; 500 is the planning figure this deployment was sized for.
    """
    from app.config_schema import describe as describe_key
    from app.limits import resolve_limit

    entry = describe_key(key)
    if entry is None or not entry.cost_relevant:
        return None

    model = load_cost_model(app)
    if model is None:
        return None

    after = _model_with(model, key, new_value)
    budget_cap = resolve_limit(app, "global_monthly_budget_usd")
    if key == "global_monthly_budget_usd":
        budget_cap = new_value

    return ChangeImpact(
        before_usd=model.for_people(people).full_use_usd,
        after_usd=after.for_people(people).full_use_usd,
        people=people,
        budget_cap_usd=budget_cap,
    )
