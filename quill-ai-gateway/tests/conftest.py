"""Shared pytest fixtures for the QUILL AI Gateway test suite.

Uses an in-memory SQLite database (via :class:`app.config.TestingConfig`)
and ``fakeredis`` in place of a real Redis server, so the full test suite
runs with no external services required — a deliberate choice for a
service this size, matching the "boring, small" philosophy of the whole
project (see docs/planning/openai.md §16).
"""

from __future__ import annotations

import fakeredis
import pytest
from app import create_app
from app.config import TestingConfig
from app.models import db as _db


@pytest.fixture()
def app():
    application = create_app(TestingConfig())
    application.extensions["gateway_redis"] = fakeredis.FakeStrictRedis(decode_responses=True)
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


def seed_default_model(db_session) -> None:
    """Most tests need at least one enabled+default model to exist."""
    from app.models import GatewayModel

    db_session.add(
        GatewayModel(
            model_id="gpt-5-nano",
            label="GPT-5 Nano",
            enabled=True,
            is_default=True,
            input_cost_per_million_usd=0.10,
            output_cost_per_million_usd=0.50,
        )
    )
    db_session.commit()


def make_user_and_device(db_session, *, token: str = "test-token") -> tuple:
    from app.auth import hash_token
    from app.models import Device, User

    user = User()
    db_session.add(user)
    db_session.flush()
    device = Device(user_id=user.id, token_hash=hash_token(token), label="test device")
    db_session.add(device)
    db_session.commit()
    return user, device


def seed_config_rows(db_session) -> None:
    """The recommended initial limits, as ``flask seed-config`` would write them.

    Tests that exercise validation or costing need real rows to edit; the
    fail-safe path in ``limits.py`` answers reads but there is nothing to
    ``PUT`` at.
    """
    from app.config_schema import describe
    from app.limits import _FEATURE_CAP_FAIL_SAFE_DEFAULTS, SEED_DEFAULTS
    from app.models import GatewayConfig

    for key, value in SEED_DEFAULTS.items():
        entry = describe(key)
        db_session.add(
            GatewayConfig(key=key, value=value, description=entry.sentence if entry else "")
        )
    for feature, value in _FEATURE_CAP_FAIL_SAFE_DEFAULTS.items():
        key = f"feature_cap.{feature}"
        entry = describe(key)
        db_session.add(
            GatewayConfig(key=key, value=value, description=entry.sentence if entry else "")
        )
    db_session.commit()


def seed_feature_flags(db_session) -> None:
    """The global switch plus the five shipped features, all on."""
    from app.models import FeatureFlag
    from app.prompts import DEFERRED_FEATURES, SHIPPED_FEATURES

    db_session.add(FeatureFlag(feature="hosted_ai", enabled=True))
    for feature in SHIPPED_FEATURES:
        db_session.add(FeatureFlag(feature=feature, enabled=True))
    for feature, reason in DEFERRED_FEATURES.items():
        db_session.add(FeatureFlag(feature=feature, enabled=False, disabled_reason=reason))
    db_session.commit()


def make_admin_client(app, client):
    """An authenticated request context for a device on the admin allowlist.

    Returns ``(client, headers, user, device)``.
    """
    from app.auth import hash_token
    from app.models import Device, User, db

    user = User()
    db.session.add(user)
    db.session.flush()
    device = Device(user_id=user.id, token_hash=hash_token("admin-token"), label="admin device")
    db.session.add(device)
    db.session.commit()
    app.config["ADMIN_ALLOWLIST"] = frozenset({device.id})
    return client, {"Authorization": "Bearer admin-token"}, user, device
