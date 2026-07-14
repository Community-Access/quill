-- Initial schema for the QUILL AI Gateway.
--
-- This is the authoritative DDL for production PostgreSQL deployments --
-- it matches app/models.py exactly, plus the one thing SQLAlchemy's ORM
-- layer here doesn't express natively: usage_events' RANGE partitioning
-- by month (docs/planning/openai.md §5's "PARTITION BY RANGE" note).
--
-- For local development, `flask --app run.py init-db` (app/cli.py) is
-- simpler and uses db.create_all() against a plain (non-partitioned)
-- table -- fine for a dev SQLite/small-Postgres instance, but production
-- should apply this file so old months can be dropped as a fast DDL
-- operation (see 002_seed_gateway_config.sql's sibling note and
-- app/cli.py's cleanup-expired command).
--
-- Apply with: psql "$DATABASE_URL" -f migrations/001_initial_schema.sql

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- for gen_random_uuid()

CREATE TABLE IF NOT EXISTS users (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    status                TEXT NOT NULL DEFAULT 'active',
    monthly_request_cap   INT,
    monthly_cost_cap_usd  NUMERIC(8,4),
    email                 TEXT UNIQUE,
    email_verified_at     TIMESTAMPTZ,
    CONSTRAINT users_status_check CHECK (status IN ('active', 'reduced', 'review', 'blocked'))
);

CREATE TABLE IF NOT EXISTS devices (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES users(id),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at          TIMESTAMPTZ,
    status                TEXT NOT NULL DEFAULT 'active',
    label                 TEXT,
    token_hash            TEXT NOT NULL UNIQUE,
    CONSTRAINT devices_status_check CHECK (status IN ('active', 'revoked'))
);
CREATE INDEX IF NOT EXISTS ix_devices_token_hash ON devices (token_hash);

-- Partitioned by month; create the current + next month's partition below
-- and add a new one each month (or automate with pg_partman if this ever
-- grows enough to justify the dependency -- not needed at this scale).
CREATE TABLE IF NOT EXISTS usage_events (
    id                    SERIAL,
    user_id               UUID NOT NULL REFERENCES users(id),
    device_id             UUID NOT NULL REFERENCES devices(id),
    feature               TEXT NOT NULL,
    model                 TEXT NOT NULL,
    tokens_in             INT NOT NULL,
    tokens_out            INT NOT NULL,
    estimated_cost_usd    NUMERIC(10,6) NOT NULL,
    status                TEXT NOT NULL,
    abuse_flag            TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE IF NOT EXISTS usage_events_default PARTITION OF usage_events DEFAULT;

CREATE INDEX IF NOT EXISTS ix_usage_events_user_created ON usage_events (user_id, created_at);
CREATE INDEX IF NOT EXISTS ix_usage_events_feature_created ON usage_events (feature, created_at);

CREATE TABLE IF NOT EXISTS monthly_usage_summary (
    user_id               UUID NOT NULL REFERENCES users(id),
    year_month            TEXT NOT NULL,
    request_count         INT NOT NULL DEFAULT 0,
    total_cost_usd        NUMERIC(10,4) NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, year_month)
);

CREATE TABLE IF NOT EXISTS feature_flags (
    feature               TEXT PRIMARY KEY,
    enabled               BOOLEAN NOT NULL DEFAULT true,
    disabled_reason       TEXT,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gateway_config (
    key                   TEXT PRIMARY KEY,
    value                 NUMERIC NOT NULL,
    description           TEXT NOT NULL,
    updated_by            TEXT,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS gateway_models (
    model_id                        TEXT PRIMARY KEY,
    label                           TEXT NOT NULL,
    enabled                         BOOLEAN NOT NULL DEFAULT true,
    is_default                      BOOLEAN NOT NULL DEFAULT false,
    input_cost_per_million_usd      NUMERIC(10,4) NOT NULL,
    output_cost_per_million_usd     NUMERIC(10,4) NOT NULL,
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- "At most one default" is enforced in application code (see
-- app/model_registry.py::set_default_model), not a DB constraint --
-- simplest to guarantee correctly in a single transaction there, and a
-- partial unique index on (is_default) WHERE is_default would work in
-- Postgres but adds a migration-fragility risk not worth it at this scale.

CREATE TABLE IF NOT EXISTS user_feature_caps (
    user_id               UUID NOT NULL REFERENCES users(id),
    feature               TEXT NOT NULL,
    monthly_cap           INT NOT NULL,
    PRIMARY KEY (user_id, feature)
);

CREATE TABLE IF NOT EXISTS diagnostic_records (
    id                    SERIAL PRIMARY KEY,
    usage_event_id        INTEGER,
    redacted_prompt       TEXT NOT NULL,
    redacted_response     TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at            TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_actions (
    id                    SERIAL PRIMARY KEY,
    admin_id              TEXT NOT NULL,
    action                TEXT NOT NULL,
    target                TEXT NOT NULL,
    reason                TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
