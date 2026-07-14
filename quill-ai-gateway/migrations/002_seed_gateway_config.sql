-- Seeds gateway_config and gateway_models with the initial-rollout
-- defaults from docs/planning/openai.md §8/§23 ("start small and
-- learn"). Idempotent (ON CONFLICT DO NOTHING) -- safe to re-run without
-- reverting any limit an admin has already tuned.
--
-- Prefer `flask --app run.py seed-config` (app/cli.py) day to day; this
-- file exists so a fresh production database can be seeded with plain
-- psql, without needing the Flask app importable in that shell.

INSERT INTO gateway_config (key, value, description) VALUES
    ('monthly_request_cap', 100, 'Free requests per user per month.'),
    ('daily_request_cap', 20, 'Free requests per user per day.'),
    ('hourly_request_cap', 8, 'Free requests per user per hour.'),
    ('device_hourly_request_cap', 8, 'Free requests per device per hour.'),
    ('max_input_tokens', 1500, 'Maximum tokens in a single request''s prompt (plus chunks).'),
    ('max_output_tokens', 500, 'Maximum tokens the model may generate per request.'),
    ('max_chunks_per_request', 3, 'Maximum document excerpts a document-Q&A request may include.'),
    ('max_image_bytes', 3145728, 'Maximum image file size, in bytes, for alt-text requests.'),
    ('max_image_edge_px', 1600, 'Maximum image longest-edge size, in pixels (client resizes below this).'),
    ('daily_image_cap', 5, 'Free image (alt-text) requests per user per day.'),
    ('monthly_cost_cap_usd', 0.15, 'Maximum estimated cost per user per month, in USD.'),
    ('global_monthly_budget_usd', 25.0, 'Total hosted-AI budget per month across all users, in USD.'),
    ('feature_cap.document_qna', 60, 'Monthly cap for the document_qna feature.'),
    ('feature_cap.summarize', 60, 'Monthly cap for the summarize feature.'),
    ('feature_cap.rewrite', 60, 'Monthly cap for the rewrite feature.'),
    ('feature_cap.alt_text', 15, 'Monthly cap for the alt_text feature.'),
    ('feature_cap.chat', 60, 'Monthly cap for the chat feature.')
ON CONFLICT (key) DO NOTHING;

INSERT INTO gateway_models (model_id, label, enabled, is_default, input_cost_per_million_usd, output_cost_per_million_usd)
VALUES ('gpt-5-nano', 'GPT-5 Nano', true, true, 0.10, 0.50)
ON CONFLICT (model_id) DO NOTHING;

INSERT INTO feature_flags (feature, enabled) VALUES
    ('hosted_ai', true),
    ('document_qna', true),
    ('summarize', true),
    ('rewrite', true),
    ('alt_text', true),
    ('chat', true)
ON CONFLICT (feature) DO NOTHING;
