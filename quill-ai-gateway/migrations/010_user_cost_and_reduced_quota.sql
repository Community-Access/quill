-- 010: two cost figures per request, and a reduced quota that reduces
-- (2026-11-20).
--
-- **usage_events.user_cost_usd.** A web search costs its tokens plus a
-- per-search charge (app/limits.py::WEB_SEARCH_CALL_COST_USD, $0.03). The
-- charge goes to the global budget and deliberately NOT to the person's own
-- monthly cost ceiling, which the search cap bounds instead. record_usage
-- already kept the two apart in monthly_usage_summary, but the event log held
-- only the full cost -- so the nightly `reconcile-usage` job, which rebuilds the
-- summary from the event log, moved every search fee onto the person. A $0.001
-- search became $0.031 overnight, and three searches could close every other
-- feature for the month. The column records the person's share; the existing
-- estimated_cost_usd stays the full cost the global budget sees.
--
-- Back-filled here: the person's share of every earlier event is its full cost,
-- less the search charge for a web search. (Every web-search event to date was
-- recorded with exactly $0.03 on top of its tokens.)
--
-- **reduced_monthly_request_cap.** The console has offered a "Reduced quota"
-- status since the start, and nothing read it: a reduced person kept the full
-- allowance. It now applies this monthly allowance instead of the normal one
-- (never more than the normal one, and a per-person number an admin typed
-- still wins). 25 is a quarter of the shipped 100.
--
-- Idempotent: re-running adds nothing and back-fills only rows still empty.

BEGIN;

ALTER TABLE usage_events
    ADD COLUMN IF NOT EXISTS user_cost_usd NUMERIC(10, 6);

UPDATE usage_events
   SET user_cost_usd = CASE
           WHEN feature = 'web_search' THEN GREATEST(estimated_cost_usd - 0.03, 0)
           ELSE estimated_cost_usd
       END
 WHERE user_cost_usd IS NULL;

INSERT INTO gateway_config (key, value, description) VALUES
    ('reduced_monthly_request_cap', 25,
     'The monthly allowance for somebody whose status is Reduced quota, instead '
     'of the normal one. Never more than the normal monthly limit.')
ON CONFLICT (key) DO NOTHING;

COMMIT;

-- Afterwards, rebuild this month's running totals from the corrected event log,
-- which takes any search fee the nightly job had moved onto somebody back off
-- them:
--     flask --app run.py reconcile-usage
