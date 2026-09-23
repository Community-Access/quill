-- 004: the monthly cost total needs eight decimal places, not four.
--
-- At the shipped limits one request costs about $0.000028. app/limits.py's
-- record_usage accumulates by reading monthly_usage_summary.total_cost_usd
-- back, adding the new cost, and writing it again -- so at NUMERIC(10,4) every
-- write rounded the total straight back to 0.0000 and it never grew.
--
-- That made the per-user cost ceiling inert: it is checked against this column,
-- so it could never trip no matter how much somebody used. The Redis request
-- counters were the only thing actually bounding anybody. Nothing was
-- over-charged and no money was lost -- the global spend counter and the
-- per-request usage_events rows were always correct -- but one of the two
-- fences was not there.
--
-- Safe to run on a live database: widening a NUMERIC never loses data, and any
-- existing zeros were already zero.

BEGIN;

ALTER TABLE monthly_usage_summary
    ALTER COLUMN total_cost_usd TYPE NUMERIC(14, 8);

COMMIT;

-- Afterwards, rebuild the running totals from the durable event log, which kept
-- full precision all along:
--     flask --app run.py reconcile-usage
