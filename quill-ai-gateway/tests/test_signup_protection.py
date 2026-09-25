"""Sign-up throttling and the new-account ramp.

Every per-user quota in ``app/limits.py`` is sound, and none of it bounds cost
while accounts are free to mint. Registration is anonymous and unauthenticated
on purpose -- "no account, no password, no email" is the accessibility premise
the whole product rests on -- so an allowance is not a cost bound, it is a cost
*quantum*: three HTTP requests and fifteen lines of script produce another
hundred free requests, and the only thing that eventually stops it is the global
budget cap switching hosted AI off for everybody.

These two measures are what close that, and neither of them asks a blind user
to solve a picture puzzle.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import seed_config_rows


def test_a_burst_of_signups_from_one_address_is_refused(app, client, db):
    seed_config_rows(db.session)  # hourly cap of 5

    accepted = 0
    for _ in range(8):
        response = client.post("/v1/device/code", headers={"X-Forwarded-For": "198.51.100.7"})
        if response.status_code == 200:
            accepted += 1
        else:
            assert response.status_code == 429
            assert response.json["status"] == "throttled"
            assert "Retry-After" in response.headers

    assert accepted == 5


def test_the_refusal_does_not_blame_the_users_computer(app, client, db):
    """The person who hits this is usually an ordinary user behind a shared
    address -- an office, a library, a school -- not the scripted abuse it is
    aimed at. The message must not read as a fault on their end."""
    seed_config_rows(db.session)
    for _ in range(6):
        response = client.post("/v1/device/code", headers={"X-Forwarded-For": "198.51.100.8"})

    message = response.json["message"]
    assert "network" in message
    assert "Try again" in message
    for blame in ("error", "invalid", "failed", "denied", "rejected"):
        assert blame not in message.lower()


def test_a_different_address_is_unaffected(app, client, db):
    seed_config_rows(db.session)
    for _ in range(6):
        client.post("/v1/device/code", headers={"X-Forwarded-For": "198.51.100.9"})

    other = client.post("/v1/device/code", headers={"X-Forwarded-For": "203.0.113.4"})
    assert other.status_code == 200


def test_an_unknown_address_is_allowed_rather_than_refused(app, client, db):
    """A proxy misconfiguration must not take sign-ups down. The failure mode
    of guessing wrong in the other direction is an outage nobody can diagnose
    from the client end."""
    seed_config_rows(db.session)
    for _ in range(20):
        response = client.post("/v1/device/code", environ_overrides={"REMOTE_ADDR": ""})
    assert response.status_code == 200


def test_blocked_signups_are_counted_for_the_console(app, client, db):
    from app.limits import registrations_blocked_today

    seed_config_rows(db.session)
    for _ in range(8):
        client.post("/v1/device/code", headers={"X-Forwarded-For": "198.51.100.10"})

    with app.app_context():
        assert registrations_blocked_today(app) >= 1


# --- The new-account ramp --------------------------------------------------------


def test_a_brand_new_account_gets_the_smaller_allowance(app, db):
    from app.limits import _effective_user_cap, is_new_account
    from app.models import User

    seed_config_rows(db.session)
    user = User()
    db.session.add(user)
    db.session.commit()

    with app.app_context():
        assert is_new_account(app, user) is True
        assert _effective_user_cap(app, user) == 15


def test_an_established_account_gets_the_full_allowance(app, db):
    from app.limits import _effective_user_cap, is_new_account
    from app.models import User

    seed_config_rows(db.session)
    user = User(created_at=datetime.now(UTC) - timedelta(days=7))
    db.session.add(user)
    db.session.commit()

    with app.app_context():
        assert is_new_account(app, user) is False
        assert _effective_user_cap(app, user) == 100


def test_an_admin_override_beats_the_ramp(app, db):
    """The override is the only number somebody deliberately typed for this
    person, so it wins over both the ramp and the global default -- otherwise
    granting a new user more would silently do nothing for two days."""
    from app.limits import _effective_user_cap
    from app.models import User

    seed_config_rows(db.session)
    user = User(monthly_request_cap=250)
    db.session.add(user)
    db.session.commit()

    with app.app_context():
        assert _effective_user_cap(app, user) == 250


def test_setting_the_window_to_zero_disables_the_ramp(app, db):
    from app.limits import is_new_account
    from app.models import GatewayConfig, User

    seed_config_rows(db.session)
    db.session.get(GatewayConfig, "new_account_hours").value = 0
    db.session.commit()

    user = User()
    db.session.add(user)
    db.session.commit()

    with app.app_context():
        assert is_new_account(app, user) is False


def test_the_ramp_makes_a_farmed_account_worth_a_fraction_of_a_real_one(app, db):
    """The whole economic point, asserted as a ratio so that tuning the numbers
    cannot quietly remove the protection."""
    from app.limits import resolve_limit

    seed_config_rows(db.session)
    with app.app_context():
        full = resolve_limit(app, "monthly_request_cap")
        new = resolve_limit(app, "new_account_request_cap")
    assert new < full / 3, (
        "A throwaway account should be worth well under a third of a real one, "
        "or farming them stays economic."
    )


def test_the_ramp_never_gives_a_new_account_more_than_an_established_one(app, db):
    """Regression. The two values are independent dials, so lowering the
    monthly cap below the ramp used to hand new accounts a *larger* allowance
    than everybody else -- turning the anti-farming measure into a reason to
    keep making fresh accounts. Found by an existing monthly-cap test that set
    the cap to 2 and watched a brand-new user sail straight past it.
    """
    from app.limits import _effective_user_cap
    from app.models import GatewayConfig, User

    seed_config_rows(db.session)
    db.session.get(GatewayConfig, "monthly_request_cap").value = 2  # below the ramp's 15
    db.session.commit()

    new_user = User()
    established = User(created_at=datetime.now(UTC) - timedelta(days=30))
    db.session.add_all([new_user, established])
    db.session.commit()

    with app.app_context():
        assert _effective_user_cap(app, new_user) <= _effective_user_cap(app, established)
        assert _effective_user_cap(app, new_user) == 2


# --- Standing caps per network ---------------------------------------------------


def test_one_address_may_not_connect_unlimited_computers(app, client, db):
    """The rate throttle stops a burst. It does not stop somebody connecting
    one more machine every few days -- and because confirming a code creates a
    whole new *account*, five computers is five full allowances, not one shared
    between them."""
    from app.limits import RegistrationThrottled as Throttled
    from app.limits import check_device_budget, note_device_registered

    seed_config_rows(db.session)  # cap of 6
    with app.app_context():
        for _ in range(6):
            check_device_budget(app, "203.0.113.9")
            note_device_registered(app, "203.0.113.9")

        with pytest.raises(Throttled) as caught:
            check_device_budget(app, "203.0.113.9")

    # And it says what to do about it rather than just refusing.
    assert "Sign one of them out" in caught.value.message


def test_signing_a_computer_out_frees_its_place(app, client, db):
    """Otherwise the cap is a lifetime total, and somebody who dutifully signs
    out an old laptop before connecting a new one is refused for doing exactly
    the right thing."""
    from app.limits import RegistrationThrottled as Throttled
    from app.limits import check_device_budget, note_device_registered, release_device_slot

    seed_config_rows(db.session)
    with app.app_context():
        for _ in range(6):
            note_device_registered(app, "203.0.113.10")
        with pytest.raises(Throttled):
            check_device_budget(app, "203.0.113.10")

        release_device_slot(app, "203.0.113.10")
        check_device_budget(app, "203.0.113.10")  # must not raise


def test_a_shared_monthly_ceiling_bounds_a_whole_network(app, db):
    """The measure that makes sponging pointless: it does not care how many
    accounts sit behind the address."""
    from app.limits import QuotaExceeded, check_network_budget
    from app.models import GatewayConfig

    seed_config_rows(db.session)
    db.session.get(GatewayConfig, "network_monthly_request_cap").value = 3
    db.session.commit()

    with app.app_context():
        for _ in range(3):
            check_network_budget(app, "198.51.100.30")
        with pytest.raises(QuotaExceeded) as caught:
            check_network_budget(app, "198.51.100.30")

    assert caught.value.scope == "network"
    assert "starts again on the 1st" in caught.value.message


def test_a_network_request_that_failed_is_given_back(app, db):
    """Counted up front like every other limit, so it needs the same undo."""
    from app.limits import check_network_budget, refund_network_request
    from app.models import GatewayConfig

    seed_config_rows(db.session)
    db.session.get(GatewayConfig, "network_monthly_request_cap").value = 2
    db.session.commit()

    with app.app_context():
        check_network_budget(app, "198.51.100.31")
        refund_network_request(app, "198.51.100.31")
        check_network_budget(app, "198.51.100.31")
        check_network_budget(app, "198.51.100.31")  # must not raise


def test_the_network_ceiling_is_several_times_one_persons_allowance(app, db):
    """So a family or a small office is never the one it catches."""
    from app.limits import resolve_limit

    seed_config_rows(db.session)
    with app.app_context():
        per_person = resolve_limit(app, "monthly_request_cap")
        per_network = resolve_limit(app, "network_monthly_request_cap")
    assert per_network >= per_person * 4


def test_an_unknown_address_is_never_refused_by_either_cap(app, db):
    """A proxy misconfiguration must not look like an outage."""
    from app.limits import check_device_budget, check_network_budget

    seed_config_rows(db.session)
    with app.app_context():
        for _ in range(50):
            check_device_budget(app, "")
            check_network_budget(app, "")


def test_the_starter_allowance_says_when_it_ends(app, db):
    """The client explains a smaller number instead of just showing one, so the
    server says when it ends -- and says nothing once an admin has lifted it."""
    from app.limits import starter_allowance_ends_at
    from app.models import User

    seed_config_rows(db.session)
    created = datetime.now(UTC) - timedelta(hours=1)
    new = User(created_at=created)
    lifted = User(created_at=created, monthly_request_cap=100)
    old = User(created_at=datetime.now(UTC) - timedelta(days=7))
    db.session.add_all([new, lifted, old])
    db.session.commit()

    with app.app_context():
        ends = starter_allowance_ends_at(app, new)
        assert ends is not None
        assert abs((ends - (created + timedelta(hours=48))).total_seconds()) < 5
        assert starter_allowance_ends_at(app, lifted) is None
        assert starter_allowance_ends_at(app, old) is None
