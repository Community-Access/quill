"""Tests for app/model_registry.py: model enable/disable and default
selection (the admin capability to "turn on or off a model, select
different models")."""

from __future__ import annotations

import pytest
from app.model_registry import (
    NoDefaultModel,
    list_models,
    resolve_default_model,
    set_default_model,
    set_model_enabled,
)
from app.models import GatewayModel


def _add_model(db, model_id: str, *, enabled=True, is_default=False):
    db.session.add(
        GatewayModel(
            model_id=model_id,
            label=model_id,
            enabled=enabled,
            is_default=is_default,
            input_cost_per_million_usd=0.10,
            output_cost_per_million_usd=0.50,
        )
    )
    db.session.commit()


def test_resolve_default_model_raises_when_none_configured(app, db):
    with pytest.raises(NoDefaultModel):
        resolve_default_model()


def test_resolve_default_model_returns_the_default(app, db):
    _add_model(db, "gpt-5-nano", is_default=True)
    resolved = resolve_default_model()
    assert resolved.model_id == "gpt-5-nano"


def test_set_default_model_switches_exactly_one_default(app, db):
    _add_model(db, "model-a", is_default=True)
    _add_model(db, "model-b", is_default=False)

    set_default_model("model-b", admin_id="test-admin")

    a = db.session.get(GatewayModel, "model-a")
    b = db.session.get(GatewayModel, "model-b")
    assert a.is_default is False
    assert b.is_default is True
    assert resolve_default_model().model_id == "model-b"


def test_disabling_the_default_model_clears_default(app, db):
    _add_model(db, "gpt-5-nano", is_default=True)
    set_model_enabled("gpt-5-nano", False, admin_id="test-admin")

    with pytest.raises(NoDefaultModel):
        resolve_default_model()


def test_list_models_excludes_disabled_unless_asked(app, db):
    _add_model(db, "on", enabled=True, is_default=True)
    _add_model(db, "off", enabled=False)

    assert [m.model_id for m in list_models()] == ["on"]
    assert {m.model_id for m in list_models(include_disabled=True)} == {"on", "off"}


def test_set_model_enabled_raises_for_unknown_model(app, db):
    with pytest.raises(ValueError):
        set_model_enabled("no-such-model", True, admin_id="test-admin")


def test_estimate_cost_uses_the_models_own_rates(app, db):
    _add_model(db, "gpt-5-nano", is_default=True)
    resolved = resolve_default_model()
    # 1,000,000 tokens in at $0.10/M + 1,000,000 tokens out at $0.50/M
    cost = resolved.estimate_cost_usd(1_000_000, 1_000_000)
    assert cost == pytest.approx(0.60)
