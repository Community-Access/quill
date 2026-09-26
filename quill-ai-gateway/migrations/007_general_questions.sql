-- 007: general questions, the sixth free feature.
--
-- One question, answered on its own, with nothing from a document and no
-- history. That shape is what makes it affordable where open-ended `chat` is
-- not: a conversation resends everything on every turn, a single question is
-- one request of a known size.
--
-- Four things move together here:
--
-- **The feature flag, on.** `ask` is in `SHIPPED_FEATURES` (app/prompts.py), so
-- `/v1/config` already reports it on when no row exists. The row makes it a
-- switch an operator can turn off from the Feature flags page.
--
-- **Its own share of the month.** `feature_cap.ask` is 60 of the 100, like every
-- other shipped feature: someone who only asks questions can still ask sixty.
--
-- **Its own answer ceiling, 1,000 tokens.** A general answer needs more room than
-- a rewritten paragraph; 500 tokens cut many of them off mid-sentence. The other
-- five features keep `max_output_tokens` at 500.
--
-- **The per-person cost fence, $0.08 -> $0.10.** At a 3,000-token passage limit
-- (migration 006), sixty general questions at the full 1,000-token answer plus
-- forty other requests reach about $0.07 a month. A fence at $0.08 would sit on
-- top of that and cut people off for using what they were given.
--
-- Not changed: `global_monthly_budget_usd` stays at $40. The Limits page prices
-- every request at the longer answer ceiling, so it will now report that $40
-- covers fewer people at full use; raise it there if the user count calls for
-- it. The gateway spec's recommendation is $80 at 1,000 people.
--
-- The chat flag's reason is reworded, because "every free feature works on a
-- passage you selected or a question about a document" stopped being true.

BEGIN;

INSERT INTO feature_flags (feature, enabled) VALUES
    ('ask', true)
ON CONFLICT (feature) DO NOTHING;

INSERT INTO gateway_config (key, value, description) VALUES
    ('feature_cap.ask', 60,
     'A ceiling on general questions specifically, inside the overall monthly total.'),
    ('max_ask_output_tokens', 1000,
     'The most the model may write back to a general question.')
ON CONFLICT (key) DO NOTHING;

UPDATE gateway_config
   SET value = 0.10
 WHERE key = 'monthly_cost_cap_usd';

INSERT INTO gateway_config (key, value, description) VALUES
    ('monthly_cost_cap_usd', 0.10,
     'One person''s requests may not cost more than this in a month.')
ON CONFLICT (key) DO NOTHING;

UPDATE feature_flags
   SET disabled_reason = 'Open-ended chat is not part of the free tier. The free tier '
                         'answers one question at a time: a conversation sends its whole '
                         'history again on every turn, so each reply costs more than the '
                         'last. Chat is available with your own API key.'
 WHERE feature = 'chat';

COMMIT;
