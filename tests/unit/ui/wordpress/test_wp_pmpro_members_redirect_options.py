"""complete.md 2.3 in the real frame: Members of This Level, Discount Codes' wp-admin row, and
Redirects > Redirect Options as a Properties sheet. Fake sites only; work runs inline."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.workbench_actions import command  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui import workbench_sheet_editor as editor  # noqa: E402
from quill.ui.workbench_frame import NodeRef  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_rest_limits import SiteApi  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_rest_limits import bench as members_bench  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_sweep import RedirectApi, _bench  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import SITE, _go  # noqa: E402

__all__ = ["members_bench"]

_GOLD = WbRow("pmpro", SITE, "2", {"name": "Gold"}, "", subkind="level", raw={"id": 2})
_OPTIONS = NodeRef("site", "redirect_options", SITE)


class _Response:
    def __init__(self, payload: Any, total: int | None) -> None:
        self.payload, self.total = payload, total


class _People(SiteApi):
    """Three people; Ann and Cy hold Gold (level 2) through pmpro/v1."""

    people = [
        {"id": 4, "name": "Ann", "email": "ann@radio.example"},
        {"id": 5, "name": "Bo", "email": "bo@radio.example"},
        {"id": 6, "name": "Cy", "email": "cy@radio.example"},
    ]

    def get(self, route: str, **params: Any) -> Any:
        if route == "pmpro/v1/get_membership_levels_for_user":
            self.reads.append((route, params))
            return [{"id": 2, "name": "Gold"}] if params["user_id"] in (4, 6) else []
        return super().get(route, **params)

    def request(self, method: str, route: str, **kw: Any) -> Any:
        if route == "wp/v2/users":
            return _Response([{"id": 4}], total=len(self.people))
        return super().request(method, route, **kw)

    def iter_collection(self, route: str, params: Any = None, **kw: Any):
        if route == "wp/v2/users" and "email" in str((params or {}).get("_fields", "")):
            yield from self.people
            return
        yield from super().iter_collection(route, params, **kw)


@pytest.fixture
def people(wx_session_app, tmp_path):
    tx.clear_cache()
    frame = _bench(_People(), tmp_path)  # type: ignore[arg-type]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


def _windows(monkeypatch: pytest.MonkeyPatch, yes: bool = True) -> dict[str, list[Any]]:
    seen: dict[str, list[Any]] = {"asked": [], "lists": []}
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **k: seen["asked"].append(k) or yes)

    class _Window:
        def Destroy(self) -> None:
            return None

    monkeypatch.setattr(
        dlg, "show_list_window", lambda *_a, **k: seen["lists"].append(k) or _Window()
    )
    return seen


# -- Members of This Level -------------------------------------------------------------


def test_members_of_a_level_are_counted_listed_and_their_addresses_copied(
    people, monkeypatch
) -> None:
    seen = _windows(monkeypatch)
    copied: list[str] = []
    monkeypatch.setattr(people, "copy_text", copied.append)
    people.provider.do_level_members(NodeRef("site", "membership_levels", SITE), _GOLD)
    asked = seen["asked"][-1]
    assert asked["title"] == "Members of This Level" and asked["yes_label"] == "Find Members"
    assert f"Find every member of Gold on {SITE}?" in asked["message"]
    assert "each of its 3 people" in asked["message"]
    assert people.said[-1] == f"Gold on {SITE} has 2 members."
    assert len([r for r, _p in people.api.reads if r.startswith("pmpro/v1/")]) == 3
    shown = seen["lists"][-1]
    assert shown["rows"] == ["Ann, ann@radio.example", "Cy, cy@radio.example"]
    [copy] = shown["actions"]
    copy.run(None)
    assert copied == ["ann@radio.example; cy@radio.example"]


def test_members_of_a_level_asks_first_and_cancel_sends_nothing(people, monkeypatch) -> None:
    seen = _windows(monkeypatch, yes=False)
    people.provider.do_level_members(NodeRef("site", "membership_levels", SITE), _GOLD)
    assert seen["asked"] and seen["lists"] == []
    assert not any(r == "pmpro/v1/get_membership_levels_for_user" for r, _p in people.api.reads)


def test_choosing_it_again_while_it_runs_stops_it(people, monkeypatch) -> None:
    import threading

    _windows(monkeypatch)
    running = threading.Event()
    people.provider.__dict__["_members_stop"] = running
    people.provider.do_level_members(NodeRef("site", "membership_levels", SITE), _GOLD)
    assert running.is_set()
    assert people.said[-1] == "Stopping the members list; the members found so far are kept."


def test_members_of_this_level_only_works_on_a_level(people, monkeypatch) -> None:
    _windows(monkeypatch)
    order = WbRow("pmpro", SITE, "9", {"code": "A1"}, "", subkind="order")
    people.provider.do_level_members(NodeRef("site", "membership_orders", SITE), order)
    assert people.said[-1] == (
        "Members of This Level works on a row of Memberships > Membership Levels."
    )


# -- Discount Codes without an ability -------------------------------------------------


def test_enter_on_the_discount_codes_note_opens_wp_admin(members_bench) -> None:
    from quill.core.wordpress.workbench_load import SiteContext
    from quill.core.wordpress.workbench_pmpro_rest import load_discount_codes

    ctx = SiteContext(SITE, members_bench.api, url="https://radio.example")
    [note] = load_discount_codes(ctx)
    assert note.kind == "discount_note"
    members_bench.provider.do_open_admin_screen(None, note)
    assert members_bench.commands.host.opened == [
        "https://radio.example/wp-admin/admin.php?page=pmpro-discountcodes"
    ]
    assert members_bench.said[-1].startswith(f"{SITE} lists its discount codes only in wp-admin.")
    assert members_bench.said[-1].endswith(
        f"Opening Memberships > Discount Codes on {SITE} in your browser."
    )


# -- Redirects > Redirect Options ---------------------------------------------------------


class OptionsApi(RedirectApi):
    """Redirection with its options route listed in the index."""

    def __init__(self, *, listed: bool = True) -> None:
        super().__init__()
        self.listed = listed
        self.reads: list[str] = []
        self.settings: dict[str, Any] = {
            "flag_case": True,
            "flag_trailing": False,
            "flag_query": "exact",
            "expire_404": 7,
            "https": False,
            "rest_api": 0,
            "aliases": [],
        }

    def get(self, route: str, **params: Any) -> Any:
        self.reads.append(route)
        if route == "" and self.listed:
            answer = dict(super().get(route, **params))
            answer["routes"] = {**answer.get("routes", {}), "/redirection/v1/setting": {}}
            return answer
        if route == "redirection/v1/setting":
            return {"settings": dict(self.settings), "installed": "5.5.2"}
        return super().get(route, **params)

    def post(self, route: str, body: Any = None, **params: Any) -> Any:
        if route == "redirection/v1/setting":
            self.writes.append(("POST", route, body))
            self.settings.update(body or {})
            return {"settings": dict(self.settings)}
        return super().post(route, body, **params)


@pytest.fixture
def options(wx_session_app, tmp_path, monkeypatch):
    tx.clear_cache()
    sheets: list[Any] = []
    monkeypatch.setattr(editor.WorkbenchSheetEditor, "show", lambda self: sheets.append(self) or 0)
    frame = _bench(OptionsApi(), tmp_path)
    frame.sheets = sheets  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


def test_redirect_options_list_the_known_options_and_count_the_rest(options) -> None:
    _go(options, _OPTIONS)
    rows = options.rows
    assert [(r.cell("option"), r.cell("value")) for r in rows[:2]] == [
        ("Ignore capital letters", "yes"),
        ("Ignore a slash at the end", "no"),
    ]
    assert rows[-1].kind == "admin_screen" and rows[-1].cell("value") == "2 in wp-admin"


def test_the_options_sheet_previews_sends_only_changes_and_undo_puts_them_back(
    options, monkeypatch
) -> None:
    previews: list[Any] = []
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **k: previews.append(k) or True)
    _go(options, _OPTIONS)
    options.provider.do_redirect_options(_OPTIONS, options.rows[0])
    sheet = options.sheets[-1]
    assert [p.title for p in sheet.sheet.pages] == ["Matching", "Logs", "Site"]
    assert sheet.title == f"Redirection Options Properties - {SITE}"
    sheet.state.edited.update({"flag_case": False, "expire_404": "30"})
    assert sheet._on_save(sheet.state) is True
    assert previews[-1]["lines"] == [
        f"Change 2 of Redirection's options on {SITE}.",
        "Ignore capital letters: yes becomes no.",
        "404 log: Keep a week becomes Keep a month.",
    ]
    assert options.api.writes[-1] == (
        "POST",
        "redirection/v1/setting",
        {"flag_case": False, "expire_404": 30},
    )
    assert options.said[-1] == f"Changed 2 of Redirection's options on {SITE}."
    options.provider.history.entries[-1].undo()
    assert options.api.writes[-1][2] == {"flag_case": True, "expire_404": 7}


def test_cancelling_the_preview_sends_nothing(options, monkeypatch) -> None:
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **_k: False)
    _go(options, _OPTIONS)
    options.run(command("redirect_options"))
    sheet = options.sheets[-1]
    sheet.state.edited["https"] = True
    assert sheet._on_save(sheet.state) is False
    assert not [w for w in options.api.writes if w[1] == "redirection/v1/setting"]


def test_a_site_whose_index_lacks_the_route_says_so_and_offers_wp_admin(
    wx_session_app, tmp_path
) -> None:
    tx.clear_cache()
    frame = _bench(OptionsApi(listed=False), tmp_path)
    try:
        _go(frame, _OPTIONS)
        [row] = frame.rows
        assert row.kind == "admin_screen"
        assert row.detail.startswith(
            f"Redirection on {SITE} does not offer its options route (redirection/v1/setting)"
        )
        assert row.link.endswith("wp-admin/tools.php?page=redirection.php&sub=options")
        assert "redirection/v1/setting" not in frame.api.reads
    finally:
        frame.frame.Destroy()
        tx.clear_cache()
