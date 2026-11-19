"""complete.md 2.3, wx-free: a level's members, every discount code, and Redirection's options.

Every answer here is a recorded shape or a fake; nothing reaches a site.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest

from quill.core.wordpress import workbench_pmpro_members as pm
from quill.core.wordpress import workbench_redirect_options as ro
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import SiteInfo
from quill.core.wordpress.workbench_load import SiteContext
from quill.core.workbench.properties import SheetState

_SITE = "Radio"
_LEVELS_ROUTE = "pmpro/v1/get_membership_levels_for_user"
_RUN = "wp-abilities/v1/abilities/{name}/run"


class _Response:
    def __init__(self, payload: Any, total: int | None = None) -> None:
        self.payload = payload
        self.total = total


class MembersApi:
    """People, each person's levels, and (optionally) PMPro's abilities, by route."""

    site_name = _SITE

    def __init__(
        self,
        people: list[dict[str, Any]],
        levels: dict[int, list[dict[str, Any]]],
        *,
        abilities: list[dict[str, Any]] | None = None,
        refuse: int = 0,
    ) -> None:
        self.people = people
        self.levels = levels
        self.abilities = abilities or []
        self.refuse = refuse
        self.asked: list[tuple[str, dict[str, Any]]] = []

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        self.asked.append((route, dict(params or {})))
        if route == "wp-abilities/v1/abilities":
            yield from self.abilities
        elif route == "wp/v2/users":
            yield from self.people

    def get(self, route: str, **params: Any) -> Any:
        self.asked.append((route, params))
        if route == _LEVELS_ROUTE:
            if self.refuse:
                raise WordPressApiError("No route.", status=self.refuse)
            return self.levels.get(int(params["user_id"]), [])
        return None

    def request(self, method: str, route: str, *, params: Any = None, **_kw: Any) -> _Response:
        self.asked.append((route, dict(params or {})))
        if route == "wp/v2/users":
            return _Response([{"id": 1}], total=len(self.people))
        user = int((params or {}).get("input[user_id]", 0))
        return _Response({"memberships": self.levels.get(user, [])})


_PEOPLE = [
    {"id": 1, "name": "Ann", "email": "ann@radio.example"},
    {"id": 2, "name": "Bo", "email": "bo@radio.example"},
    {"id": 3, "name": "Cy &amp; Di", "email": "ANN@radio.example"},
]
_LEVELS = {
    1: [{"id": 2, "name": "Gold", "startdate": "2026-01-05 10:00:00"}],
    2: [{"id": 3, "name": "Silver"}],
    3: [{"id": 2, "name": "Gold", "status": "active"}],
}


# -- members of a level ---------------------------------------------------------------


def test_members_are_found_from_each_persons_levels_through_pmpro_v1() -> None:
    api = MembersApi(_PEOPLE, _LEVELS)
    found = pm.find_members(api, 2, "Gold", _SITE, people=3)
    assert [m.name for m in found.members] == ["Ann", "Cy & Di"]
    assert found.members[0].line() == "Ann, ann@radio.example, since 2026-01-05"
    assert found.sentence() == "Gold on Radio has 2 members."
    assert found.emails() == "ann@radio.example"  # the same address once
    users = next(p for r, p in api.asked if r == "wp/v2/users")
    assert users["context"] == "edit" and "email" in users["_fields"]


def test_the_ability_is_used_when_the_site_offers_it() -> None:
    ability = {"name": pm.MEMBER_ABILITY, "meta": {"annotations": {"readonly": True}}}
    api = MembersApi(_PEOPLE, _LEVELS, abilities=[ability])
    found = pm.find_members(api, 3, "Silver", _SITE)
    assert [m.name for m in found.members] == ["Bo"]
    assert not any(route == _LEVELS_ROUTE for route, _p in api.asked)
    run = _RUN.format(name=pm.MEMBER_ABILITY)
    assert any(r == run and p.get("input[include_inactive]") is False for r, p in api.asked)


def test_a_cancelled_or_expired_level_is_not_a_member() -> None:
    levels = {1: [{"id": 2, "status": "cancelled"}], 2: [{"id": 2, "status": "expired"}]}
    found = pm.find_members(MembersApi(_PEOPLE[:2], levels), 2, "Gold", _SITE)
    assert found.members == () and found.sentence() == "Gold on Radio has 0 members."


def test_stopping_keeps_what_was_found_and_says_how_far_it_got() -> None:
    stop = threading.Event()
    seen: list[tuple[int, int]] = []

    def progress(checked: int, members: int) -> None:
        seen.append((checked, members))
        stop.set()  # stop after the first person

    found = pm.find_members(
        MembersApi(_PEOPLE, _LEVELS), 2, "Gold", _SITE, people=3, stop=stop, progress=progress
    )
    assert seen == [(1, 1)] and found.stopped and found.checked == 1
    assert found.sentence() == "Stopped after 1 of 3 people on Radio: 1 member of Gold so far."


def test_a_site_without_the_routes_is_refused_after_the_first_person() -> None:
    api = MembersApi(_PEOPLE, _LEVELS, refuse=404)
    with pytest.raises(WordPressApiError, match="neither the Paid Memberships Pro"):
        pm.find_members(api, 2, "Gold", _SITE)
    assert sum(route == _LEVELS_ROUTE for route, _p in api.asked) == 1


def test_one_unreadable_person_is_counted_not_fatal() -> None:
    class Flaky(MembersApi):
        def get(self, route: str, **params: Any) -> Any:
            if route == _LEVELS_ROUTE and params["user_id"] == 2:
                raise WordPressApiError("Busy.", status=500)
            return super().get(route, **params)

    found = pm.find_members(Flaky(_PEOPLE, _LEVELS), 2, "Gold", _SITE)
    assert found.unread == 1 and len(found.members) == 2
    assert found.sentence().endswith("1 person could not be read.")


def test_the_question_counts_people_and_says_plainly_when_it_is_slow() -> None:
    assert pm.count_people(MembersApi(_PEOPLE, _LEVELS)) == 3
    small = pm.ask_words("Gold", _SITE, 3)
    assert "about each of its 3 people, one at a time" in small and "slow" not in small
    big = pm.ask_words("Gold", _SITE, pm.SLOW_FROM)
    assert "On a site this size that is slow" in big
    assert "choosing Members of This Level again stops it" in big
    assert "slow" in pm.ask_words("Gold", _SITE, None)  # a site that does not say


# -- every discount code ------------------------------------------------------------------


class CodesApi:
    """A discount-codes ability that answers 50 a page."""

    site_name = _SITE

    def __init__(self, count: int) -> None:
        self.codes = [{"id": i, "code": f"C{i}", "uses": 0} for i in range(1, count + 1)]
        self.pages: list[int] = []

    def iter_collection(self, route: str, params: Any = None, **_kw: Any):
        yield {"name": "pmpro/discount-codes-query", "meta": {"annotations": {"readonly": True}}}

    def request(self, method: str, route: str, *, params: Any = None, **_kw: Any) -> _Response:
        page, limit = int(params["input[page]"]), int(params["input[limit]"])
        self.pages.append(page)
        items = self.codes[(page - 1) * limit : page * limit]
        return _Response({"items": items, "total": len(self.codes)})


def _ctx(api: Any, *namespaces: str) -> SiteContext:
    info = SiteInfo(_SITE, "", "https://radio.example", "6.9", namespaces, "", ())
    return SiteContext(_SITE, api, url="https://radio.example", info=info)


def test_every_discount_code_is_read_page_by_page_through_the_ability() -> None:
    from quill.core.wordpress.workbench_pmpro_rest import load_discount_codes

    api = CodesApi(120)
    rows = load_discount_codes(_ctx(api, "wp-abilities/v1", "pmpro/v1"))
    assert len(rows) == 120 and api.pages == [1, 2, 3]
    assert rows[-1].cell("code") == "C120"


def test_without_the_ability_the_node_says_wp_admin_and_enter_opens_it() -> None:
    from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS, command
    from quill.core.wordpress.workbench_node_help import row_help
    from quill.core.wordpress.workbench_pmpro_rest import load_discount_codes

    class NoAbility(CodesApi):
        def iter_collection(self, route: str, params: Any = None, **_kw: Any):
            yield from ()

    [note] = load_discount_codes(_ctx(NoAbility(0), "wp-abilities/v1", "pmpro/v1"))
    assert note.kind == "discount_note"
    assert note.detail.startswith("Radio lists its discount codes only in wp-admin.")
    assert "Enter opens Memberships > Discount Codes in your browser." in note.detail
    assert note.link == "https://radio.example/wp-admin/admin.php?page=pmpro-discountcodes"
    menu = [a.command_id for a in WORDPRESS_ACTIONS.rows_for("discount_note")]
    assert menu[:3] == [
        command("open_admin_screen"),
        command("look_up_discount"),
        command("new_discount_code"),
    ]
    assert row_help("discount_note") != row_help("fact")


# -- Redirection's options ------------------------------------------------------------------

_SETTINGS = {
    "flag_case": True,
    "flag_trailing": "1",
    "flag_query": "exact",
    "expire_redirect": 7,
    "ip_logging": 2,
    "https": False,
    "preferred_domain": "",
    "redirect_cache": 1,
    "monitor_types": ["post"],
    "rest_api": 0,
    "flag_regex": "maybe",  # a value QUILL does not understand is not shown
}


def test_the_route_answer_is_read_nested_or_flat_and_a_missing_route_is_none() -> None:
    class Api:
        site_name = _SITE

        def __init__(self, answer: Any) -> None:
            self.answer = answer

        def get(self, route: str, **_p: Any) -> Any:
            assert route == "redirection/v1/setting"
            if isinstance(self.answer, Exception):
                raise self.answer
            return self.answer

    assert ro.read_options(Api({"settings": _SETTINGS, "groups": []})) == _SETTINGS
    assert ro.read_options(Api({"flag_case": False})) == {"flag_case": False}
    missing = WordPressApiError("No route.", status=404, wp_code="rest_no_route")
    assert ro.read_options(Api(missing)) is None
    with pytest.raises(WordPressApiError, match="403"):
        ro.read_options(Api(WordPressApiError("403 Forbidden.", status=403)))
    with pytest.raises(WordPressApiError, match="without Redirection's options"):
        ro.read_options(Api(["nothing"]))
    assert ro.options_offered(()) is None
    assert ro.options_offered(("/redirection/v1/redirect",)) is False
    assert ro.options_offered(("/redirection/v1/setting",)) is True


def test_only_known_options_become_rows_and_the_rest_are_counted() -> None:
    rows = ro.option_rows(_SITE, "https://radio.example", _SETTINGS)
    shown = [r.key for r in rows if r.kind == "redirect_option"]
    assert shown == [
        "flag_case",
        "flag_trailing",
        "flag_query",
        "expire_redirect",
        "ip_logging",
        "https",
        "preferred_domain",
        "redirect_cache",
    ]
    by_key = {r.key: r for r in rows}
    assert by_key["flag_trailing"].cell("value") == "yes"
    assert by_key["expire_redirect"].cell("value") == "Keep a week"
    assert by_key["ip_logging"].cell("value") == "Kept with the end hidden"
    more = rows[-1]
    assert more.kind == "admin_screen" and more.cell("value") == "3 in wp-admin"
    assert more.link.endswith("wp-admin/tools.php?page=redirection.php&sub=options")


def test_the_sheet_has_only_known_options_and_sends_only_what_changed() -> None:
    sheet, values = ro.options_sheet(_SITE, _SETTINGS)
    assert [p.key for p in sheet.pages] == ["general", "logs", "site"]
    assert "flag_regex" not in values and values["expire_redirect"] == "7"
    state = SheetState(sheet, loaded=dict(values))
    state.set("flag_case", False)
    state.set("expire_redirect", "30")
    state.set("preferred_domain", "nowww")
    pending = state.pending()
    assert ro.body_for(pending) == {
        "flag_case": False,
        "expire_redirect": 30,
        "preferred_domain": "nowww",
    }
    assert ro.undo_body(pending) == {
        "flag_case": True,
        "expire_redirect": 7,
        "preferred_domain": "",
    }
    assert ro.options_preview(pending, _SITE) == [
        "Change 3 of Redirection's options on Radio.",
        "Ignore capital letters: yes becomes no.",
        "Redirect log: Keep a week becomes Keep a month.",
        "www in the address: Left as asked becomes Always without www.",
    ]


def test_the_answer_is_checked_option_by_option() -> None:
    body = {"flag_case": False, "expire_redirect": 30}
    assert (
        ro.verified(_SITE, body, {"settings": {"flag_case": False, "expire_redirect": "30"}})
        == "Changed 2 of Redirection's options on Radio."
    )
    kept = ro.verified(_SITE, body, {"settings": {"flag_case": True, "expire_redirect": 30}})
    assert kept == "Redirection on Radio did not take every change. Still as before: " + (
        "Ignore capital letters."
    )
    assert "not checked" in ro.verified(_SITE, body, None)


def test_a_route_with_no_known_option_is_refused_plainly() -> None:
    with pytest.raises(WordPressApiError, match="none of the options QUILL knows"):
        ro.options_sheet(_SITE, {"rest_api": 0})


def test_the_route_is_covered_and_the_node_has_help_and_a_reason_for_no_chord() -> None:
    from quill.core.wordpress.workbench_actions import WORDPRESS_ACTIONS
    from quill.core.wordpress.workbench_admin_actions import KEYLESS as ADMIN_KEYLESS
    from quill.core.wordpress.workbench_coverage import classify
    from quill.core.wordpress.workbench_node_help import node_help, row_help
    from quill.core.wordpress.workbench_sweep_places import KEYLESS
    from quill.core.wordpress.workbench_tree import WORDPRESS_TREE

    assert classify("/redirection/v1/setting").status == "covered"
    assert "Redirect Options" in classify("/redirection/v1/setting").home
    assert "redirect_options" in {n.key for n in WORDPRESS_TREE.template("site")}
    assert node_help("redirect_options") and row_help("redirect_option") != row_help("fact")
    [change] = [a for a in WORDPRESS_ACTIONS.rows_for("redirect_option") if a.default]
    assert change.label == "Change Options..." and KEYLESS[change.command_id]
    members = [a for a in WORDPRESS_ACTIONS.rows_for("pmpro") if a.label.startswith("Members")]
    assert members and ADMIN_KEYLESS[members[0].command_id] and members[0].help
