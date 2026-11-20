# Migrations

Hand-written SQL files for a production PostgreSQL deployment, applied once
each, **in numeric order**. Every file is idempotent (`IF NOT EXISTS`,
`ON CONFLICT DO NOTHING`, or an `UPDATE` that names the value it corrects), so
re-running one, or the whole list, is safe.

## A new, empty database

Apply every file, in this order:

```
psql "$DATABASE_URL" -f migrations/001_initial_schema.sql
psql "$DATABASE_URL" -f migrations/002_seed_gateway_config.sql
psql "$DATABASE_URL" -f migrations/003_luna6_and_signup_protection.sql
psql "$DATABASE_URL" -f migrations/004_cost_precision.sql
psql "$DATABASE_URL" -f migrations/005_network_caps.sql
psql "$DATABASE_URL" -f migrations/006_wider_input_and_budget.sql
psql "$DATABASE_URL" -f migrations/007_general_questions.sql
psql "$DATABASE_URL" -f migrations/008_conversations_and_writing_tools.sql
psql "$DATABASE_URL" -f migrations/009_web_search.sql
psql "$DATABASE_URL" -f migrations/010_user_cost_and_reduced_quota.sql
```

then, from inside the web container:

```
flask --app run.py seed-config     # adds any limit or flag the files do not name
flask --app run.py check-config    # exits non-zero if anything is wrong
```

With Docker Compose on the host, run psql inside the database container, once
per file in the order above, for example:

```
docker compose -f docker-compose.prod.yml exec -T postgres \
    psql -U quill_ai_gateway -d quill_ai_gateway < migrations/001_initial_schema.sql
```

| File | What it does | Afterwards |
|---|---|---|
| 001 | Every table, with `usage_events` partitioned by month | |
| 002 | The day-one limits, model and feature flags | |
| 003 | `reasoning_tokens`, GPT-6 Luna as default, sign-up throttles, Proofread and Explain, images and chat switched off | |
| 004 | `monthly_usage_summary.total_cost_usd` to eight decimal places | `reconcile-usage` |
| 005 | Server defaults on `updated_at`; devices and requests per network | |
| 006 | 3,000-token input ceiling; $40 budget | |
| 007 | General questions (`ask`); $0.10 per-person ceiling | |
| 008 | Conversations and the ten writing tools | |
| 009 | Web search, switched off, ten a month | |
| 010 | `usage_events.user_cost_usd` (the person's share of a request's cost, kept apart from the full cost); the Reduced quota allowance | `reconcile-usage` |

`tests/test_migrations.py` checks two things: that this list names every file
in the folder, in order, and -- when `GATEWAY_TEST_POSTGRES_URL` names a
PostgreSQL server, as the `gateway-ci` workflow does -- that a clean database
initialises through every file, twice, ends with every column the models
declare, and takes `seed-config`, a recorded request and `reconcile-usage` on
top.

## An existing database

Apply only the files after the last one it has had, in order, and run each
"Afterwards" step from the table. Nothing records which files a database has
had; if in doubt, apply them all -- they are idempotent.

## Local development

`flask --app run.py init-db` followed by `flask --app run.py seed-config` (see
`app/cli.py`) is simpler and works against SQLite too -- it uses SQLAlchemy's
`db.create_all()`, which creates a plain (non-partitioned) `usage_events`
table and every column the models declare, so none of these files is needed.
That is fine for development; production should use the files above so
`usage_events` is created with monthly `RANGE` partitioning from the start (see
001's comments for why).

## Adding a new migration

Add `011_*.sql` following the same pattern: idempotent, wrapped in
`BEGIN`/`COMMIT`, a comment explaining what changed and why, and any
"afterwards" command at the end. Add it to both lists above in the same change;
`tests/test_migrations.py` fails until you do. Ten numbered files is about the
point where Alembic would start to pay for itself, and moving to it is a
reasonable next step; until then, keep numbering.

## Partition maintenance (production only)

`usage_events` is partitioned by month for fast retention enforcement
(PRD §4.4: 13-month retention, enforced by dropping old partitions rather
than a slow row-by-row `DELETE`). This repo does not yet automate
partition creation/rotation — for now, create each new month's partition
manually a few days before it's needed:

```sql
CREATE TABLE usage_events_2026_08 PARTITION OF usage_events
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
```

and drop partitions older than 13 months:

```sql
DROP TABLE usage_events_2025_06;
```

If this becomes a recurring operational burden, `pg_partman` automates
both steps — a reasonable upgrade once the service has been running long
enough to prove that's worth the added dependency.
