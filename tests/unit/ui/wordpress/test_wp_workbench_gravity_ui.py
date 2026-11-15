"""Gravity Forms in the WordPress Workbench window (complete.md 10B.3), end to end.

The real shared frame and provider over a fake Gravity Forms site whose
answers are the documented ``gf/v2`` shapes; background work runs inline and
every dialog is answered by patching the helper the commands call. Each test
calls the handler a person reaches from a menu or a key.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.api import WordPressApiError  # noqa: E402
from quill.core.wordpress.sites import SiteProfile, SiteStore  # noqa: E402
from quill.core.wordpress.workbench_actions import command  # noqa: E402
from quill.core.wordpress.workbench_permissions import Access  # noqa: E402
from quill.core.workbench.properties import SheetState  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_gravity_entries import GRAVITY_ENTRY_SHEET  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

SITE = "Community Radio"

FORM = {
    "id": "1",
    "title": "Signup",
    "fields": [
        {"id": 1, "type": "text", "label": "Name", "isRequired": True},
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
    ],
    "notifications": {
        "a1": {
            "id": "a1",
            "name": "Admin Notification",
            "event": "form_submission",
            "to": "{admin_email}",
            "toType": "email",
        },
        "b2": {"id": "b2", "name": "Thanks", "to": "2", "toType": "field"},
    },
}


class GravityApi:
    """A site with Gravity Forms: one form, one feed, one entry."""

    def __init__(self) -> None:
        self.site_name = SITE
        self.writes: list[tuple[str, str, Any, dict[str, Any]]] = []
        self.caps: dict[str, bool] = {"edit_posts": True, "gform_full_access": True}
        self.feed = {
            "id": "7",
            "form_id": "1",
            "is_active": "1",
            "meta": {"feedName": "Newsletter list", "mailchimpList": "abc"},
            "addon_slug": "gravityformsmailchimp",
        }
        self.entry = {
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
        self.more: list[dict[str, Any]] = []
        self.searches: list[dict[str, Any]] = []
        self.notes: dict[str, dict[str, Any]] = {
            "1": {"id": "1", "user_name": "Jeff", "date_created": "2026-11-09", "value": "First"}
        }

    def get(self, route: str, **params: Any) -> Any:
        if route == "wp/v2/users/me":
            return {"id": 3, "name": "Jeff", "roles": ["administrator"], "capabilities": self.caps}
        if route == "":
            return {"name": SITE, "namespaces": ["wp/v2", "gf/v2"], "routes": {}}
        if route == "gf/v2/forms":
            return {"1": {"id": "1", "title": "Signup", "entries": "1"}}
        if route == "gf/v2/forms/1":
            return FORM
        if route == "gf/v2/feeds":
            return [dict(self.feed)]
        if route == "gf/v2/feeds/7":
            return dict(self.feed)
        if route == "gf/v2/entries":
            self.searches.append(dict(params))
            return _search(self.entries(), params)
        if route == "gf/v2/entries/5":
            return dict(self.entry)
        if route == "gf/v2/entries/5/notes":
            return dict(self.notes)
        if route == "gf/v2/forms/1/results":
            return {"entry_count": 2, "field_data": {"3": {"gpoll1a": 2, "gpoll1b": 0}}}
        if route == "gf/v2/forms/1/field-filters":
            return [
                {"key": "1", "text": "Name", "operators": ["is", "isnot"]},
                {
                    "key": "3",
                    "text": "Favourite show",
                    "operators": ["is", "isnot"],
                    "values": [
                        {"text": "Morning Show", "value": "gpoll1a"},
                        {"text": "Night Owls", "value": "gpoll1b"},
                    ],
                },
            ]
        return []

    def entries(self) -> list[dict[str, Any]]:
        return [dict(self.entry), *self.more]

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        yield from ()

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        self.writes.append(("POST", route, body, params))
        if route.endswith("/notifications"):
            return params["_notifications"].split(",")
        if route == "gf/v2/entries/5/notes":
            self.notes["2"] = {"id": "2", "user_name": "Jeff", "value": body["value"]}
            return {"id": 2}
        if route.endswith("/submissions/validation"):
            if not body.get("input_1"):
                raise WordPressApiError(
                    "refused",
                    status=400,
                    body={"is_valid": False, "validation_messages": {"1": "This is required."}},
                )
            return {"is_valid": True}
        if route.endswith("/submissions"):
            return {"is_valid": True, "entry_id": 12, "confirmation_message": "Thanks!"}
        return dict(body or {})

    def request(self, method: str, route: str, **kw: Any) -> Any:
        body = kw.get("json_body")
        self.writes.append((method, route, body, {}))
        if method == "PUT" and route == "gf/v2/feeds/7":
            self.feed = dict(body)
        if method == "PUT" and route == "gf/v2/entries/5":
            self.entry = dict(body)

        class _R:
            payload: Any = body
            total = 0

        return _R()

    def delete(self, route: str, **params: Any) -> Any:
        self.writes.append(("DELETE", route, None, params))
        return {}


def _search(entries: list[dict[str, Any]], params: dict[str, Any]) -> dict[str, Any]:
    """What gf/v2/entries answers: the search's field filters, then one page, then the count."""
    search = json.loads(params.get("search", "{}"))
    filters = dict(search.get("field_filters") or {})
    mode = filters.pop("mode", "all")

    def hit(entry: dict[str, Any], f: dict[str, Any]) -> bool:
        have = str(entry.get(f["key"], ""))
        if f["operator"] == "contains":
            return f["value"].casefold() in have.casefold()
        return have != f["value"]  # isnot

    def keep(entry: dict[str, Any]) -> bool:
        results = [hit(entry, f) for f in filters.values()]
        return not results or (any(results) if mode == "any" else all(results))

    found = [e for e in entries if keep(e) and e.get("status") == search.get("status", "active")]
    size = int(params.get("paging[page_size]", 20))
    page = int(params.get("paging[current_page]", 1))
    return {"entries": found[(page - 1) * size : page * size], "total_count": len(found)}


class _Host:
    def __init__(self, said: list[str]) -> None:
        self.said = said
        self.parent = None

    def announce(self, text: str) -> None:
        self.said.append(text)

    def open_in_browser(self, url: str) -> None:
        pass


class _Commands:
    def __init__(self, said: list[str]) -> None:
        self.host = _Host(said)

    def sites(self) -> SiteStore:
        return SiteStore([SiteProfile("s1", SITE, "https://radio.example", "jeff")], "s1")


def _inline(_name: str, work: Any, done: Any, failed: Any) -> None:
    try:
        result = work()
    except Exception as exc:  # noqa: BLE001
        failed(exc)
        return
    done(result)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = GravityApi()
    provider = WordPressWorkbenchProvider(
        _Commands(said), announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


@pytest.fixture
def answers(monkeypatch):
    """Answer every dialog the commands open: previews yes, the rest from a queue."""
    asked: dict[str, list[Any]] = {"previews": [], "reports": [], "texts": [], "choices": []}
    replies: dict[str, list[Any]] = {"text": [], "choice": [], "checks": []}

    def preview(*_a: Any, **kw: Any) -> bool:
        asked["previews"].append(kw)
        return True

    def text(*_a: Any, **kw: Any) -> Any:
        asked["texts"].append(kw)
        return replies["text"].pop(0)

    def choice(*_a: Any, **kw: Any) -> Any:
        asked["choices"].append(kw)
        return replies["choice"].pop(0)

    monkeypatch.setattr(wdlg, "ask_preview", preview)
    monkeypatch.setattr(wdlg, "ask_checks", lambda *_a, **_k: replies["checks"].pop(0))
    monkeypatch.setattr(dlg, "ask_text", text)
    monkeypatch.setattr(dlg, "ask_choice", choice)
    monkeypatch.setattr(dlg, "show_report", lambda *_a, **kw: asked["reports"].append(kw))
    asked["replies"] = replies  # type: ignore[assignment]
    return asked


def _go(frame: WorkbenchFrame, key: str) -> None:
    ref = NodeRef("site", key, SITE)
    assert frame.select(ref), ref
    if frame.current != ref:
        frame._show_node(ref, remember=True)


def _row(frame: WorkbenchFrame, key: str) -> Any:
    _go(frame, key)
    assert frame.rows, key
    frame.list.Select(0)
    return frame.rows[0]


def test_feeds_toggle_rename_and_delete_after_a_preview(bench, answers) -> None:
    provider, api = bench.provider, bench.api
    feed = _row(bench, "form_feeds")
    assert (feed.title, feed.cell("addon"), feed.cell("status")) == (
        "Newsletter list",
        "Mailchimp",
        "Active",
    )
    provider.do_toggle_feed(None, feed)
    assert api.writes[-1][:2] == ("PUT", "gf/v2/feeds/7")
    assert api.feed["is_active"] == 0 and api.feed["meta"]["mailchimpList"] == "abc"
    assert answers["previews"][-1]["yes"] == "Deactivate"
    assert provider.history.undo() and api.feed["is_active"] == "1"

    answers["replies"]["text"].append("Members")
    provider.do_rename_feed(None, bench.rows[0])
    assert api.feed["meta"] == {"feedName": "Members", "mailchimpList": "abc"}

    provider.do_delete_permanently(None, bench.rows[0])
    assert ("DELETE", "gf/v2/feeds/7", None, {}) in api.writes
    assert "Ctrl+Z here makes each again" in answers["previews"][-1]["lines"][-1]
    provider.history.undo()
    assert api.writes[-1][:2] == ("POST", "gf/v2/feeds")
    assert api.writes[-1][2]["addon_slug"] == "gravityformsmailchimp"


def test_a_form_shows_its_feeds_and_results(bench, answers) -> None:
    form = _row(bench, "forms")
    bench.provider.do_show_feeds(None, form)
    assert bench.current == NodeRef("site", "form_feeds", SITE)
    assert bench.filter.GetValue() == 'form:"Signup"'
    bench.provider.do_show_entries(None, form)
    assert bench.filter.GetValue() == 'form:"Signup"' and len(bench.rows) == 1
    bench.provider.do_show_results(None, form)
    assert bench.current == NodeRef("site", "form_results", SITE)
    assert [r.cell("answer") for r in bench.rows] == ["Morning Show", "Night Owls"]
    assert bench.rows[0].detail.startswith("Favourite show, 2 responses: Morning Show 2")


def test_entry_notes_are_read_and_one_is_added(bench, answers) -> None:
    entry = _row(bench, "form_entries")
    answers["replies"]["text"].append("Rang her back")
    bench.provider.do_entry_notes(None, entry)
    assert answers["previews"][-1]["lines"][0].endswith(": First")
    write = bench.api.writes[-1]
    assert write[:2] == ("POST", "gf/v2/entries/5/notes")
    assert write[2]["value"] == "Rang her back" and write[2]["user_name"] == "Jeff"
    assert bench.said[-1] == f"Added a note to Signup entry on {SITE}."
    bench.provider.history.undo()
    assert bench.api.writes[-1][:2] == ("DELETE", "gf/v2/notes/2")


def test_star_and_read_send_the_whole_entry_and_undo(bench, answers) -> None:
    entry = _row(bench, "form_entries")
    bench.provider.do_toggle_starred(None, entry)
    assert bench.api.entry["is_starred"] == 1 and bench.api.entry["1"] == "Ann"
    assert bench.said[-1] == f"Starred 1 entry on {SITE}."
    bench.provider.history.undo()
    assert bench.api.entry["is_starred"] == 0
    bench.provider.do_toggle_read(None, bench.rows[0])
    assert bench.api.entry["is_read"] == 1


def test_resend_notifications_previews_who_gets_them(bench, answers) -> None:
    entry = _row(bench, "form_entries")
    answers["replies"]["checks"].append([0, 1])
    bench.provider.do_resend_notifications(None, entry)
    lines = answers["previews"][-1]["lines"]
    assert lines[:2] == [
        "Admin Notification: to the site's admin email",
        "Thanks: to the address in field 2, ann@example.com",
    ]
    assert bench.api.writes[-1] == (
        "POST",
        "gf/v2/entries/5/notifications",
        None,
        {"_notifications": "a1,b2"},
    )
    assert "sent 2 notifications again" in bench.said[-1]


def test_test_this_form_validates_first_then_submits(bench, answers) -> None:
    form = _row(bench, "forms")
    answers["replies"]["text"].append("input_1: \ninput_3: gpoll1b")
    bench.provider.do_test_form(None, form)
    assert answers["reports"][-1]["text"] == "Name: This is required."
    assert not any(w[1] == "gf/v2/forms/1/submissions" for w in bench.api.writes)

    answers["replies"]["text"].append("input_1: Ann\ninput_3: gpoll1b")
    bench.provider.do_test_form(None, form)
    preview = answers["previews"][-1]
    assert "A practice site is better" in preview["lines"][0]
    assert bench.api.writes[-1] == (
        "POST",
        "gf/v2/forms/1/submissions",
        {"input_1": "Ann", "input_3": "gpoll1b"},
        {},
    )
    assert "entry 12" in bench.said[-1] and "Thanks!" in bench.said[-1]


def test_the_filter_builder_uses_the_forms_own_field_filters(bench, answers) -> None:
    _go(bench, "form_entries")
    answers["replies"]["choice"] += [0, 1, 0, 1]  # Signup, Favourite show, is, Night Owls
    bench.provider.do_filter_builder(None, None)
    assert bench.filter.GetValue() == "form:Signup 3:gpoll1b"
    assert bench.rows == []  # Ann answered gpoll1a


def test_the_filter_goes_to_the_site_as_gravity_forms_search(bench, answers) -> None:
    bench.api.more = [
        {"id": str(100 + i), "form_id": "1", "status": "active", "1": f"Bo {i}", "3": "gpoll1b"}
        for i in range(150)
    ]
    _go(bench, "form_entries")
    answers["replies"]["choice"] += [0, 1, 0, 1]  # Signup, Favourite show, is, Night Owls
    bench.provider.do_filter_builder(None, None)
    sent = bench.api.searches[-1]
    assert json.loads(sent["search"]) == {
        "status": "active",
        "field_filters": {
            "0": {"key": "3", "value": "gpoll1b", "operator": "contains"},
            "mode": "all",
        },
    }
    assert sent["form_ids[0]"] == "1" and sent["paging[page_size]"] == 100
    pages = [s["paging[current_page]"] for s in bench.api.searches[-2:]]
    assert pages == [1, 2]  # 150 matches: read past the first hundred
    assert len(bench.rows) == 150 and all(r.raw["3"] == "gpoll1b" for r in bench.rows)
    status = bench.provider.cut_for(bench.current)
    assert status == "150 responses match the filter on the site, and all are shown."


def test_a_second_condition_asks_all_or_any_and_sends_the_mode(bench, answers) -> None:
    _go(bench, "form_entries")
    answers["replies"]["choice"] += [0, 1, 0, 1]  # Favourite show is Night Owls
    bench.provider.do_filter_builder(None, None)
    assert bench.rows == []  # Ann answered gpoll1a
    answers["replies"]["choice"] += [0, 0, 0, 1]  # Name is ..., then Any
    answers["replies"]["text"].append("Ann")
    bench.provider.do_filter_builder(None, None)
    search = json.loads(bench.api.searches[-1]["search"])
    assert search["field_filters"]["mode"] == "any"
    assert [r.raw["1"] for r in bench.rows] == ["Ann"]  # the site matched Name, not the show
    assert "any of the conditions" in bench.provider.cut_for(bench.current)


def test_only_what_the_site_cannot_answer_stays_on_this_computer() -> None:
    from quill.core.wordpress import workbench_gravity_search as gs
    from quill.core.workbench.filters import Condition, Operator

    conditions = (
        Condition("form", Operator.IS, "Signup"),
        Condition("1.3", Operator.IS_NOT, "Ann"),
        Condition("is_starred", Operator.IS, "1"),
        Condition("status", Operator.IS, "active"),
    )
    with gs.gravity_scope(conditions, "any") as scope:
        assert gs.current_scope() is scope
        assert [c.attribute for c in scope.conditions] == ["1.3", "is_starred"]
        assert [c.attribute for c in scope.local] == ["form", "status"]
        assert scope.form == "Signup"
    assert gs.current_scope() is None
    sent = json.loads(gs.search_json("spam", conditions, "any"))
    assert sent["field_filters"]["0"]["operator"] == "isnot" and sent["status"] == "spam"
    scope.searched, scope.total, scope.shown = True, 40, 12
    assert gs.count_words(scope).startswith("12 of the 40 responses that match any of the")


def test_refusals_name_the_plugin_access_and_permission(bench, answers) -> None:
    provider = bench.provider
    entry = _row(bench, "form_entries")
    qaf = replace(entry, subkind="qaf")
    assert "Gravity Forms command" in provider.refusal_for(command("entry_notes"), qaf)
    provider.access_store.set("s1", Access.READ_ONLY)
    assert "Workbench access" in provider.refusal_for(command("toggle_starred"), entry)
    assert provider.refusal_for(command("entry_notes"), entry) == ""  # reading is allowed
    provider.access_store.set("s1", Access.FULL)
    bench.api.caps = {"edit_posts": True}
    provider._contexts.clear()
    _go(bench, "form_entries")
    said = provider.refusal_for(command("resend_notifications"), bench.rows[0])
    assert "gravityforms edit entries" in said


def test_an_entrys_properties_show_notes_and_save_its_flags(bench, answers) -> None:
    entry = _row(bench, "form_entries")
    sheet, values, _fresh, _names, _meta = bench.provider._load_sheet(entry)
    assert sheet.kind == GRAVITY_ENTRY_SHEET.kind and sheet.title == GRAVITY_ENTRY_SHEET.title
    assert values["is_starred"] is False and "First" in values["notes"]
    state = SheetState(sheet, dict(values))
    state.set("is_read", True)
    assert bench.provider.gravity_entry_save(entry, state) is True
    assert bench.api.entry["is_read"] == 1 and bench.api.entry["2"] == "ann@example.com"
