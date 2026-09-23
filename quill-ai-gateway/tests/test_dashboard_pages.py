"""The four new console pages, and the per-person actions on an existing one.

These are page-level tests: they assert that a page renders, that the plain
language an operator needs is actually on it, and that each action reaches the
same effect as its JSON-API counterpart. They are not a substitute for a real
screen-reader pass, but they do pin the handful of accessibility properties that
are structural rather than visual -- a caption on every table, a label for every
control, and a status word next to every status colour.
"""

from __future__ import annotations

import re

import pytest
from app.auth import hash_token

from tests.conftest import (
    make_user_and_device,
    seed_config_rows,
    seed_default_model,
    seed_feature_flags,
)


def _admin_session_client(app, client):
    from app.models import Device, User, db

    user = User()
    db.session.add(user)
    db.session.flush()
    device = Device(user_id=user.id, token_hash=hash_token("admin-token"), label="admin device")
    db.session.add(device)
    db.session.commit()
    app.config["ADMIN_ALLOWLIST"] = frozenset({device.id})
    login = client.post("/dashboard/login", data={"token": "admin-token", "next": ""})
    assert login.status_code == 302
    return client, user, device


@pytest.fixture()
def dash(app, client, db):
    seed_default_model(db.session)
    seed_config_rows(db.session)
    seed_feature_flags(db.session)
    return _admin_session_client(app, client)


# --- The pages render at all -------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/dashboard/",
        "/dashboard/config",
        "/dashboard/locked",
        "/dashboard/safety",
        "/dashboard/glossary",
        "/dashboard/users",
        "/dashboard/models",
        "/dashboard/feature-flags",
        "/dashboard/audit-log",
    ],
)
def test_every_page_renders(dash, path):
    c, _user, _device = dash
    response = c.get(path)
    assert response.status_code == 200, f"{path} did not render"


@pytest.mark.parametrize(
    "path",
    ["/dashboard/config", "/dashboard/locked", "/dashboard/safety", "/dashboard/glossary"],
)
def test_every_new_page_needs_a_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/dashboard/login" in response.headers["Location"]


# --- Structural accessibility properties --------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/dashboard/",
        "/dashboard/config",
        "/dashboard/locked",
        "/dashboard/safety",
        "/dashboard/glossary",
        "/dashboard/users",
    ],
)
def test_every_table_has_a_caption(dash, path):
    """A table without a caption is a table a screen-reader user lands in with
    no idea what they are looking at."""
    c, _user, _device = dash
    html = c.get(path).get_data(as_text=True)
    tables = html.count("<table")
    captions = html.count("<caption")
    assert captions >= tables, f"{path} has {tables} table(s) but only {captions} caption(s)"


@pytest.mark.parametrize(
    "path",
    ["/dashboard/config", "/dashboard/users", "/dashboard/safety", "/dashboard/locked"],
)
def test_no_page_uses_javascript(dash, path):
    """Every interaction is a form post or a link. No JS means a screen reader
    or keyboard-only user gets the identical, fully-supported experience, and
    there is no build step to rot."""
    c, _user, _device = dash
    html = c.get(path).get_data(as_text=True)
    assert "<script" not in html.lower()
    assert "onclick" not in html.lower()


def test_every_input_on_the_limits_page_has_a_real_label(dash):
    """Not a placeholder, not a title attribute -- a <label for>."""
    c, _user, _device = dash
    html = c.get("/dashboard/config").get_data(as_text=True)

    input_ids = set(re.findall(r'<input[^>]*\bid="([^"]+)"', html))
    labelled = set(re.findall(r'<label[^>]*\bfor="([^"]+)"', html))
    unlabelled = input_ids - labelled
    assert not unlabelled, f"Inputs with no <label for>: {sorted(unlabelled)}"


def test_the_limits_page_explains_and_bounds_every_field(dash):
    """Each input points at its explanation and its safe range, so the reader
    hears what the number does before being asked to change it."""
    c, _user, _device = dash
    html = c.get("/dashboard/config").get_data(as_text=True)
    assert 'aria-describedby="what-monthly_request_cap range-monthly_request_cap"' in html
    assert 'id="what-monthly_request_cap"' in html
    assert 'id="range-monthly_request_cap"' in html
    assert "Must be between 0 and 1,000" in html


def test_status_is_never_carried_by_colour_alone(dash):
    """Every status badge contains a word. A red dot is unreadable aloud and
    invisible to a colourblind reader."""
    c, _user, _device = dash
    html = c.get("/dashboard/safety").get_data(as_text=True)
    badges = re.findall(r'<span class="status-badge"[^>]*>(.*?)</span>', html, re.S)
    assert badges
    for badge in badges:
        assert re.search(r"[A-Za-z]", badge), "A status badge with no words in it"


# --- The Limits page says what things cost ------------------------------------


def test_the_limits_page_shows_what_the_settings_cost(dash):
    c, _user, _device = dash
    html = c.get("/dashboard/config").get_data(as_text=True)
    assert "What today's settings cost" in html
    assert "If everyone uses everything" in html
    assert "budget cap" in html
    # The caveat that every figure derives from a number somebody typed.
    assert "not what it actually charges" in html


def test_sizes_are_shown_in_words_as_well_as_tokens(dash):
    c, _user, _device = dash
    html = c.get("/dashboard/config").get_data(as_text=True)
    assert "words (1,500 tokens)" in html


def test_the_image_settings_are_grouped_as_not_in_use(dash):
    """Images are not a shipped feature. The settings are shown rather than
    hidden so nobody wonders whether they are doing something."""
    c, _user, _device = dash
    html = c.get("/dashboard/config").get_data(as_text=True)
    assert "Not in use yet" in html
    assert "images not shipped" in html


def test_an_out_of_range_value_is_refused_with_a_sentence(dash, db):
    from app.models import GatewayConfig

    c, _user, _device = dash
    response = c.post(
        "/dashboard/config/monthly_request_cap", data={"value": "99999"}, follow_redirects=True
    )
    html = response.get_data(as_text=True)
    assert "must be between" in html.lower()
    assert db.session.get(GatewayConfig, "monthly_request_cap").value == 100


def test_a_cost_doubling_is_not_saved_without_the_confirmation(dash, db):
    from app.models import GatewayConfig

    c, _user, _device = dash
    response = c.post(
        "/dashboard/config/monthly_request_cap", data={"value": "500"}, follow_redirects=True
    )
    html = response.get_data(as_text=True)
    assert "was not saved" in html
    assert db.session.get(GatewayConfig, "monthly_request_cap").value == 100

    response = c.post(
        "/dashboard/config/monthly_request_cap",
        data={"value": "500", "confirm": "yes"},
        follow_redirects=True,
    )
    assert db.session.get(GatewayConfig, "monthly_request_cap").value == 500


def test_an_ordinary_change_reports_its_cost_impact(dash):
    c, _user, _device = dash
    response = c.post(
        "/dashboard/config/monthly_request_cap", data={"value": "120"}, follow_redirects=True
    )
    html = response.get_data(as_text=True)
    assert "changed from" in html
    assert "a month" in html  # the before-and-after sentence


# --- Fixed by code -------------------------------------------------------------


def test_the_locked_page_shows_the_prompts_verbatim(dash):
    c, _user, _device = dash
    html = c.get("/dashboard/locked").get_data(as_text=True)
    assert "Correct the spelling, grammar and punctuation" in html
    assert "reasoning_effort" in html
    assert "max_completion_tokens" in html
    assert "No web search. No tools." in html


def test_the_locked_page_explains_why_each_thing_is_locked(dash):
    c, _user, _device = dash
    html = c.get("/dashboard/locked").get_data(as_text=True)
    # Collapse markup and whitespace: the page emphasises phrases with <strong>,
    # so the sentence a reader hears is not a contiguous string in the source.
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html))
    assert "doubles the entire bill" in text
    assert "$10 per thousand calls" in text
    assert "app/prompts.py" in text


def test_the_locked_page_names_the_deferred_features(dash):
    c, _user, _device = dash
    html = c.get("/dashboard/locked").get_data(as_text=True)
    assert "not a shipped feature" in html
    assert "not part of the free tier" in html


# --- Safety checks ---------------------------------------------------------------


def test_the_safety_page_flags_an_unconfigured_alert_webhook(dash):
    """The check most likely to rot, and the one whose failure is only
    discovered at the worst moment."""
    c, _user, _device = dash
    html = c.get("/dashboard/safety").get_data(as_text=True)
    assert "NOT CONFIGURED" in html
    assert "Needs attention" in html


def test_the_safety_page_is_quiet_when_everything_is_normal(app, dash):
    c, _user, _device = dash
    app.config["ALERT_WEBHOOK_URL"] = "https://example.invalid/hook"
    html = c.get("/dashboard/safety").get_data(as_text=True)
    assert "Everything below is in its normal state." in html
    assert "Needs attention" not in html


def test_the_safety_page_checks_the_no_content_invariant_live(dash):
    """Checked against the live database mapping rather than a comment, because
    a migration that added a prompt column would be the worst regression this
    service could ship."""
    c, _user, _device = dash
    html = c.get("/dashboard/safety").get_data(as_text=True)
    assert "Nothing anyone wrote is stored" in html
    assert "BROKEN" not in html


def test_the_safety_page_reports_the_signup_throttle(dash):
    c, _user, _device = dash
    html = c.get("/dashboard/safety").get_data(as_text=True)
    assert "Sign-ups are throttled" in html
    assert "refused today" in html


# --- Finding and helping one person ------------------------------------------------


def test_searching_by_support_id_finds_the_person(dash, db):
    c, _admin, _device = dash
    user, _d = make_user_and_device(db.session, token="theirs")
    response = c.get(f"/dashboard/users?q={user.support_id}")
    html = response.get_data(as_text=True)
    assert user.support_id in html
    assert "1 account matching" in html


def test_a_search_that_finds_nothing_says_so_usefully(dash):
    c, _admin, _device = dash
    html = c.get("/dashboard/users?q=ZZZZ-9999").get_data(as_text=True)
    assert "Nothing matched that support ID" in html
    # And it says why a mistyped code is likely, rather than just "no results".
    assert "mishear" in html


def test_resetting_an_allowance_from_the_page_requires_a_reason(dash, db):
    c, _admin, _device = dash
    user, _d = make_user_and_device(db.session, token="theirs")
    response = c.post(
        f"/dashboard/users/{user.id}/reset-usage", data={"reason": ""}, follow_redirects=True
    )
    assert "Give a reason" in response.get_data(as_text=True)


def test_resetting_an_allowance_from_the_page_works_and_says_what_it_did(dash, db):
    from app.limits import check_request_allowed, record_usage, remaining_quota

    c, _admin, _device = dash
    user, device = make_user_and_device(db.session, token="theirs")
    with c.application.app_context():
        check_request_allowed(c.application, user, device, "summarize")
        record_usage(
            c.application, user, device, "summarize", "gpt-6-luna", 100, 20, 0.0004, "allowed"
        )

    response = c.post(
        f"/dashboard/users/{user.id}/reset-usage",
        data={"reason": "outage on our end"},
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)
    assert "Allowance reset" in html
    assert "use the service again immediately" in html
    with c.application.app_context():
        assert remaining_quota(c.application, user).monthly_used == 0


def test_the_person_page_says_blank_means_no_override(dash, db):
    """The single most confusable control on the page."""
    c, _admin, _device = dash
    user, _d = make_user_and_device(db.session, token="theirs")
    html = c.get(f"/dashboard/users/{user.id}").get_data(as_text=True)
    assert (
        "Leave a field\n    empty to use the normal limit" in html
        or "empty to use the normal limit" in html
    )
    assert "No override" in html


def test_setting_and_clearing_a_per_person_cap_from_the_page(dash, db):
    c, _admin, _device = dash
    user, _d = make_user_and_device(db.session, token="theirs")

    c.post(
        f"/dashboard/users/{user.id}/caps",
        data={"monthly_request_cap": "400", "monthly_cost_cap_usd": "", "reason": "tester"},
        follow_redirects=True,
    )
    db.session.refresh(user)
    assert user.monthly_request_cap == 400
    assert user.monthly_cost_cap_usd is None

    c.post(
        f"/dashboard/users/{user.id}/caps",
        data={"monthly_request_cap": "", "monthly_cost_cap_usd": ""},
        follow_redirects=True,
    )
    db.session.refresh(user)
    assert user.monthly_request_cap is None


def test_rotating_a_token_shows_it_once(dash, db):
    c, _admin, _device = dash
    user, device = make_user_and_device(db.session, token="maybe-leaked")
    response = c.post(
        f"/dashboard/devices/{device.id}/rotate", data={"reason": "unsure"}, follow_redirects=True
    )
    html = response.get_data(as_text=True)
    assert "shown once and never again" in html
    db.session.refresh(device)
    assert device.status == "active"  # rotated, not signed out


def test_signing_out_one_computer_from_the_page(dash, db):
    c, _admin, _device = dash
    user, device = make_user_and_device(db.session, token="theirs")
    c.post(f"/dashboard/devices/{device.id}/revoke", follow_redirects=True)
    db.session.refresh(device)
    assert device.status == "revoked"


# --- The glossary ------------------------------------------------------------------


def test_the_glossary_defines_the_words_the_console_uses(dash):
    c, _user, _device = dash
    html = c.get("/dashboard/glossary").get_data(as_text=True)
    for term in ("Token", "Reasoning token", "Allowance", "Support ID", "Bearer token"):
        assert f">{term}</dt>" in html


def test_every_page_links_to_the_glossary(dash):
    c, _user, _device = dash
    html = c.get("/dashboard/safety").get_data(as_text=True)
    assert "Read the glossary" in html


# --- Switches and the audit log ----------------------------------------------------


def test_the_switches_page_separates_never_built_from_paused(dash):
    """A feature that was never built and one paused for an hour are completely
    different facts. Mixing them invites an operator to switch on something
    that has no way to be reached."""
    c, _user, _device = dash
    html = c.get("/dashboard/feature-flags").get_data(as_text=True)
    assert "The five features" in html
    assert "Features that were never built" in html
    assert "not a shipped feature" in html


def test_the_switches_page_names_features_in_plain_language(dash):
    """Buttons and headings say what a person would say. Raw feature ids may
    still appear in form actions -- that is markup, not reading material."""
    c, _user, _device = dash
    html = c.get("/dashboard/feature-flags").get_data(as_text=True)
    visible = re.sub(r"<[^>]+>", " ", html)
    assert "Questions about documents" in visible
    assert "document_qna" not in visible
    assert "alt_text" not in visible


def test_an_automatic_pause_is_not_shown_as_somebody_flipping_a_switch(dash, db):
    """Resuming without raising the cap re-pauses within the hour. An operator
    who does not know that will think the switch is broken."""
    from app.models import FeatureFlag

    c, _user, _device = dash
    flag = db.session.get(FeatureFlag, "hosted_ai")
    flag.enabled = False
    flag.disabled_reason = "Global monthly budget cap reached."
    db.session.commit()

    html = c.get("/dashboard/feature-flags").get_data(as_text=True)
    assert "nobody turned it off by hand" in html
    assert "Before switching it back on, raise the cap" in html


def test_the_audit_log_reads_as_sentences(dash, db):
    c, _admin, _device = dash
    user, _d = make_user_and_device(db.session, token="theirs")
    c.post(
        f"/dashboard/users/{user.id}/reset-usage",
        data={"reason": "ran out during a demo"},
        follow_redirects=True,
    )

    html = c.get("/dashboard/audit-log").get_data(as_text=True)
    assert "gave" in html and "their allowance back" in html
    assert "Reason: ran out during a demo." in html
    # The person is named by the support ID they would actually quote, not by
    # a UUID nobody can read down a phone line.
    assert user.support_id in html


def test_the_client_is_told_about_every_feature_including_the_new_ones(app, client, db):
    """``/v1/config`` used to list a hardcoded five. The moment Proofread and
    Explain were added, the client was being told about two features it could
    no longer reach while two it *could* reach went unmentioned."""
    seed_feature_flags(db.session)
    flags = client.get("/v1/config").get_json()["feature_flags"]
    assert flags["proofread"] is True
    assert flags["explain"] is True
    assert flags["summarize"] is True
    assert flags["rewrite"] is True
    assert flags["document_qna"] is True
    # And the two that were never built are reported off, so the client never
    # offers a button for them.
    assert flags["alt_text"] is False
    assert flags["chat"] is False
