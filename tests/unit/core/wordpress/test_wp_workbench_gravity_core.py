"""Gravity Forms in the Workbench, wx-free: feeds, notes, flags, notifications, results, tests.

Every answer below is a Gravity Forms REST API v2 shape as its documentation
gives it (forms keyed by id, feeds with ``meta.feedName``, notes keyed by id,
results with ``field_data`` and ``labels``, a refused submission as HTTP 400
with ``validation_messages``); no request leaves the test.
"""

from __future__ import annotations

import io
from typing import Any
from urllib.error import HTTPError

import pytest

from quill.core.wordpress import workbench_gravity as gravity
from quill.core.wordpress import workbench_gravity_submit as submitting
from quill.core.wordpress.api import WordPressApiError, _error_from_http
from quill.core.wordpress.site import Account, SiteInfo
from quill.core.wordpress.workbench_actions import WINDOW_MENU, WORDPRESS_ACTIONS, WORDPRESS_KEYS
from quill.core.wordpress.workbench_coverage import classify
from quill.core.wordpress.workbench_gravity_actions import GRAVITY_ONLY, KEYLESS, command
from quill.core.wordpress.workbench_load import SiteContext, load
from quill.core.wordpress.workbench_node_help import NODE_HELP, ROW_HELP
from quill.core.wordpress.workbench_tree import WORDPRESS_TREE
from quill.core.workbench.menus import all_rows, problems

ADMIN = Account(1, "Jeff", "jeff", ("administrator",), frozenset({"gform_full_access"}))

FEED = {
    "id": "7",
    "form_id": "1",
    "is_active": "1",
    "feed_order": "0",
    "meta": {"feedName": "Newsletter list", "mailchimpList": "abc", "mappedFields_EMAIL": "2"},
    "addon_slug": "gravityformsmailchimp",
}
FORM = {
    "id": "1",
    "title": "Signup",
    "fields": [
        {"id": 1, "type": "text", "label": "Name"},
        {"id": 2, "type": "email", "label": "Email"},
        {
            "id": 3,
            "type": "poll",
            "inputType": "radio",
            "label": "Favourite show",
            "choices": [
                {"text": "Morning Show", "value": "gpoll1a"},
                {"text": "Night Owls", "value": "gpoll1b"},
            ],
        },
        {"id": 4, "type": "html", "label": "Intro"},
        {"id": 5, "type": "fileupload", "label": "Photo", "isRequired": True},
        {
            "id": 6,
            "type": "checkbox",
            "label": "Topics",
            "choices": [{"text": "News", "value": "news"}],
            "inputs": [{"id": "6.1", "label": "News"}],
        },
    ],
    "notifications": {
        "a1": {
            "id": "a1",
            "name": "Admin Notification",
            "event": "form_submission",
            "to": "{admin_email}",
            "toType": "email",
            "isActive": True,
        },
        "b2": {
            "id": "b2",
            "name": "Thanks",
            "event": "form_submission",
            "to": "2",
            "toType": "field",
        },
        "c3": {
            "id": "c3",
            "name": "Routing",
            "toType": "routing",
            "isActive": False,
            "routing": [
                {
                    "email": "news@radio.example",
                    "fieldId": "3",
                    "operator": "is",
                    "value": "gpoll1a",
                }
            ],
        },
    },
}
ENTRY = {
    "id": "5",
    "form_id": "1",
    "status": "active",
    "is_starred": "0",
    "is_read": "0",
    "date_created": "2026-11-09 10:00:00",
    "1": "Ann",
    "2": "ann@example.com",
    "3": "gpoll1a",
}


class Api:
    """A Gravity Forms site: answers by route, records every write."""

    def __init__(self) -> None:
        self.writes: list[tuple[str, str, Any, dict[str, Any]]] = []
        self.entry = dict(ENTRY)
        self.feeds_status = 200
        self.reads: list[tuple[str, dict[str, Any]]] = []

    def get(self, route: str, **params: Any) -> Any:
        self.reads.append((route, params))
        if route == "gf/v2/forms":
            return {
                "1": {"id": "1", "title": "Signup", "entries": "1"},
                "2": {"id": "2", "title": "Contact"},
            }
        if route == "gf/v2/feeds":
            if self.feeds_status != 200:
                raise WordPressApiError("no route", status=self.feeds_status)
            return [FEED]
        if route == "gf/v2/forms/1/feeds":
            return [FEED]
        if route == "gf/v2/forms/2/feeds":
            return []
        if route == "gf/v2/forms/1":
            return FORM
        if route == "gf/v2/forms/2":
            return {"id": "2", "title": "Contact", "fields": [{"id": 1, "type": "text"}]}
        if route == "gf/v2/forms/1/results":
            return {
                "entry_count": "4",
                "field_data": {"3": {"gpoll1a": 3, "gpoll1b": 1}},
                "status": "complete",
                "timestamp": 1,
            }
        if route == "gf/v2/forms/1/field-filters":
            return [
                {"key": "0", "text": "Any form field", "operators": ["contains", "is"]},
                {"key": "1", "text": "Name", "operators": ["is", "isnot", "contains"]},
                {
                    "key": "3",
                    "text": "Favourite show",
                    "operators": ["is", "isnot"],
                    "values": [{"text": "Morning Show", "value": "gpoll1a"}],
                },
                {
                    "text": "Entry",
                    "group": True,
                    "filters": [{"key": "is_starred", "text": "Starred", "operators": ["is"]}],
                },
            ]
        if route == "gf/v2/entries/5/notes":
            return {
                "2": {
                    "id": "2",
                    "user_name": "Jeff",
                    "date_created": "2026-11-10 09:00:00",
                    "value": "<p>Called back</p>",
                    "note_type": "user",
                },
                "1": {
                    "id": "1",
                    "user_name": "",
                    "date_created": "2026-11-09 10:01:00",
                    "value": "Mailchimp: subscribed",
                    "note_type": "notification",
                },
            }
        if route == "gf/v2/entries/5":
            return dict(self.entry)
        return []

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        self.writes.append(("POST", route, body, params))
        if route.endswith("/notifications"):
            return params["_notifications"].split(",")
        if route.endswith("/notes"):
            return {"id": 9}
        if route.endswith("/submissions/validation"):
            if not body.get("input_1"):
                raise WordPressApiError(
                    "refused",
                    status=400,
                    body={
                        "is_valid": False,
                        "validation_messages": {"1": "This field is required."},
                    },
                )
            return {"is_valid": True, "page_number": 0}
        if route.endswith("/submissions"):
            return {"is_valid": True, "entry_id": 12, "confirmation_message": "<p>Thanks!</p>"}
        return {}

    def request(self, method: str, route: str, **kw: Any) -> Any:
        self.writes.append((method, route, kw.get("json_body"), {}))
        if route == "gf/v2/entries/5" and method == "PUT":
            self.entry = dict(kw["json_body"])

        class _R:
            payload: Any = kw.get("json_body")

        return _R()

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, None, params))
        return {}


def _ctx(api: Any) -> SiteContext:
    info = SiteInfo("Radio", "", "https://radio.example", "7.1", ("wp/v2", "gf/v2"), "")
    return SiteContext("Radio", api, url="https://radio.example", account=ADMIN, info=info)


# --------------------------------------------------------------------------- #
# feeds


def test_feeds_list_with_their_add_on_and_state() -> None:
    api = Api()
    rows = load(_ctx(api), "forms:feeds", {}, {})
    assert [(r.title, r.cell("form"), r.cell("addon"), r.cell("status")) for r in rows] == [
        ("Newsletter list", "Signup", "Mailchimp", "Active")
    ]
    assert rows[0].route == "gf/v2/feeds/7" and rows[0].kind == "gravity_feed"
    assert ("gf/v2/feeds", {"form_ids[0]": "1", "form_ids[1]": "2"}) in api.reads


def test_feeds_fall_back_to_each_form_when_the_site_has_no_feeds_route() -> None:
    api = Api()
    api.feeds_status = 404
    rows = gravity.load_feeds(_ctx(api))
    assert [r.title for r in rows] == ["Newsletter list"]


def test_a_feed_change_keeps_every_other_setting() -> None:
    body, lines = gravity.feed_body(FEED, active=False)
    assert body["is_active"] == 0 and body["meta"] == FEED["meta"]
    assert lines[0] == "Active: yes becomes no."
    body, lines = gravity.feed_body(FEED, name="Members")
    assert body["meta"] == {**FEED["meta"], "feedName": "Members"}
    assert FEED["meta"]["feedName"] == "Newsletter list"  # not mutated
    assert "Name: Newsletter list becomes Members." in lines
    assert gravity.addon_name("gravityformsfoo-bar") == "Foo Bar"


def test_feeds_and_results_need_gravity_forms() -> None:
    info = SiteInfo("Radio", "", "https://radio.example", "7.1", ("wp/v2",), "")
    ctx = SiteContext("Radio", Api(), url="https://radio.example", account=ADMIN, info=info)
    with pytest.raises(WordPressApiError, match="does not list Gravity Forms"):
        load(ctx, "forms:feeds", {}, {})


# --------------------------------------------------------------------------- #
# notes and flags


def test_notes_read_oldest_first_and_a_note_is_signed() -> None:
    api = Api()
    lines = gravity.note_lines(gravity.read_notes(api, 5))
    assert (
        lines[0].startswith("Gravity Forms,")
        and "(notification): Mailchimp: subscribed" in lines[0]
    )
    assert lines[1].startswith("Jeff, ") and lines[1].endswith(": Called back")
    gravity.add_note(api, 5, "Rang her", ADMIN)
    assert api.writes[-1][:3] == (
        "POST",
        "gf/v2/entries/5/notes",
        {
            "value": "Rang her",
            "note_type": "user",
            "entry_id": 5,
            "user_id": 1,
            "user_name": "Jeff",
        },
    )
    assert gravity.note_lines([]) == ["This entry has no notes yet."]


def test_a_flag_is_sent_with_the_whole_fresh_entry() -> None:
    api = Api()
    api.entry["1"] = "Ann Changed"  # someone edited it since the list loaded
    was = gravity.set_entry_flag(api, "gf/v2/entries/5", "is_starred", True)
    assert was is False
    method, route, body, _ = api.writes[-1]
    assert (method, route) == ("PUT", "gf/v2/entries/5")
    assert body["is_starred"] == 1 and body["1"] == "Ann Changed" and body["2"] == "ann@example.com"
    with pytest.raises(ValueError):
        gravity.set_entry_flag(api, "gf/v2/entries/5", "status", True)


def test_admins_hold_gravity_forms_permissions_as_full_access() -> None:
    assert gravity.gravity_can(ADMIN, "gravityforms_edit_entries")
    editor = Account(2, "Ed", "ed", ("editor",), frozenset({"edit_posts"}))
    assert not gravity.gravity_can(editor, "gravityforms_edit_entries")


# --------------------------------------------------------------------------- #
# notifications


def test_notifications_name_who_each_reaches_for_this_entry() -> None:
    found = gravity.entry_notifications(FORM, ENTRY)
    assert [n.line for n in found] == [
        "Admin Notification: to the site's admin email",
        "Thanks: to the address in Email, ann@example.com",
        "Routing: to news@radio.example when Favourite show is gpoll1a, turned off",
    ]
    api = Api()
    assert gravity.resend_notifications(api, 5, ["a1", "b2"]) == ["a1", "b2"]
    assert api.writes[-1] == (
        "POST",
        "gf/v2/entries/5/notifications",
        None,
        {"_notifications": "a1,b2"},
    )


# --------------------------------------------------------------------------- #
# results and field filters


def test_results_are_a_row_per_answer_and_a_sentence_per_question() -> None:
    rows = load(_ctx(Api()), "forms:results", {}, {})
    assert [(r.cell("answer"), r.cell("count"), r.cell("share")) for r in rows] == [
        ("Morning Show", "3", "75 percent"),
        ("Night Owls", "1", "25 percent"),
    ]
    assert rows[0].detail == (
        "Favourite show, 4 responses: Morning Show 3, 75 percent; Night Owls 1, 25 percent."
    )


def test_results_use_the_labels_gravity_forms_sends_and_say_when_still_counting() -> None:
    rows = gravity.result_rows(
        "Radio",
        "Signup",
        {"id": "1", "fields": []},
        {
            "entry_count": 2,
            "status": "incomplete",
            "field_data": {"9": {"a": {"x": 2}}},
            "labels": {"9": {"label": "Likert", "choices": {"a": "Row A", "x": "Agree"}}},
        },
    )
    assert "still counting" in rows[0].detail
    assert rows[1].cell("question") == "Likert" and rows[1].cell("answer") == "Row A, Agree"


def test_field_filters_flatten_groups_and_skip_any_field() -> None:
    found = gravity.field_filters(Api(), "1")
    assert [f.key for f in found] == ["1", "3", "is_starred"]
    assert found[1].values == (("Morning Show", "gpoll1a"),)


# --------------------------------------------------------------------------- #
# test submission


def test_sample_inputs_fill_what_they_can_and_name_what_they_cannot() -> None:
    inputs, skipped = submitting.sample_inputs(FORM)
    assert [(i.name, i.value) for i in inputs] == [
        ("input_1", "QUILL test"),
        ("input_2", "test@example.com"),
        ("input_3", "gpoll1a"),
        ("input_6_1", "news"),
    ]
    assert skipped == ["Photo"]
    assert submitting.parse_inputs("input_1: Ann\ninput_6_1: news\nnot a line\nwebsite: x") == {
        "input_1": "Ann",
        "input_6_1": "news",
    }
    assert submitting.parse_inputs("input_7: https://a.example/b") == {
        "input_7": "https://a.example/b"
    }


def test_validation_messages_survive_a_400_and_a_submission_names_its_entry() -> None:
    api = Api()
    refused = submitting.submit(api, "1", {"input_1": ""}, validate_only=True)
    assert not refused.valid and refused.lines({"1": "Name"}) == ["Name: This field is required."]
    assert api.writes[-1][1] == "gf/v2/forms/1/submissions/validation"
    ok = submitting.submit(api, "1", {"input_1": "Ann"}, validate_only=False)
    assert ok.valid and ok.entry_id == "12" and ok.confirmation == "Thanks!"
    assert api.writes[-1][1] == "gf/v2/forms/1/submissions"


def test_a_refusal_keeps_its_body_for_gravity_forms() -> None:
    error = HTTPError(
        "https://radio.example/wp-json/gf/v2/forms/1/submissions",
        400,
        "Bad Request",
        {},  # type: ignore[arg-type]
        io.BytesIO(b'{"is_valid": false, "validation_messages": {"2": "Bad email"}}'),
    )
    made = _error_from_http(error, method="POST", site_name="Radio")
    assert made.status == 400 and made.body["validation_messages"] == {"2": "Bad email"}


def test_the_practice_site_is_recognised() -> None:
    assert submitting.is_practice_site("http://127.0.0.1:9400/")
    assert submitting.is_practice_site("https://radio.test/")
    assert submitting.is_practice_site("https://x.example", "Practice Site")
    assert not submitting.is_practice_site("https://radio.example/", "Radio")


# --------------------------------------------------------------------------- #
# the window's tables


def test_every_gravity_command_has_a_key_or_a_reason_and_its_help() -> None:
    assert problems(WINDOW_MENU) == []
    on_bar = {row.command_id for _menu, row in all_rows(WINDOW_MENU)}
    for command_id in GRAVITY_ONLY | {command("change_gravity_field_type")}:
        assert command_id in on_bar, command_id
        assert WORDPRESS_KEYS.get(command_id) or KEYLESS.get(command_id), command_id
    for kind in ("gravity_feed", "gravity_result"):
        assert kind in WORDPRESS_ACTIONS.row_types and ROW_HELP.get(kind)
    for key in ("form_feeds", "form_results"):
        assert NODE_HELP[key] and key in {n.key for n in WORDPRESS_TREE.template("site")}
    assert WORDPRESS_TREE.depth("sites") <= 4


def test_the_gravity_routes_have_homes() -> None:
    assert classify("/gf/v2/feeds/(?P<feed_id>[\\d]+)").home == "Sites > site > Forms > Feeds"
    assert classify("/gf/v2/forms/(?P<form_id>[\\d]+)/results").status == "covered"
    assert classify("/gf/v2/entries/(?P<entry_id>[\\d]+)/notifications").status == "covered"
