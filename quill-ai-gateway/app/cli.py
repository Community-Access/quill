"""Operational CLI commands (``flask --app run.py <command>``).

These back the parts of PRD §4.4 (retention) and §7 (reconciliation)
that are jobs, not requests — run them from cron (see README.md's
deployment section for the recommended schedule).
"""

from __future__ import annotations

from datetime import UTC, datetime

import click
from flask import Flask


def register_cli_commands(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db() -> None:
        """Create every table from the SQLAlchemy models. Idempotent —
        safe to run against an already-initialized database (existing
        tables are left untouched). For anything beyond the very first
        deploy, prefer a real migration tool (Alembic) layered on top of
        this; see migrations/README.md."""
        from app.models import db

        db.create_all()
        click.echo("Tables created (or already existed).")

    @app.cli.command("seed-config")
    def seed_config() -> None:
        """Seed gateway_config, gateway_models and feature_flags with the
        recommended initial values.

        Safe to re-run: existing rows are left untouched and only missing keys
        are inserted, so re-running this after an admin has tuned some limits
        never silently reverts their changes. That also means it cannot be used
        to *correct* a value -- change it on the Limits page, or with
        ``PUT /admin/config/<key>``.
        """
        from app.config_schema import describe as describe_key
        from app.limits import _FEATURE_CAP_FAIL_SAFE_DEFAULTS, SEED_DEFAULTS
        from app.models import FeatureFlag, GatewayConfig, GatewayModel, db
        from app.prompts import DEFERRED_FEATURES, FEATURE_LABELS, SHIPPED_FEATURES

        added = 0

        # Descriptions come from the plain-language schema, so the sentence an
        # operator reads on the Limits page and the sentence stored in the
        # database are the same sentence, written once.
        for key, value in SEED_DEFAULTS.items():
            if db.session.get(GatewayConfig, key) is not None:
                continue
            described = describe_key(key)
            db.session.add(
                GatewayConfig(
                    key=key,
                    value=value,
                    description=described.sentence if described else "",
                )
            )
            added += 1

        for feature, value in _FEATURE_CAP_FAIL_SAFE_DEFAULTS.items():
            key = f"feature_cap.{feature}"
            if db.session.get(GatewayConfig, key) is not None:
                continue
            described = describe_key(key)
            label = FEATURE_LABELS.get(feature, feature)
            db.session.add(
                GatewayConfig(
                    key=key,
                    value=value,
                    description=(described.sentence if described else f"Monthly cap for {label}."),
                )
            )
            added += 1

        # Feature flags. The global switch and the five shipped features are on;
        # the deferred ones are off *and carry their reason*, so anyone who
        # reaches them is told "this was never built" rather than the generic
        # "temporarily paused while we review unusual activity", which would
        # send them to support over a feature that does not exist.
        if db.session.get(FeatureFlag, "hosted_ai") is None:
            db.session.add(FeatureFlag(feature="hosted_ai", enabled=True))
            added += 1
        for feature in SHIPPED_FEATURES:
            if db.session.get(FeatureFlag, feature) is None:
                db.session.add(FeatureFlag(feature=feature, enabled=True))
                added += 1
        for feature, reason in DEFERRED_FEATURES.items():
            if db.session.get(FeatureFlag, feature) is None:
                db.session.add(FeatureFlag(feature=feature, enabled=False, disabled_reason=reason))
                added += 1

        if db.session.query(GatewayModel).count() == 0:
            db.session.add(
                GatewayModel(
                    model_id=app.config.get("OPENAI_MODEL", "gpt-6-luna"),
                    label="GPT-6 Luna",
                    enabled=True,
                    is_default=True,
                    input_cost_per_million_usd=0.10,
                    output_cost_per_million_usd=0.50,
                )
            )
            added += 1

        db.session.commit()
        click.echo(f"Seeded {added} new row(s). Existing rows were left untouched.")

    @app.cli.command("check-config")
    def check_config() -> None:
        """Report anything an operator would want to know before trusting the
        numbers: out-of-range limits, a budget cap that normal use can reach,
        a missing default model, and whether alerting actually goes anywhere.

        Exits non-zero if something is wrong, so it can be a deploy step rather
        than a thing somebody remembers to run.
        """
        from app.config_schema import validate as validate_value
        from app.costing import load_cost_model
        from app.limits import resolve_limit
        from app.models import GatewayConfig, db

        problems: list[str] = []

        for row in db.session.query(GatewayConfig).all():
            problem = validate_value(row.key, float(row.value))
            if problem:
                problems.append(problem)

        model = load_cost_model(app)
        if model is None:
            problems.append(
                "No enabled model is marked default, so every request is failing. "
                "Set one on the Models page."
            )
        else:
            cap = resolve_limit(app, "global_monthly_budget_usd")
            worst_500 = model.for_people(500).full_use_usd
            if cap <= 0:
                problems.append(
                    "There is no global budget cap, so nothing will stop runaway "
                    "spending. Set global_monthly_budget_usd."
                )
            elif cap < worst_500:
                problems.append(
                    f"The budget cap (${cap:,.2f}) is below what 500 people at full "
                    f"use would cost (${worst_500:,.2f}). The service will pause "
                    "itself partway through a busy month."
                )
            per_person = model.per_person_month_usd
            user_cap = resolve_limit(app, "monthly_cost_cap_usd")
            if 0 < user_cap < per_person:
                problems.append(
                    f"The per-person cost ceiling (${user_cap:,.4f}) is below what "
                    f"one person's monthly requests can cost (${per_person:,.4f}), "
                    "so people will be cut off before using their allowance."
                )

        if not app.config.get("ALERT_WEBHOOK_URL"):
            problems.append(
                "No alert webhook is configured, so the 50%, 75% and 90% budget "
                "warnings go to a log nobody reads. The first you would hear of a "
                "problem is the service switching itself off."
            )

        if not problems:
            click.echo("Configuration looks sound.")
            return
        for problem in problems:
            click.echo(f"- {problem}")
        raise SystemExit(1)

    @app.cli.command("cleanup-expired")
    def cleanup_expired() -> None:
        """Delete expired diagnostic records (PRD §4.4) and any
        usage_events partitions past the 13-month retention window.
        Intended to run daily from cron -- see README.md."""
        from app.models import DiagnosticRecord, db

        now = datetime.now(UTC)
        deleted = (
            db.session
            .query(DiagnosticRecord)
            .filter(DiagnosticRecord.expires_at < now)
            .delete(synchronize_session=False)
        )
        db.session.commit()
        click.echo(f"Deleted {deleted} expired diagnostic record(s).")

        # usage_events retention (13 months, PRD §4.4): with the table
        # partitioned by month (see migrations/001_initial_schema.sql),
        # dropping old data is a partition DROP, not a slow row-by-row
        # DELETE -- that DDL is intentionally left to a dedicated
        # migration/ops script (see migrations/README.md) rather than
        # driven from the ORM, since partition management is a DBA-level
        # operation this module shouldn't paper over.
        click.echo(
            "Reminder: usage_events partition retention is a separate DBA step -- "
            "see migrations/README.md."
        )

    @app.cli.command("reconcile-usage")
    def reconcile_usage() -> None:
        """Recompute monthly_usage_summary from usage_events, in case a
        crash ever left the running aggregate slightly behind the
        durable event log (see app/limits.py::record_usage's docstring
        on why this is a safety net, not a routine necessity). Intended
        to run nightly from cron."""
        from sqlalchemy import func

        from app.models import MonthlyUsageSummary, UsageEvent, db

        now = datetime.now(UTC)
        year_month = now.strftime("%Y-%m")
        rows = (
            db.session
            .query(
                UsageEvent.user_id,
                func.count(UsageEvent.id),
                func.sum(UsageEvent.estimated_cost_usd),
            )
            .filter(
                UsageEvent.created_at
                >= now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            )
            .group_by(UsageEvent.user_id)
            .all()
        )
        for user_id, count, total_cost in rows:
            summary = db.session.get(
                MonthlyUsageSummary, {"user_id": user_id, "year_month": year_month}
            )
            if summary is None:
                summary = MonthlyUsageSummary(user_id=user_id, year_month=year_month)
                db.session.add(summary)
            summary.request_count = count
            summary.total_cost_usd = float(total_cost or 0)
        db.session.commit()
        click.echo(f"Reconciled {len(rows)} user(s) for {year_month}.")
