"""complete.md 10B.3 in the real frame: Open in Dashboard, theme Activate, Install on Sites
Missing It, WordPress.org (after consent), PMPro's pmpro/v1, Site Health Information and
Security. Reuses the fake site of ``test_wp_workbench_window``; work runs inline."""

from __future__ import annotations

import io
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import dotorg  # noqa: E402
from quill.core.wordpress import site_taxonomies as tx  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from quill.ui import wordpress_dialogs as dlg  # noqa: E402
from quill.ui import wordpress_workbench_dialogs as wdlg  # noqa: E402
from quill.ui.wordpress_workbench_window import WordPressWorkbenchProvider  # noqa: E402
from quill.ui.workbench_frame import NodeRef, WorkbenchFrame  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_window import (  # noqa: E402
    SITE,
    FakeApi,
    _Commands,
    _go,
    _inline,
)


class _Answer(io.BytesIO):
    def __enter__(self) -> _Answer:
        return self

    def __exit__(self, *_a: Any) -> None:
        self.close()


class SiteApi(FakeApi):
    timeout = 5.0

    def __init__(self) -> None:
        super().__init__()
        self.role = "administrator"
        self.sent: list[Any] = []
        self.reads: list[tuple[str, dict[str, Any]]] = []

    def _opener(self, request: Any, timeout: float = 0, context: Any = None) -> Any:
        self.sent.append(request)
        return _Answer(b"<methodResponse><string>pingback.ping</string></methodResponse>")

    def get(self, route: str, **params: Any) -> Any:
        self.reads.append((route, params))
        if route == "wp-site-health/v1/directory-sizes":
            return {"uploads_size": {"raw": 2048, "size": "2 KB"}}
        if route == "pmpro/v1/has_membership_access":
            return [False, ["2"], ["Gold"]]
        if route == "pmpro/v1/discount_code":
            return {"id": 3, "code": params.get("code"), "uses": 5, "expires": ""}
        if route == "pmpro/v1/get_membership_levels_for_user":
            return [{"id": 2, "name": "Gold"}]
        if route == "wp/v2/settings":
            return {"language": "de_DE"}
        return super().get(route, **params)


@pytest.fixture
def bench(wx_session_app, tmp_path):
    tx.clear_cache()
    said: list[str] = []
    api = SiteApi()
    commands = _Commands(said)
    provider = WordPressWorkbenchProvider(
        commands, announce=said.append, data_dir=tmp_path, api_for=lambda _p: api
    )
    frame = WorkbenchFrame(provider, announce=said.append, run_background=_inline)
    frame.said = said  # type: ignore[attr-defined]
    frame.api = api  # type: ignore[attr-defined]
    frame.commands = commands  # type: ignore[attr-defined]
    yield frame
    frame.frame.Destroy()
    tx.clear_cache()


def _ref() -> NodeRef:
    return NodeRef("site", "plugins", SITE)


def _opened(bench: Any) -> list[str]:
    return bench.commands.host.opened


# -- 1. what REST cannot do ------------------------------------------------------------


def test_open_in_dashboard_says_why_then_opens_the_plugins_screen(bench) -> None:
    row = WbRow("plugin", SITE, "akismet/akismet", {"plugin": "Akismet"}, "")
    bench.provider.do_open_dashboard(_ref(), row)
    assert _opened(bench) == ["https://radio.example/wp-admin/plugins.php"]
    assert "cannot update a plugin" in bench.said[-1]
    assert not bench.api.writes


def test_activate_theme_opens_appearance_themes_for_that_theme(bench) -> None:
    row = WbRow("theme", SITE, "calm", {"theme": "Calm"}, "", status="inactive")
    bench.provider.do_activate_theme(_ref(), row)
    assert _opened(bench) == ["https://radio.example/wp-admin/themes.php?theme=calm"]
    assert "only reads themes" in bench.said[-1]
    active = WbRow("theme", SITE, "tt5", {"theme": "TT5"}, "", status="active")
    bench.provider.do_activate_theme(_ref(), active)
    assert "already the theme" in bench.said[-1]


def test_install_missing_installs_a_plugin_by_slug_after_the_preview(bench, monkeypatch) -> None:
    previews: list[list[str]] = []
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **k: previews.append(k["lines"]) or True)
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: False)  # WordPress.org not asked
    row = WbRow(
        "across",
        "",
        "Akismet",
        {},
        "",
        subkind="plugins",
        raw={
            "missing": [SITE],
            "objects": {"Other": {"plugin": "akismet/akismet", "status": "active"}},
        },
    )
    bench.provider.do_install_missing(None, row)
    assert previews == [
        [f"{SITE}: installs akismet, left inactive", "Not checked on WordPress.org."]
    ]
    assert ("POST", "wp/v2/plugins", {"slug": "akismet", "status": "inactive"}) in bench.api.writes
    assert "installed on 1 of 1 sites" in bench.said[-1]


def test_install_missing_opens_add_new_for_a_theme_and_cancel_sends_nothing(
    bench, monkeypatch
) -> None:
    answers = iter([False, True])
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **_k: next(answers))
    row = WbRow(
        "across",
        "",
        "Calm",
        {},
        "",
        subkind="themes",
        raw={"missing": [SITE], "objects": {"Other": {"stylesheet": "calm"}}},
    )
    bench.provider.do_install_missing(None, row)
    assert _opened(bench) == []
    bench.provider.do_install_missing(None, row)
    assert _opened(bench) == ["https://radio.example/wp-admin/theme-install.php?search=calm"]
    assert not bench.api.writes


# -- 5. WordPress.org, behind its consent --------------------------------------------------


def test_find_theme_asks_consent_first_and_sends_nothing_on_cancel(bench, monkeypatch) -> None:
    asked: list[str] = []
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "calm")
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **k: asked.append(k["message"]) or False)
    monkeypatch.setattr(dotorg, "search_themes", lambda _w: pytest.fail("sent without consent"))
    row = WbRow("theme", SITE, "tt5", {"theme": "TT5"}, "")
    bench.provider.do_find_theme(_ref(), row)
    assert "api.wordpress.org" in asked[0] and "nothing about your sites" in asked[0]
    assert bench.said[-1] == "Nothing was sent to WordPress.org."


def test_find_theme_reads_each_theme_and_opens_add_new_for_the_one_chosen(
    bench, monkeypatch
) -> None:
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "calm")
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    rows_seen: list[list[str]] = []
    monkeypatch.setattr(dlg, "ask_choice", lambda *_a, **k: rows_seen.append(k["rows"]) or 0)
    sent: list[str] = []
    theme = dotorg.DotorgTheme("calm", "Calm", "1.2")
    monkeypatch.setattr(dotorg, "search_themes", lambda w: sent.append(w) or [theme])
    row = WbRow("theme", SITE, "tt5", {"theme": "TT5"}, "")
    bench.provider.do_find_theme(_ref(), row)
    bench.provider.do_find_theme(_ref(), row)  # agreed once for the window
    assert sent == ["calm", "calm"]
    assert rows_seen[0] == ["Calm, version 1.2."]
    assert _opened(bench)[-1] == "https://radio.example/wp-admin/theme-install.php?search=calm"


def test_language_packs_report_each_site_after_consent(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "confirm", lambda *_a, **_k: True)
    reports: list[str] = []
    monkeypatch.setattr(dlg, "show_report", lambda *_a, **k: reports.append(k["text"]))
    facts: list[Any] = []

    def languages(given: Any) -> list[tuple[str, str]]:
        facts.extend(given)
        return [(SITE, f"{SITE} uses German.")]

    monkeypatch.setattr(dotorg, "site_languages", languages)
    row = WbRow("setting", SITE, "language", {"setting": "Language"}, "")
    bench.provider.do_language_packs(NodeRef("site", "settings", SITE), row)
    assert facts[0][:2] == (SITE, "de_DE")
    assert reports == [f"{SITE} uses German."]


# -- 2. PMPro pmpro/v1 ---------------------------------------------------------------------


def _user() -> WbRow:
    return WbRow("user", SITE, "4", {"name": "Ann"}, "", route="wp/v2/users/4")


def test_check_access_asks_pmpro_and_says_which_levels_would_let_them(bench, monkeypatch) -> None:
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "12")
    bench.provider.do_check_access(NodeRef("site", "users", SITE), _user())
    route, params = bench.api.reads[-1]
    assert route == "pmpro/v1/has_membership_access" and params["post_id"] == 12
    assert (
        bench.said[-1] == f"Ann cannot see item 12 on {SITE}. It needs one of these levels: Gold."
    )


def test_show_memberships_falls_back_to_pmpro_v1_without_abilities(bench, monkeypatch) -> None:
    reports: list[str] = []
    monkeypatch.setattr(dlg, "show_report", lambda *_a, **k: reports.append(k["text"]))
    bench.provider.do_pmpro_memberships(NodeRef("site", "users", SITE), _user())
    assert reports == ["Gold: active"]


def test_look_up_and_new_discount_code(bench, monkeypatch) -> None:
    ref = NodeRef("site", "membership_discount_codes", SITE)
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: "fall")
    bench.provider.do_look_up_discount(ref, None)
    assert bench.said[-1].startswith("Discount code fall: 5 uses")
    answers = iter(["spring", "2", "10.00", "5", ""])
    monkeypatch.setattr(dlg, "ask_text", lambda *_a, **_k: next(answers))
    previews: list[list[str]] = []
    monkeypatch.setattr(wdlg, "ask_preview", lambda *_a, **k: previews.append(k["lines"]) or True)
    bench.provider.do_new_discount_code(ref, None)
    assert previews[0][0].startswith("Code SPRING on Community Radio: 5 uses")
    route, body = bench.api.writes[-1][1:]
    assert route == "pmpro/v1/discount_code" and body["levels"][0]["level"] == 2
    assert bench.said[-1] == f"Made the discount code SPRING on {SITE}."


# -- 3 and 4. Site Health Information and Security ------------------------------------------


def test_information_and_security_nodes_load_and_enter_opens_the_info_tab(bench) -> None:
    _go(bench, NodeRef("site", "site_health_info", SITE))
    first = bench.rows[0]
    assert first.kind == "dashboard"
    bench.list.Select(0)
    bench.default_action()
    assert _opened(bench) == ["https://radio.example/wp-admin/site-health.php?tab=debug"]
    _go(bench, NodeRef("site", "site_health_security", SITE))
    assert "XML-RPC is on" in bench.rows[0].detail
    assert "https://radio.example/xmlrpc.php" in [r.full_url for r in bench.api.sent]
