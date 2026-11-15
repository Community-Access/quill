"""QUILL Accessible Forms' spam contract as the Workbench uses it, wx-free (complete.md WP-C).

The reply shapes are QAF's own (``S:\\code\\qaf`` includes/spam/class-qaf-spam-rest.php
``state()``, and QAF_Spam::entry_view / mark_entry), copied here so CI needs no QAF.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import SiteInfo
from quill.core.wordpress.workbench_forms import load_forms, set_entry_spam
from quill.core.wordpress.workbench_load import SiteContext
from quill.core.wordpress.workbench_qaf_spam import (
    form_spam_text,
    held_reason,
    mark_entry,
    spam_state_text,
)
from quill.core.wordpress.workbench_rows import WbRow

STATE = {
    "providers": [
        {"id": "honeypot", "label": "Honeypot", "enabled": True, "available": True,
         "runs": True, "sends_content": False, "note": ""},
        {"id": "akismet", "label": "Akismet", "enabled": True, "available": False,
         "runs": False, "sends_content": True, "note": "Akismet is not active"},
        {"id": "altcha", "label": "Proof of work", "enabled": False, "available": True,
         "runs": False, "sends_content": False, "note": ""},
    ],
    "limits": {"min_seconds": 3, "max_links": 3, "oopspam_threshold": 3,
               "altcha_max_number": 50000, "use_disallowed": True, "use_moderation": False},
    "questions": {"mode": "auto", "form_modes": {"4": "always"},
                  "kinds": {"sense": True, "maths": False}, "site_questions": 2,
                  "send_anyway_after": 3,
                  "this_week": {"week": "2026-W46", "asked": 5, "passed": 3, "failed": 2,
                                "sent_anyway": 1}},
    "oopspam_key_saved": False,
}  # fmt: skip


class Api:
    site_name = "Radio"

    def __init__(self, answers: dict[str, Any] | None = None) -> None:
        self.answers = answers or {}
        self.writes: list[tuple[str, Any]] = []

    def get(self, route: str, **_p: Any) -> Any:
        answer = self.answers.get(route)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.writes.append((route, body))
        answer = self.answers.get(route, {"id": 11})
        if isinstance(answer, Exception):
            raise answer
        return answer

    def iter_collection(self, route: str, params: Any = None, **_k: Any):
        answer = self.answers.get(route, [])
        yield from (answer(params) if callable(answer) else answer)


def _ctx(api: Api, *namespaces: str) -> SiteContext:
    info = SiteInfo("Radio", "", "https://radio.example", "6.9", namespaces, "", ())
    return SiteContext("Radio", api, url="https://radio.example", info=info)  # type: ignore[arg-type]


def _held() -> WbRow:
    return WbRow("form_entry", "Radio", "11", {}, "", route="qaf/v1/entries/11", subkind="qaf")


def test_the_spam_page_reads_every_part_of_qafs_state() -> None:
    text = spam_state_text(STATE)
    lines = text.splitlines()
    assert lines[0] == "Honeypot: on and running."
    assert lines[1] == (
        "Akismet: on, but cannot run; sends what visitors type to its service. "
        "Akismet is not active."
    )
    assert lines[2] == "Proof of work: off."
    assert "at least 3 seconds on the page; at most 3 links" in lines[3]
    assert "disallowed words are used, and its moderation words are not" in lines[3]
    assert lines[4] == (
        "Questions are asked only when the checks are unsure, using common-sense questions; "
        "2 are the site's own; Send Anyway is offered after 3 wrong answers. "
        "1 forms choose their own."
    )
    assert lines[5] == (
        "This week (2026-W46): 5 asked, 3 answered, 2 answered wrongly, 1 sent anyway."
    )
    assert "OOPSpam key is not saved" in lines[6]
    assert "older than the route that changes them" in lines[-1]
    writable = spam_state_text({**STATE, "revision": "abc", "can_edit": True})
    assert writable.splitlines()[-1].startswith("Change them on this page, below;")


def test_a_site_whose_qaf_has_no_spam_route_says_so() -> None:
    api = Api({"qaf/v1/spam": WordPressApiError("no route", status=404)})
    assert "does not show its spam settings" in form_spam_text(_ctx(api, "qaf/v1"))
    assert "no QUILL Accessible Forms" in form_spam_text(_ctx(Api(), "wp/v2"))
    shown = form_spam_text(_ctx(Api({"qaf/v1/spam": STATE}), "qaf/v1"))
    assert shown.startswith("Honeypot: on and running.")


def test_a_held_entry_says_why_and_by_which_check() -> None:
    raw = {"spam": {"check": "oopspam", "reason": "Scored as likely spam.", "score": 4.0,
                    "score_max": 6.0, "held_at_submit": True}}  # fmt: skip
    assert held_reason(raw) == "Held because: Scored as likely spam (oopspam check, score 4 of 6)."
    assert held_reason({"spam": {"check": "person", "reason": "Marked as spam by a person."}}) == (
        "Held because: Marked as spam by a person."
    )
    assert held_reason({"spam": None}) == "" and held_reason({}) == ""

    api = Api({
        "qaf/v1/forms": [{"id": 3, "title": "Contact", "entry_count": 1}],
        "qaf/v1/entries": lambda p: [
            {"id": 11, "form_id": 3, "status": p["status"], "created_at": "2026-11-09",
             "fields": {"name": "X"}, **raw}
        ],
    })  # fmt: skip
    row = load_forms(_ctx(api, "qaf/v1"), "spam")[0]
    assert "Held because: Scored as likely spam" in row.detail


def test_spam_and_not_spam_use_qafs_routes_so_providers_learn() -> None:
    api = Api({"qaf/v1/entries/11/spam": {"id": 11, "told": ["akismet"], "released": False}})
    assert mark_entry(api, _held(), True) == ["akismet"]
    assert set_entry_spam(_ctx(api, "qaf/v1"), [_held()], False) == []
    assert api.writes == [("qaf/v1/entries/11/spam", {}), ("qaf/v1/entries/11/not-spam", {})]


def test_an_older_qaf_without_the_routes_has_the_status_set_instead() -> None:
    api = Api({"qaf/v1/entries/11/spam": WordPressApiError("no route", status=404)})
    assert mark_entry(api, _held(), True) == []
    assert api.writes[-1] == ("qaf/v1/entries/11", {"status": "spam"})


def test_any_other_refusal_is_not_hidden_by_the_fallback() -> None:
    api = Api({"qaf/v1/entries/11/spam": WordPressApiError("in the trash", status=409)})
    with pytest.raises(WordPressApiError, match="trash"):
        mark_entry(api, _held(), True)
    assert set_entry_spam(_ctx(api, "qaf/v1"), [_held()], True) == ["11: in the trash"]
    assert len(api.writes) == 2  # the two tries, and no status write behind them


def test_the_coverage_ledger_places_qafs_spam_routes_and_the_deferred_plugins() -> None:
    from quill.core.wordpress.workbench_coverage import classify

    assert classify("/qaf/v1/spam").status == "covered"
    assert "Spam page" in classify("/qaf/v1/spam").home
    assert classify("/qaf/v1/spam/pow").status == "out_of_scope"
    assert classify("/qaf/v1/spam/weeks").status == "covered"
    assert "Form Spam Questions" in classify("/qaf/v1/spam/questions/(?P<id>[0-9a-f]{12})").home
    assert classify(r"/qaf/v1/entries/(?P<id>[\d]+)/not-spam").status == "covered"
    for route, name in (
        ("/mp/v1/members", "MemberPress"),
        ("/rcp/v1/memberships", "Restrict Content Pro"),
        ("/wpforms/v1/forms", "WPForms"),
        ("/contact-form-7/v1/contact-forms", "Contact Form 7"),
        ("/fluentform/v1/forms", "Fluent Forms"),
        ("/frm/v2/forms", "Formidable Forms"),
        ("/ninja-forms-submissions/submissions", "Ninja Forms"),
        ("/forminator/v1/forms", "Forminator"),
    ):
        found = classify(route, ["GET"])
        assert found.status == "schema_built", route
        assert found.home.startswith(f"{name}: deferred, not a current commitment"), route
    assert classify("/mp/v1/members", ["POST"]).status == "wp_admin_only"
