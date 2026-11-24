"""Scribe Status's text, built by a pure function from fake account and queue data."""

from __future__ import annotations

import time

from quill.core.scribe import queue as q
from quill.core.scribe.model import Account
from quill.core.scribe.status import (
    RECENT_LIMIT,
    SECTIONS,
    StatusInputs,
    build_status,
    renewal_date,
)

NOW = 1_800_000_000.0


def _account(**kw: object) -> Account:
    base: dict[str, object] = {
        "first_name": "Pat",
        "last_name": "Reader",
        "email": "pat@example.com",
        "organization_name": "Acme",
        "pages_remaining": 412,
    }
    base.update(kw)
    return Account(**base)  # type: ignore[arg-type]


def _section(text: str, heading: str) -> list[str]:
    for block in text.split("\n\n"):
        lines = block.split("\n")
        if lines[0].split(" (")[0] == heading:
            return lines[1:]
    raise AssertionError(f"no {heading} section")


def test_every_section_in_order_with_the_most_important_fact_first() -> None:
    jobs = (
        q.Job(
            file_name="Notes.pdf",
            state=q.CONVERTING,
            stage="convert",
            progress=0.4,
            eta_seconds=120,
            formats=["docx", "epub"],
            created=NOW - 50,
        ),
        q.Job(file_name="Next.pdf", formats=["docx"], created=NOW - 40),
        q.Job(file_name="Locked.pdf", state=q.NEEDS_PASSWORD, created=NOW - 30),
        q.Job(file_name="Old.pdf", state=q.DONE, formats=["docx"], created=NOW - 900),
        q.Job(file_name="Bad.pdf", state=q.FAILED, message="Bad file.", created=NOW - 800),
    )
    report = build_status(
        StatusInputs(
            signed_in=True,
            account=_account(
                phone_number="555-0100",
                has_subscription=True,
                subscription_store="web",
                subscription_renews_at="2026-12-12T00:00:00Z",
            ),
            jobs=jobs,
            runner_app="QUILL Lite",
            actions_this_minute=3,
            now=NOW,
        )
    )
    lines = report.text.split("\n")
    assert lines[0] == "Signed in as Pat Reader, using credits from Acme. 412 pages left."
    assert report.first_line == lines[0]
    headings = [block.split("\n")[0].split(" (")[0] for block in report.text.split("\n\n")[1:]]
    assert headings == list(SECTIONS)
    account = _section(report.text, "Account")
    assert "Email: pat@example.com" in account and "Phone: 555-0100" in account
    assert "Organization: Acme" in account
    assert "Subscription: active, bought on the Scribe website, renews 12 December 2026." in account
    assert "Sign-in: kept on this computer for every QUILL app, and renewed by itself." in account
    usage = _section(report.text, "Usage")
    assert usage[0] == "Pages left: 412, using credits from Acme."
    assert any(line.startswith("Pace: 3 of 8 uploads") for line in usage)
    now = _section(report.text, "Now converting")
    assert now[0].startswith("Notes.pdf, converting, 40 percent, about 2 minutes.")
    assert "Word and EPUB" in now[0] and now[-1] == "QUILL Lite is doing the work."
    assert "Waiting (2)" in report.text
    waiting = _section(report.text, "Waiting")
    assert waiting[0].startswith("Next.pdf: Queued.")
    assert "Conversions on This Computer has what to do." in waiting[1]
    recent = _section(report.text, "Recent")
    assert recent[0].startswith("Bad.pdf: Failed.") and recent[0].endswith("Bad file.")
    assert recent[1].startswith("Old.pdf: Done.")
    assert not report.offer_sign_in


def test_an_individual_with_no_subscription() -> None:
    report = build_status(
        StatusInputs(signed_in=True, account=_account(organization_name="", pages_remaining=1))
    )
    assert report.first_line == "Signed in as Pat Reader. 1 page left."
    assert "Subscription: none." in _section(report.text, "Account")
    assert _section(report.text, "Usage")[0] == "Pages left: 1."


def test_not_signed_in_says_so_and_offers_sign_in() -> None:
    report = build_status(StatusInputs(signed_in=False, jobs=(q.Job(file_name="A.pdf"),)))
    assert report.first_line.startswith("You are not signed in to Scribe for Documents.")
    assert report.offer_sign_in
    assert _section(report.text, "Usage")[0] == "Pages left: sign in to see them."
    assert _section(report.text, "Waiting")[0].startswith("A.pdf: Queued.")  # local, still shown


def test_an_api_error_gives_the_sentence_and_the_code() -> None:
    report = build_status(
        StatusInputs(
            signed_in=True,
            error_message="Couldn't connect to Scribe.",
            error_code="QUILL-SCRIBE-OFFLINE",
        )
    )
    assert report.first_line == (
        "Signed in, but your Scribe account could not be read: "
        "Couldn't connect to Scribe. (QUILL-SCRIBE-OFFLINE)"
    )
    assert "Refresh tries again" in report.text
    assert not report.offer_sign_in


def test_an_ended_sign_in_offers_sign_in_again() -> None:
    report = build_status(
        StatusInputs(signed_in=True, sign_in_ended=True, error_message="Ended.", error_code="X")
    )
    assert report.first_line.startswith("Your Scribe for Documents sign-in has ended.")
    assert report.offer_sign_in


def test_no_jobs_and_still_checking() -> None:
    report = build_status(StatusInputs(signed_in=True, checking=True))
    assert report.first_line == "Signed in. Checking your Scribe account..."
    assert _section(report.text, "Now converting") == ["Nothing is converting."]
    assert _section(report.text, "Waiting") == ["Nothing is waiting."]
    assert _section(report.text, "Recent") == ["No finished conversions on this computer."]


def test_a_rate_limit_pause_shows_when_it_ends() -> None:
    report = build_status(StatusInputs(signed_in=True, paused_until=NOW + 30, now=NOW))
    at = time.strftime("%H:%M:%S", time.localtime(NOW + 30))
    assert any(at in line and "slow down" in line for line in _section(report.text, "Usage"))


def test_recent_keeps_the_newest_few() -> None:
    jobs = tuple(
        q.Job(file_name=f"F{i}.pdf", state=q.DONE, created=NOW - i) for i in range(RECENT_LIMIT + 2)
    )
    recent = _section(build_status(StatusInputs(jobs=jobs)).text, "Recent")
    assert recent[0].startswith("F0.pdf")
    assert recent[-1] == "2 more in Conversions on This Computer."


def test_the_token_is_never_in_the_text() -> None:
    report = build_status(
        StatusInputs(signed_in=True, renews=False, sign_in_ends=NOW + 60, now=NOW)
    )
    assert "ends at" in report.text and "token" not in report.text.lower()


def test_renewal_dates() -> None:
    assert renewal_date("2026-12-12T00:00:00Z") == "12 December 2026"
    assert renewal_date("") == ""
    assert renewal_date("soon") == "soon"


def test_the_billing_fields_are_read_from_the_api() -> None:
    account = Account.from_mappings(
        {"first_name": "Pat", "phone_number": "555"},
        {
            "pages_remaining": 9,
            "subscription": {"store": "app_store", "renews_at": "2027-01-01T00:00:00Z"},
            "app_account_token": "secret-uuid",
        },
    )
    assert account.has_subscription and account.subscription_store == "app_store"
    assert account.phone_number == "555"
    assert "secret-uuid" not in repr(account)
    assert not Account.from_mappings({}, {"subscription": None}).has_subscription


def test_the_queue_pace_is_read_only(tmp_path) -> None:  # type: ignore[no-untyped-def]
    family = q.FamilyQueue(tmp_path, now=lambda: NOW)
    assert family.pace() == (0, 0.0)
    family.reserve_action()
    family.reserve_action()
    assert family.pace() == (2, 0.0)
    family.pause_for_rate_limit()
    count, until = family.pace()
    assert count == 2 and until == NOW + q.RATE_LIMITED_WAIT_S


def test_the_sign_in_line_names_the_family_in_every_app() -> None:
    text = build_status(StatusInputs(app_name="QUILL Lite", signed_in=True)).text
    assert "every QUILL app" in text and "every QUILL Lite app" not in text


def test_an_account_with_no_name_is_not_called_by_a_placeholder() -> None:
    account = Account(pages_remaining=3)
    report = build_status(StatusInputs(signed_in=True, account=account))
    assert report.first_line == "Signed in. 3 pages left."


def test_a_failed_refresh_keeps_the_last_account_below_the_error() -> None:
    report = build_status(
        StatusInputs(
            signed_in=True,
            account=_account(),
            error_message="Couldn't connect to Scribe.",
            error_code="QUILL-SCRIBE-OFFLINE",
        )
    )
    assert report.first_line.startswith("Signed in, but your Scribe account could not be read")
    assert "Email: pat@example.com" in _section(report.text, "Account")
