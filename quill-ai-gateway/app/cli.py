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
        """Seed gateway_config and gateway_models with the PRD §8/§23
        initial-rollout defaults. Safe to re-run: existing rows are left
        untouched, only missing keys are inserted, so re-running this
        after an admin has already tuned some limits will never silently
        revert their changes."""
        from app.limits import _FAIL_SAFE_DEFAULTS, _FEATURE_CAP_FAIL_SAFE_DEFAULTS
        from app.models import GatewayConfig, GatewayModel, db

        descriptions = {
            "monthly_request_cap": "Free requests per user per month.",
            "daily_request_cap": "Free requests per user per day.",
            "hourly_request_cap": "Free requests per user per hour.",
            "device_hourly_request_cap": "Free requests per device per hour.",
            "max_input_tokens": "Maximum tokens in a single request's prompt (plus chunks).",
            "max_output_tokens": "Maximum tokens the model may generate per request.",
            "max_chunks_per_request": "Maximum document excerpts a document-Q&A request may "
            "include.",
            "max_image_bytes": "Maximum image file size, in bytes, for alt-text requests.",
            "max_image_edge_px": "Maximum image longest-edge size, in pixels (client resizes "
            "below this).",
            "daily_image_cap": "Free image (alt-text) requests per user per day.",
            "monthly_cost_cap_usd": "Maximum estimated cost per user per month, in USD.",
            "global_monthly_budget_usd": "Total hosted-AI budget per month across all users, "
            "in USD.",
        }
        added = 0
        for key, value in _FAIL_SAFE_DEFAULTS.items():
            if db.session.get(GatewayConfig, key) is None:
                db.session.add(
                    GatewayConfig(key=key, value=value, description=descriptions.get(key, ""))
                )
                added += 1
        for feature, value in _FEATURE_CAP_FAIL_SAFE_DEFAULTS.items():
            key = f"feature_cap.{feature}"
            if db.session.get(GatewayConfig, key) is None:
                db.session.add(
                    GatewayConfig(
                        key=key,
                        value=value,
                        description=f"Monthly cap for the '{feature}' feature.",
                    )
                )
                added += 1
        if db.session.query(GatewayModel).count() == 0:
            db.session.add(
                GatewayModel(
                    model_id="gpt-5-nano",
                    label="GPT-5 Nano",
                    enabled=True,
                    is_default=True,
                    input_cost_per_million_usd=0.10,
                    output_cost_per_million_usd=0.50,
                )
            )
            added += 1
        db.session.commit()
        click.echo(f"Seeded {added} new row(s). Existing rows were left untouched.")

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
