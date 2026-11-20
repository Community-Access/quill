"""The production migration path: every file, in order, from an empty database.

``migrations/README.md`` used to stop at 002 and describe a third migration as
hypothetical while 003 to 009 sat beside it, and nothing tested that applying
the files in order actually produces the schema the models describe. Two
checks close that:

* The runbook names every migration file, in order. Pure text, always runs.
* A clean PostgreSQL database initialises through every migration, twice (each
  file says it is safe to re-run), ends with the columns the models declare,
  and takes ``seed-config`` and a recorded request on top. That one needs a
  real PostgreSQL server -- the partitioning, ``gen_random_uuid()`` and the
  ``ALTER COLUMN ... TYPE`` in these files mean nothing to SQLite -- so it runs
  when ``GATEWAY_TEST_POSTGRES_URL`` names a server it may create a scratch
  database on. The ``gateway-ci`` workflow provides one; locally,
  ``docker run -e POSTGRES_PASSWORD=pg -p 5432:5432 postgres:16-alpine`` and
  ``GATEWAY_TEST_POSTGRES_URL=postgresql://postgres:pg@localhost:5432/postgres``.
"""

from __future__ import annotations

import os
import re
import secrets
from pathlib import Path

import pytest

_GATEWAY = Path(__file__).resolve().parents[1]
_MIGRATIONS = _GATEWAY / "migrations"


def _migration_files() -> list[Path]:
    return sorted(_MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"))


def test_the_migrations_are_numbered_without_gaps():
    numbers = [int(path.name[:3]) for path in _migration_files()]
    assert numbers == list(range(1, len(numbers) + 1))


def test_the_runbook_applies_every_migration_in_order():
    runbook = (_MIGRATIONS / "README.md").read_text("utf-8")
    named = re.findall(r'psql "\$DATABASE_URL" -f migrations/(\d{3}_[\w]+\.sql)', runbook)
    assert named == [path.name for path in _migration_files()]


_POSTGRES_URL = os.environ.get("GATEWAY_TEST_POSTGRES_URL", "")


@pytest.fixture()
def scratch_database():
    """A brand-new, empty database on the test server, dropped afterwards.
    Yields its SQLAlchemy URL."""
    psycopg2 = pytest.importorskip("psycopg2")
    from sqlalchemy.engine import make_url

    name = f"quill_gw_migrate_{secrets.token_hex(4)}"
    server = make_url(_POSTGRES_URL).set(drivername="postgresql")
    admin = psycopg2.connect(server.render_as_string(hide_password=False))
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{name}"')
    try:
        yield server.set(database=name)
    finally:
        with admin.cursor() as cur:
            cur.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        admin.close()


def _apply_all(url) -> None:
    import psycopg2

    conn = psycopg2.connect(url.render_as_string(hide_password=False))
    conn.autocommit = True  # each file manages its own BEGIN/COMMIT, as under psql
    try:
        with conn.cursor() as cur:
            for path in _migration_files():
                cur.execute(path.read_text("utf-8"))
    finally:
        conn.close()


@pytest.mark.skipif(
    not _POSTGRES_URL, reason="needs GATEWAY_TEST_POSTGRES_URL (see module docstring)"
)
def test_a_clean_database_initialises_through_every_migration(scratch_database):
    import fakeredis
    from sqlalchemy import inspect

    _apply_all(scratch_database)
    _apply_all(scratch_database)  # every file claims it is safe to re-run

    from app import create_app
    from app.config import TestingConfig
    from app.models import db

    url = scratch_database.set(drivername="postgresql+psycopg2").render_as_string(
        hide_password=False
    )

    class _Config(TestingConfig):
        SQLALCHEMY_DATABASE_URI = url

    app = create_app(_Config())
    app.extensions["gateway_redis"] = fakeredis.FakeStrictRedis(decode_responses=True)
    with app.app_context():
        # 1. Every column every model declares exists after the migrations alone.
        inspector = inspect(db.engine)
        for table in db.metadata.sorted_tables:
            present = {column["name"] for column in inspector.get_columns(table.name)}
            declared = {column.name for column in table.columns}
            assert declared <= present, f"{table.name} is missing {sorted(declared - present)}"

        # 2. The day-one commands run on top of them.
        runner = app.test_cli_runner()
        seeded = runner.invoke(args=["seed-config"])
        assert seeded.exit_code == 0, seeded.output

        # 3. And a request can be recorded and reconciled against the result,
        #    which is the partitioned table and the widened cost column at work.
        from app.limits import record_usage
        from app.models import Device, MonthlyUsageSummary, User

        user = User()
        db.session.add(user)
        db.session.flush()
        device = Device(user_id=user.id, token_hash="0" * 64, label="migration test")
        db.session.add(device)
        db.session.commit()
        record_usage(
            app,
            user,
            device,
            "web_search",
            "m",
            10,
            10,
            0.030028,
            "allowed",
            user_cost_usd=0.000028,
        )
        reconciled = runner.invoke(args=["reconcile-usage"])
        assert reconciled.exit_code == 0, reconciled.output
        db.session.expire_all()
        summary = db.session.query(MonthlyUsageSummary).one()
        assert float(summary.total_cost_usd) == pytest.approx(0.000028)
        db.session.remove()
        db.engine.dispose()  # let the fixture drop the scratch database cleanly
