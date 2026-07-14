"""SQLAlchemy models for the QUILL AI Gateway.

This is the concrete implementation of the schema in
``docs/planning/openai.md`` §5. Every table there has a matching model
here; read that document first if you're new to this codebase -- it
explains *why* the schema looks the way it does (pseudonymous identity,
metadata-only usage tracking, no prompt/document columns anywhere) before
you read *what* it looks like.

The one invariant every future migration must preserve: **no column in
this file may ever hold prompt text, document text, or a full AI
response**, except ``DiagnosticRecord.redacted_prompt``/``redacted_response``,
which exist only for explicit, per-incident, user-opted-in troubleshooting
and have a mandatory expiry. If you're adding a column to log "what the
user asked," stop and re-read PRD §4 first -- that's very likely the wrong
design for this service.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

db = SQLAlchemy()


def _uuid_str() -> str:
    """A fresh UUID4 as a string -- used as the Python-side default for
    UUID primary keys so tests against SQLite (which has no native UUID
    type or server-side ``gen_random_uuid()``) still get real, unique ids."""
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


class User(db.Model):
    """A pseudonymous QUILL AI Gateway account.

    Created at device registration (see ``app/routes/device.py``). No
    email or name is required -- see PRD §4.2 for the identity model this
    intentionally implements. ``status`` gates every quota check in
    ``app/limits.py`` before anything else is evaluated.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid_str)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    status: Mapped[str] = mapped_column(String(16), default="active")
    """One of: active | reduced | review | blocked. See PRD §9's abuse model."""

    # NULL means "use the live gateway_config default." A non-NULL value
    # here is always a deliberate, per-user admin override -- see PRD §8's
    # rationale for why these are nullable rather than always-populated.
    monthly_request_cap: Mapped[int | None] = mapped_column(nullable=True)
    monthly_cost_cap_usd: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)

    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    devices: Mapped[list[Device]] = relationship(back_populates="user")

    def effective_status_allows_requests(self) -> bool:
        """False for ``blocked`` -- the one status that short-circuits everything."""
        return self.status != "blocked"


class Device(db.Model):
    """One registered client install, belonging to exactly one :class:`User`.

    ``token_hash`` is the SHA-256 of the bearer token QUILL's client holds
    -- the raw token is never stored (see ``app/auth/device_flow.py``).
    Revoking a device (``status = "revoked"``) takes effect on its very
    next request with no propagation delay, because every authenticated
    request looks this row up directly (PRD §7's "Compromised device" flow).
    """

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    """active | revoked."""
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="devices")

    __table_args__ = (Index("ix_devices_token_hash", "token_hash"),)


class UsageEvent(db.Model):
    """One metered request. Metadata only -- see the module docstring.

    In a real Postgres deployment this table should be created as a
    partitioned table (``PARTITION BY RANGE (created_at)``, monthly
    partitions) per PRD §5; SQLAlchemy's declarative model here maps the
    *logical* shape, and the partitioning DDL lives in
    ``migrations/001_initial_schema.sql`` since SQLAlchemy's ORM layer
    doesn't model native partitioning directly.
    """

    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), nullable=False)
    feature: Mapped[str] = mapped_column(String(32), nullable=False)
    """document_qna | summarize | rewrite | alt_text | chat."""
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    tokens_in: Mapped[int] = mapped_column(nullable=False)
    tokens_out: Mapped[int] = mapped_column(nullable=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    """allowed | throttled | blocked."""
    abuse_flag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    """null | high_volume | repeated_large_prompt | anomalous_device."""
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_usage_events_user_created", "user_id", "created_at"),
        Index("ix_usage_events_feature_created", "feature", "created_at"),
    )


class MonthlyUsageSummary(db.Model):
    """A running aggregate per ``(user, month)``, updated on every write.

    This is the source of truth for "has this user exceeded their monthly
    limit" once Redis's faster-but-ephemeral counters (see
    ``app/limits.py``) are reconciled against it; it's also what the admin
    console and the client's ``GET /v1/quota`` response read from.
    """

    __tablename__ = "monthly_usage_summary"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    year_month: Mapped[str] = mapped_column(String(7), primary_key=True)
    """'2026-07' -- a plain string, not a date, so equality/grouping is trivial."""
    request_count: Mapped[int] = mapped_column(default=0)
    total_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), default=0)


class FeatureFlag(db.Model):
    """A kill switch, per feature, plus the one global ``hosted_ai`` row.

    Checked *before* any per-user quota logic -- see
    ``app/limits.py::check_request_allowed``. The global row is what an
    admin flips (or what the budget-cap auto-pause flips, PRD §13) to halt
    every hosted request at once, regardless of any individual user's
    remaining quota.
    """

    __tablename__ = "feature_flags"

    feature: Mapped[str] = mapped_column(String(32), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    disabled_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class GatewayConfig(db.Model):
    """One live, admin-tunable numeric limit. See PRD §5/§8/§8.1/§10.

    This table is the entire reason an admin can change "100 requests per
    month" to "250 requests per month" by editing one row instead of
    editing code and redeploying. ``app/limits.py::resolve_limit`` reads
    from here (with a short Redis cache to avoid hitting Postgres on every
    single request) and falls back to a hardcoded fail-safe constant only
    if a key is somehow missing entirely (a fresh, not-yet-seeded database)
    -- see ``migrations/002_seed_gateway_config.sql`` for the values this
    ships with on day one.
    """

    __tablename__ = "gateway_config"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[float] = mapped_column(Numeric, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class GatewayModel(db.Model):
    """One model the admin has configured as available to the hosted tier.

    Unlike the fixed prompt templates (which stay in code -- see PRD §8),
    *which models* are turned on is deliberately admin-tunable: an admin
    can add a model row, flip ``enabled`` off without deleting history,
    and mark exactly one enabled row ``is_default`` per the constraint
    enforced in ``app/routes/admin.py`` (never in the database itself,
    since "exactly one default" is easiest to guarantee in application
    code with a transaction, not a constraint that fights SQLite in
    tests). ``app/limits.py``'s cost math and ``app/openai_client.py``'s
    actual API call both read the *default* row for a feature unless a
    request names a specific (enabled) model explicitly.
    """

    __tablename__ = "gateway_models"

    model_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    """The exact string sent to the provider, e.g. 'gpt-5-nano'."""
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    """Human-readable name shown in the admin console, e.g. 'GPT-5 Nano'."""
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    input_cost_per_million_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    output_cost_per_million_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class UserFeatureCap(db.Model):
    """An explicit per-user, per-feature monthly cap override.

    Unlike :class:`GatewayConfig` (a global default) or ``User.monthly_request_cap``
    (a per-user override of the *overall* monthly cap), this table only
    ever holds deliberate exceptions -- there is no "default" row here;
    absence means "use the global per-feature default from GatewayConfig".
    """

    __tablename__ = "user_feature_caps"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    feature: Mapped[str] = mapped_column(String(32), primary_key=True)
    monthly_cap: Mapped[int] = mapped_column(nullable=False)


class DiagnosticRecord(db.Model):
    """An explicit, user-opted-in, auto-expiring troubleshooting record.

    The *only* place in this schema where prompt/response text is ever
    stored, and even here it's redacted (PII-scrubbed, truncated) before
    it's written -- see ``app/redaction.py``. ``expires_at`` is enforced
    by a scheduled cleanup job (``app/cli.py``'s ``cleanup-expired``
    command), not merely documented as policy.
    """

    __tablename__ = "diagnostic_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usage_event_id: Mapped[int | None] = mapped_column(ForeignKey("usage_events.id"), nullable=True)
    redacted_prompt: Mapped[str] = mapped_column(nullable=False)
    redacted_response: Mapped[str | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdminAction(db.Model):
    """An audit-trail row for every admin-console action. Never deleted.

    Answers "who disabled this user and why" for as long as the row
    exists -- there is no retention policy on this table (unlike usage
    metadata) because an audit trail that expires isn't much of an audit
    trail.
    """

    __tablename__ = "admin_actions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    """disable_user | disable_device | set_quota | set_config | rotate_key | ..."""
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    """A user_id / device_id / feature id / config key / "global"."""
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
