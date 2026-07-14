# Migrations

Two hand-written SQL files, applied once in order, for a production
PostgreSQL deployment:

```
psql "$DATABASE_URL" -f migrations/001_initial_schema.sql
psql "$DATABASE_URL" -f migrations/002_seed_gateway_config.sql
```

For local development, `flask --app run.py init-db` followed by
`flask --app run.py seed-config` (see `app/cli.py`) is simpler and works
against SQLite too — it uses SQLAlchemy's `db.create_all()`, which
creates a plain (non-partitioned) `usage_events` table. That's fine for
development; production should use `001_initial_schema.sql` so
`usage_events` is created with monthly `RANGE` partitioning from the
start (see that file's comments for why).

## Adding a new migration

This project intentionally does not use Alembic yet — two migrations is
too little to justify the tooling overhead. If a third migration is ever
needed, this is the natural point to introduce Alembic instead of
hand-numbering more `.sql` files; until then, add `003_*.sql` following
the same pattern (idempotent where practical, a comment explaining what
changed and why).

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
