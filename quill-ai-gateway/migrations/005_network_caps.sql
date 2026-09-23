-- 005: two standing caps per network.
--
-- Confirming a device code creates a brand-new pseudonymous **user**, not
-- another device on an existing account. That is the right trade for the
-- accessibility premise -- no account, no password, no email -- and it has a
-- consequence worth writing down: two computers are two accounts with a full
-- allowance each, and five are five. The per-IP throttle in 003 limits how
-- *fast* somebody can connect machines; it does nothing about connecting one
-- more every few days.
--
-- So the honest place to bound a person is the one thing their computers have
-- in common. Both numbers are set generously: they are aimed at one household
-- quietly running six laptops through the free tier, never at an office, and
-- the first report of either catching a real workplace should be answerable in
-- one edit rather than one release.

BEGIN;

-- First, a schema divergence this migration tripped over and which would have
-- bitten every future one.
--
-- 001_initial_schema.sql declares updated_at as NOT NULL DEFAULT now(), but the
-- SQLAlchemy models carried only a *Python-side* default. A database created
-- with `flask init-db` (which uses the models) therefore had the NOT NULL and no
-- default -- so any plain-psql INSERT that did not name the column failed, while
-- the identical insert through SQLAlchemy succeeded. Two ways to create the
-- schema that do not agree is a trap for whoever next reaches for psql, which
-- migrations/README.md explicitly tells them to do.
--
-- The models now declare server_default too. This brings an already-created
-- database into line; it is a no-op where the column already had the default.

ALTER TABLE gateway_config   ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE gateway_models   ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE feature_flags    ALTER COLUMN updated_at SET DEFAULT now();

INSERT INTO gateway_config (key, value, description) VALUES
    ('active_devices_cap_per_ip', 6,
     'How many computers may be connected to the free tier from one address at '
     'once. Signing one out frees its place. Zero means no limit.'),
    ('network_monthly_request_cap', 600,
     'A ceiling shared by everybody behind one address, however many accounts '
     'they have. Zero means no limit.')
ON CONFLICT (key) DO NOTHING;

COMMIT;

-- The device count lives in Redis rather than on the device row: the address a
-- device registered from is not stored in Postgres, and adding it would put a
-- piece of network metadata into a schema whose whole claim is that it holds no
-- more about a person than it must.
