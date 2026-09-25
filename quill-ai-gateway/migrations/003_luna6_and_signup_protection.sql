-- 003: GPT-6 Luna, the five shipped features, sign-up protection, and the
-- numbers that were wrong.
--
-- Run after 001 and 002 on an existing deployment. On a fresh database,
-- `flask --app run.py init-db && flask --app run.py seed-config` produces the
-- same end state and this file is not needed.
--
-- Idempotent throughout (ON CONFLICT DO NOTHING / IF NOT EXISTS), so it is safe
-- to re-run. Note that the UPDATE statements are deliberately *not* guarded:
-- they correct values that were wrong, and re-running them re-applies the
-- correction rather than reverting an admin's later tuning, because each one
-- names the old value in its WHERE clause.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Reasoning tokens get a column of their own.
-- ---------------------------------------------------------------------------
-- Billed at the output rate, never shown to the user, and therefore the one
-- component of a bill that can grow without anybody noticing. Folded into
-- tokens_out it is invisible; broken out it is answerable.

ALTER TABLE usage_events
    ADD COLUMN IF NOT EXISTS reasoning_tokens INTEGER NOT NULL DEFAULT 0;

-- ---------------------------------------------------------------------------
-- 2. The model.
-- ---------------------------------------------------------------------------
-- The price columns were already $0.10 / $0.50 per million, which is exactly
-- GPT-6 Luna's price, so the cost math needs no change at all -- only the id
-- and the label. Confirm the exact model-id string against the provider's own
-- model list before running this: it is the string that goes into a billed API
-- call.

INSERT INTO gateway_models
    (model_id, label, enabled, is_default,
     input_cost_per_million_usd, output_cost_per_million_usd)
VALUES
    ('gpt-6-luna', 'GPT-6 Luna', true, true, 0.10, 0.50)
ON CONFLICT (model_id) DO NOTHING;

-- Exactly one row may be default. Demote the old one in the same transaction
-- as promoting the new, so there is never a moment with two or none.
UPDATE gateway_models SET is_default = false, enabled = false
 WHERE model_id = 'gpt-5-nano';
UPDATE gateway_models SET is_default = true, enabled = true
 WHERE model_id = 'gpt-6-luna';

-- ---------------------------------------------------------------------------
-- 3. The two numbers that were wrong.
-- ---------------------------------------------------------------------------
-- The budget cap was $25 against a 500-user worst case of $20 -- 25% headroom,
-- which is not headroom. A cap normal operation can reach is not a backstop,
-- it is a scheduled outage. The WHERE clause means this only corrects the
-- original seeded value; a cap somebody has since tuned is left alone.
UPDATE gateway_config
   SET value = 40.0,
       description = 'When total spending across everybody reaches this, QUILL''s '
                     'free AI switches off for everyone until an admin turns it '
                     'back on. You are alerted at 50%, 75% and 90% first.'
 WHERE key = 'global_monthly_budget_usd' AND value = 25.0;

-- The per-user cost ceiling was $0.15, but 100 requests at the full size limit
-- costs $0.040 -- 3.75x above anything reachable, so it was decoration rather
-- than a fence. $0.08 is still double the reachable worst case, so it cannot
-- false-trip a legitimate user, but it now catches a genuine anomaly.
UPDATE gateway_config
   SET value = 0.08
 WHERE key = 'monthly_cost_cap_usd' AND value = 0.15;

-- ---------------------------------------------------------------------------
-- 4. Sign-up protection.
-- ---------------------------------------------------------------------------
-- Registration is anonymous and unauthenticated on purpose -- "no account, no
-- password, no email" is the accessibility premise the product rests on -- but
-- that makes a per-user allowance a cost *quantum* rather than a cost bound:
-- anyone who can script three HTTP requests can mint as many allowances as they
-- like. These four rows are what make that uneconomic without asking a blind
-- user to solve a picture puzzle.

INSERT INTO gateway_config (key, value, description) VALUES
    ('new_account_hours', 48,
     'A brand-new account gets a smaller allowance for this long, then the full '
     'one. Somebody exploring barely notices; somebody making throwaway accounts '
     'gets a fraction of the value out of each.'),
    ('new_account_request_cap', 15,
     'The monthly allowance while an account is still new. Applies instead of '
     'the normal monthly limit, not on top of it, and never exceeds it.'),
    ('registration_hourly_cap_per_ip', 5,
     'How many times one internet address may start the connect-a-computer flow '
     'in an hour.'),
    ('registration_daily_cap_per_ip', 20,
     'The same limit over a day. A shared address -- an office, a library, a '
     'university -- should still fit comfortably inside it.'),
    ('review_daily_request_cap', 5,
     'The smaller daily limit that applies to somebody under review. A soft '
     'throttle, never a silent block.')
ON CONFLICT (key) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 5. The five shipped features.
-- ---------------------------------------------------------------------------
-- Proofread and Explain are new. Summarize, Rewrite and Questions-about-
-- documents already existed.

INSERT INTO gateway_config (key, value, description) VALUES
    ('feature_cap.proofread', 60,
     'A ceiling on proofread specifically, inside the overall monthly total.'),
    ('feature_cap.explain', 60,
     'A ceiling on explain specifically, inside the overall monthly total.')
ON CONFLICT (key) DO NOTHING;

INSERT INTO feature_flags (feature, enabled) VALUES
    ('proofread', true),
    ('explain', true)
ON CONFLICT (feature) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 6. The two deferred features.
-- ---------------------------------------------------------------------------
-- Images are not shipped. Neither is open-ended chat. Both keep an id and a
-- template so the route recognises them and can answer with a real reason --
-- being told "this was never built" is a completely different fact from
-- "temporarily paused while we review unusual activity", and the second sends
-- somebody to support over a feature that does not exist.
--
-- Belt and braces: the flag is off *and* the cap is zero. A feature switched
-- off in one place and uncapped in another is one flag flip away from being
-- live and unlimited at the same time.

UPDATE feature_flags
   SET enabled = false,
       disabled_reason = 'Describing pictures is not a shipped feature yet. It costs '
                         'several times more per request than text does and needs its '
                         'own limits, so it is deliberately last. Nothing in QUILL or '
                         'QUILL Lite can reach it.'
 WHERE feature = 'alt_text';

UPDATE feature_flags
   SET enabled = false,
       disabled_reason = 'Open-ended chat is not part of the free tier. Every free '
                         'feature works on a passage you selected or a question about '
                         'a document you have open, which is what keeps requests small '
                         'and predictable. Chat is available with your own API key.'
 WHERE feature = 'chat';

UPDATE gateway_config SET value = 0 WHERE key IN ('feature_cap.alt_text', 'feature_cap.chat');
UPDATE gateway_config SET value = 0 WHERE key = 'daily_image_cap';

COMMIT;

-- After running, confirm the whole picture from inside the container:
--     flask --app run.py check-config
-- It reports an out-of-range limit, a budget cap normal use can reach, a
-- missing default model, and an unconfigured alert webhook -- the last of which
-- is the difference between noticing at 50% of budget and noticing when the
-- service switches itself off.
