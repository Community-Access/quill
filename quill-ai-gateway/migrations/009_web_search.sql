-- 009: web search, built and switched off (2026-10-15).
--
-- **What it is.** A `web_search` feature: the user types a question, the
-- service asks a search-capable model (GATEWAY_OPENAI_SEARCH_MODEL, default
-- gpt-4o-mini-search-preview) through its own call
-- (app/openai_client.py::search), and the answer comes back with its sources.
-- Clients learn about it from GET /v1/config (`web_search` and, while it is on,
-- a catalogue row) and see how many searches are left in GET /v1/quota.
--
-- **Why it is off.** Every search is charged by the provider on top of its
-- tokens (reckoned at $0.03 in app/limits.py::WEB_SEARCH_CALL_COST_USD). The
-- flag is seeded off with the sentence its refusal shows; an operator turns it
-- on from the Features page once the global budget has room.
--
-- **The cap.** Ten searches per account per month
-- (app/limits.py::WEB_SEARCH_MONTHLY_CAP), a feature cap like every other, so
-- it can be moved on the Limits page. At ten, the search charge adds at most
-- about $0.30 per active person per month to the worst case. That charge goes
-- to the global budget and NOT to the person's own monthly cost ceiling, which
-- was sized for text requests: the cap is what bounds it.
--
-- Not changed: any other limit, `global_monthly_budget_usd` included. Raise the
-- budget before switching the flag on.

BEGIN;

INSERT INTO feature_flags (feature, enabled, disabled_reason) VALUES
    ('web_search', false,
     'Web search is switched off on this service. Each search is charged by the provider on top of its words, so it is turned on deliberately. Everything else still works.')
ON CONFLICT (feature) DO NOTHING;

INSERT INTO gateway_config (key, value, description) VALUES
    ('feature_cap.web_search', 10,
     'How many web searches one person may make in a month, inside the overall monthly total. Only matters while Web search is switched on on the Features page; it ships switched off.')
ON CONFLICT (key) DO NOTHING;

COMMIT;
