"""What must stop the process booting, and what must only shout.

This file exists because of a real deadlock. ``Config.validate()`` used to
report an empty admin allowlist as a *problem*, and ``create_app`` refuses to
boot on any problem — so a brand-new deployment could not start. The documented
first-run sequence is: register a device through the ordinary device-code flow,
then put its id in ``GATEWAY_ADMIN_ALLOWLIST``. Registering needs the service
running. Running needed the allowlist. Neither could go first.

It only surfaced by standing the thing up on a real host, which is the argument
for these tests: every other test in this suite constructs the app through
``TestingConfig``, where both branches are skipped.
"""

from __future__ import annotations

import pytest
from app import create_app
from app.config import Config


class _Base(Config):
    """A config with the genuinely required secrets present."""

    OPENAI_API_KEY = "sk-test-not-a-real-key"
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


def test_an_empty_admin_allowlist_does_not_stop_the_service_starting():
    """The deadlock, asserted directly.

    An empty allowlist is the *correct* state for a deployment that has not yet
    registered its first admin, which is every deployment for its first few
    minutes. Refusing to boot on it is not caution; it is a service that can
    never be configured.
    """

    class NoAdmins(_Base):
        ADMIN_ALLOWLIST = frozenset()

    cfg = NoAdmins()
    assert cfg.validate() == []
    app = create_app(cfg)
    assert app is not None


def test_an_empty_admin_allowlist_is_still_shouted_about():
    """Not fatal is not the same as not mentioned. It has to be impossible to
    miss in the first screen of ``docker compose logs``."""

    class NoAdmins(_Base):
        ADMIN_ALLOWLIST = frozenset()

    notes = NoAdmins().warnings()
    assert any("GATEWAY_ADMIN_ALLOWLIST" in note for note in notes)
    assert any("restart" in note for note in notes)


def test_a_missing_provider_key_does_stop_the_service_starting():
    """The other direction. With no key every request would fail anyway, so
    failing loudly at boot beats accepting traffic and failing per-request."""

    class NoKey(_Base):
        OPENAI_API_KEY = ""

    cfg = NoKey()
    assert cfg.validate()
    with pytest.raises(RuntimeError, match="Refusing to start"):
        create_app(cfg)


def test_a_missing_session_key_does_stop_the_service_starting():
    """Without it the dashboard's session cookie would be unsigned, which is
    worse than the dashboard being unavailable."""

    class NoSecret(_Base):
        SECRET_KEY = ""

    cfg = NoSecret()
    assert cfg.validate()
    with pytest.raises(RuntimeError, match="Refusing to start"):
        create_app(cfg)


def test_a_missing_alert_webhook_is_a_warning_not_a_failure():
    """A service with no alerting is still a working service. A service that
    will not start is not."""

    class NoAlerts(_Base):
        ADMIN_ALLOWLIST = frozenset({"some-device"})
        ALERT_WEBHOOK_URL = ""

    cfg = NoAlerts()
    assert cfg.validate() == []
    notes = cfg.warnings()
    assert any("switching itself off" in note for note in notes)


def test_a_fully_configured_deployment_has_nothing_to_say():
    class Complete(_Base):
        ADMIN_ALLOWLIST = frozenset({"some-device"})
        ALERT_WEBHOOK_URL = "https://example.invalid/hook"

    cfg = Complete()
    assert cfg.validate() == []
    assert cfg.warnings() == []
