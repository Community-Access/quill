-- 008: conversations, and ten writing tools (QUILL Lite 1.1, 2026-09).
--
-- **Conversations (`chat`).** Deferred until now because a conversation resends
-- its whole history on every turn, so each reply costs more than the last. It
-- ships on the condition that removes that: the history is trimmed to the same
-- `max_input_tokens` every other request has, oldest turns first
-- (app/limits.py::fit_history), so a turn never costs more than any other
-- request. What a long conversation loses is memory of its opening, never
-- money. Its share of the month is 40 of the 100: a conversation is many
-- requests by nature, and forty still leaves sixty for everything else.
--
-- **Ten writing tools**, each the shape of Summarize -- one passage in, one
-- result out, under the same input ceiling: shorten, simplify, formal,
-- friendly, make_list, action_items, headings, continue, email_reply and
-- translate. Each gets the ordinary share of 60. Translate's language must be
-- one of app/prompts.py::LANGUAGES.
--
-- **Answer ceilings** are code, not rows: app/prompts.py::LONG_ANSWER_FEATURES
-- gives the conversation, translate, continue, email_reply, headings, make_list
-- and simplify the longer `max_ask_output_tokens` (1,000). The Limits page
-- already prices every request at that longer ceiling, so the worst case per
-- person ($0.08 a month at the seeded sizes) and the per-person fence ($0.10)
-- do not move.
--
-- Not changed: `global_monthly_budget_usd`, `monthly_request_cap`,
-- `max_input_tokens`.

BEGIN;

-- The chat flag already exists (seeded off, with a "never built" reason).
UPDATE feature_flags
   SET enabled = true,
       disabled_reason = NULL
 WHERE feature = 'chat';

INSERT INTO feature_flags (feature, enabled) VALUES
    ('chat', true),
    ('shorten', true),
    ('simplify', true),
    ('formal', true),
    ('friendly', true),
    ('make_list', true),
    ('action_items', true),
    ('headings', true),
    ('continue', true),
    ('email_reply', true),
    ('translate', true)
ON CONFLICT (feature) DO NOTHING;

UPDATE gateway_config
   SET value = 40,
       description = 'A ceiling on conversation turns specifically, inside the overall monthly total.'
 WHERE key = 'feature_cap.chat';

INSERT INTO gateway_config (key, value, description) VALUES
    ('feature_cap.chat', 40,
     'A ceiling on conversation turns specifically, inside the overall monthly total.'),
    ('feature_cap.shorten', 60, 'Monthly cap for Shorten.'),
    ('feature_cap.simplify', 60, 'Monthly cap for Simplify.'),
    ('feature_cap.formal', 60, 'Monthly cap for Make more formal.'),
    ('feature_cap.friendly', 60, 'Monthly cap for Make friendlier.'),
    ('feature_cap.make_list', 60, 'Monthly cap for Turn into a list.'),
    ('feature_cap.action_items', 60, 'Monthly cap for Find action items.'),
    ('feature_cap.headings', 60, 'Monthly cap for Suggest headings.'),
    ('feature_cap.continue', 60, 'Monthly cap for Continue writing.'),
    ('feature_cap.email_reply', 60, 'Monthly cap for Write an email reply.'),
    ('feature_cap.translate', 60, 'Monthly cap for Translate.')
ON CONFLICT (key) DO NOTHING;

COMMIT;
