"""The running cost total has to actually run.

A request at the shipped limits costs about $0.000028. ``record_usage``
accumulates the monthly total by reading the column back, adding, and writing it
again -- so the column's precision is not a display concern, it is the whole
mechanism. At ``NUMERIC(10, 4)`` every write rounded the new total back down to
``0.0000`` and it never moved off zero.

That made the per-user cost ceiling inert. It is checked against this column, so
it could never trip however much somebody used; the Redis request counters were
the only thing bounding anybody. Nothing was ever over-charged and no money went
missing -- ``usage_events`` and the global spend counter both kept full
precision -- but one of the two fences was not there.

Found by reading the first real request back out of the database on the host:
the event said $0.000028 and the summary said $0.000000.
"""

from __future__ import annotations

from app.limits import _month_key, record_usage, resolve_limit
from app.models import MonthlyUsageSummary

from tests.conftest import (
    make_user_and_device,
    seed_config_rows,
    seed_default_model,
    seed_feature_flags,
)

#: What one real request cost on the host: 95 tokens in, 37 out, GPT-6 Luna.
_ONE_REAL_REQUEST_USD = 0.000028


def _summary(db, user):
    return db.session.get(MonthlyUsageSummary, {"user_id": user.id, "year_month": _month_key()})


def test_a_single_sub_cent_request_is_not_rounded_away(app, db):
    seed_default_model(db.session)
    user, device = make_user_and_device(db.session, token="t")

    with app.app_context():
        record_usage(
            app, user, device, "summarize", "gpt-6-luna", 95, 37, _ONE_REAL_REQUEST_USD, "allowed"
        )

    assert float(_summary(db, user).total_cost_usd) > 0, (
        "One request's cost rounded away to nothing. The monthly total is "
        "accumulated by reading this column back, so a precision too coarse for "
        "a single request means it never grows at all."
    )


def test_a_hundred_requests_accumulate_to_what_they_actually_cost(app, db):
    """The failure this exists to catch is silent: the count goes up, the money
    stays at zero, and nothing anywhere says so."""
    seed_default_model(db.session)
    user, device = make_user_and_device(db.session, token="t")

    with app.app_context():
        for _ in range(100):
            record_usage(
                app,
                user,
                device,
                "summarize",
                "gpt-6-luna",
                95,
                37,
                _ONE_REAL_REQUEST_USD,
                "allowed",
            )

    summary = _summary(db, user)
    expected = 100 * _ONE_REAL_REQUEST_USD
    assert summary.request_count == 100
    assert float(summary.total_cost_usd) == expected


def test_the_per_user_cost_ceiling_can_actually_be_reached(app, db):
    """The fence, end to end.

    An account that spends its whole monthly request allowance at the full size
    limit must move the recorded total far enough that the ceiling is a real
    number rather than a decorative one.
    """
    from app.models import GatewayConfig

    seed_default_model(db.session)
    seed_config_rows(db.session)
    seed_feature_flags(db.session)
    user, device = make_user_and_device(db.session, token="t")

    # A worst-case request: every token the limits allow.
    with app.app_context():
        max_in = int(resolve_limit(app, "max_input_tokens"))
        max_out = int(resolve_limit(app, "max_output_tokens"))
        worst_case = max_in / 1_000_000 * 0.10 + max_out / 1_000_000 * 0.50

        # Give this account plenty of requests so the *cost* fence is what we
        # are measuring, not the request cap.
        db.session.get(GatewayConfig, "hourly_request_cap").value = 10_000
        db.session.get(GatewayConfig, "daily_request_cap").value = 10_000
        db.session.commit()
        user.monthly_request_cap = 500
        db.session.commit()

        for _ in range(100):
            record_usage(
                app, user, device, "summarize", "gpt-6-luna", max_in, max_out, worst_case, "allowed"
            )

    recorded = float(_summary(db, user).total_cost_usd)
    ceiling = 0.08  # the shipped per-user ceiling
    assert recorded > 0
    assert recorded >= ceiling * 0.4, (
        f"100 worst-case requests recorded only ${recorded:.6f} against a "
        f"${ceiling} ceiling. The ceiling is unreachable, so it is decoration."
    )


def test_the_column_is_precise_enough_for_one_token(app, db):
    """A single input token is $0.0000001 at the shipped price. The column does
    not have to resolve one token, but it must not be so coarse that hundreds of
    them vanish."""
    seed_default_model(db.session)
    user, device = make_user_and_device(db.session, token="t")

    one_token_usd = 0.10 / 1_000_000
    with app.app_context():
        for _ in range(1000):
            record_usage(
                app, user, device, "summarize", "gpt-6-luna", 1, 0, one_token_usd, "allowed"
            )

    # A thousand single tokens is $0.0001 -- right at the old precision's floor,
    # and exactly the amount that used to disappear.
    assert float(_summary(db, user).total_cost_usd) > 0.00009
