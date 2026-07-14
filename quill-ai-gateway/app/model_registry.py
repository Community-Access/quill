"""Which OpenAI models the hosted tier may use, and which one is the
default for a given feature -- the admin-tunable model registry backing
:class:`app.models.GatewayModel`.

Kept separate from ``app/limits.py`` (which is about *how much*, not
*which model*) so each module stays focused on one PRD concern.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import GatewayModel, db


class NoDefaultModel(Exception):
    """Raised when no enabled model is marked default -- a misconfigured
    deployment, not a user-facing error; the caller should treat this as
    "hosted AI is unavailable" (PRD §8's global kill-switch response)
    rather than expose the internal cause to the client."""


@dataclass(slots=True)
class ResolvedModel:
    model_id: str
    input_cost_per_million_usd: float
    output_cost_per_million_usd: float

    def estimate_cost_usd(self, tokens_in: int, tokens_out: int) -> float:
        return (
            tokens_in / 1_000_000 * self.input_cost_per_million_usd
            + tokens_out / 1_000_000 * self.output_cost_per_million_usd
        )


def list_models(include_disabled: bool = False) -> list[GatewayModel]:
    """Every configured model, default-first, for the admin console's
    model-picker screen (PRD §10's "select different models" requirement)."""
    query = db.session.query(GatewayModel)
    if not include_disabled:
        query = query.filter(GatewayModel.enabled.is_(True))
    return sorted(query.all(), key=lambda m: (not m.is_default, m.label))


def resolve_default_model() -> ResolvedModel:
    """The model a request uses when it doesn't name one explicitly (which
    is every hosted-tier request today -- PRD §8 deliberately never lets
    the client pick a model). Raises :class:`NoDefaultModel` if the admin
    has somehow left no enabled model marked default; the caller (see
    ``app/routes/chat.py``) treats this exactly like the global kill
    switch being off."""
    row = (
        db.session
        .query(GatewayModel)
        .filter(GatewayModel.enabled.is_(True), GatewayModel.is_default.is_(True))
        .one_or_none()
    )
    if row is None:
        raise NoDefaultModel("No enabled model is marked default.")
    return ResolvedModel(
        model_id=row.model_id,
        input_cost_per_million_usd=float(row.input_cost_per_million_usd),
        output_cost_per_million_usd=float(row.output_cost_per_million_usd),
    )


def set_default_model(model_id: str, admin_id: str) -> None:
    """Mark *model_id* as the (only) default, enabling it if needed.

    Enforced here, in a single transaction, rather than as a database
    constraint: "exactly one default row" is a two-statement invariant
    (unset the old one, set the new one) that's simplest to guarantee in
    application code, and doing it here keeps the invariant next to the
    one function that's allowed to break and re-establish it.
    """
    from app.models import AdminAction

    target = db.session.get(GatewayModel, model_id)
    if target is None:
        raise ValueError(f"Unknown model_id: {model_id!r}")

    db.session.query(GatewayModel).filter(GatewayModel.is_default.is_(True)).update({
        "is_default": False
    })
    target.is_default = True
    target.enabled = True
    db.session.add(AdminAction(admin_id=admin_id, action="set_default_model", target=model_id))
    db.session.commit()


def set_model_enabled(model_id: str, enabled: bool, admin_id: str) -> None:
    """Turn one model on or off (PRD §10's "enable/disable a model").

    Disabling the current default is allowed (an admin might be
    deliberately pulling a model that's misbehaving) but leaves no default
    set until the admin explicitly picks a new one via
    :func:`set_default_model` -- :func:`resolve_default_model` then raises
    :class:`NoDefaultModel`, which the chat route surfaces as "hosted AI is
    paused," never a silent fallback to some other model the admin didn't
    choose.
    """
    from app.models import AdminAction

    target = db.session.get(GatewayModel, model_id)
    if target is None:
        raise ValueError(f"Unknown model_id: {model_id!r}")
    target.enabled = enabled
    if not enabled and target.is_default:
        target.is_default = False
    db.session.add(
        AdminAction(
            admin_id=admin_id,
            action="enable_model" if enabled else "disable_model",
            target=model_id,
        )
    )
    db.session.commit()
