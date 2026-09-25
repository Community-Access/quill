-- 006: a wider input ceiling, and the budget headroom it needs.
--
-- Two numbers, and the second exists because of the first.
--
-- **max_input_tokens: 1,500 -> 3,000.** 1,500 tokens is about 1,125 words, so a
-- document short enough to ask a question about whole was the exception rather
-- than the rule. Input is the cheap half of a request: per token the answer
-- costs several times what the question does, so doubling the input ceiling is a
-- modest increase per request rather than a doubling of anything.
--
-- **global_monthly_budget_usd, raised to match.** The gateway spec had already
-- flagged the old value as too tight before this change: the worst case consumed
-- most of it, and any reasoning-token leakage doubles a bill. What makes that
-- dangerous rather than merely tight is the failure mode -- tripping this cap
-- does not slow the service down or degrade it for heavy users, it turns hosted
-- AI **off for everyone**, which is the loudest failure this system has. The new
-- value is the spec's own recommendation and leaves room that is actually room.
--
-- Neither number is raised in `app/limits.py`. Those are the *fail-safe*
-- defaults, used when a config row is missing, and their comment is explicit
-- that a missing row must never make the gateway more permissive than intended.
-- A floor that quietly rose with the ceiling would not be a floor. The same
-- goes for the client's own default in `quill/core/ai/gateway_client.py`, which
-- is what an installed copy assumes before it has ever reached the service.
--
-- Why a migration rather than an edit to 002: that file seeds with
-- `ON CONFLICT (key) DO NOTHING`, deliberately, so that re-running it never
-- reverts a limit an admin has tuned by hand. The consequence is that editing
-- it changes nothing on a database that already exists -- it is the value a
-- *fresh* deployment starts from. This file is how a running deployment moves.

BEGIN;

UPDATE gateway_config
   SET value = 3000,
       description = 'Maximum tokens in a single request''s prompt (plus chunks).'
 WHERE key = 'max_input_tokens';

UPDATE gateway_config
   SET value = 40.0,
       description = 'Total hosted-AI budget per month across all users, in USD.'
 WHERE key = 'global_monthly_budget_usd';

-- Idempotent for a database that never ran 002 (a deployment seeded some other
-- way): insert the rows if the UPDATEs above matched nothing.
INSERT INTO gateway_config (key, value, description) VALUES
    ('max_input_tokens', 3000,
     'Maximum tokens in a single request''s prompt (plus chunks).'),
    ('global_monthly_budget_usd', 40.0,
     'Total hosted-AI budget per month across all users, in USD.')
ON CONFLICT (key) DO NOTHING;

COMMIT;

-- Not changed here, and worth saying why: `max_chunks_per_request` stays at 3.
-- Chunks are about 180 words each, so three of them is roughly 540 words of
-- document context, and the wider ceiling makes that fit more comfortably
-- rather than more tightly. Raising the count is a separate decision with a
-- trade-off of its own -- a fourth and fifth passage reach more of a long
-- document, and also dilute a good answer with weaker matches -- and it should
-- be taken on its own evidence rather than carried along by this one.
