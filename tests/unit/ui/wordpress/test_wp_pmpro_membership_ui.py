"""Change Membership Level and Cancel Membership in the Workbench window (complete.md WP-C).

The real provider over a fake site with PMPro's abilities and ``pmpro/v1``
routes. Each run reads the member and their subscriptions, previews, and only
then posts; every run asks again. Background work runs inline.
"""

from __future__ import annotations

from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.api import WordPressApiError  # noqa: E402
from quill.core.wordpress.sites import SiteProfile, SiteStore  # noqa: E402
from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, command  # noqa: E402
from quill.core.wordpress.workbench_admin_actions import KEYLESS  # noqa: E402
from quill.core.wordpress.workbench_permissions import Access  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.core.workbench.actions import Tier  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402

SITE = "Community Radio"
RUN = "wp-abilities/v1/abilities/{}/run"


def _ability(name: str, props: tuple[str, ...] = ()) -> dict:
    return {
        "name": name,
        "label": name,
        "meta": {"annotations": {"readonly": True}},
        "input_schema": {"properties": {p: {} for p in props}},
    }


class PmproApi:
    def __init__(self) -> None:
        self.site_name = SITE
        self.posts: list[tuple[str, Any]] = []
        self.memberships = [
            {"id": 2, "name": "Gold", "status": "active", "cardtype": "Visa"},
            {"id": 1, "name": "Bronze", "status": "expired"},
        ]
        self.subscriptions = [
            {"id": 31, "user_id": 4, "status": "active", "gateway": "stripe",
             "membership_level_id": 2, "billing_amount": "10.00", "cycle_number": 1,
             "cycle_period": "Month", "next_payment_date": "2026-12-01"},
        ]  # fmt: skip

    def get(self, route: str, **_p: Any) -> Any:
        if route == "wp/v2/users/me":
            caps = {"edit_users": True, "list_users": True, "manage_options": True}
            return {"id": 1, "name": "Jeff", "roles": ["administrator"], "capabilities": caps}
        if route == "":
            return {"name": SITE, "namespaces": ["wp/v2", "wp-abilities/v1", "pmpro/v1"]}
        if route == "wp/v2/search":
            return [{"id": 9, "title": "Members News"}]
        if route == "pmpro/v1/has_membership_access":
            self.access_asked = dict(_p)
            return [False, [2], ["Gold"]]
        return []

    def iter_collection(self, route: str, *_a: Any, **_k: Any):
        if route == "wp-abilities/v1/abilities":
            yield from (
                _ability("pmpro/member-memberships-get", ("user_id",)),
                _ability("pmpro/levels-query"),
                _ability("pmpro/subscriptions-query", ("user_id",)),
            )

    def request(self, method: str, route: str, **kw: Any) -> Any:
        if method == "OPTIONS":  # no schema: the sheet keeps its own fields
            raise WordPressApiError("No route was found.", status=404)
        assert method == "GET"
        answers = {
            RUN.format("pmpro/member-memberships-get"): {"memberships": self.memberships},
            RUN.format("pmpro/levels-query"): {
                "items": [{"id": 2, "name": "Gold"}, {"id": 3, "name": "Silver"}]
            },
            RUN.format("pmpro/subscriptions-query"): {"items": self.subscriptions},
        }

        class _R:
            payload = answers.get(route)
            total = 0

        return _R()

    def post(self, route: str, body: Any = None, **_p: Any) -> Any:
        self.posts.append((route, body))
        return True


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
    api = PmproApi()
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
def previews(monkeypatch):
    seen: list[dict[str, Any]] = []
    replies: list[bool] = []

    def preview(*_a: Any, **kw: Any) -> bool:
        seen.append(kw)
        return replies.pop(0) if replies else True

    monkeypatch.setattr(wdlg, "ask_preview", preview)
    seen.append({"replies": replies})  # index 0 holds the reply queue
    return seen


_REF = NodeRef("site", "users", SITE)


def _ann() -> WbRow:
    return WbRow("user", SITE, "4", {"name": "Ann"}, "", route="wp/v2/users/4")


def test_cancel_previews_the_gateway_consequence_every_run(bench, previews) -> None:
    api = bench.api
    previews[0]["replies"].append(False)
    bench.provider.do_cancel_membership(_REF, _ann())
    assert api.posts == []  # declined: nothing sent
    bench.provider.do_cancel_membership(_REF, _ann())
    first, second = previews[1], previews[2]
    assert first["lines"] == second["lines"]  # asked again, from a fresh read
    assert first["summary"] == f"Cancel Ann's Gold membership on {SITE}."
    assert first["yes"] == "Cancel Membership"
    assert "cancels subscription 31 at stripe, 10.00 every 1 Month" in first["lines"][1]
    assert "Visa" not in repr(first)
    assert api.posts == [("pmpro/v1/cancel_membership_level", {"user_id": 4, "level_id": 2})]
    assert bench.said[-1] == f"Cancelled Ann's Gold membership on {SITE}."


def test_change_picks_a_level_previews_what_ends_and_posts(bench, previews, monkeypatch) -> None:
    offered: list[list[str]] = []
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **k: offered.append(k["rows"]) or 1)
    bench.provider.do_change_membership(_REF, _ann())
    assert offered == [["Gold (level 2)", "Silver (level 3)"]]
    lines = previews[1]["lines"]
    assert lines[:2] == [
        f"Ann gets Silver on {SITE} now, with no checkout and no payment taken.",
        "Gold ends.",
    ]
    assert "cancels subscription 31" in lines[2]
    assert bench.api.posts == [("pmpro/v1/change_membership_level", {"user_id": 4, "level_id": 3})]
    bench.provider.do_change_membership(_REF, _ann())
    assert len(previews) == 3  # a second run is a second preview


def test_change_to_a_level_they_have_sends_nothing(bench, previews, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **_k: 0)
    bench.provider.do_change_membership(_REF, _ann())
    assert bench.api.posts == [] and "already has Gold" in bench.said[-1]


def test_nobody_without_a_current_level_is_offered_a_cancellation(bench, previews) -> None:
    bench.api.memberships = [{"id": 1, "name": "Bronze", "status": "expired"}]
    bench.provider.do_cancel_membership(_REF, _ann())
    assert len(previews) == 1 and bench.api.posts == []
    assert bench.said[-1] == f"Ann has no current membership on {SITE}."


def test_both_need_full_access_and_have_help_and_a_reason_for_no_chord(bench, previews) -> None:
    provider = bench.provider
    provider.access_store.set("s1", Access.ORGANIZE)
    for verb in ("change_membership", "cancel_membership"):
        assert "Workbench access" in provider.refusal_for(command(verb), _ann())
    provider.do_cancel_membership(_REF, _ann())
    assert len(previews) == 1 and bench.api.posts == []

    offered = {a.command_id: a for a in WORDPRESS_ACTIONS.rows_for("user")}
    assert offered[command("cancel_membership")].tier is Tier.DESTRUCTIVE
    assert offered[command("change_membership")].tier is Tier.WRITE
    for verb in ("change_membership", "cancel_membership"):
        assert offered[command(verb)].help and KEYLESS[command(verb)]


def test_a_members_properties_have_an_access_page_that_checks_a_post(bench, monkeypatch) -> None:
    from quill.ui.workbench_sheet_editor import WorkbenchSheetEditor

    sheet, values, *_rest = bench.provider._load_sheet(_ann())
    assert sheet.pages[-1].title == "Access"
    assert "Check a Post or Page" in values["pmpro_access"]
    shown = WorkbenchSheetEditor(
        bench.frame,
        sheet,
        values,
        title="Ann Properties",
        copy_text=lambda _t: None,
        field_buttons=bench.provider._featured(_ann()),
    )  # read only (no save): the check is a read, so its button is there anyway
    try:
        (button,) = shown.buttons["pmpro_access"]
        assert button.GetLabel() == "&Check a Post or Page..."
        monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "Members News")
        box = shown.controls["pmpro_access"]
        bench.provider.access_buttons(_ann())["pmpro_access"][0].run(box.ChangeValue, "")
        assert bench.api.access_asked == {"user_id": 4, "post_id": 9}
        assert box.GetValue() == (
            f"Ann cannot see Members News on {SITE}. It needs one of these levels: Gold."
        )
    finally:
        shown.dialog.Destroy()


def test_a_site_without_pmpro_routes_gets_no_access_page(bench) -> None:
    from quill.core.wordpress.workbench_sheets import _STATIC

    class _Info:
        def supports(self, _ns: str) -> bool:
            return False

    class _Ctx:
        info = _Info()

    sheet = _STATIC["user"]
    assert bench.provider.with_access_page(_Ctx(), sheet, {}) is sheet
