"""The QUILL AI Gateway: a small, boring, private Flask service that owns
the real OpenAI key so the open-source QUILL desktop client never has to.

See ``docs/planning/openai.md`` at the repository root for the full
product requirements document this implements — read that first if
you're new here. This package is the reference implementation of its
§24 API contract.

Application-factory pattern (``create_app``), matching the convention
already used by the sibling ``quillin-hub/`` service in this repository,
so both services are operated the same way on the same host.
"""

from __future__ import annotations

import logging

from flask import Flask

from app.config import Config
from app.models import db


def create_app(config_object: type[Config] | Config | None = None) -> Flask:
    """Build and return the configured Flask application.

    *config_object* defaults to :class:`~app.config.Config` (reads from
    the environment); pass :class:`~app.config.TestingConfig` from tests.
    Startup **fails loudly** (raises ``RuntimeError``) if
    :meth:`~app.config.Config.validate` finds a missing required secret —
    better to refuse to start than to accept traffic it can't actually
    serve (see that method's docstring).
    """
    app = Flask(__name__)
    app.config.from_object(config_object or Config())

    problems = app.config.get("_validated_problems")
    if problems is None:
        cfg = config_object if isinstance(config_object, Config) else Config()
        problems = cfg.validate()
    if problems and not app.config.get("TESTING"):
        for problem in problems:
            logging.getLogger("gateway.startup").error(problem)
        raise RuntimeError(
            "Refusing to start with an invalid configuration:\n- " + "\n- ".join(problems)
        )

    db.init_app(app)

    _init_redis(app)
    _register_blueprints(app)
    _register_cli(app)

    @app.get("/healthz")
    def healthz():
        """Liveness/readiness check. The `quillin-hub` deployment runbook
        calls out its own missing ``/healthz`` as a to-do (see
        docs/planning/openai.md §16) — this service ships one from day
        one, checking both its real dependencies, not just "the process
        is running"."""
        from app.models import db as _db

        checks = {}
        try:
            _db.session.execute(_db.text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:  # noqa: BLE001 - health check must report, not crash
            checks["database"] = f"error: {exc}"
        try:
            app.extensions["gateway_redis"].ping()
            checks["redis"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["redis"] = f"error: {exc}"

        healthy = all(v == "ok" for v in checks.values())
        return checks, 200 if healthy else 503

    return app


def _init_redis(app: Flask) -> None:
    import redis as redis_lib

    app.extensions["gateway_redis"] = redis_lib.from_url(
        app.config["REDIS_URL"], decode_responses=True
    )


def _register_blueprints(app: Flask) -> None:
    from app.routes import admin, chat, client_config, dashboard, device

    app.register_blueprint(device.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(client_config.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(dashboard.bp)


def _register_cli(app: Flask) -> None:
    from app.cli import register_cli_commands

    register_cli_commands(app)
